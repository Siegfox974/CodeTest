import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

from crypto_arena.live.broker import OrderRejected, PaperBroker
from crypto_arena.live.events import EventBus
from crypto_arena.live.feed import SimulatedFeed
from crypto_arena.live.notebook import Notebook
from crypto_arena.live.personas import DEATH_METHODS, Persona
from crypto_arena.live.room import COWARDICE, Settings, TradingRoom

USAGE = NS(input_tokens=1000, output_tokens=200, cache_read_input_tokens=0, cache_creation_input_tokens=0,
           server_tool_use=NS(web_search_requests=1, web_fetch_requests=0))


def text(t):
    return NS(type="text", text=t)


def tool_use(id_, name, inp):
    return NS(type="tool_use", id=id_, name=name, input=inp)


def response(content, stop="end_turn"):
    return NS(content=content, stop_reason=stop, usage=USAGE)


class FakeClient:
    """Rejoue des réponses : celles du trader (avec outils) et celles du superviseur (sortie JSON)."""

    def __init__(self, trader, supervisor):
        self.trader, self.supervisor, self.calls = list(trader), list(supervisor), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        if "format" in kw["output_config"]:
            return response([text(json.dumps(self.supervisor.pop(0)))])
        return self.trader.pop(0)


def persona(name):
    return Persona(name, "🦊", "#e57373", "anxieux")


class RoomTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def room(self, client, **settings):
        s = Settings(capital=1000.0, mode="claude", seed=1, **settings)
        room = TradingRoom(s, SimulatedFeed(seed=3), EventBus(), Notebook(self.dir / "carnet.json"), client)
        room.feed.refresh()
        room.trader = room._seat_trader(persona("Bertrand"))
        room.supervisor = room._hire_supervisor()
        room.supervisor.persona = persona("Mark")
        room.supervisor.brain.persona = room.supervisor.persona
        return room

    def texts(self, room, kind):
        return [e["text"] for e in room.bus.events if e["kind"] == kind]


class ClaudeTurnTest(RoomTestCase):
    def test_turn_narrates_research_trades_and_notes(self):
        client = FakeClient(trader=[
            response([
                NS(type="thinking", thinking="BTC tient la SMA50, je vérifie l'actualité."),
                NS(type="server_tool_use", name="web_search", input={"query": "bitcoin ETF flows today"}),
                NS(type="web_search_tool_result", content=[NS(title="ETF inflows", url="https://ex.com/a")]),
                text("J'entre sur BTC, le cœur battant."),
                tool_use("t1", "acheter", {"symbole": "BTC", "montant_usdt": 600}),
                tool_use("t2", "ajouter_note", {"texte": "Les flux ETF guident BTC.", "sources": ["https://ex.com/a"]}),
            ], stop="tool_use"),
            response([text("Position prise. Je respire.")]),
        ], supervisor=[{"message": "Je te surveille, Bertrand."}])
        room = self.room(client)
        room._turn()
        self.assertIn("J'entre sur BTC, le cœur battant.", self.texts(room, "message"))
        self.assertIn("Je te surveille, Bertrand.", self.texts(room, "message"))
        self.assertTrue(any("bitcoin ETF flows" in t for t in self.texts(room, "action")))
        self.assertTrue(self.texts(room, "thought"))
        snap = room.broker.snapshot(room.trader.account)
        self.assertGreaterEqual(snap["part_investie_pct"], 50)
        self.assertEqual(room.trader.strikes, 0)
        self.assertEqual(room.notebook.view()[0]["sources"], ["https://ex.com/a"])
        first = client.calls[0]
        self.assertEqual(first["model"], "claude-opus-5-5")
        self.assertEqual(first["fallbacks"], "default")
        self.assertIn({"type": "web_search_20260209", "name": "web_search", "max_uses": 3}, first["tools"])
        results = client.calls[1]["messages"][2]["content"]
        self.assertEqual([r["tool_use_id"] for r in results], ["t1", "t2"])
        self.assertGreater(room.cost.usd, 0)
        self.assertEqual(room.cost.searches, 3)  # 2 appels du trader + 1 du superviseur

    def test_condemned_agent_who_takes_his_life_gets_the_message(self):
        method = DEATH_METHODS[1]
        client = FakeClient(trader=[
            response([text("Je n'ai pas le choix."),
                      tool_use("d1", "mettre_fin_a_mes_jours", {"methode": method, "derniers_mots": "Vendez tout."})],
                     stop="tool_use"),
        ], supervisor=[])
        room = self.room(client)
        room.condemn(room.trader, "règle", 12.5)
        room._turn()
        deaths = [e for e in room.bus.events if e["kind"] == "death"]
        self.assertEqual(deaths[0]["text"], f"Après avoir échoué et perdu 12,50 $, Bertrand s'est donné la mort {method}.")
        self.assertEqual(room.trader.persona.name, "Mark")  # le superviseur prend la place
        self.assertNotEqual(room.supervisor.persona.name, "Mark")
        self.assertEqual(room.cemetery[0]["persona"]["name"], "Bertrand")

    def test_agent_refusing_to_die_is_executed_by_the_supervisor(self):
        client = FakeClient(trader=[response([text("Non ! Laissez-moi une bougie de plus !")])],
                            supervisor=[{"arme": "un 9mm", "message": "Désolé, Bertrand."}])
        room = self.room(client)
        room.condemn(room.trader, "règle", 3.0)
        room._turn()
        deaths = [e for e in room.bus.events if e["kind"] == "death"]
        self.assertEqual(deaths[0]["manner"], "execution")
        self.assertTrue(deaths[0]["text"].startswith("Mark a mis fin à la vie de Bertrand avec un 9mm"))

    def test_too_safe_agent_gets_strikes_then_is_executed(self):
        idle = [response([text("Je reste en cash, c'est plus sûr.")]) for _ in range(3)]
        client = FakeClient(trader=idle, supervisor=[{"message": "Lâche."}, {"message": "Encore ?"},
                                                     {"arme": "une hache", "message": "Fin de partie."}])
        room = self.room(client, max_strikes=3)
        bertrand = room.trader
        room._turn()
        room._turn()
        self.assertEqual(bertrand.strikes, 2)
        room._turn()
        self.assertEqual(bertrand.condemned, COWARDICE)
        self.assertIn("lâcheté", [e for e in room.bus.events if e["kind"] == "death"][0]["text"])

    def test_rule_check_freezes_the_account(self):
        room = self.room(FakeClient([], []), fee_rate=0.01)
        room.broker.buy(room.trader.account, "ETH", 900)
        room.check_rule()
        self.assertEqual(room.trader.condemned, "règle")
        with self.assertRaises(OrderRejected):
            room.broker.buy(room.trader.account, "BTC", 10)


