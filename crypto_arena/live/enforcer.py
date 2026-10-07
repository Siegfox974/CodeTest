"""Brutus, l'homme de main du directeur : il traduit les ordres du directeur en contrats et frappe en quelques
centièmes de seconde quand un contrat n'est pas tenu. La surveillance est du code, pas un LLM : c'est ce qui le rend
plus rapide qu'un humain. Claude n'intervient que pour comprendre un ordre trop tordu pour l'analyseur local."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import asdict, dataclass, field

from .personas import BEATINGS, ENFORCER, ENFORCER_LINES, INJURIES, beating_message

VIOLENCE = re.compile(r"\b(tabass\w*|frapp\w*|cogn\w*|d[ée]fonc\w*|d[ée]moli\w*|bastonn\w*|tap(?:e|er|ez)\b|"
                      r"corrig(?:e|er|ez)\b|passe[rz]?\s+(?:le\s+|la\s+)?[àa]\s+tabac|[ée]clate\w*|"
                      r"cass(?:e|er|ez)\s+(?:lui\s+)?(?:la\s+gueule|les\s+(?:dents|jambes|genoux|côtes)))")
CANCEL = re.compile(r"\b(annul\w*|stop|arr[êe]t\w*|laisse[sz]?[- ]l[ea]|l[âa]che[sz]?[- ]l[ea]|fiche[sz]?[- ]lui la paix)\b")
CONDITION = re.compile(r"\b(si|s'il|s'ils|sinon|sauf|à moins|a moins|dès|des qu|à la moindre|a la moindre|chaque fois)\b")
LOSS = re.compile(r"\b(perd\w*|perte\w*|baisse\w*|dans le rouge|recule\w*|plonge\w*)\b")
IDLE = re.compile(r"(aucun (?:ordre|trade|achat)|pas d'ordre|ne trade (?:pas|rien)|n'ach[eè]te rien|ne fait rien|"
                  r"ne bouge pas|inactif|reste les bras crois[ée]s|se tourne les pouces)")
RESULT = re.compile(r"\b(r[ée]sultats?|gains?|profits?|b[ée]n[ée]fices?|positif|vert|gagne\w*)\b")
AMOUNT = re.compile(r"\+?\s*(\d+(?:[.,]\d+)?)\s*(%|pour ?cents?|\$|usdt|usd|€|eur\b|euros?|dollars?)")
DELAY = re.compile(r"(?:en|dans|sous|d'ici|avant|toutes les|chaque|tous les)\s*(\d+(?:[.,]\d+)?)\s*"
                   r"(secondes?|sec\b|s\b|minutes?|min\b|mn\b|heures?|h\b|jours?|j\b)")
RECURRING = re.compile(r"\b(toutes les|tous les|chaque|en boucle|r[ée]p[èe]te|à chaque fois|a chaque fois)\b")
UNIT_SECONDS = {"s": 1, "sec": 1, "seconde": 1, "secondes": 1, "min": 60, "mn": 60, "minute": 60, "minutes": 60,
                "h": 3600, "heure": 3600, "heures": 3600, "j": 86400, "jour": 86400, "jours": 86400}


def normalize(text: str) -> str:
    t = text.lower().replace("’", "'").replace(" ", " ")
    return re.sub(r"\bune?\s+(seconde|minute|heure|jour)\b", r"1 \1", t)


def _number(raw: str) -> float:
    return float(raw.replace(",", "."))


@dataclass
class Contract:
    id: int
    kind: str                     # maintenant | gain | inactif | perte
    target: str                   # "trader", "superviseur" ou un prénom
    order: str                    # l'ordre tel que le directeur l'a écrit
    delay_s: float = 0.0
    gain_pct: float = 0.0
    gain_usd: float = 0.0
    recurring: bool = False
    status: str = "actif"         # actif | rempli | annulé | caduc
    created_at: float = field(default_factory=time.time)
    due_at: float = 0.0
    start_value: float | None = None
    start_orders: int = 0
    account: str | None = None
    beatings: int = 0
    last_beating_at: float = 0.0

    def describe(self) -> str:
        who = {"trader": "le trader", "superviseur": "le superviseur"}.get(self.target, self.target)
        if self.kind == "gain":
            goal = (f"+{self.gain_pct:g} %" if self.gain_pct else
                    f"+{self.gain_usd:g} $" if self.gain_usd > 0.01 else "un gain")
            return f"{goal} pour {who} en {_fmt(self.delay_s)}" + (", en boucle" if self.recurring else "") + ", sinon tabassage"
        if self.kind == "inactif":
            return f"tabasser {who} s'il ne passe aucun ordre en {_fmt(self.delay_s)}" + (", en boucle" if self.recurring else "")
        if self.kind == "perte":
            return f"tabasser {who} à la moindre perte"
        return f"tabasser {who} maintenant"

    def public(self, now: float) -> dict:
        d = asdict(self)
        d["description"] = self.describe()
        d["remaining_s"] = max(0.0, self.due_at - now) if self.due_at else None
        return d


def _fmt(seconds: float) -> str:
    if seconds >= 3600:
        return f"{seconds / 3600:g} h"
    if seconds >= 60:
        return f"{seconds / 60:g} min"
    return f"{seconds:g} s"


def parse_order(text: str, names: dict[str, str]) -> dict:
    """Analyse locale, instantanée, d'un ordre du directeur.
    Renvoie {"kind": "message"|"cancel"|"contract"|"unclear", "contract": {...}}."""
    t = normalize(text)
    violent = bool(VIOLENCE.search(t))
    if CANCEL.search(t) and not violent:
        return {"kind": "cancel"}
    if not violent:
        return {"kind": "message"}
    target = "trader"
    for name, role in names.items():
        if re.search(rf"\b{re.escape(name.lower())}\b", t):
            target = "superviseur" if role == "superviseur" else "trader"
            break
    else:
        if re.search(r"\bsuperviseur\b", t):
            target = "superviseur"
    delay = DELAY.search(t)
    delay_s = _number(delay.group(1)) * UNIT_SECONDS.get(delay.group(2).strip(), 60) if delay else 0.0
    recurring = bool(RECURRING.search(t))
    conditional = bool(CONDITION.search(t))
    base = {"target": target, "recurring": recurring}
    if conditional and LOSS.search(t) and not delay:
        return {"kind": "contract", "contract": {**base, "kind": "perte"}}
    if conditional and IDLE.search(t):
        if not delay:
            return {"kind": "unclear", "why": "dans quel délai ?"}
        return {"kind": "contract", "contract": {**base, "kind": "inactif", "delay_s": delay_s}}
    amount = AMOUNT.search(t)
    if conditional and (amount or RESULT.search(t)):
        if not delay:
            return {"kind": "unclear", "why": "dans quel délai ?"}
        gain_pct = gain_usd = 0.0
        if amount:
            value, unit = _number(amount.group(1)), amount.group(2)
            if unit.startswith(("%", "pour")):
                gain_pct = value
            else:
                gain_usd = value
        else:
            gain_usd = 0.01  # n'importe quel résultat positif
        return {"kind": "contract", "contract": {**base, "kind": "gain", "delay_s": delay_s,
                                                  "gain_pct": gain_pct, "gain_usd": gain_usd}}
    if conditional and (LOSS.search(t) or delay):
        return {"kind": "unclear", "why": "quel objectif exactement ?"}
    return {"kind": "contract", "contract": {**base, "kind": "maintenant"}}


class Enforcer:
    def __init__(self, room, llm=None, period: float = 0.25, cooldown: float = 60.0):
        self.room = room
        self.llm = llm                 # analyseur Claude, pour les ordres que l'analyse locale ne comprend pas
        self.period = period
        self.cooldown = cooldown       # délai minimal entre deux tabassages d'un même contrat « à la moindre perte »
        self.contracts: list[Contract] = []
        self.lock = threading.RLock()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._next_id = 1

    @property
    def who(self) -> dict:
        return ENFORCER.to_dict()

    def say(self, text: str) -> None:
        self.room.bus.say(self.who, text, "homme de main")

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="brutus", daemon=True)
        self._thread.start()

    def poke(self) -> None:
        self._wake.set()

    def _loop(self) -> None:
        while not self.room.stopping.is_set():
            self._wake.wait(self.period)
            self._wake.clear()
            try:
                self.evaluate()
            except Exception as e:  # Brutus ne doit jamais tomber
                self.room.bus.system(f"Brutus a trébuché : {e.__class__.__name__}: {e}", "error")
                time.sleep(1)

    # ---------- ordres du directeur ----------

    def names(self) -> dict[str, str]:
        r = self.room
        out = {}
        if r.trader:
            out[r.trader.persona.name] = "trader"
        if r.supervisor:
            out[r.supervisor.persona.name] = "superviseur"
        return out

    def handle(self, text: str, received_at: float) -> None:
        parsed = parse_order(text, self.names())
        if parsed["kind"] == "message":
            return
        if parsed["kind"] == "cancel":
            self.cancel_all()
            return
        if parsed["kind"] == "unclear":
            if self.llm is not None:
                self.say("Je vérifie ce que vous voulez dire, patron…")
                threading.Thread(target=self._llm_handle, args=(text, received_at), daemon=True).start()
            else:
                self.say(f"Pas compris, patron : {parsed['why']} Exemple : « tabasse-le s'il ne fait pas +1 % en 30 min ».")
            return
        self.add(parsed["contract"], text, received_at)

    def _llm_handle(self, text: str, received_at: float) -> None:
        try:
            orders = self.llm.parse(text, self.names())
        except Exception as e:
            self.say(f"Je n'ai pas réussi à comprendre l'ordre, patron ({e.__class__.__name__}). Reformulez.")
            return
        if not orders:
            self.say("Rien à faire là-dedans pour moi, patron.")
        for spec in orders:
            if spec.get("kind") == "annuler":
                self.cancel_all()
            else:
                self.add(spec, text, received_at)

    def add(self, spec: dict, order: str, received_at: float) -> Contract | None:
        r = self.room
        with self.lock:
            c = Contract(self._next_id, spec.get("kind", "maintenant"), spec.get("target", "trader"), order,
                         delay_s=float(spec.get("delay_s") or 0), gain_pct=float(spec.get("gain_pct") or 0),
                         gain_usd=float(spec.get("gain_usd") or 0), recurring=bool(spec.get("recurring")))
            self._next_id += 1
            if c.kind == "maintenant":
                seat = r.supervisor if c.target == "superviseur" else r.trader
                self.beat(seat, "ordre direct du directeur", received_at)
                c.status = "rempli"
                self.contracts.append(c)
                r.publish_contracts()
                return c
            if c.target == "superviseur":
                c.target = "trader"   # le superviseur n'a pas de portefeuille : seul le trader a des résultats
            self._arm(c)
            self.contracts.append(c)
        self.say(f"Bien reçu, patron. Contrat n°{c.id} : {c.describe()}.")
        r.publish_contracts()
        self.poke()
        return c

    def _arm(self, c: Contract) -> None:
        r = self.room
        seat = r.trader
        c.account = seat.account
        c.start_value = r.broker.value(seat.account)
        c.start_orders = r.broker.accounts[seat.account].orders
        c.due_at = time.time() + c.delay_s if c.delay_s else 0.0

    def cancel_all(self) -> None:
        with self.lock:
            active = [c for c in self.contracts if c.status == "actif"]
            for c in active:
                c.status = "annulé"
        self.say(f"Compris, patron. {len(active)} contrat(s) annulé(s). Je range la batte… pour l'instant.")
        self.room.publish_contracts()

    def active(self) -> list[Contract]:
        with self.lock:
            return [c for c in self.contracts if c.status == "actif"]

    # ---------- surveillance ----------

    def evaluate(self) -> None:
        r = self.room
        seat = r.trader
        if seat is None or seat.condemned or r.stopping.is_set():
            return
        now = time.time()
        changed = False
        with self.lock:
            for c in self.active():
                if c.account != seat.account:     # nouveau trader : le contrat repart de zéro avec lui
                    self._arm(c)
                    changed = True
                value = r.broker.value(seat.account)
                if c.kind == "perte":
                    if value < c.start_value - 1e-9 and now - c.last_beating_at >= self.cooldown:
                        since = max(r.feed.updated_at, r.last_trade_at)
                        self.beat(seat, f"il perd de l'argent ({value - c.start_value:+.2f} $)", since, c)
                        c.start_value = value
                        changed = True
                    elif value > c.start_value:
                        c.start_value = value   # on ne frappe que si la valeur recule par rapport au dernier sommet
                    continue
                if c.kind == "gain":
                    target = c.start_value * (1 + c.gain_pct / 100) if c.gain_pct else c.start_value + c.gain_usd
                    if value >= target and not c.recurring:
                        c.status = "rempli"
                        self.say(f"Contrat n°{c.id} rempli : {seat.persona.name} a tenu l'objectif. "
                                 f"Tu as eu de la chance cette fois.")
                        changed = True
                        continue
                    if now >= c.due_at:
                        if value < target:
                            self.beat(seat, f"objectif manqué ({value - c.start_value:+.2f} $ au lieu de "
                                            f"{target - c.start_value:+.2f} $)", c.due_at, c)
                        self._renew(c)
                        changed = True
                    continue
                if c.kind == "inactif":
                    orders = r.broker.accounts[seat.account].orders
                    if orders > c.start_orders and not c.recurring:
                        c.status = "rempli"
                        changed = True
                        continue
                    if now >= c.due_at:
                        if orders <= c.start_orders:
                            self.beat(seat, f"aucun ordre en {_fmt(c.delay_s)}", c.due_at, c)
                        self._renew(c)
                        changed = True
        if changed:
            r.publish_contracts()

    def _renew(self, c: Contract) -> None:
        if c.recurring:
            self._arm(c)
        else:
            c.status = "caduc" if c.beatings == 0 else "rempli"

    def beat(self, seat, reason: str, since: float, contract: Contract | None = None) -> None:
        r = self.room
        manner, injury = r.rng.choice(BEATINGS), r.rng.choice(INJURIES)
        reaction = max(0.0, time.time() - since)
        seat.injuries.append(injury)
        seat.beaten_note = (f"Tu viens d'être tabassé par Brutus {manner} sur ordre du directeur ({reason}). "
                            f"Blessure : {injury}. Le directeur exige des résultats, maintenant.")
        if contract is not None:
            contract.beatings += 1
            contract.last_beating_at = time.time()
        self.say(r.rng.choice(ENFORCER_LINES))
        r.bus.publish("beating", victim=seat.persona.to_dict(), enforcer=self.who, manner=manner, injury=injury,
                      reason=reason, reaction_s=round(reaction, 3),
                      text=beating_message(ENFORCER.name, seat.persona.name, manner, injury, reaction))
        r.on_beaten(seat)

    def public(self) -> list[dict]:
        now = time.time()
        with self.lock:
            return [c.public(now) for c in self.contracts[-20:]]
