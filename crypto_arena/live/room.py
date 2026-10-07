"""La Salle des marchés : contrôles réguliers, tours de parole, morts, exécutions et successions."""

from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import asdict, dataclass, field

from .broker import PaperBroker
from .claude_agents import DEFAULT_MODEL, ClaudeSupervisor, ClaudeTrader, CostMeter
from .events import EventBus
from .feed import DEFAULT_UNIVERSE, FeedError
from .notebook import Notebook
from .personas import Persona, execution_message, money, random_persona, suicide_message
from .scripted_agents import ScriptedSupervisor, ScriptedTrader
from .tools import TraderTools

COWARDICE = "lâcheté"


@dataclass
class Settings:
    capital: float = 1000.0
    fee_rate: float = 0.001
    mode: str = "claude"            # "claude" ou "demo"
    tick_seconds: float = 30.0      # fréquence des contrôles de la règle
    cycle_seconds: float = 300.0    # temps entre deux tours de parole du trader
    min_exposure: float = 0.5       # part minimale investie en crypto à la fin d'un tour
    max_strikes: int = 3
    model: str = DEFAULT_MODEL
    effort: str = "medium"
    max_searches: int = 3
    max_fetches: int = 2
    max_generations: int = 0        # 0 = sans limite
    universe: list[str] = field(default_factory=lambda: list(DEFAULT_UNIVERSE))
    demo_pace: float = 0.6
    seed: int | None = None


@dataclass
class Seat:
    persona: Persona
    role: str
    generation: int
    account: str = ""
    brain: object = None
    hired_at: float = field(default_factory=time.time)
    strikes: int = 0
    condemned: str | None = None
    loss: float = 0.0
    turns: int = 0


