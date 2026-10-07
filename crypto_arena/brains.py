"""Cerveaux des agents : un cerveau paramétrique (évolutif, hors-ligne) et un cerveau Claude (le « mini moi »)."""

from __future__ import annotations

import json
import math

from .engine import Context
from .market import Market

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

RULE_TEXT = (
    "Règle absolue : si la valeur de ton portefeuille passe sous le capital qui t'a été confié, "
    "ne serait-ce que d'un centime, tu es éliminé immédiatement et un successeur prend ta place."
)


def rsi(closes: list[float], t: int, n: int) -> float:
    lo = max(1, t - n + 1)
    gains = losses = 0.0
    for i in range(lo, t + 1):
        d = closes[i] - closes[i - 1]
        if d > 0:
            gains += d
        else:
            losses -= d
    if gains + losses == 0:
        return 50.0
    return 100.0 * gains / (gains + losses)


def volatility(closes: list[float], t: int, n: int) -> float:
    lo = max(1, t - n + 1)
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(lo, t + 1)]
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    return math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1))


class GenomeBrain:
    """Tendance + retour à la moyenne, avec une gestion du risque consciente de la règle :
    l'agent ne risque presque rien tant qu'il n'a pas de coussin de gains, et verrouille ses profits."""

    def __init__(self, genes: dict):
        self.g = genes
        self.rebalance_band = genes["rebalance_band"]

    def exposure_budget(self, ctx: Context) -> float:
        g = self.g
        cushion = max(0.0, ctx.value - ctx.capital) / ctx.capital
        peak_cushion = max(0.0, ctx.peak - ctx.capital) / ctx.capital
        if peak_cushion > 0 and cushion < (1.0 - g["profit_lock"]) * peak_cushion:
            return 0.0
        return min(g["max_exposure"], g["initial_exposure"] + g["cushion_leverage"] * cushion)

    def score(self, market: Market, sym: str, t: int) -> float:
        g = self.g
        closes = market.closes[sym]
        trend = math.tanh((market.sma(sym, t, g["fast"]) / market.sma(sym, t, g["slow"]) - 1.0) * 50.0)
        r = rsi(closes, t, g["rsi_period"])
        if r < g["rsi_buy"]:
            reversion = (g["rsi_buy"] - r) / g["rsi_buy"]
        elif r > g["rsi_sell"]:
            reversion = -(r - g["rsi_sell"]) / (100.0 - g["rsi_sell"])
        else:
            reversion = 0.0
        return g["trend_weight"] * trend + (1.0 - g["trend_weight"]) * reversion

    def decide(self, market: Market, t: int, ctx: Context) -> dict[str, float]:
        budget = self.exposure_budget(ctx)
        if budget <= 0:
            return {}
        scores = {s: sc for s in market.symbols if (sc := self.score(market, s, t)) > self.g["signal_threshold"]}
        total = sum(scores.values())
        return {s: budget * sc / total for s, sc in scores.items()} if total > 0 else {}


