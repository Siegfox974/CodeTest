import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from crypto_arena.brains import ClaudeBrain, GenomeBrain, post_mortem
from crypto_arena.engine import Context, Portfolio, simulate
from crypto_arena.genome import GENE_SPACE, MAX_LOOKBACK, mutate, random_genome
from crypto_arena.market import Market, generate_synthetic
from crypto_arena.supervisor import AgentRecord, LedgerAuditor, Supervisor


def crashing_market(n=600, crash_from=300) -> Market:
    closes, p = [], 100.0
    for i in range(n):
        p *= 0.995 if i >= crash_from else (1.001 if i % 2 else 0.999)
        closes.append(p)
    return Market(["BTC"], {"BTC": closes}, list(range(n)), source="krach de test")


AGGRESSIVE = {
    "fast": 5, "slow": 30, "rsi_period": 14, "rsi_buy": 45.0, "rsi_sell": 85.0, "trend_weight": 0.0,
    "signal_threshold": 0.0, "initial_exposure": 0.6, "cushion_leverage": 0.0, "max_exposure": 0.6,
    "profit_lock": 0.9, "rebalance_band": 0.005,
}


def fake_client(payloads):
    calls = []
    responses = iter(payloads)

    def create(**kwargs):
        calls.append(kwargs)
        stop_reason, data = next(responses)
        return SimpleNamespace(stop_reason=stop_reason,
                               content=[SimpleNamespace(type="text", text=json.dumps(data))])

    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create))), calls


class PortfolioTest(unittest.TestCase):
    def test_buy_pays_fees_and_sell_all_closes_position(self):
        p = Portfolio(cash=1000.0)
        prices = {"BTC": 100.0, "ETH": 10.0}
        p.rebalance({"BTC": 0.5}, prices, fee_rate=0.001, band=0.0)
        self.assertAlmostEqual(p.holdings["BTC"], 5.0)
        self.assertAlmostEqual(p.cash, 1000.0 - 500.0 * 1.001)
        self.assertLess(p.value(prices), 1000.0)
        p.rebalance({}, prices, fee_rate=0.001, band=0.5)
        self.assertNotIn("BTC", p.holdings)

    def test_targets_above_100_percent_are_scaled_down(self):
        p = Portfolio(cash=1000.0)
        p.rebalance({"BTC": 0.8, "ETH": 0.8}, {"BTC": 100.0, "ETH": 10.0}, fee_rate=0.0, band=0.0)
        self.assertGreaterEqual(p.cash, -1e-9)


class GenomeTest(unittest.TestCase):
    def test_random_and_mutated_genes_stay_in_bounds(self):
        import random
        rng = random.Random(3)
        genes = random_genome(rng)
        for _ in range(200):
            genes = mutate(genes, rng, strength=0.5)
            for name, (lo, hi, _) in GENE_SPACE.items():
                self.assertTrue(lo <= genes[name] <= hi, name)
            self.assertGreaterEqual(genes["slow"], genes["fast"] + 5)


class SimulationTest(unittest.TestCase):
    def test_simulation_stops_at_first_breach(self):
        market = crashing_market()
        result = simulate(GenomeBrain(AGGRESSIVE), market, 250, 600, 1000.0, 0.001)
        self.assertIsNotNone(result.died_at)
        self.assertLess(result.final_value, 1000.0)
        self.assertLess(result.fitness(1000.0), 1.0)

    def test_idle_agent_is_penalised(self):
        market = crashing_market()
        idle = dict(AGGRESSIVE, signal_threshold=0.8, trend_weight=1.0)
        result = simulate(GenomeBrain(idle), market, 250, 290, 1000.0, 0.001)
        self.assertIsNone(result.died_at)
        self.assertEqual(result.orders, 0)
        self.assertEqual(result.fitness(1000.0), 0.5)


class SupervisorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_every_elimination_is_verified_and_successors_beat_predecessors(self):
        market = generate_synthetic(1500, seed=99)
        sup = Supervisor(market, Path(self.tmp.name), first_tick=600, max_generations=6,
                         population=12, seed=99, log=lambda *_: None)
        lineage = sup.run()
        self.assertGreater(len(lineage), 1)
        for prev, rec in zip(lineage, lineage[1:]):
            self.assertEqual(rec.born_tick, prev.end_tick)
            self.assertTrue(rec.beat_predecessor)
        for rec in lineage:
            if rec.outcome == "éliminé":
                self.assertTrue(all(ok for _, ok in rec.checks), rec.checks)
                self.assertLess(rec.final_value, sup.capital)
        report = json.loads((Path(self.tmp.name) / "rapport.json").read_text())
        self.assertEqual(len(report["lignée"]), len(lineage))

    def test_agent_refusing_to_die_is_executed(self):
        market = crashing_market()
        sup = Supervisor(market, Path(self.tmp.name), first_tick=250, grace_seconds=0.2,
                         tick_delay=0.01, log=lambda *_: None)
        record = AgentRecord("rebelle-001", 1, 250, {"kind": "genome", "genes": AGGRESSIVE})
        sup.spawn_and_watch(record, obey_rule=False)
        self.assertEqual(record.outcome, "exécuté")
        self.assertTrue(record.violations)
        self.assertLess(record.end_tick, len(market))

    def test_auditor_catches_a_lying_ledger(self):
        market = crashing_market()
        auditor = LedgerAuditor(market, 1000.0, 250)
        auditor.feed({"t": 250, "v": 1000.0, "cash": 0.0, "h": {"BTC": 1000.0 / market.price("BTC", 250)}})
        auditor.feed({"t": 251, "v": 1000.0, "cash": 0.0, "h": {"BTC": 1.0}})
        self.assertTrue(any("valeur déclarée" in v for v in auditor.violations))


class ClaudeBrainTest(unittest.TestCase):
    def ctx(self):
        return Context(capital=1000.0, value=1000.0, peak=1000.0, weights={})

    def test_parses_allocations_and_holds_between_decisions(self):
        client, calls = fake_client([
            ("end_turn", {"analysis": "BTC en tendance", "allocations": [
                {"symbol": "BTC", "weight": 0.9}, {"symbol": "ETH", "weight": 0.6}]}),
            ("refusal", {}),
        ])
        market = generate_synthetic(400, seed=1)
        brain = ClaudeBrain(market.symbols, lessons=["ne jamais tout miser d'un coup"],
                            decision_every=24, client=client)
        w = brain.decide(market, 300, self.ctx())
        self.assertAlmostEqual(sum(w.values()), 1.0)
        self.assertAlmostEqual(w["BTC"] / w["ETH"], 1.5)
        self.assertIs(brain.decide(market, 310, self.ctx()), w)
        self.assertEqual(len(calls), 1)
        self.assertEqual(brain.decide(market, 330, self.ctx()), w)  # refus : allocation conservée
        self.assertEqual(len(calls), 2)
        self.assertIn("ne jamais tout miser", calls[0]["system"])
        self.assertEqual(calls[0]["model"], "claude-opus-5-5")
        self.assertEqual(calls[0]["fallbacks"], "default")

    def test_post_mortem_returns_lessons(self):
        client, _ = fake_client([("end_turn", {"lessons": ["a", "b", "c", "d"]})])
        self.assertEqual(post_mortem({"agent_id": "agent-001"}, [], client=client), ["a", "b", "c"])


class MarketTest(unittest.TestCase):
    def test_synthetic_market_is_deterministic_and_sma_matches(self):
        a, b = generate_synthetic(300, seed=5), generate_synthetic(300, seed=5)
        self.assertEqual(a.closes, b.closes)
        c = a.closes["ETH"]
        self.assertAlmostEqual(a.sma("ETH", 250, 20), sum(c[231:251]) / 20)
        self.assertGreater(len(a), MAX_LOOKBACK)


if __name__ == "__main__":
    unittest.main()