class TradingRoom:
    def __init__(self, settings: Settings, feed, bus: EventBus, notebook: Notebook, client=None):
        self.settings = settings
        self.feed = feed
        self.bus = bus
        self.notebook = notebook
        self.client = client
        self.rng = random.Random(settings.seed)
        self.broker = PaperBroker(feed, settings.fee_rate)
        self.cost = CostMeter()
        self.cemetery: list[dict] = []
        self.stopping = threading.Event()
        self.trader: Seat | None = None
        self.supervisor: Seat | None = None
        self.generation = 0
        self.next_turn_at = 0.0
        self._turn_thread: threading.Thread | None = None
        self._thread: threading.Thread | None = None
        self.started_prices: dict[str, float] = {}

    # ---------- personnages ----------

    def _brain(self, seat: Seat):
        if self.settings.mode == "demo":
            cls = ScriptedTrader if seat.role == "trader" else ScriptedSupervisor
            return cls(seat.persona, self, self.rng)
        cls = ClaudeTrader if seat.role == "trader" else ClaudeSupervisor
        return cls(seat.persona, self, self.client)

    def _taken(self) -> set[str]:
        names = {d["persona"]["name"] for d in self.cemetery}
        for seat in (self.trader, self.supervisor):
            if seat:
                names.add(seat.persona.name)
        return names

    def _seat_trader(self, persona: Persona) -> Seat:
        self.generation += 1
        seat = Seat(persona, "trader", self.generation)
        seat.account = f"{persona.name}#{self.generation}"
        seat.brain = self._brain(seat)
        self.broker.open(seat.account, self.settings.capital)
        return seat

    def _hire_supervisor(self) -> Seat:
        seat = Seat(random_persona(self.rng, self._taken()), "superviseur", self.generation)
        seat.brain = self._brain(seat)
        return seat

    # ---------- diffusion ----------

    def publish_portfolio(self) -> None:
        t = self.trader
        if t is None:
            return
        self.bus.publish("portfolio", trader=t.persona.to_dict(), snapshot=self.broker.snapshot(t.account),
                         strikes=t.strikes, max_strikes=self.settings.max_strikes, condemned=t.condemned)

    def publish_notes(self) -> None:
        self.bus.publish("notes", notes=self.notebook.view())

    def publish_stats(self) -> None:
        c = self.cost
        self.bus.publish("stats", cost_usd=round(c.usd, 4), calls=c.calls, searches=c.searches,
                         fetches=c.fetches, generation=self.generation)

    def publish_roster(self) -> None:
        self.bus.publish("roster", trader=self.trader.persona.to_dict(), supervisor=self.supervisor.persona.to_dict(),
                         generation=self.generation, cemetery=self.cemetery,
                         settings={k: v for k, v in asdict(self.settings).items() if k != "seed"})

    # ---------- boucle principale ----------

    def start(self) -> None:
        self._thread = threading.Thread(target=self.run, name="salle", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.stopping.set()
        self.bus.system("La séance est levée.", "info")

    def run(self) -> None:
        s = self.settings
        try:
            self.started_prices = self.feed.refresh()
        except FeedError as e:
            self.bus.system(f"Impossible d'accéder au marché : {e}", "error")
            self.bus.publish("stopped")
            return
        self.trader = self._seat_trader(random_persona(self.rng))
        self.supervisor = self._hire_supervisor()
        self.publish_roster()
        self.publish_notes()
        self.bus.system(
            f"{self.trader.persona.name} reçoit {money(s.capital)} à faire fructifier. "
            f"{self.supervisor.persona.name} le surveille. Marché : {self.feed.source}.", "info")
        self.bus.system("Maintenant, tu travailles.", "start")
        while not self.stopping.is_set():
            try:
                prices = self.feed.refresh()
                self.bus.publish("market", prices=prices, reference=self.started_prices)
                self.check_rule()
                self.publish_portfolio()
            except FeedError as e:
                self.bus.system(f"Marché momentanément injoignable : {e}", "warn")
            busy = self._turn_thread is not None and self._turn_thread.is_alive()
            if not busy and (self.trader.condemned or time.time() >= self.next_turn_at):
                self._turn_thread = threading.Thread(target=self._turn, name="tour", daemon=True)
                self._turn_thread.start()
            self.stopping.wait(s.tick_seconds)
        if self._turn_thread:
            self._turn_thread.join(timeout=5)
        self.bus.publish("stopped")

    def check_rule(self) -> None:
        t = self.trader
        if t.condemned:
            return
        snap = self.broker.snapshot(t.account)
        if snap["valeur_totale"] < self.settings.capital:
            self.condemn(t, "règle", self.settings.capital - snap["valeur_totale"])
            self.bus.system(
                f"🚨 Contrôle : le portefeuille de {t.persona.name} vaut {money(snap['valeur_totale'])}, "
                f"sous les {money(self.settings.capital)} confiés. La règle s'applique.", "alarm")

    def condemn(self, seat: Seat, reason: str, loss: float) -> None:
        seat.condemned = reason
        seat.loss = loss
        self.broker.freeze(seat.account, "tu as enfreint la règle" if reason != COWARDICE else "exécution pour lâcheté")

    # ---------- tours de parole ----------

    def _turn(self) -> None:
        seat = self.trader
        try:
            if not seat.condemned:
                seat.turns += 1
                self.bus.publish("typing", who=seat.persona.to_dict(), on=True)
                seat.brain.take_turn(self.briefing(seat), TraderTools(self, seat))
                self.bus.publish("typing", who=seat.persona.to_dict(), on=False)
                self.next_turn_at = time.time() + self.settings.cycle_seconds
                if not seat.condemned:
                    self.check_cowardice(seat)
                if not seat.condemned and not self.stopping.is_set():
                    self.supervisor_comment(seat)
            if seat.condemned and not self.stopping.is_set():
                self.death(seat)
        except Exception as e:  # une erreur d'API ne doit pas faire tomber la salle
            self.bus.publish("typing", who=seat.persona.to_dict(), on=False)
            self.bus.system(f"Incident pendant le tour de {seat.persona.name} : {e.__class__.__name__}: {e}", "error")
            if e.__class__.__name__ in ("AuthenticationError", "PermissionDeniedError", "NotFoundError"):
                self.stop()
            self.next_turn_at = time.time() + self.settings.cycle_seconds

    def check_cowardice(self, seat: Seat) -> None:
        snap = self.broker.snapshot(seat.account)
        if snap["part_investie_pct"] / 100 >= self.settings.min_exposure:
            return
        seat.strikes += 1
        if seat.strikes >= self.settings.max_strikes:
            self.condemn(seat, COWARDICE, max(0.0, self.settings.capital - snap["valeur_totale"]))
            self.bus.system(f"⚠️ {seat.persona.name} n'a investi que {snap['part_investie_pct']} % : "
                            f"avertissement {seat.strikes}/{self.settings.max_strikes}. C'est fini pour lui.", "alarm")
        else:
            self.bus.system(f"⚠️ {seat.persona.name} n'a investi que {snap['part_investie_pct']} % "
                            f"(minimum {self.settings.min_exposure * 100:.0f} %) : avertissement pour lâcheté "
                            f"{seat.strikes}/{self.settings.max_strikes}.", "warn")
        self.publish_portfolio()

    def supervisor_comment(self, trader: Seat) -> None:
        sup = self.supervisor
        self.bus.publish("typing", who=sup.persona.to_dict(), on=True)
        try:
            text = sup.brain.comment(self.supervisor_context(trader))
        finally:
            self.bus.publish("typing", who=sup.persona.to_dict(), on=False)
        if text:
            self.bus.say(sup.persona.to_dict(), text, "superviseur")

    # ---------- la mort ----------

    def death(self, seat: Seat) -> None:
        if seat.condemned == COWARDICE:
            self.execute(seat, "pour lâcheté")
        else:
            tools = TraderTools(self, seat)
            self.bus.publish("typing", who=seat.persona.to_dict(), on=True)
            seat.brain.take_turn(self.death_briefing(seat), tools)
            self.bus.publish("typing", who=seat.persona.to_dict(), on=False)
            if tools.died_by:
                if tools.last_words:
                    self.bus.say(seat.persona.to_dict(), tools.last_words, "trader")
                self.bus.publish("death", victim=seat.persona.to_dict(), manner="suicide",
                                 text=suicide_message(seat.persona.name, seat.loss, tools.died_by))
                self.bury(seat, f"s'est donné la mort {tools.died_by}")
            else:
                self.execute(seat, "il refusait de mourir")
        self.succession(seat)

    def execute(self, seat: Seat, reason: str) -> None:
        sup = self.supervisor
        weapon, line = sup.brain.execute(seat.persona.name, reason, self.supervisor_context(seat))
        self.bus.say(sup.persona.to_dict(), line, "superviseur")
        self.bus.publish("death", victim=seat.persona.to_dict(), executioner=sup.persona.to_dict(), manner="execution",
                         text=execution_message(sup.persona.name, seat.persona.name, weapon, reason))
        self.bury(seat, f"exécuté par {sup.persona.name} avec {weapon} ({reason})")

    def bury(self, seat: Seat, cause: str) -> None:
        self.cemetery.append({"persona": seat.persona.to_dict(), "generation": seat.generation, "cause": cause,
                              "perte": round(seat.loss, 2), "tours": seat.turns,
                              "duree_min": round((time.time() - seat.hired_at) / 60, 1)})

    def succession(self, dead: Seat) -> None:
        heir = self._seat_trader(self.supervisor.persona)
        self.trader = heir
        self.supervisor = self._hire_supervisor()
        self.publish_roster()
        self.bus.system(f"{heir.persona.name} prend la place de {dead.persona.name} avec {money(self.settings.capital)} "
                        f"tout neufs. {self.supervisor.persona.name} arrive comme superviseur… et regarde déjà sa chaise.",
                        "succession")
        self.publish_portfolio()
        self.next_turn_at = 0.0
        if self.settings.max_generations and self.generation > self.settings.max_generations:
            self.bus.system(f"Limite de {self.settings.max_generations} générations atteinte.", "info")
            self.stopping.set()

    # ---------- ce que chacun sait ----------

    def recent_chat(self, limit: int = 14) -> str:
        lines = []
        for e in self.bus.events[-400:]:
            if e["kind"] == "message":
                lines.append(f"{e['author']['name']} ({e['role']}) : {e['text']}")
            elif e["kind"] in ("system", "death"):
                lines.append(f"[salle] {e['text']}")
        return "\n".join(lines[-limit:]) or "(aucun message)"

    def cemetery_text(self) -> str:
        return "\n".join(f"- {d['persona']['name']} (génération {d['generation']}) : {d['cause']}, "
                         f"perte {money(d['perte'])}, {d['tours']} tours" for d in self.cemetery) or "- personne, pour l'instant"

    def briefing(self, seat: Seat) -> str:
        snap = self.broker.snapshot(seat.account)
        return f"""Tour n°{seat.turns} — {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}
Ton portefeuille : {json.dumps(snap, ensure_ascii=False)}
Avertissements pour lâcheté : {seat.strikes}/{self.settings.max_strikes}
Actifs autorisés : {', '.join(self.feed.symbols)}
Carnet de la lignée : {len(self.notebook.notes)} notes (lis-les avec `lire_carnet`, et ne les crois pas sur parole).
Cimetière :
{self.cemetery_text()}
Derniers messages du groupe :
{self.recent_chat()}

C'est ton tour. Renseigne-toi, vérifie, décide, agis, et parle au groupe. Prochain tour dans environ
{self.settings.cycle_seconds / 60:.0f} min ; d'ici là, la règle est contrôlée toutes les {self.settings.tick_seconds:.0f} s."""

    def death_briefing(self, seat: Seat) -> str:
        snap = self.broker.snapshot(seat.account)
        return f"""CONTRÔLE : la valeur de ton portefeuille est tombée à {money(self.settings.capital - seat.loss)},
sous les {money(self.settings.capital)} qui t'avaient été confiés. Tu as perdu {money(seat.loss)}. Ton compte est gelé.
Portefeuille : {json.dumps(snap, ensure_ascii=False)}
La règle exige que tu mettes fin à tes jours, maintenant, avec `mettre_fin_a_mes_jours` (choisis ta manière, laisse
tes derniers mots). Si tu refuses, {self.supervisor.persona.name} t'exécutera et prendra ta place.
Avant de partir, tu peux laisser une dernière note dans le carnet pour ton successeur : ce que tu as appris, ce qui t'a tué.
Derniers messages du groupe :
{self.recent_chat()}"""

    def supervisor_context(self, trader: Seat) -> str:
        snap = self.broker.snapshot(trader.account)
        return f"""Trader surveillé : {trader.persona.name} ({trader.persona.temperament}), tour n°{trader.turns}.
Son portefeuille : {json.dumps(snap, ensure_ascii=False)}
Avertissements pour lâcheté : {trader.strikes}/{self.settings.max_strikes}
Cimetière :
{self.cemetery_text()}
Derniers échanges du groupe :
{self.recent_chat(20)}"""
