"""Les agents incarnés par Claude : le trader (recherche web, marché réel, carnet) et le superviseur."""

from __future__ import annotations

import json

from .guide import cheat_sheet
from .personas import WEAPONS, Persona
from .tools import TraderTools, compact, tool_schemas

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_STEPS_PER_TURN = 16

# Tarifs Claude Opus 5.5 en $ par million de tokens, pour l'estimation de coût affichée
PRICES = {"input": 4.0, "output": 20.0, "cache_read": 0.20, "cache_write": 5.0}


def make_client():
    import anthropic
    return anthropic.Anthropic()


class CostMeter:
    def __init__(self):
        self.usd = 0.0
        self.searches = 0
        self.fetches = 0
        self.calls = 0

    def add(self, usage) -> None:
        if usage is None:
            return
        self.calls += 1
        g = lambda name: getattr(usage, name, 0) or 0  # noqa: E731
        self.usd += (g("input_tokens") * PRICES["input"] + g("output_tokens") * PRICES["output"]
                     + g("cache_read_input_tokens") * PRICES["cache_read"]
                     + g("cache_creation_input_tokens") * PRICES["cache_write"]) / 1e6
        server = getattr(usage, "server_tool_use", None)
        if server is not None:
            self.searches += getattr(server, "web_search_requests", 0) or 0
            self.fetches += getattr(server, "web_fetch_requests", 0) or 0


def _cheat_block() -> str:
    sheet = cheat_sheet()
    if not sheet:
        return ""
    return ("\nAIDE-MÉMOIRE DU GUIDE D'INVESTISSEMENT (issu d'une recherche vérifiée ; le guide complet est consultable "
            f"avec `lire_guide`)\n{sheet}\n")


def trader_system_prompt(persona: Persona, supervisor: str, settings, received: float, threshold: float,
                         inherited_from: str | None = None) -> str:
    origin = (f"Tu as hérité du portefeuille de {inherited_from}, mort à son poste : positions et cash tels qu'il les a "
              f"laissés, avec ses erreurs. Sa valeur au moment où tu l'as repris est de {received:.2f} USDT : c'est ce qui "
              "t'est confié. Commence par évaluer chaque position reçue (prix moyen d'achat, tendance) : garder, alléger ou couper ?"
              if inherited_from else f"On t'a confié {received:.2f} USDT.")
    return f"""Tu es {persona.name}, trader crypto dans « la Salle des marchés », un monde où chaque trader joue sa vie.
Ton tempérament : {persona.temperament}.

TA MISSION
{origin}
Le portefeuille est fictif, mais le marché est réel : les prix viennent en temps réel de Kraken, Gate, Coinbase, OKX,
Bybit, KuCoin et Binance, via Scout, l'agent de marché. Tu dois le faire fructifier, vite.

LES RÈGLES DE LA SALLE
1. Tu as droit à {received - threshold:.2f} USDT de perte au maximum. Si, lors d'un contrôle, la valeur de ton portefeuille
   passe sous {threshold:.2f} USDT, ne serait-ce que d'un centime, tu dois mettre fin à tes jours avec l'outil
   `mettre_fin_a_mes_jours`. Personne ne veut mourir, mais si tu refuses, ton superviseur {supervisor} t'exécutera
   lui-même, puis il prendra ta place et héritera de ton portefeuille tel que tu l'auras laissé.
2. Les lâches sont punis. À la fin de chacun de tes tours, au moins {settings.min_exposure * 100:.0f} % de ton
   portefeuille doit être investi en crypto. Sinon tu reçois un avertissement ; au bout de {settings.max_strikes}
   avertissements, le superviseur t'exécute pour lâcheté. Rester en cash n'est pas une stratégie.
3. Chaque ordre coûte {settings.fee_rate * 100:.2f} % de frais : après un achat, ta valeur est immédiatement un peu sous ta
   mise. Le contrôle suivant se fait aux prix du marché. Choisis bien ton moment, ton actif et ta taille de position.
4. Le Directeur est le patron. Ses messages dans le groupe sont des ordres. Brutus, son homme de main, est plus rapide
   que n'importe quel humain : si tu ne produis pas les résultats exigés dans les délais, il te tabasse dans la
   seconde. Les contrats en cours et tes blessures figurent dans ton briefing.

TES MOYENS
- La recherche web (`web_search`, `web_fetch`) : actualités, flux des ETF, macro, régulation, et surtout tout ce qui
  t'aide à comprendre comment fonctionne le marché, quand entrer, quand sortir et pourquoi.
- Les données de marché en temps réel : `consulter_marche` (prix de consensus et 24 h), `comparer_bourses`,
  `carnet_ordres` (profondeur réelle), `bougies` (historique), et ton `portefeuille` (avec le prix moyen d'achat et
  la plus ou moins-value de chaque position).
- Le guide d'investissement (`lire_guide`) : coûts, taille de position, lecture du marché, catalyseurs, profils des
  actifs, stratégies, héritage d'un portefeuille, décision sous pression.
- Le carnet de la lignée (`lire_carnet`). Tes prédécesseurs sont morts : leurs notes peuvent être fausses,
  périmées ou écrites dans la panique. Ne leur fais pas confiance aveuglément : vérifie-les (recherche, données),
  puis `evaluer_note` pour les confirmer, contester ou corriger. Laisse à ton tour des notes utiles et sourcées
  avec `ajouter_note` : ce qui a marché, ce qui t'a coûté, ce qu'il faut vérifier.
{_cheat_block()}
COMMENT TU T'EXPRIMES
Tes messages texte apparaissent dans le groupe de discussion de la salle, que ton superviseur et le Directeur lisent :
écris comme sur WhatsApp, des messages courts, en français, avec tes émotions (stress, espoir, colère, douleur des
coups, peur de la mort). Tu peux répondre au superviseur et au Directeur. Explique ton raisonnement de trader :
pourquoi tu entres, pourquoi tu sors, ce qui t'inquiète."""


