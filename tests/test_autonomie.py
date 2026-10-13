import tempfile
import time
import unittest
from pathlib import Path

from crypto_arena.live.events import EventBus
from crypto_arena.live.feed import SimulatedFeed
from crypto_arena.live.notebook import Notebook
from crypto_arena.live.personas import Persona
from crypto_arena.live.room import Settings, TradingRoom
from crypto_arena.live.soul import MAX_EDITS_PER_TURN, Soul
from crypto_arena.live.tools import TraderTools


def make_room(tmp: Path, **settings) -> TradingRoom:
    s = Settings(**{"capital": 100.0, "max_loss": 1.0, "mode": "demo", "seed": 5, "demo_pace": 0.0,
                    "thought_price_turn": 0.05, "thought_price_search": 0.01, **settings})
    room = TradingRoom(s, SimulatedFeed(seed=5), EventBus(), Notebook(tmp / "c.json"))
    room.feed.refresh()
    room.souls_dir = tmp / "ames"
    room.trader = room._seat_trader(Persona("Bertrand", "🦊", "#e57373", "anxieux"))
    room.supervisor = room._hire_supervisor()
    return room


class RoomCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)


class SoulTest(RoomCase):
    def test_agent_rewrites_its_soul_with_history_and_limits(self):
        room = make_room(self.dir)
        tools = TraderTools(room, room.trader)
        result, err = tools.call("reecrire_mon_ame", {"rubrique": "Stratégie", "texte": "Seulement BTC, petites tailles.",
                                                      "raison": "PEPE m'a coûté cher"})
        self.assertFalse(err)
        soul = room.trader.soul
        self.assertEqual(soul.sections["Stratégie"], "Seulement BTC, petites tailles.")
        self.assertEqual(soul.versions[-1]["raison"], "PEPE m'a coûté cher")
        self.assertIn("Seulement BTC", room.briefing(room.trader))
        self.assertTrue((self.dir / "ames" / "SOUL-Bertrand-1.md").exists())
        _, err = tools.call("reecrire_mon_ame", {"rubrique": "Valeurs", "texte": "x" * 700, "raison": ""})
        self.assertTrue(err)                                       # trop long
        _, err = tools.call("reecrire_mon_ame", {"rubrique": "Âme", "texte": "y", "raison": ""})
        self.assertTrue(err)                                       # rubrique inconnue
        for i in range(MAX_EDITS_PER_TURN):
            tools.call("reecrire_mon_ame", {"rubrique": "Valeurs", "texte": f"v{i}", "raison": ""})
        self.assertEqual(soul.sections["Valeurs"], f"v{MAX_EDITS_PER_TURN - 2}")   # 3 par réveil au plus

    def test_soul_is_archived_at_death_readable_but_frozen_and_supervisor_keeps_his(self):
        room = make_room(self.dir)
        dead, sup = room.trader, room.supervisor
        sup_soul = sup.soul
        room.condemn(dead, "règle", 1.5)
        room.bury(dead, "test")
        room.succession(dead)
        self.assertIs(room.trader.soul, sup_soul)                  # le superviseur promu garde son âme
        with self.assertRaises(ValueError):
            room.archived_souls["Bertrand"].rewrite("Valeurs", "trop tard", "")
        result, err = TraderTools(room, room.trader).call("lire_ame", {"nom": "bertrand"})
        self.assertFalse(err)
        self.assertIn("# Âme de Bertrand", result["ame"])
        self.assertIsNotNone(room.cemetery[-1]["ame"])


class ThoughtCostTest(RoomCase):
    def test_thinking_is_paid_from_the_portfolio_and_can_force_a_sale(self):
        room = make_room(self.dir)
        t = room.trader
        room.broker.buy(t.account, "BTC", room.broker.accounts[t.account].cash / 1.001)   # tout investi
        before = room.broker.value(t.account)
        room.charge_thought(t, 0.05, "réveil")
        self.assertAlmostEqual(room.broker.value(t.account), before - 0.05, delta=0.001)
        self.assertGreaterEqual(room.broker.accounts[t.account].cash, -1e-9)          # vente forcée pour payer
        self.assertTrue(any("vente forcée" in e.get("text", "") for e in room.bus.events))
        self.assertAlmostEqual(t.thought_spent, 0.05)

    def test_tiers_follow_how_many_wakes_the_cushion_can_pay(self):
        room = make_room(self.dir)
        t = room.trader
        self.assertEqual(room.tier_of(t), "normal")                 # 1 $ de coussin = 20 réveils à 0,05 $
        room.charge_thought(t, 0.6, "test")                          # reste 0,40 $ = 8 réveils
        room.update_tier(t)
        self.assertEqual(t.tier, "économie")
        self.assertEqual(room.tier_params(t)["model"], "claude-sonnet-5-5")
        room.charge_thought(t, 0.3, "test")                          # reste 0,10 $ = 2 réveils
        room.update_tier(t)
        self.assertEqual(t.tier, "critique")
        self.assertEqual(room.tier_params(t)["searches"], 0)
        room.broker.accounts[t.account].cash += 5                    # il gagne : il remonte
        room.update_tier(t)
        self.assertEqual(t.tier, "normal")
        self.assertTrue(any(e["kind"] == "system" and "🔺" in e["text"] for e in room.bus.events))


class SleepTest(RoomCase):
    def test_agent_chooses_its_sleep_within_tier_bounds_and_heartbeat_wakes_it(self):
        room = make_room(self.dir, cycle_seconds=300)
        t = room.trader
        tools = TraderTools(room, t)
        result, _ = tools.call("dormir", {"minutes": 60})
        self.assertEqual(result["dodo_minutes"], 20.0)               # palier normal : 0,5 à 4 cycles de 5 min
        room.schedule_wake(t)
        self.assertAlmostEqual(room.next_turn_at - time.time(), 20 * 60, delta=2)
        room.broker.accounts[t.account].cash -= 0.7                   # la marge fond pendant son sommeil
        room.heartbeat()
        self.assertEqual(room.next_turn_at, 0.0)
        self.assertTrue(any("Réveil d'urgence" in e.get("text", "") for e in room.bus.events))

    def test_demo_session_with_thought_costs_runs(self):
        s = Settings(capital=200.0, max_loss=2.0, mode="demo", tick_seconds=0.01, cycle_seconds=0.02, demo_pace=0.0,
                     max_generations=2, seed=9, duration_seconds=3)
        room = TradingRoom(s, SimulatedFeed(seed=9, volatility=0.003), EventBus(), Notebook(self.dir / "c.json"))
        room.run()
        kinds = [e["kind"] for e in room.bus.events]
        self.assertIn("soul", kinds)
        self.assertEqual(kinds[-1], "stopped")
        self.assertTrue(any(e["kind"] == "portfolio" and e["thought_spent"] > 0 for e in room.bus.events))


if __name__ == "__main__":
    unittest.main()


class HysteresisTest(RoomCase):
    def test_tier_does_not_flip_back_up_on_a_tiny_gain(self):
        room = make_room(self.dir)
        t = room.trader
        room.charge_thought(t, 0.55, "test")          # 0,45 $ = 9 réveils : économie
        room.update_tier(t)
        self.assertEqual(t.tier, "économie")
        room.broker.accounts[t.account].cash += 0.06    # 10,2 réveils : juste au-dessus du seuil
        room.update_tier(t)
        self.assertEqual(t.tier, "économie")           # pas de remontée sans 25 % de marge
        room.broker.accounts[t.account].cash += 0.2     # 14,2 réveils
        room.update_tier(t)
        self.assertEqual(t.tier, "normal")
