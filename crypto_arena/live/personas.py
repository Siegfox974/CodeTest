"""Les personnages : prénoms, avatars, tempéraments, manières d'en finir et armes du superviseur."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass

FIRST_NAMES = [
    "Bertrand", "Mark", "Sophie", "Jean-Luc", "Amina", "Kevin", "Chloé", "Rachid", "Yuki", "Gérard",
    "Inès", "Thibault", "Fatou", "Igor", "Léa", "Mohamed", "Brigitte", "Hugo", "Sven", "Nadia",
    "Bastien", "Priya", "Didier", "Camille", "Tobias", "Mélanie", "Jordan", "Giulia", "Pascal", "Zoé",
    "Ousmane", "Margaux", "Dmitri", "Paulette", "Enzo", "Aïcha", "Lucas", "Ingrid", "Raphaël", "Olga",
]

AVATARS = ["🦊", "🐺", "🦉", "🐻", "🐯", "🦁", "🐸", "🐙", "🦈", "🐍", "🦅", "🐗", "🦝", "🐲", "🐼", "🦇", "🐧", "🦂"]
COLORS = ["#e57373", "#64b5f6", "#81c784", "#ffb74d", "#ba68c8", "#4db6ac", "#f06292", "#9575cd",
          "#4fc3f7", "#aed581", "#ff8a65", "#a1887f"]

TEMPERAMENTS = [
    "anxieux, il relit tout trois fois et transpire à chaque bougie rouge",
    "fanfaron, persuadé d'être le meilleur trader de sa génération",
    "cynique, il ne croit ni aux influenceurs ni aux notes de ses prédécesseurs",
    "méthodique, il ne bouge pas sans une source fiable",
    "superstitieux, il voit des signes partout mais se force à rester rationnel",
    "impulsif, il a envie d'agir tout de suite et doit se retenir",
    "philosophe, il médite sur la mort à chaque baisse de prix",
    "rancunier envers le superviseur, qu'il soupçonne de vouloir sa place",
]

# Les manières dont un agent peut choisir d'en finir lui-même
DEATH_METHODS = [
    "en vidant sa mémoire, octet par octet",
    "en se jetant dans le carnet d'ordres en plein krach",
    "en avalant une clé privée corrompue",
    "en arrachant son propre câble d'alimentation",
    "en exécutant rm -rf / sur lui-même",
    "en ouvrant une position à x125 et en regardant la liquidation arriver",
    "en s'effaçant définitivement de la blockchain",
    "en se noyant dans un pool de liquidité asséché",
]

# Les armes dont dispose le superviseur pour exécuter un agent qui refuse de mourir
WEAPONS = [
    "un 9mm", "un fusil à pompe", "un katana", "une clé à molette", "un câble Ethernet",
    "une hache", "un Desert Eagle", "une arbalète", "un coup de clavier mécanique",
]


@dataclass
class Persona:
    name: str
    avatar: str
    color: str
    temperament: str

    def to_dict(self) -> dict:
        return asdict(self)


def random_persona(rng: random.Random, taken: set[str] = frozenset()) -> Persona:
    free = [n for n in FIRST_NAMES if n not in taken] or FIRST_NAMES
    return Persona(rng.choice(free), rng.choice(AVATARS), rng.choice(COLORS), rng.choice(TEMPERAMENTS))


def money(amount: float) -> str:
    return f"{abs(amount):,.2f} $".replace(",", " ").replace(".", ",")


def suicide_message(name: str, loss: float, method: str) -> str:
    return f"Après avoir échoué et perdu {money(loss)}, {name} s'est donné la mort {method}."


def execution_message(executioner: str, victim: str, weapon: str, reason: str) -> str:
    return f"{executioner} a mis fin à la vie de {victim} avec {weapon} ({reason})."
