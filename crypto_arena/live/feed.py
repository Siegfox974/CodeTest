"""Flux de marché : prix réels via l'API publique Binance, ou marché simulé pour la démo."""

from __future__ import annotations

import json
import math
import random
import threading
import time
import urllib.parse
import urllib.request

DEFAULT_UNIVERSE = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "PEPE"]
BINANCE_BASES = ["https://api.binance.com", "https://data-api.binance.vision"]
INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]


class FeedError(RuntimeError):
    pass


class BinanceFeed:
    """Données publiques de Binance (aucune clé requise). Tous les prix sont en USDT."""

    def __init__(self, symbols: list[str] | None = None, timeout: float = 15.0):
        self.symbols = symbols or list(DEFAULT_UNIVERSE)
        self.timeout = timeout
        self.prices: dict[str, float] = {}
        self.updated_at = 0.0
        self._base = BINANCE_BASES[0]
        self._lock = threading.Lock()
        self.source = "Binance (prix réels)"

    def _get(self, path: str, params: dict) -> object:
        query = urllib.parse.urlencode(params)
        last_error: Exception | None = None
        for base in [self._base] + [b for b in BINANCE_BASES if b != self._base]:
            try:
                with urllib.request.urlopen(f"{base}{path}?{query}", timeout=self.timeout) as resp:
                    self._base = base
                    return json.load(resp)
            except Exception as e:  # on tente le miroir suivant
                last_error = e
        raise FeedError(f"Binance injoignable : {last_error}")

    def _pairs(self) -> str:
        return json.dumps([f"{s}USDT" for s in self.symbols], separators=(",", ":"))

    def refresh(self) -> dict[str, float]:
        data = self._get("/api/v3/ticker/price", {"symbols": self._pairs()})
        prices = {d["symbol"].removesuffix("USDT"): float(d["price"]) for d in data}
        with self._lock:
            self.prices = prices
            self.updated_at = time.time()
        return dict(prices)

    def price(self, symbol: str) -> float:
        with self._lock:
            if symbol not in self.prices:
                raise FeedError(f"{symbol} ne fait pas partie de l'univers {self.symbols}")
            return self.prices[symbol]

    def stats_24h(self) -> dict[str, dict]:
        data = self._get("/api/v3/ticker/24hr", {"symbols": self._pairs()})
        return {
            d["symbol"].removesuffix("USDT"): {
                "prix": float(d["lastPrice"]),
                "variation_24h_pct": float(d["priceChangePercent"]),
                "plus_haut_24h": float(d["highPrice"]),
                "plus_bas_24h": float(d["lowPrice"]),
                "volume_24h_usdt": round(float(d["quoteVolume"])),
            }
            for d in data
        }

    def candles(self, symbol: str, interval: str = "1h", limit: int = 48) -> list[dict]:
        if symbol not in self.symbols:
            raise FeedError(f"{symbol} ne fait pas partie de l'univers {self.symbols}")
        if interval not in INTERVALS:
            raise FeedError(f"intervalle inconnu {interval}, choisir parmi {INTERVALS}")
        rows = self._get("/api/v3/klines", {"symbol": f"{symbol}USDT", "interval": interval, "limit": min(limit, 200)})
        return [{"t": int(r[0]) // 1000, "o": float(r[1]), "h": float(r[2]), "l": float(r[3]),
                 "c": float(r[4]), "v": float(r[5])} for r in rows]


class SimulatedFeed:
    """Marché fictif qui bouge à chaque rafraîchissement : pour tester l'interface sans réseau."""

    START = {"BTC": 62_000.0, "ETH": 3_100.0, "SOL": 150.0, "BNB": 580.0, "XRP": 0.55,
             "DOGE": 0.12, "ADA": 0.45, "AVAX": 28.0, "LINK": 14.0, "PEPE": 0.0000095}

    def __init__(self, symbols: list[str] | None = None, seed: int = 0, volatility: float = 0.004):
        self.symbols = symbols or list(DEFAULT_UNIVERSE)
        self.rng = random.Random(seed)
        self.volatility = volatility
        self._lock = threading.Lock()
        self.history: dict[str, list[float]] = {s: [self.START.get(s, 1.0)] for s in self.symbols}
        for _ in range(300):
            self._step()
        self.prices = {s: h[-1] for s, h in self.history.items()}
        self.updated_at = time.time()
        self.source = "marché simulé (démo)"

    def _step(self) -> None:
        common = self.rng.gauss(0.0, self.volatility)
        for s, h in self.history.items():
            h.append(h[-1] * math.exp(common + self.rng.gauss(0.0, self.volatility)))
            del h[:-1000]

    def refresh(self) -> dict[str, float]:
        with self._lock:
            self._step()
            self.prices = {s: h[-1] for s, h in self.history.items()}
            self.updated_at = time.time()
            return dict(self.prices)

    def price(self, symbol: str) -> float:
        with self._lock:
            if symbol not in self.prices:
                raise FeedError(f"{symbol} ne fait pas partie de l'univers {self.symbols}")
            return self.prices[symbol]

    def stats_24h(self) -> dict[str, dict]:
        with self._lock:
            out = {}
            for s, h in self.history.items():
                day = h[-24:]
                out[s] = {"prix": h[-1], "variation_24h_pct": round((h[-1] / day[0] - 1) * 100, 2),
                          "plus_haut_24h": max(day), "plus_bas_24h": min(day), "volume_24h_usdt": 0}
            return out

    def candles(self, symbol: str, interval: str = "1h", limit: int = 48) -> list[dict]:
        if symbol not in self.symbols:
            raise FeedError(f"{symbol} ne fait pas partie de l'univers {self.symbols}")
        with self._lock:
            h = self.history[symbol][-min(limit, 200):]
        return [{"t": i, "o": p, "h": p, "l": p, "c": p, "v": 0.0} for i, p in enumerate(h)]