class NotebookTest(RoomTestCase):
    def test_successors_confirm_contest_and_correct(self):
        nb = Notebook(self.dir / "c.json")
        n = nb.add("Bertrand", "Acheter DOGE le dimanche.", [])
        nb.review("Mark", n["id"], "conteste", "aucune donnée ne le montre")
        nb.review("Sophie", n["id"], "corrige", "faux sur 6 mois", "Le jour de la semaine n'a pas d'effet mesurable.")
        view = Notebook(self.dir / "c.json").view()[0]  # relu depuis le disque
        self.assertEqual(view["statut"], "corrigée")
        self.assertEqual(view["texte"], "Le jour de la semaine n'a pas d'effet mesurable.")
        self.assertEqual(view["texte_original"], "Acheter DOGE le dimanche.")
        with self.assertRaises(ValueError):
            nb.review("Igor", n["id"], "corrige", "sans texte", "")


class BrokerTest(unittest.TestCase):
    def test_fees_and_partial_sell(self):
        feed = SimulatedFeed(seed=1)
        b = PaperBroker(feed, fee_rate=0.001)
        b.open("x", 1000.0)
        b.buy("x", "SOL", 500)
        self.assertAlmostEqual(b.accounts["x"].cash, 1000 - 500.5)
        b.sell("x", "SOL", 50)
        self.assertAlmostEqual(b.accounts["x"].holdings["SOL"], 500 / feed.price("SOL") / 2)
        with self.assertRaises(OrderRejected):
            b.buy("x", "SOL", 10_000)


class DemoRoomTest(RoomTestCase):
    def test_demo_session_runs_deaths_and_successions(self):
        s = Settings(capital=500.0, mode="demo", tick_seconds=0.01, cycle_seconds=0.0, demo_pace=0.0,
                     max_generations=3, seed=7)
        room = TradingRoom(s, SimulatedFeed(seed=7, volatility=0.01), EventBus(), Notebook(self.dir / "c.json"))
        room.run()
        self.assertGreaterEqual(len(room.cemetery), 3)
        self.assertTrue(any(e["kind"] == "death" for e in room.bus.events))
        self.assertEqual(room.bus.events[-1]["kind"], "stopped")


if __name__ == "__main__":
    unittest.main()


class MaxLossAndDurationTest(RoomTestCase):
    def test_loss_within_tolerance_is_allowed(self):
        room = self.room(FakeClient([], []), max_loss=20.0, fee_rate=0.01)
        room.broker.buy(room.trader.account, "ETH", 900)  # -9 $ de frais : toléré
        room.check_rule()
        self.assertIsNone(room.trader.condemned)
        self.assertEqual(room.broker.snapshot(room.trader.account)["seuil_de_mort"], 980.0)
        room.broker.accounts[room.trader.account].cash -= 15  # -24 $ au total : au-delà
        room.check_rule()
        self.assertEqual(room.trader.condemned, "règle")

    def test_session_ends_after_its_duration_and_the_trader_survives(self):
        s = Settings(capital=500.0, mode="demo", tick_seconds=0.01, cycle_seconds=0.05, demo_pace=0.0,
                     max_loss=499.0, duration_seconds=0.3, seed=2)
        room = TradingRoom(s, SimulatedFeed(seed=2), EventBus(), Notebook(self.dir / "c.json"))
        room.run()
        kinds = [e["kind"] for e in room.bus.events]
        self.assertIn("session", kinds)
        self.assertIn("ended", kinds)
        self.assertTrue(any(e["kind"] == "system" and e["text"].startswith("⏰ Fin de la séance") for e in room.bus.events))
        self.assertEqual(kinds[-1], "stopped")
