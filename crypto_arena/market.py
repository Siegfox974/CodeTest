"""Données de marché : marché synthétique, chargement CSV et import Binance."""

from __future__ import annotations

import csv
import json
import math
import random
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# (prix initial, volatilité horaire propre, sensibilité au marché global)
DEFAULT_ASSETS = {
    "BTC": (60_000.0, 0.004, 1.0),
    "ETH": (3_000.0, 0.006, 1.2),
    "SOL": (150.0, 0.009, 1.5),
    "DOGE": (0.15, 0.012, 1.7),
}

# Régimes de marché : dérive horaire et volatilité du facteur commun
REGIMES = {
    "haussier": (0.00035, 0.004),
    "baissier": (-0.00040, 0.005),
    "latéral": (0.0, 0.003),
}


@dataclass
class Market:
    symbols: list[str]
    closes: dict[str, list[float]]
    timestamps: list[int]
    source: str = "inconnue"
    _prefix: dict[str, list[float]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        lengths = {len(self.closes[s]) for s in self.symbols}
        if len(lengths) != 1 or len(self.timestamps) not in lengths:
            raise ValueError("toutes les séries de prix doivent avoir la même longueur")
        for sym in self.symbols:
            acc, prefix = 0.0, [0.0]
            for p in self.closes[sym]:
                acc += p
                prefix.append(acc)
            self._prefix[sym] = prefix

    def __len__(self) -> int:
        return len(self.timestamps)

    def price(self, sym: str, t: int) -> float:
        return self.closes[sym][t]

    def prices_at(self, t: int) -> dict[str, float]:
        return {s: self.closes[s][t] for s in self.symbols}

    def sma(self, sym: str, t: int, n: int) -> float:
        """Moyenne mobile simple des n dernières clôtures jusqu'à t inclus."""
        lo = max(0, t - n + 1)
        prefix = self._prefix[sym]
        return (prefix[t + 1] - prefix[lo]) / (t + 1 - lo)

    def to_csv(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", *self.symbols])
            for i, ts in enumerate(self.timestamps):
                w.writerow([ts, *(repr(self.closes[s][i]) for s in self.symbols)])


def generate_synthetic(n_ticks: int = 3000, seed: int = 42, assets: dict | None = None) -> Market:
    """Marché horaire simulé : facteur commun à régimes + bruit propre + krachs/pumps rares."""
    assets = assets or DEFAULT_ASSETS
    rng = random.Random(seed)
    regime_names = list(REGIMES)
    regime = rng.choice(regime_names)
    prices = {s: params[0] for s, params in assets.items()}
    closes: dict[str, list[float]] = {s: [] for s in assets}
    for _ in range(n_ticks):
        if rng.random() > 0.995:
            regime = rng.choice([r for r in regime_names if r != regime])
        drift, vol = REGIMES[regime]
        common = drift + rng.gauss(0.0, vol)
        if rng.random() < 0.002:
            common += rng.gauss(0.0, 0.04)
        for sym, (_, own_vol, beta) in assets.items():
            prices[sym] *= math.exp(beta * common + rng.gauss(0.0, own_vol))
            closes[sym].append(prices[sym])
    start = 1_700_000_000
    return Market(
        symbols=list(assets),
        closes=closes,
        timestamps=[start + 3600 * i for i in range(n_ticks)],
        source=f"synthétique (seed={seed})",
    )


def load_csv(path: str | Path) -> Market:
    """CSV au format large : timestamp,SYM1,SYM2,..."""
    with Path(path).open(newline="") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    symbols = header[1:]
    closes = {s: [float(r[i + 1]) for r in body] for i, s in enumerate(symbols)}
    return Market(
        symbols=symbols,
        closes=closes,
        timestamps=[int(float(r[0])) for r in body],
        source=f"csv:{path}",
    )


def fetch_binance(symbols: list[str], interval: str = "1h", limit: int = 1000) -> Market:
    """Clôtures publiques Binance (aucune clé requise), alignées sur les horodatages communs."""
    series: dict[str, dict[int, float]] = {}
    for sym in symbols:
        url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval={interval}&limit={limit}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            klines = json.load(resp)
        series[sym] = {int(k[0]) // 1000: float(k[4]) for k in klines}
    common = sorted(set.intersection(*(set(s) for s in series.values())))
    names = [s.removesuffix("USDT") for s in symbols]
    return Market(
        symbols=names,
        closes={n: [series[s][ts] for ts in common] for n, s in zip(names, symbols)},
        timestamps=common,
        source=f"binance {interval}",
    )
