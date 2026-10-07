"""Flux de marché temps réel multi-bourses (prix de consensus), ou marché simulé pour la démo."""

from __future__ import annotations

import math
import random
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait

from .exchanges import ALL_EXCHANGES, Quote, http_get

DEFAULT_UNIVERSE = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "PEPE"]
INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]


class FeedError(RuntimeError):
    pass


class MultiExchangeFeed:
    """Interroge toutes les bourses en parallèle à chaque rafraîchissement. Le prix retenu pour un actif est la
    médiane des bourses qui le cotent ; une cotation qui s'en écarte de plus de `max_deviation` est ignorée."""

    def __init__(self, symbols: list[str] | None = None, exchanges: list | None = None, get=http_get,
                 max_deviation: float = 0.02, deadline: float = 8.0):
        self.symbols = symbols or list(DEFAULT_UNIVERSE)
        self.exchanges = exchanges or [cls(get) for cls in ALL_EXCHANGES]
        self.max_deviation = max_deviation
        self.deadline = deadline                  # au-delà, une bourse est déclarée sans réponse
        self._pending: dict[str, object] = {}     # requêtes encore en cours d'un relevé précédent
        self.prices: dict[str, float] = {}
        self.quotes: dict[str, dict[str, Quote]] = {}
        self.status: dict[str, str] = {}          # bourse -> "ok" ou message d'erreur
        self.updated_at = 0.0
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=len(self.exchanges))
        self.source = "temps réel : " + ", ".join(e.name for e in self.exchanges)

    def _fetch(self, ex) -> tuple[str, dict[str, Quote] | None, str]:
        try:
            quotes = ex.tickers(self.symbols)
            return ex.name, quotes, "ok" if quotes else "aucun actif coté"
        except Exception as e:
            return ex.name, None, f"{e.__class__.__name__}: {e}"[:160]

    def refresh(self) -> dict[str, float]:
        futures = {}
        for ex in self.exchanges:
            previous = self._pending.get(ex.name)
            futures[ex.name] = previous if previous is not None and not previous.done() else self._pool.submit(self._fetch, ex)
        done, _ = wait(futures.values(), timeout=self.deadline)
        results = []
        for name, fut in futures.items():
            if fut in done:
                self._pending.pop(name, None)
                results.append(fut.result())
            else:
                self._pending[name] = fut
                results.append((name, None, f"pas de réponse en {self.deadline:.0f} s"))
        by_symbol: dict[str, dict[str, Quote]] = {s: {} for s in self.symbols}
        status = {}
        for name, quotes, state in results:
            status[name] = state
            for sym, q in (quotes or {}).items():
                if sym in by_symbol and q.last and q.last > 0:
                    by_symbol[sym][name] = q
        prices = {}
        for sym, quotes in by_symbol.items():
            if not quotes:
                continue
            median = statistics.median(q.last for q in quotes.values())
            kept = {n: q for n, q in quotes.items() if abs(q.last / median - 1) <= self.max_deviation}
            by_symbol[sym] = kept
            prices[sym] = statistics.median(q.last for q in kept.values())
        if not prices:
            with self._lock:
                self.status = status
            raise FeedError("aucune bourse ne répond : " + "; ".join(f"{n} → {s}" for n, s in status.items()))
        with self._lock:
            self.prices = {**self.prices, **prices}
            self.quotes = by_symbol
            self.status = status
            self.updated_at = time.time()
            return dict(self.prices)

    def price(self, symbol: str) -> float:
        with self._lock:
            if symbol not in self.prices:
                raise FeedError(f"aucun prix disponible pour {symbol} (univers : {self.symbols})")
            return self.prices[symbol]

    def stats_24h(self) -> dict[str, dict]:
        with self._lock:
            out = {}
            for sym, quotes in self.quotes.items():
                if sym not in self.prices:
                    continue
                with_stats = [q for q in quotes.values() if q.change_pct is not None]
                ref = with_stats[0] if with_stats else None
                out[sym] = {
                    "prix_consensus": self.prices[sym],
                    "variation_24h_pct": round(statistics.median(q.change_pct for q in with_stats), 2) if with_stats else None,
                    "plus_haut_24h": ref.high if ref else None,
                    "plus_bas_24h": ref.low if ref else None,
                    "volume_24h_usd_toutes_bourses": round(sum(q.volume_usd or 0 for q in quotes.values())),
                    "bourses": sorted(quotes),
                }
            return out

    def compare(self, symbol: str) -> dict:
        with self._lock:
            quotes = self.quotes.get(symbol, {})
            consensus = self.prices.get(symbol)
        if not quotes:
            raise FeedError(f"aucune bourse ne cote {symbol} en ce moment")
        lasts = [q.last for q in quotes.values()]
        return {
            "symbole": symbol, "prix_consensus": consensus,
            "ecart_max_entre_bourses_pct": round((max(lasts) / min(lasts) - 1) * 100, 3),
            "bourses": {n: {"dernier": q.last, "achat": q.bid, "vente": q.ask,
                            "spread_pct": round((q.ask / q.bid - 1) * 100, 4) if q.bid and q.ask else None}
                        for n, q in quotes.items()},
        }

    def _first(self, method: str, symbol: str, *args) -> tuple[str, object]:
        if symbol not in self.symbols:
            raise FeedError(f"{symbol} ne fait pas partie de l'univers {self.symbols}")
        errors = []
        for ex in self.exchanges:
            fn = getattr(ex, method)
            if symbol in ex.unsupported or (method == "candles" and args[0] not in ex.candle_intervals):
                continue
            try:
                data = fn(symbol, *args)
                if data:
                    return ex.name, data
            except NotImplementedError:
                continue
            except Exception as e:
                errors.append(f"{ex.name}: {e}"[:120])
        raise FeedError(f"aucune bourse n'a répondu pour {symbol} ({'; '.join(errors) or 'non disponible'})")

    def candles(self, symbol: str, interval: str = "1h", limit: int = 48) -> list[dict]:
        if interval not in INTERVALS:
            raise FeedError(f"intervalle inconnu {interval}, choisir parmi {INTERVALS}")
        name, rows = self._first("candles", symbol, interval, limit)
        self.last_candle_source = name
        return rows[-limit:]

    def order_book(self, symbol: str, depth: int = 10) -> tuple[str, dict]:
        return self._first("order_book", symbol, depth)


