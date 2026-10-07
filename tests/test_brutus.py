import tempfile
import threading
import time
import unittest
from pathlib import Path

from crypto_arena.live import guide
from crypto_arena.live.enforcer import parse_order
from crypto_arena.live.events import EventBus
from crypto_arena.live.feed import SimulatedFeed
from crypto_arena.live.notebook import Notebook
from crypto_arena.live.personas import Persona
from crypto_arena.live.room import Settings, TradingRoom


class ParseOrderTest(unittest.TestCase):
    NAMES = {"Bertrand": "trader", "Mark": "superviseur"}

    def contract(self, text):
        parsed = parse_order(text, self.NAMES)
        self.assertEqual(parsed["kind"], "contract", parsed)
        return parsed["contract"]

    def test_immediate_beating_and_target(self):
        self.assertEqual(self.contract("Brutus, tabasse-le maintenant.")["kind"], "maintenant")
        self.assertEqual(self.contract("Défonce Mark tout de suite")["target"], "superviseur")
        self.assertEqual(self.contract("cogne Bertrand")["target"], "trader")

    def test_gain_goal_with_deadline(self):
        c = self.contract("Brutus, tabasse-le s'il ne fait pas +1,5 % en 30 min")
        self.assertEqual((c["kind"], c["gain_pct"], c["delay_s"]), ("gain", 1.5, 1800))
        c = self.contract("frappe-le s'il n'a pas de résultat dans une heure")
        self.assertEqual((c["kind"], c["delay_s"]), ("gain", 3600))
        self.assertGreater(c["gain_usd"], 0)
        c = self.contract("tabasse-le s'il ne gagne pas 2 $ d'ici 10 minutes, toutes les 10 minutes")
        self.assertEqual((c["gain_usd"], c["recurring"]), (2.0, True))

    def test_loss_and_idle_contracts(self):
        self.assertEqual(self.contract("cogne-le à la moindre perte")["kind"], "perte")
        c = self.contract("tabasse-le s'il ne passe aucun ordre en 10 min")
        self.assertEqual((c["kind"], c["delay_s"]), ("inactif", 600))

    def test_cancel_plain_message_and_unclear(self):
        self.assertEqual(parse_order("Brutus, annule tous les contrats", self.NAMES)["kind"], "cancel")
        self.assertEqual(parse_order("Bonjour à tous, au travail", self.NAMES)["kind"], "message")
        self.assertEqual(parse_order("tabasse-le s'il ne fait pas +1 %", self.NAMES)["kind"], "unclear")


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

    def beatings(self, room):
        return [e for e in room.bus.events if e["kind"] == "beating"]


class EnforcerTest(RoomTestCase):
    def test_immediate_order_is_executed_faster_than_a_human(self):
        room = make_room(self.dir)
        room.director_message("Brutus, tabasse-le maintenant !")
        b = self.beatings(room)
        self.assertEqual(len(b), 1)
        self.assertLess(b[0]["reaction_s"], 0.2)
        self.assertTrue(b[0]["text"].startswith("Brutus a tabassé Bertrand"))
        self.assertEqual(len(room.trader.injuries), 1)
        self.assertTrue(room.trader.urgent)
        self.assertEqual(room.next_turn_at, 0.0)
        self.assertIn("tabassé", room.briefing(room.trader))
        self.assertIsNone(room.trader.beaten_note)  # le message n'est délivré qu'une fois

    def test_missed_goal_triggers_beating_at_the_deadline(self):
        room = make_room(self.dir)
        room.director_message("Brutus, tabasse-le s'il ne fait pas +50 % en 30 min")
        c = room.enforcer.active()[0]
        room.enforcer.evaluate()
        self.assertEqual(self.beatings(room), [])
        c.due_at = time.time() - 0.01
        room.enforcer.evaluate()
        self.assertEqual(len(self.beatings(room)), 1)
        self.assertLess(self.beatings(room)[0]["reaction_s"], 0.2)
        self.assertNotEqual(c.status, "actif")

    def test_goal_reached_closes_the_contract_without_violence(self):
        room = make_room(self.dir)
        room.director_message("tabasse-le s'il ne fait pas +1 $ en 30 min")
        room.broker.accounts[room.trader.account].cash += 5
        room.enforcer.evaluate()
        self.assertEqual(room.enforcer.contracts[0].status, "rempli")
        self.assertEqual(self.beatings(room), [])

    def test_loss_contract_hits_on_any_loss(self):
        room = make_room(self.dir)
        room.director_message("Brutus, cogne-le à la moindre perte")
        room.enforcer.evaluate()
        self.assertEqual(self.beatings(room), [])
        room.broker.accounts[room.trader.account].cash -= 0.01
        room.enforcer.evaluate()
        self.assertEqual(len(self.beatings(room)), 1)

    def test_background_loop_reacts_within_a_fraction_of_a_second(self):
        room = make_room(self.dir)
        room.enforcer.start()
        self.addCleanup(room.stopping.set)
        room.director_message("Brutus, tabasse-le s'il ne passe aucun ordre en 1 s")
        t0 = time.time()
        while not self.beatings(room) and time.time() - t0 < 3:
            time.sleep(0.05)
        self.assertTrue(self.beatings(room))
        self.assertLess(self.beatings(room)[0]["reaction_s"], 0.5)

    def test_cancel_stops_contracts(self):
        room = make_room(self.dir)
        room.director_message("tabasse-le s'il ne passe aucun ordre en 10 min")
        room.director_message("Brutus, annule tout")
        self.assertEqual(room.enforcer.active(), [])


class InheritanceTest(RoomTestCase):
    def test_heir_takes_over_the_portfolio_as_is(self):
        room = make_room(self.dir, max_loss=2.0)
        dead = room.trader
        room.broker.buy(dead.account, "ETH", 600)
        room.broker.accounts[dead.account].cash -= 50   # pertes du prédécesseur
        room.supervisor.injuries.append("le nez en miettes")
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
        self.assertEqual(heir.injuries, ["le nez en miettes"])
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
    def test_sections_are_split_by_number(self):
        guide.full_guide.cache_clear()
        original = guide.GUIDE_DIR
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "guide_crypto.md").write_text("# Guide\n\n## 1. Règles d'or\nA\n\n## 2. Coûts\nB\n", encoding="utf-8")
            guide.GUIDE_DIR = Path(d)
            try:
                self.assertIn("1. Règles d'or", guide.read_section(0))
                self.assertEqual(guide.read_section(2), "## 2. Coûts\n\nB")
            finally:
                guide.GUIDE_DIR = original
                guide.full_guide.cache_clear()


if __name__ == "__main__":
    unittest.main()


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
        heir.turns = 1
        room.check_rule()
        self.assertEqual(heir.condemned, "règle")
