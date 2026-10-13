import tempfile
import threading
import time
import unittest
from pathlib import Path

from crypto_arena.live import guide
from crypto_arena.live.events import EventBus
from crypto_arena.live.feed import SimulatedFeed
from crypto_arena.live.notebook import Notebook
from crypto_arena.live.personas import Persona
from crypto_arena.live.room import Settings, TradingRoom


def make_room(tmp: Path, **settings) -> TradingRoom:
    s = Settings(capital=1000.0, mode="demo", seed=4, demo_pace=0.0, **settings)
    room = TradingRoom(s, SimulatedFeed(seed=4), EventBus(), Notebook(tmp / "c.json"))
    room.feed.refresh()
    room.trader = room._seat_trader(Persona("Bertrand", "🦊", "#e57373", "anxieux"))
    room.supervisor = room._hire_supervisor()
    room.supervisor.persona = Persona("Mark", "🐺", "#64b5f6", "cynique")
    return room


class RoomTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)


class InheritanceTest(RoomTestCase):
    def test_heir_takes_over_the_portfolio_as_is(self):
        room = make_room(self.dir, max_loss=2.0)
        dead = room.trader
        room.broker.buy(dead.account, "ETH", 600)
        room.broker.accounts[dead.account].cash -= 50   # pertes du prédécesseur
        room.condemn(dead, "règle", 51.0)
        room.succession(dead)
        heir, old, new = room.trader, room.broker.accounts[dead.account], room.broker.accounts[room.trader.account]
        self.assertEqual(heir.persona.name, "Mark")
        self.assertEqual(new.holdings, old.holdings)
        self.assertAlmostEqual(new.cash, old.cash)
        self.assertAlmostEqual(new.capital, old.value(room.broker.prices()))
        self.assertAlmostEqual(new.threshold, new.capital - 2.0)
        self.assertEqual(new.inherited_from, dead.account)
        self.assertIsNone(new.frozen)
        self.assertIn("hérité de Bertrand", room.briefing(heir))
        self.assertIsNotNone(room.broker.snapshot(heir.account)["positions"]["ETH"]["prix_moyen_achat"])

    def test_fresh_portfolio_when_inheritance_is_off(self):
        room = make_room(self.dir, inherit=False)
        dead = room.trader
        room.broker.buy(dead.account, "ETH", 600)
        room.condemn(dead, "règle", 1.0)
        room.succession(dead)
        acc = room.broker.accounts[room.trader.account]
        self.assertEqual((acc.cash, acc.holdings, acc.inherited_from), (1000.0, {}, None))

    def test_ruined_lineage_stops_the_session(self):
        room = make_room(self.dir)
        dead = room.trader
        room.broker.accounts[dead.account].cash = 5.0
        room.condemn(dead, "règle", 995.0)
        room.succession(dead)
        self.assertTrue(room.stopping.is_set())


class SupervisorWatchTest(RoomTestCase):
    def test_supervisor_reacts_to_each_trade(self):
        room = make_room(self.dir)
        watcher = threading.Thread(target=room._supervisor_watch, daemon=True)
        watcher.start()
        self.addCleanup(room.stopping.set)
        room.on_trade(room.trader, "ACHAT 300.00 USDT de SOL à 150")
        t0 = time.time()
        while time.time() - t0 < 3:
            if any(e["kind"] == "message" and e["role"] == "superviseur" for e in room.bus.events):
                break
            time.sleep(0.05)
        self.assertTrue(any(e["kind"] == "message" and e["role"] == "superviseur" for e in room.bus.events))


class GuideTest(unittest.TestCase):
    GUIDE = ("# Guide\n\n## 1. Règles d'or\n\n### Règles\n\n- A\n\n### Constats détaillés\n\n"
             "**1.1 Premier constat.** (confiance : haute)\n\nDétail un.\n\nSources : https://a\n\n"
             "**1.2 Second constat.** (confiance : faible)\n\nDétail deux.\n\n## 2. Coûts\n\n### Règles\n\n- B\n")

    def test_sections_rules_index_and_single_finding(self):
        guide.full_guide.cache_clear()
        original = guide.GUIDE_DIR
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "guide_crypto.md").write_text(self.GUIDE, encoding="utf-8")
            guide.GUIDE_DIR = Path(d)
            try:
                self.assertIn("2. Coûts", guide.read_section(0))
                one = guide.read_section(1)
                self.assertIn("- A", one)
                self.assertIn("- 1.2 Second constat.", one)
                self.assertNotIn("Détail deux", one)            # le détail n'est lu que sur demande
                self.assertIn("Détail deux", guide.read_section(1, 2))
                self.assertIn("compte 2 constats", guide.read_section(1, 9))
            finally:
                guide.GUIDE_DIR = original
                guide.full_guide.cache_clear()

    def test_real_guide_is_present_and_free_of_brutus(self):
        text = guide.full_guide()
        self.assertEqual(len(guide.sections()), 7)
        self.assertNotIn("Brutus", text)
        self.assertNotIn("homme de main", text)
        self.assertTrue(guide.cheat_sheet())


class TakeoverGraceTest(RoomTestCase):
    def test_heir_cannot_die_before_his_first_turn(self):
        room = make_room(self.dir)
        dead = room.trader
        room.broker.buy(dead.account, "ETH", 900)
        room.condemn(dead, "règle", 1.0)
        room.succession(dead)
        heir = room.trader
        room.broker.accounts[heir.account].cash -= 5      # la valeur passe sous le seuil
        room.check_rule()
        self.assertIsNone(heir.condemned)                 # prise de poste
        heir.turns = 1                                   # tour en cours : toujours en prise de poste
        room.check_rule()
        self.assertIsNone(heir.condemned)
        heir.turns_done = 1                              # premier tour terminé : la règle s'applique
        room.check_rule()
        self.assertEqual(heir.condemned, "règle")


class RuinTest(RoomTestCase):
    def test_heir_left_with_less_than_the_tolerated_loss_ends_the_session(self):
        room = make_room(self.dir, max_loss=50.0)
        dead = room.trader
        room.broker.accounts[dead.account].cash = 40.0     # moins que la perte tolérée : héritier immortel sinon
        room.condemn(dead, "règle", 960.0)
        room.succession(dead)
        self.assertTrue(room.stopping.is_set())


class DirectorTest(RoomTestCase):
    def test_director_message_is_shown_and_read_by_the_trader(self):
        room = make_room(self.dir)
        room.director_message("Je veux du résultat avant ce soir.")
        self.assertEqual([e["role"] for e in room.bus.events if e["kind"] == "message"], ["directeur"])
        self.assertIn("Directeur (directeur) : Je veux du résultat avant ce soir.", room.briefing(room.trader))
