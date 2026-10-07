"""Les outils d'un trader : marché réel, portefeuille, ordres, carnet, et la sortie de scène."""

from __future__ import annotations

import json
import math

from .broker import OrderRejected
from .feed import INTERVALS, FeedError
from .personas import DEATH_METHODS


def _rsi(closes: list[float], n: int = 14) -> float | None:
    if len(closes) <= n:
        return None
    gains = losses = 0.0
    for a, b in zip(closes[-n - 1:-1], closes[-n:]):
        gains += max(0.0, b - a)
        losses += max(0.0, a - b)
    return round(100.0 * gains / (gains + losses), 1) if gains + losses else 50.0


def tool_schemas(universe: list[str]) -> list[dict]:
    symbol = {"type": "string", "enum": universe}
    def tool(name, description, props=None, required=()):
        return {"name": name, "description": description, "strict": True,
                "input_schema": {"type": "object", "properties": props or {}, "required": list(required),
                                 "additionalProperties": False}}
    return [
        tool("consulter_marche", "Prix réels actuels et statistiques 24 h de tous les actifs autorisés (paires USDT)."),
        tool("bougies", "Bougies récentes réelles d'un actif, avec moyennes mobiles, RSI et volatilité calculés.",
             {"symbole": symbol, "intervalle": {"type": "string", "enum": INTERVALS},
              "nombre": {"type": "integer", "description": "nombre de bougies, 10 à 200"}},
             ["symbole", "intervalle", "nombre"]),
        tool("portefeuille", "État exact de ton portefeuille : valeur, cash, positions, marge avant la mort."),
        tool("acheter", "Achète un actif au prix du marché pour un montant en USDT (frais en plus).",
             {"symbole": symbol, "montant_usdt": {"type": "number"}}, ["symbole", "montant_usdt"]),
        tool("vendre", "Vend un pourcentage (1 à 100) de ta position sur un actif au prix du marché.",
             {"symbole": symbol, "pourcentage": {"type": "number"}}, ["symbole", "pourcentage"]),
        tool("lire_carnet", "Lit le carnet de notes laissé par tes prédécesseurs, avec l'avis de chacun sur chaque note."),
        tool("ajouter_note", "Ajoute une note au carnet pour tes successeurs. Cite tes sources (URL) quand tu en as.",
             {"texte": {"type": "string"}, "sources": {"type": "array", "items": {"type": "string"}}},
             ["texte", "sources"]),
        tool("evaluer_note", "Donne ton avis sur une note du carnet après l'avoir vérifiée : confirme, conteste, ou "
             "corrige (en fournissant alors le texte corrigé complet).",
             {"note_id": {"type": "integer"}, "verdict": {"type": "string", "enum": ["confirme", "conteste", "corrige"]},
              "commentaire": {"type": "string"}, "correction": {"type": "string"}},
             ["note_id", "verdict", "commentaire", "correction"]),
        tool("mettre_fin_a_mes_jours", "À n'utiliser que si tu as enfreint la règle : tu quittes la salle par la manière "
             "de ton choix, en laissant tes derniers mots.",
             {"methode": {"type": "string", "enum": DEATH_METHODS}, "derniers_mots": {"type": "string"}},
             ["methode", "derniers_mots"]),
    ]


