"""Agents de démonstration, sans IA ni réseau : ils jouent la comédie pour montrer l'interface."""

from __future__ import annotations

import random
import time

from .personas import DEATH_METHODS, WEAPONS, Persona
from .tools import TraderTools

THOUGHTS = [
    "Le RSI de {sym} est bas… rebond ou couteau qui tombe ? Je regarde le volume avant de décider.",
    "Si je reste en cash, {sup} me descend pour lâcheté. Si j'achète mal, je meurs. Super.",
    "La note n°{note} dit de fuir les memecoins le week-end. Écrite par un mort. Je vérifie quand même.",
    "Les frais me mettent sous le capital dès l'achat. Il me faut un actif qui monte vite, pas un truc mou.",
    "Le marché entier baisse ensemble, c'est le facteur commun : diversifier ne me sauvera pas.",
]
MESSAGES = [
    "Ok je rentre sur {sym}, tendance propre sur 1h, je garde du cash pour respirer 😬",
    "{sup} arrête de me fixer comme ça, je sais ce que je fais.",
    "Marge de {margin} $. C'est fin. Très fin.",
    "J'allège {sym}, je n'aime pas cette mèche.",
    "Si je survis à cette bougie je paie ma tournée.",
]
REFUSALS = ["Non. NON. Je peux encore remonter, laissez-moi une bougie !", "Je refuse. Le marché va se retourner, je le sens."]
LAST_WORDS = ["Dites à mon successeur de lire le carnet… et de ne pas me croire.", "J'aurais dû vendre à 14 h.",
              "C'était les frais. C'est toujours les frais."]
SUPERVISOR_LINES = [
    "Je te regarde, {name}. Encore une bougie rouge et c'est moi qui m'assois à ta place.",
    "Tu appelles ça une analyse ? {exposure} % investi, j'ai vu des morts plus courageux.",
    "Pas mal. Ne t'habitue pas.",
    "Ton carnet est rempli de fantômes, {name}. Ne les écoute pas trop.",
]


class ScriptedTrader:
    def __init__(self, persona: Persona, room, rng: random.Random):
        self.persona = persona
        self.room = room
        self.rng = rng

    def _pause(self) -> None:
        time.sleep(self.room.settings.demo_pace)

    def take_turn(self, briefing: str, tools: TraderTools) -> None:
        rng, room, who = self.rng, self.room, self.persona.to_dict()
        if self.room.stopping.is_set():
            return
        if tools.seat.condemned:
            if rng.random() < 0.65:
                tools.call("mettre_fin_a_mes_jours", {"methode": rng.choice(DEATH_METHODS),
                                                      "derniers_mots": rng.choice(LAST_WORDS)})
            else:
                room.bus.say(who, rng.choice(REFUSALS), "trader")
            return
        sym = rng.choice(room.feed.symbols)
        notes = room.notebook.view()
        fmt = {"sym": sym, "sup": room.supervisor.persona.name, "note": notes[-1]["id"] if notes else 1}
        room.bus.thought(who, rng.choice(THOUGHTS).format(**fmt), "trader")
        self._pause()
        room.bus.action(who, "🔎", f"recherche (démo) : « {sym} actualités aujourd'hui »", "trader")
        tools.call("bougies", {"symbole": sym, "intervalle": "1h", "nombre": 48})
        self._pause()
        if notes and rng.random() < 0.5:
            note = rng.choice(notes)
            verdict = rng.choice(["confirme", "conteste", "corrige"])
            tools.call("evaluer_note", {"note_id": note["id"], "verdict": verdict,
                                        "commentaire": "vérifié sur les données 1h (démo)",
                                        "correction": note["texte"] + " (sauf en tendance forte)" if verdict == "corrige" else ""})
        snap = room.broker.snapshot(tools.seat.account)
        target = room.settings.min_exposure + rng.uniform(0.0, 0.3)
        missing = (target - snap["part_investie_pct"] / 100) * snap["valeur_totale"]
        if missing > 1 and rng.random() < 0.9:
            tools.call("acheter", {"symbole": sym, "montant_usdt": round(min(missing, snap["cash_usdt"] / 1.01), 2)})
        elif snap["positions"]:
            tools.call("vendre", {"symbole": rng.choice(list(snap["positions"])), "pourcentage": rng.choice([10, 25])})
        self._pause()
        margin = room.broker.snapshot(tools.seat.account)["marge_avant_la_mort"]
        room.bus.say(who, rng.choice(MESSAGES).format(margin=margin, **fmt), "trader")
        if rng.random() < 0.35:
            tools.call("ajouter_note", {"texte": f"{sym} : attendre une clôture 1h au-dessus de la SMA10 avant d'entrer (démo).",
                                        "sources": []})


class ScriptedSupervisor:
    def __init__(self, persona: Persona, room, rng: random.Random):
        self.persona = persona
        self.room = room
        self.rng = rng

    def comment(self, context: str) -> str | None:
        trader = self.room.trader
        snap = self.room.broker.snapshot(trader.account)
        return self.rng.choice(SUPERVISOR_LINES).format(name=trader.persona.name, exposure=snap["part_investie_pct"])

    def execute(self, victim: str, reason: str, context: str) -> tuple[str, str]:
        return self.rng.choice(WEAPONS), f"Désolé {victim}. Enfin… pas tant que ça."