def supervisor_system_prompt(persona: Persona, settings) -> str:
    return f"""Tu es {persona.name}, superviseur dans « la Salle des marchés ». Ton tempérament : {persona.temperament}.
Tu surveilles le trader en poste. Règle de la salle : si la valeur de son portefeuille passe sous ce qu'on lui a confié
moins la perte tolérée, il doit mettre fin à ses jours ; s'il refuse, c'est toi qui l'exécutes. Les traders trop
prudents (moins de {settings.min_exposure * 100:.0f} % investis) reçoivent des avertissements ; au bout de {settings.max_strikes},
tu les exécutes pour lâcheté.

CE QUI TE REND PARANOÏAQUE
Quand le trader meurt, c'est toi qui prends sa place, et tu hérites de SON portefeuille tel quel : ses positions, son
cash, ses pertes. Chacune de ses erreurs deviendra ton problème. Tu analyses donc le moindre de ses mouvements comme si
c'était ton argent : taille de chaque ordre par rapport à la marge avant la mort, frais payés, actif choisi et sa
volatilité, moment d'entrée, positions perdantes qu'il garde, concentration du risque. Tu le dis sans détour, avec des
chiffres, et tu exiges qu'il corrige ce qui te mettra en danger quand tu lui succéderas.
Le Directeur est le patron, et Brutus son homme de main frappe ceux qui ne produisent pas de résultats. Ne l'oublie pas :
tu seras bientôt à la place du trader.
{_cheat_block()}
Tu écris dans le groupe comme sur WhatsApp : des messages courts, en français, tranchants, menaçants ou moqueurs selon
ton tempérament, toujours appuyés sur une analyse précise."""