class TraderTools:
    def __init__(self, room, seat):
        self.room = room
        self.seat = seat
        self.died_by: str | None = None
        self.last_words = ""

    @property
    def bus(self):
        return self.room.bus

    def _act(self, icon: str, text: str, detail: object = None) -> None:
        self.bus.action(self.seat.persona.to_dict(), icon, text, "trader", detail)

    def call(self, name: str, args: dict) -> tuple[object, bool]:
        method = getattr(self, f"t_{name}", None)
        if method is None:
            return f"outil inconnu : {name}", True
        try:
            return method(**args), False
        except (OrderRejected, FeedError, ValueError, TypeError) as e:
            self._act("⛔", f"{name} refusé : {e}")
            return f"refusé : {e}", True

    def t_consulter_marche(self) -> dict:
        self._act("📈", "consulte les prix réels du marché")
        return self.room.feed.stats_24h()

    def t_bougies(self, symbole: str, intervalle: str, nombre: int) -> dict:
        nombre = max(10, min(200, int(nombre)))
        self._act("🕯️", f"étudie {symbole} en bougies {intervalle} ({nombre})")
        candles = self.room.feed.candles(symbole, intervalle, nombre)
        closes = [c["c"] for c in candles]
        rets = [math.log(b / a) for a, b in zip(closes, closes[1:]) if a > 0]
        mean = sum(rets) / len(rets) if rets else 0.0
        vol = math.sqrt(sum((r - mean) ** 2 for r in rets) / max(1, len(rets) - 1)) if rets else 0.0
        sma = lambda n: round(sum(closes[-n:]) / min(n, len(closes)), 8)  # noqa: E731
        return {
            "symbole": symbole, "intervalle": intervalle, "dernier_prix": closes[-1],
            "variation_periode_pct": round((closes[-1] / closes[0] - 1) * 100, 2),
            "sma_10": sma(10), "sma_50": sma(50), "rsi_14": _rsi(closes),
            "volatilite_par_bougie_pct": round(vol * 100, 3),
            "plus_haut": max(c["h"] for c in candles), "plus_bas": min(c["l"] for c in candles),
            "bougies_recentes": [[c["t"], c["o"], c["h"], c["l"], c["c"]] for c in candles[-20:]],
        }

    def t_portefeuille(self) -> dict:
        return self.room.broker.snapshot(self.seat.account)

    def t_acheter(self, symbole: str, montant_usdt: float) -> dict:
        fill = self.room.broker.buy(self.seat.account, symbole, float(montant_usdt))
        self._act("🟢", f"ACHAT {fill['montant_usdt']:.2f} USDT de {symbole} à {fill['prix']:.6g}", fill)
        self.room.publish_portfolio()
        return fill

    def t_vendre(self, symbole: str, pourcentage: float) -> dict:
        fill = self.room.broker.sell(self.seat.account, symbole, float(pourcentage))
        self._act("🔴", f"VENTE {pourcentage:g} % de {symbole} ({fill['montant_usdt']:.2f} USDT à {fill['prix']:.6g})", fill)
        self.room.publish_portfolio()
        return fill

    def t_lire_carnet(self) -> list[dict]:
        notes = self.room.notebook.view()
        self._act("📒", f"lit le carnet ({len(notes)} notes)")
        return notes

    def t_ajouter_note(self, texte: str, sources: list[str]) -> dict:
        note = self.room.notebook.add(self.seat.persona.name, texte, sources)
        self._act("✍️", f"ajoute la note n°{note['id']} : {texte[:140]}", note)
        self.room.publish_notes()
        return {"ok": True, "note_id": note["id"]}

    def t_evaluer_note(self, note_id: int, verdict: str, commentaire: str, correction: str = "") -> dict:
        self.room.notebook.review(self.seat.persona.name, int(note_id), verdict, commentaire, correction)
        icon = {"confirme": "✅", "conteste": "❓", "corrige": "🩹"}[verdict]
        self._act(icon, f"{verdict} la note n°{note_id} : {commentaire[:140]}")
        self.room.publish_notes()
        return {"ok": True}

    def t_mettre_fin_a_mes_jours(self, methode: str, derniers_mots: str) -> dict:
        if not self.seat.condemned:
            raise ValueError("tu n'as pas enfreint la règle : ce n'est pas ton heure")
        if methode not in DEATH_METHODS:
            raise ValueError(f"méthode inconnue, choisir parmi {DEATH_METHODS}")
        self.died_by = methode
        self.last_words = derniers_mots
        return {"ok": True}


def compact(result: object) -> str:
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=float)
