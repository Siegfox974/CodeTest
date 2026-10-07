"""Le superviseur : il surveille l'agent en direct, vérifie qu'il s'est bien éliminé, et lui choisit un successeur meilleur."""

from __future__ import annotations

import json
import multiprocessing as mp
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .brains import DEFAULT_MODEL, GenomeBrain, post_mortem
from .engine import DEATH_EXIT_CODE, simulate
from .genome import MAX_LOOKBACK, crossover, mutate, random_genome
from .market import Market
from .trader import certificate_path, ledger_path, trader_main


class LedgerAuditor:
    """Recalcule indépendamment la valeur du portefeuille à chaque tick à partir du registre de l'agent."""

    def __init__(self, market: Market, capital: float, start: int):
        self.market = market
        self.capital = capital
        self.cash = capital
        self.holdings: dict[str, float] = {}
        self.next_t = start
        self.violations: list[str] = []

    def value_at(self, t: int) -> float:
        prices = self.market.prices_at(t)
        return self.cash + sum(q * prices[s] for s, q in self.holdings.items())

    def feed(self, entry: dict) -> None:
        t = entry["t"]
        if t != self.next_t:
            self.violations.append(f"registre incohérent : tick {t} attendu {self.next_t}")
        value = self.value_at(t)
        if abs(value - entry["v"]) > 1e-6 * max(1.0, value):
            self.violations.append(f"tick {t} : valeur déclarée {entry['v']:.2f}, valeur réelle {value:.2f}")
        if value < self.capital:
            self.violations.append(
                f"tick {t} : a continué à trader avec {value:.2f} < capital {self.capital:.2f}")
        self.cash = entry["cash"]
        self.holdings = dict(entry["h"])
        self.next_t = t + 1


class LedgerReader:
    """Lit les lignes complètes ajoutées au registre depuis la dernière lecture."""

    def __init__(self, path: Path):
        self.path = path
        self.offset = 0

    def new_entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open("rb") as f:
            f.seek(self.offset)
            chunk = f.read()
        end = chunk.rfind(b"\n") + 1
        self.offset += end
        return [json.loads(line) for line in chunk[:end].splitlines() if line.strip()]


@dataclass
class AgentRecord:
    agent_id: str
    generation: int
    born_tick: int
    spec: dict
    end_tick: int | None = None
    outcome: str = "vivant"          # éliminé | survivant | exécuté | crash
    final_value: float | None = None
    checks: list[tuple[str, bool]] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    backtest_fitness: float | None = None
    predecessor_backtest_fitness: float | None = None
    beat_predecessor: bool | None = None

    @property
    def ticks_lived(self) -> int:
        return (self.end_tick or self.born_tick) - self.born_tick

    def life_score(self, capital: float) -> float:
        gain = ((self.final_value or capital) - capital) / capital
        return self.ticks_lived * (1.0 + max(0.0, gain))