class SimulatedFeed:
    """Marché fictif qui bouge à chaque rafraîchissement : pour tester l'interface sans réseau."""

    START = {"BTC": 62_000.0, "ETH": 3_100.0, "SOL": 150.0, "BNB": 580.0, "XRP": 0.55,
             "DOGE": 0.12, "ADA": 0.45, "AVAX": 28.0, "LINK": 14.0, "PEPE": 0.0000095}
    VENUES = ["Kraken (simulé)", "Gate (simulé)", "OKX (simulé)"]

    def __init__(self, symbols: list[str] | None = None, seed: int = 0, volatility: float = 0.004):
        self.symbols = symbols or list(DEFAULT_UNIVERSE)
        self.rng = random.Random(seed)
        self.volatility = volatility
        self._lock = threading.Lock()
        self.history: dict[str, list[float]] = {s: [self.START.get(s, 1.0)] for s in self.symbols}
        for _ in range(300):
            self._step()
        self.prices = {s: h[-1] for s, h in self.history.items()}
        self.status = {v: "ok" for v in self.VENUES}
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
                out[s] = {"prix_consensus": h[-1], "variation_24h_pct": round((h[-1] / day[0] - 1) * 100, 2),
                          "plus_haut_24h": max(day), "plus_bas_24h": min(day), "bourses": self.VENUES}
            return out

    def compare(self, symbol: str) -> dict:
        p = self.price(symbol)
        return {"symbole": symbol, "prix_consensus": p, "ecart_max_entre_bourses_pct": 0.05,
                "bourses": {v: {"dernier": p * (1 + 0.0002 * i), "achat": p * 0.9995, "vente": p * 1.0005,
                                "spread_pct": 0.1} for i, v in enumerate(self.VENUES)}}

    def candles(self, symbol: str, interval: str = "1h", limit: int = 48) -> list[dict]:
        if symbol not in self.symbols:
            raise FeedError(f"{symbol} ne fait pas partie de l'univers {self.symbols}")
        with self._lock:
            h = self.history[symbol][-min(limit, 200):]
        self.last_candle_source = "simulé"
        return [{"t": i, "o": p, "h": p, "l": p, "c": p, "v": 0.0} for i, p in enumerate(h)]

    def order_book(self, symbol: str, depth: int = 10) -> tuple[str, dict]:
        p = self.price(symbol)
        return "simulé", {"bids": [[p * (1 - 0.0005 * (i + 1)), 1.0] for i in range(depth)],
                          "asks": [[p * (1 + 0.0005 * (i + 1)), 1.0] for i in range(depth)]}

