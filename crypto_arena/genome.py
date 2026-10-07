"""Génome d'un agent trader : les paramètres que l'évolution ajuste."""

from __future__ import annotations

import random

# nom -> (min, max, type)
GENE_SPACE: dict[str, tuple[float, float, type]] = {
    "fast": (3, 50, int),                  # moyenne mobile courte
    "slow": (20, 200, int),                # moyenne mobile longue
    "rsi_period": (5, 30, int),
    "rsi_buy": (15.0, 45.0, float),        # RSI sous ce seuil = survendu
    "rsi_sell": (55.0, 85.0, float),       # RSI au-dessus = suracheté
    "trend_weight": (0.0, 1.0, float),     # 1 = suiveur de tendance, 0 = retour à la moyenne
    "signal_threshold": (0.0, 0.8, float),
    "initial_exposure": (0.05, 0.6, float),  # part investie tant qu'il n'y a aucun coussin de gains
    "cushion_leverage": (0.0, 20.0, float),  # exposition ajoutée par unité de gain accumulé
    "max_exposure": (0.1, 1.0, float),
    "profit_lock": (0.1, 0.9, float),      # part du coussin max qu'on refuse de rendre au marché
    "rebalance_band": (0.005, 0.1, float),  # écart minimal avant de retrader (économise les frais)
}

MAX_LOOKBACK = int(max(GENE_SPACE["slow"][1], GENE_SPACE["rsi_period"][1])) + 1


def _clip(name: str, value: float) -> float:
    lo, hi, kind = GENE_SPACE[name]
    value = min(hi, max(lo, value))
    return int(round(value)) if kind is int else float(value)


def _repair(genes: dict) -> dict:
    if genes["slow"] < genes["fast"] + 5:
        genes["slow"] = _clip("slow", genes["fast"] + 5)
        genes["fast"] = min(genes["fast"], genes["slow"] - 5)
    genes["initial_exposure"] = min(genes["initial_exposure"], genes["max_exposure"])
    return genes


def random_genome(rng: random.Random) -> dict:
    genes = {}
    for name, (lo, hi, _) in GENE_SPACE.items():
        genes[name] = _clip(name, rng.uniform(lo, hi))
    return _repair(genes)


def mutate(genes: dict, rng: random.Random, strength: float = 0.15) -> dict:
    """Chaque gène bouge d'un bruit gaussien proportionnel à sa plage."""
    child = dict(genes)
    for name, (lo, hi, _) in GENE_SPACE.items():
        if rng.random() < 0.6:
            child[name] = _clip(name, child[name] + rng.gauss(0.0, strength * (hi - lo)))
    return _repair(child)


def crossover(a: dict, b: dict, rng: random.Random) -> dict:
    return _repair({name: (a if rng.random() < 0.5 else b)[name] for name in GENE_SPACE})