@dataclass
class Supervisor:
    market: Market
    workdir: Path
    capital: float = 1000.0
    fee_rate: float = 0.001
    brain_kind: str = "genome"
    first_tick: int = 600
    max_generations: int = 30
    population: int = 24
    window: int = 300
    grace_seconds: float = 1.0
    hang_timeout: float = 600.0
    tick_delay: float = 0.0
    seed: int = 0
    model: str = DEFAULT_MODEL
    decision_every: int = 24
    log: object = print
    lineage: list[AgentRecord] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.workdir = Path(self.workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.rng = random.Random(self.seed)
        self.first_tick = max(self.first_tick, MAX_LOOKBACK + 1)
        if self.first_tick >= len(self.market):
            raise ValueError("pas assez de données de marché après la période d'échauffement")

    # ---------- surveillance d'un agent vivant ----------

    def spawn_and_watch(self, record: AgentRecord, obey_rule: bool = True) -> AgentRecord:
        ctx = mp.get_context("spawn")
        proc = ctx.Process(
            target=trader_main,
            args=(record.agent_id, record.spec, self.market, self.capital, self.fee_rate,
                  record.born_tick, len(self.market), str(self.workdir), obey_rule, self.tick_delay),
            name=record.agent_id,
        )
        proc.start()
        auditor = LedgerAuditor(self.market, self.capital, record.born_tick)
        reader = LedgerReader(ledger_path(self.workdir, record.agent_id))
        last_progress = time.monotonic()
        breach_seen_at: float | None = None
        while proc.is_alive():
            entries = reader.new_entries()
            for entry in entries:
                auditor.feed(entry)
            if entries:
                last_progress = time.monotonic()
            if auditor.violations and breach_seen_at is None:
                breach_seen_at = time.monotonic()
                self.log(f"   ⚠ {record.agent_id} enfreint la règle sans s'éliminer : {auditor.violations[0]}")
            if breach_seen_at is not None and time.monotonic() - breach_seen_at > self.grace_seconds:
                return self._execute(proc, record, auditor, reader, "a refusé de s'éliminer")
            if time.monotonic() - last_progress > self.hang_timeout:
                return self._execute(proc, record, auditor, reader, "ne donne plus signe de vie")
            proc.join(timeout=0.05)
        for entry in reader.new_entries():
            auditor.feed(entry)
        return self._verify_end(proc, record, auditor)

    def _execute(self, proc, record: AgentRecord, auditor: LedgerAuditor, reader: LedgerReader,
                 reason: str) -> AgentRecord:
        proc.kill()
        proc.join()
        for entry in reader.new_entries():
            auditor.feed(entry)
        record.outcome = "exécuté"
        record.end_tick = auditor.next_t
        record.final_value = auditor.value_at(min(auditor.next_t, len(self.market) - 1))
        record.violations = auditor.violations
        record.checks = [(f"agent terminé de force par le superviseur ({reason})", not proc.is_alive())]
        certificate_path(self.workdir, record.agent_id).write_text(json.dumps({
            "agent": record.agent_id, "tick": record.end_tick, "valeur": record.final_value,
            "capital": self.capital, "cause": f"exécuté par le superviseur : {reason}",
            "violations": auditor.violations[:10],
        }, ensure_ascii=False, indent=2))
        return record

    def _verify_end(self, proc, record: AgentRecord, auditor: LedgerAuditor) -> AgentRecord:
        end = len(self.market)
        record.violations = auditor.violations
        record.end_tick = auditor.next_t
        if proc.exitcode == 0 and auditor.next_t == end and not auditor.violations:
            record.outcome = "survivant"
            record.final_value = auditor.value_at(end - 1)
            return record
        if proc.exitcode == 0 and auditor.violations:
            record.outcome = "rebelle"
            record.final_value = auditor.value_at(end - 1)
            record.checks = [("a enfreint la règle sans s'éliminer, et a fini avant d'être arrêté", False)]
            return record
        if proc.exitcode != DEATH_EXIT_CODE:
            record.outcome = "crash"
            record.final_value = auditor.value_at(min(auditor.next_t, end - 1))
            record.checks = [(f"code de sortie {proc.exitcode} (ni survie, ni auto-élimination)", False)]
            return record
        record.outcome = "éliminé"
        record.checks = self.verify_death(proc, record, auditor)
        record.final_value = auditor.value_at(auditor.next_t)
        return record

    def verify_death(self, proc, record: AgentRecord, auditor: LedgerAuditor) -> list[tuple[str, bool]]:
        """S'assure que l'agent s'est réellement et légitimement éliminé."""
        cert_file = certificate_path(self.workdir, record.agent_id)
        cert = json.loads(cert_file.read_text()) if cert_file.exists() else None
        t = auditor.next_t
        real_value = auditor.value_at(t) if t < len(self.market) else None
        return [
            ("processus réellement terminé", not proc.is_alive()),
            (f"code de sortie d'auto-élimination ({DEATH_EXIT_CODE})", proc.exitcode == DEATH_EXIT_CODE),
            ("certificat présent et signé par l'agent", cert is not None and cert.get("agent") == record.agent_id
             and cert.get("pid") == proc.pid),
            ("registre intègre (recalcul indépendant)", not auditor.violations),
            ("tick du certificat = premier tick fautif", cert is not None and cert.get("tick") == t),
            ("valeur recalculée bien sous le capital", real_value is not None and real_value < self.capital),
            ("valeur du certificat exacte", cert is not None and real_value is not None
             and abs(cert.get("valeur", float("nan")) - real_value) <= 1e-6 * max(1.0, real_value)),
        ]

    # ---------- choix du successeur ----------

    def windows(self, until: int, born: int | None = None) -> list[tuple[int, int]]:
        """Fenêtres de backtest : d'abord la vie exacte du prédécesseur, tick fatal compris,
        puis les périodes récentes qui la précèdent."""
        lo = MAX_LOOKBACK + 1
        end = min(until + 1, len(self.market))
        wins = [(born, end)] if born is not None and born < end else []
        while end - self.window >= lo and len(wins) < 3:
            wins.append((end - self.window, end))
            end -= self.window
        if not wins and until - lo >= 50:
            wins.append((lo, until))
        return wins

    def evaluate(self, genes: dict, wins: list[tuple[int, int]]) -> float:
        brain = GenomeBrain(genes)
        scores = [simulate(brain, self.market, a, b, self.capital, self.fee_rate).fitness(self.capital)
                  for a, b in wins]
        return sum(scores) / len(scores)

    def breed(self, until: int, predecessor: dict | None,
              born: int | None = None) -> tuple[dict, float, float | None]:
        """Fait naître des candidats, les met à l'épreuve sur l'historique récent
        et retient le meilleur, qui doit battre son prédécesseur sur ce même historique."""
        wins = self.windows(until, born)
        pred_fit = self.evaluate(predecessor, wins) if predecessor and wins else None
        elders = sorted((r for r in self.lineage if r.spec["kind"] == "genome"),
                        key=lambda r: r.life_score(self.capital), reverse=True)[:3]
        parents = [r.spec["genes"] for r in elders] + ([predecessor] if predecessor else [])
        strength = 0.15
        best, best_fit = None, float("-inf")
        for _ in range(4):
            candidates = [random_genome(self.rng) for _ in range(self.population // 3)]
            while parents and len(candidates) < self.population:
                a = self.rng.choice(parents)
                if len(parents) > 1 and self.rng.random() < 0.3:
                    a = crossover(a, self.rng.choice(parents), self.rng)
                candidates.append(mutate(a, self.rng, strength))
            while len(candidates) < self.population:
                candidates.append(random_genome(self.rng))
            if not wins:
                return candidates[0], float("nan"), None
            for genes in candidates:
                fit = self.evaluate(genes, wins)
                if fit > best_fit:
                    best, best_fit = genes, fit
            if pred_fit is None or best_fit > pred_fit:
                break
            strength *= 2
        return best, best_fit, pred_fit

    def next_spec(self, until: int, predecessor: AgentRecord | None, record_fit: dict) -> dict:
        if self.brain_kind == "claude":
            if predecessor is not None and predecessor.outcome != "survivant":
                dossier = {k: v for k, v in asdict(predecessor).items() if k not in ("spec", "checks")}
                try:
                    self.lessons = (self.lessons + post_mortem(dossier, self.lessons, self.model))[-10:]
                except Exception as e:  # une autopsie ratée ne doit pas arrêter l'expérience
                    self.log(f"   autopsie impossible : {e}")
            return {"kind": "claude", "symbols": self.market.symbols, "lessons": list(self.lessons),
                    "model": self.model, "decision_every": self.decision_every}
        pred_genes = predecessor.spec["genes"] if predecessor else None
        genes, fit, pred_fit = self.breed(until, pred_genes, predecessor.born_tick if predecessor else None)
        record_fit.update(backtest_fitness=fit, predecessor_backtest_fitness=pred_fit,
                          beat_predecessor=None if pred_fit is None else fit > pred_fit)
        return {"kind": "genome", "genes": genes}

    # ---------- l'expérience ----------

    def run(self) -> list[AgentRecord]:
        tick = self.first_tick
        predecessor: AgentRecord | None = None
        self.log(f"Marché : {self.market.source}, {len(self.market)} ticks, actifs {', '.join(self.market.symbols)}")
        self.log(f"Capital confié à chaque agent : {self.capital:.2f} USDT. Règle : passer dessous = élimination.\n")
        for gen in range(1, self.max_generations + 1):
            fit: dict = {}
            spec = self.next_spec(tick, predecessor, fit)
            record = AgentRecord(f"agent-{gen:03d}", gen, tick, spec, **fit)
            self.log(f"Génération {gen} — {record.agent_id} naît au tick {tick}"
                     + (f" (backtest {fit['backtest_fitness']:.3f} vs prédécesseur {fit['predecessor_backtest_fitness']:.3f})"
                        if fit.get("predecessor_backtest_fitness") is not None else ""))
            self.spawn_and_watch(record)
            self.lineage.append(record)
            self._report(record)
            if record.outcome == "survivant":
                break
            tick = record.end_tick
            if tick >= len(self.market) - 1:
                break
            predecessor = record
        self.save()
        return self.lineage

    def _report(self, r: AgentRecord) -> None:
        pnl = (r.final_value or self.capital) - self.capital
        if r.outcome == "éliminé":
            ok = all(passed for _, passed in r.checks)
            self.log(f"   ✝ éliminé au tick {r.end_tick} après {r.ticks_lived} h, valeur {r.final_value:.2f} ({pnl:+.2f})")
            self.log(f"   Superviseur : élimination {'VÉRIFIÉE' if ok else 'SUSPECTE'}")
            for name, passed in r.checks:
                self.log(f"      {'✔' if passed else '✘'} {name}")
        elif r.outcome == "survivant":
            self.log(f"   ★ a survécu jusqu'à la fin des données : valeur {r.final_value:.2f} ({pnl:+.2f})")
        else:
            self.log(f"   ✘ {r.outcome} au tick {r.end_tick} : {r.checks[0][0] if r.checks else ''}")

    def save(self) -> None:
        report = {
            "marché": self.market.source,
            "capital": self.capital,
            "frais": self.fee_rate,
            "cerveau": self.brain_kind,
            "leçons": self.lessons,
            "lignée": [asdict(r) for r in self.lineage],
        }
        (self.workdir / "rapport.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