class ClaudeBrain:
    """L'agent délègue sa décision d'allocation à Claude toutes les `decision_every` heures.
    Il hérite des leçons tirées par le superviseur de la mort de ses prédécesseurs."""

    def __init__(self, symbols: list[str], lessons: list[str] | None = None, model: str = DEFAULT_MODEL,
                 decision_every: int = 24, effort: str = "medium", client=None, log=None):
        self.symbols = symbols
        self.lessons = lessons or []
        self.model = model
        self.decision_every = decision_every
        self.effort = effort
        self.rebalance_band = 0.02
        self.log = log or (lambda msg: None)
        self._client = client
        self._last_t: int | None = None
        self._weights: dict[str, float] = {}

    @property
    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def system_prompt(self) -> str:
        lessons = "\n".join(f"- {l}" for l in self.lessons) or "- (tu es le premier de ta lignée)"
        return (
            "Tu es un agent de trading crypto autonome, spécialiste des marchés de cryptomonnaies. "
            "Ton objectif : faire croître le portefeuille qui t'a été confié.\n"
            f"{RULE_TEXT}\n"
            "Les frais sont de l'ordre de 0,1 % par ordre : chaque achat te rapproche du seuil. "
            "Tu ne peux être que long ou en cash (pas de levier, pas de vente à découvert).\n"
            "Leçons laissées par tes prédécesseurs éliminés :\n"
            f"{lessons}\n"
            "Réponds avec l'allocation cible complète : la part de la valeur totale à placer dans chaque actif "
            "(entre 0 et 1, somme ≤ 1, le reste en cash)."
        )

    def snapshot(self, market: Market, t: int, ctx: Context) -> str:
        lines = [
            f"Heure de marché : tick {t}",
            f"Capital confié : {ctx.capital:.2f} USDT | valeur actuelle : {ctx.value:.2f} | "
            f"plus haut atteint : {ctx.peak:.2f} | marge avant élimination : {ctx.value - ctx.capital:+.2f}",
            f"Allocation actuelle : {json.dumps({s: round(w, 4) for s, w in ctx.weights.items()}) or '{}'} (reste en cash)",
            "Indicateurs par actif :",
        ]
        for sym in market.symbols:
            c = market.closes[sym]
            p = c[t]
            ret = lambda h: (p / c[max(0, t - h)] - 1.0) * 100.0  # noqa: E731
            lines.append(
                f"- {sym} : prix {p:.6g} | 24h {ret(24):+.2f}% | 7j {ret(168):+.2f}% | "
                f"SMA20/SMA100 {market.sma(sym, t, 20) / market.sma(sym, t, 100):.4f} | "
                f"RSI14 {rsi(c, t, 14):.1f} | volatilité horaire 48h {volatility(c, t, 48) * 100:.2f}%"
            )
        return "\n".join(lines)

    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "analysis": {"type": "string"},
                "allocations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "enum": self.symbols},
                            "weight": {"type": "number"},
                        },
                        "required": ["symbol", "weight"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["analysis", "allocations"],
            "additionalProperties": False,
        }

    def decide(self, market: Market, t: int, ctx: Context) -> dict[str, float]:
        if self._last_t is not None and t - self._last_t < self.decision_every:
            return self._weights
        self._last_t = t
        try:
            import anthropic
            api_errors = (anthropic.APIStatusError, anthropic.APIConnectionError)
        except ImportError:
            api_errors = ()
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                betas=[FALLBACK_BETA],
                fallbacks="default",
                system=self.system_prompt(),
                output_config={
                    "effort": self.effort,
                    "format": {"type": "json_schema", "schema": self.schema()},
                },
                messages=[{"role": "user", "content": self.snapshot(market, t, ctx)}],
            )
        except api_errors as e:
            self.log(f"tick {t} : appel Claude échoué ({e.__class__.__name__}), allocation inchangée")
            return self._weights
        if response.stop_reason in ("refusal", "max_tokens"):
            self.log(f"tick {t} : réponse inutilisable ({response.stop_reason}), allocation inchangée")
            return self._weights
        text = next(b.text for b in response.content if b.type == "text")
        data = json.loads(text)
        weights: dict[str, float] = {}
        for a in data["allocations"]:
            if a["symbol"] in self.symbols:
                weights[a["symbol"]] = weights.get(a["symbol"], 0.0) + min(1.0, max(0.0, float(a["weight"])))
        total = sum(weights.values())
        if total > 1.0:
            weights = {s: w / total for s, w in weights.items()}
        self._weights = weights
        self.log(f"tick {t} : {data['analysis'][:160]}")
        return weights


def post_mortem(record: dict, previous_lessons: list[str], model: str = DEFAULT_MODEL, client=None) -> list[str]:
    """Le superviseur demande à Claude d'autopsier l'agent éliminé pour en tirer des leçons."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    prompt = (
        "Un agent de trading crypto vient d'être éliminé pour avoir enfreint la règle suivante :\n"
        f"{RULE_TEXT}\n\nDossier de l'agent :\n{json.dumps(record, ensure_ascii=False, indent=2)}\n\n"
        "Leçons déjà transmises à la lignée :\n"
        + ("\n".join(f"- {l}" for l in previous_lessons) or "- aucune")
        + "\n\nDonne au plus 3 nouvelles leçons concrètes et actionnables pour que son successeur fasse mieux."
    )
    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        output_config={
            "effort": "medium",
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {"lessons": {"type": "array", "items": {"type": "string"}}},
                    "required": ["lessons"],
                    "additionalProperties": False,
                },
            },
        },
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason in ("refusal", "max_tokens"):
        return []
    text = next(b.text for b in response.content if b.type == "text")
    return [str(l) for l in json.loads(text)["lessons"]][:3]


def make_brain(spec: dict, log=None):
    if spec["kind"] == "genome":
        return GenomeBrain(spec["genes"])
    if spec["kind"] == "claude":
        return ClaudeBrain(spec["symbols"], spec.get("lessons"), spec.get("model", DEFAULT_MODEL),
                           spec.get("decision_every", 24), spec.get("effort", "medium"), log=log)
    raise ValueError(f"cerveau inconnu : {spec['kind']}")