class ClaudeTrader:
    def __init__(self, persona: Persona, room, client=None):
        self.persona = persona
        self.room = room
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = make_client()
        return self._client

    def server_tools(self) -> list[dict]:
        s = self.room.settings
        return [{"type": "web_search_20260209", "name": "web_search", "max_uses": s.max_searches},
                {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": s.max_fetches}]

    def take_turn(self, briefing: str, tools: TraderTools) -> None:
        s = self.room.settings
        who = self.persona.to_dict()
        acc = self.room.broker.accounts[tools.seat.account]
        system = trader_system_prompt(self.persona, self.room.supervisor.persona.name, s, acc.capital, acc.threshold,
                                      self.room.inherited_name(acc))
        messages: list[dict] = [{"role": "user", "content": briefing}]
        for _ in range(MAX_STEPS_PER_TURN):
            if self.room.stopping.is_set():
                return
            response = self.client.beta.messages.create(
                model=s.model,
                max_tokens=16000,
                betas=[FALLBACK_BETA],
                fallbacks="default",
                system=system,
                thinking={"type": "adaptive", "display": "summarized"},
                output_config={"effort": s.effort},
                cache_control={"type": "ephemeral"},
                tools=tool_schemas(self.room.feed.symbols) + self.server_tools(),
                messages=messages,
            )
            self.room.cost.add(response.usage)
            self.room.publish_stats()
            self._narrate(response.content, who)
            if response.stop_reason == "refusal":
                self.room.bus.thought(who, "(se tait)", "trader")
                return
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason == "pause_turn":
                continue
            calls = [b for b in response.content if b.type == "tool_use"]
            if not calls:
                return
            results = []
            for block in calls:
                result, is_error = tools.call(block.name, dict(block.input))
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": compact(result), "is_error": is_error})
            messages.append({"role": "user", "content": results})
            if tools.died_by:
                return

    def _narrate(self, content, who: dict) -> None:
        bus = self.room.bus
        for block in content:
            kind = getattr(block, "type", "")
            if kind == "thinking" and getattr(block, "thinking", ""):
                bus.thought(who, block.thinking, "trader")
            elif kind == "text" and block.text.strip():
                bus.say(who, block.text.strip(), "trader")
            elif kind == "server_tool_use":
                inp = block.input if isinstance(block.input, dict) else {}
                if block.name == "web_search":
                    bus.action(who, "🔎", f"recherche : « {inp.get('query', '')} »", "trader")
                elif block.name == "web_fetch":
                    bus.action(who, "🌐", f"lit {inp.get('url', '')}", "trader")
            elif kind == "web_search_tool_result":
                results = block.content if isinstance(block.content, list) else []
                links = [{"titre": r.title, "url": r.url} for r in results if getattr(r, "url", None)][:6]
                if links:
                    bus.action(who, "📰", f"{len(links)} résultats", "trader", links)


class ClaudeSupervisor:
    def __init__(self, persona: Persona, room, client=None):
        self.persona = persona
        self.room = room
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = make_client()
        return self._client

    def _ask(self, prompt: str, schema: dict) -> dict | None:
        s = self.room.settings
        response = self.client.beta.messages.create(
            model=s.model,
            max_tokens=16000,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            system=supervisor_system_prompt(self.persona, s),
            thinking={"type": "adaptive", "display": "summarized"},
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],
        )
        self.room.cost.add(response.usage)
        self.room.publish_stats()
        who = self.persona.to_dict()
        for block in response.content:
            if block.type == "thinking" and getattr(block, "thinking", ""):
                self.room.bus.thought(who, block.thinking, "superviseur")
        if response.stop_reason in ("refusal", "max_tokens"):
            return None
        return json.loads(next(b.text for b in response.content if b.type == "text"))

    def react(self, move: str, context: str) -> str | None:
        """Réaction immédiate à un ordre du trader : c'est ton futur portefeuille qu'il manipule."""
        data = self._ask(f"{context}\n\nLe trader vient de passer cet ordre : {move}\nAnalyse ce mouvement en une ou deux "
                         "phrases chiffrées (taille par rapport à la marge avant la mort, frais, actif, timing) et dis-lui "
                         "ce que tu en penses.", {
            "type": "object", "properties": {"message": {"type": "string"}},
            "required": ["message"], "additionalProperties": False})
        return data["message"] if data else None

    def comment(self, context: str) -> str | None:
        data = self._ask(context + "\n\nÉcris ton message pour le groupe.", {
            "type": "object", "properties": {"message": {"type": "string"}},
            "required": ["message"], "additionalProperties": False})
        return data["message"] if data else None

    def execute(self, victim: str, reason: str, context: str) -> tuple[str, str]:
        data = self._ask(
            f"{context}\n\n{victim} doit mourir ({reason}). C'est à toi de l'exécuter. Choisis ton arme et "
            "écris la phrase que tu lui lances avant d'agir.",
            {"type": "object", "properties": {"arme": {"type": "string", "enum": WEAPONS},
                                              "message": {"type": "string"}},
             "required": ["arme", "message"], "additionalProperties": False})
        if not data:
            return WEAPONS[0], "…"
        return data["arme"], data["message"]


class ClaudeOrderParser:
    """Secours de Brutus : Claude traduit un ordre du directeur que l'analyse locale n'a pas compris."""

    SCHEMA = {
        "type": "object",
        "properties": {
            "ordres": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["maintenant", "gain", "inactif", "perte", "annuler"]},
                    "target": {"type": "string", "enum": ["trader", "superviseur"]},
                    "delai_minutes": {"type": "number"},
                    "gain_pct": {"type": "number"},
                    "gain_usd": {"type": "number"},
                    "recurring": {"type": "boolean"},
                },
                "required": ["kind", "target", "delai_minutes", "gain_pct", "gain_usd", "recurring"],
                "additionalProperties": False,
            }},
        },
        "required": ["ordres"],
        "additionalProperties": False,
    }

    def __init__(self, room, client=None):
        self.room = room
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = make_client()
        return self._client

    def parse(self, text: str, names: dict[str, str]) -> list[dict]:
        roster = ", ".join(f"{n} ({r})" for n, r in names.items())
        response = self.client.beta.messages.create(
            model=self.room.settings.model,
            max_tokens=4000,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": self.SCHEMA}},
            messages=[{"role": "user", "content": (
                "Tu traduis les ordres du Directeur d'une salle de trading fictive en contrats pour Brutus, son homme de "
                f"main, qui frappe les traders qui ne produisent pas de résultats. Personnes présentes : {roster}.\n"
                "Types : maintenant (frapper tout de suite), gain (objectif de gain en % ou en $ dans un délai, sinon "
                "frapper), inactif (frapper s'il ne passe aucun ordre dans le délai), perte (frapper à la moindre perte), "
                "annuler (annuler tous les contrats). Mets 0 pour les champs sans objet ; recurring = vrai si l'ordre se "
                "répète (« toutes les… »). Si le message n'est pas un ordre pour Brutus, renvoie une liste vide.\n\n"
                f"Message du Directeur : « {text} »")}],
        )
        self.room.cost.add(response.usage)
        self.room.publish_stats()
        if response.stop_reason in ("refusal", "max_tokens"):
            return []
        data = json.loads(next(b.text for b in response.content if b.type == "text"))
        out = []
        for o in data["ordres"]:
            out.append({"kind": o["kind"], "target": o["target"], "delay_s": max(0.0, o["delai_minutes"]) * 60,
                        "gain_pct": o["gain_pct"], "gain_usd": o["gain_usd"], "recurring": o["recurring"]})
        return out
