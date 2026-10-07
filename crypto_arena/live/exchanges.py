"""Connecteurs aux API publiques des bourses (aucune clé requise) : prix, bougies et carnets d'ordres en temps réel."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

USER_AGENT = "crypto-arena/1.0 (paper trading)"


def http_get(url: str, timeout: float = 10.0, headers: dict | None = None) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _f(value) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


@dataclass
class Quote:
    last: float
    bid: float | None = None
    ask: float | None = None
    change_pct: float | None = None
    high: float | None = None
    low: float | None = None
    volume_usd: float | None = None


def _candle(t, o, h, l, c, v) -> dict:
    return {"t": int(float(t)), "o": float(o), "h": float(h), "l": float(l), "c": float(c), "v": float(v)}


class Exchange:
    name = "?"
    candle_intervals: dict[str, str] = {}

    def __init__(self, get=http_get):
        self.get = get
        self.unsupported: set[str] = set()   # symboles absents de cette bourse

    def url(self, path: str, **params) -> str:
        return f"{self.base}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")

    def tickers(self, symbols: list[str]) -> dict[str, Quote]:
        raise NotImplementedError

    def candles(self, symbol: str, interval: str, limit: int) -> list[dict]:
        raise NotImplementedError

    def order_book(self, symbol: str, depth: int) -> dict:
        raise NotImplementedError


class Gate(Exchange):
    """Gate : un seul appel renvoie tous les tickers."""
    name = "Gate"
    base = "https://api.gateio.ws/api/v4"
    candle_intervals = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d", "1w": "7d"}

    def tickers(self, symbols):
        wanted = {f"{s}_USDT": s for s in symbols}
        out = {}
        for d in self.get(self.url("/spot/tickers")):
            sym = wanted.get(d.get("currency_pair"))
            if sym and _f(d.get("last")):
                out[sym] = Quote(_f(d["last"]), _f(d.get("highest_bid")), _f(d.get("lowest_ask")),
                                 _f(d.get("change_percentage")), _f(d.get("high_24h")), _f(d.get("low_24h")),
                                 _f(d.get("quote_volume")))
        return out

    def candles(self, symbol, interval, limit):
        rows = self.get(self.url("/spot/candlesticks", currency_pair=f"{symbol}_USDT",
                                 interval=self.candle_intervals[interval], limit=limit))
        # [horodatage, volume en USDT, clôture, plus haut, plus bas, ouverture, volume de base, clôturée]
        return [_candle(r[0], r[5], r[3], r[4], r[2], r[1]) for r in rows]

    def order_book(self, symbol, depth):
        d = self.get(self.url("/spot/order_book", currency_pair=f"{symbol}_USDT", limit=depth))
        return {"bids": [[float(p), float(q)] for p, q, *_ in d["bids"]],
                "asks": [[float(p), float(q)] for p, q, *_ in d["asks"]]}


class Kraken(Exchange):
    """Kraken : une requête par paire. BTC s'y appelle XBT et DOGE XDG ; on essaie USDT puis USD."""
    name = "Kraken"
    base = "https://api.kraken.com/0/public"
    aliases = {"BTC": "XBT", "DOGE": "XDG"}
    candle_intervals = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "1440", "1w": "10080"}

    def __init__(self, get=http_get):
        super().__init__(get)
        self.pairs: dict[str, str] = {}

    def _call(self, path: str, symbol: str, **params) -> object:
        """Renvoie le contenu de la paire, en mémorisant le nom de paire qui fonctionne."""
        k = self.aliases.get(symbol, symbol)
        candidates = [self.pairs[symbol]] if symbol in self.pairs else [f"{k}USDT", f"{k}USD", f"{symbol}USD"]
        for pair in candidates:
            data = self.get(self.url(path, pair=pair, **params))
            if data.get("error"):
                continue
            result = {key: v for key, v in data["result"].items() if key != "last"}
            if result:
                self.pairs[symbol] = pair
                return next(iter(result.values()))
        self.unsupported.add(symbol)
        raise LookupError(f"{symbol} indisponible sur Kraken")

    def tickers(self, symbols):
        out, last_error = {}, None
        for sym in symbols:
            if sym in self.unsupported:
                continue
            try:
                d = self._call("/Ticker", sym)
            except LookupError:
                continue
            except Exception as e:  # une paire en erreur ne doit pas faire tomber les autres
                last_error = e
                continue
            last, opening = _f(d["c"][0]), _f(d.get("o"))
            out[sym] = Quote(last, _f(d["b"][0]), _f(d["a"][0]),
                             (last / opening - 1) * 100 if opening else None,
                             _f(d["h"][1]), _f(d["l"][1]), (_f(d["v"][1]) or 0) * last)
        if not out and last_error is not None:
            raise last_error
        return out

    def candles(self, symbol, interval, limit):
        rows = self._call("/OHLC", symbol, interval=self.candle_intervals[interval])
        # [horodatage, ouverture, plus haut, plus bas, clôture, vwap, volume, nombre de trades]
        return [_candle(r[0], r[1], r[2], r[3], r[4], r[6]) for r in rows][-limit:]

    def order_book(self, symbol, depth):
        d = self._call("/Depth", symbol, count=depth)
        return {"bids": [[float(p), float(q)] for p, q, *_ in d["bids"]],
                "asks": [[float(p), float(q)] for p, q, *_ in d["asks"]]}


class OKX(Exchange):
    name = "OKX"
    base = "https://www.okx.com/api/v5"
    candle_intervals = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D", "1w": "1W"}

    def tickers(self, symbols):
        wanted = {f"{s}-USDT": s for s in symbols}
        out = {}
        for d in self.get(self.url("/market/tickers", instType="SPOT"))["data"]:
            sym = wanted.get(d.get("instId"))
            if sym and _f(d.get("last")):
                last, opening = _f(d["last"]), _f(d.get("open24h"))
                out[sym] = Quote(last, _f(d.get("bidPx")), _f(d.get("askPx")),
                                 (last / opening - 1) * 100 if opening else None,
                                 _f(d.get("high24h")), _f(d.get("low24h")), _f(d.get("volCcy24h")))
        return out

    def candles(self, symbol, interval, limit):
        rows = self.get(self.url("/market/candles", instId=f"{symbol}-USDT", bar=self.candle_intervals[interval],
                                 limit=min(limit, 300)))["data"]
        # du plus récent au plus ancien : [ms, ouverture, haut, bas, clôture, volume, ...]
        return [_candle(int(r[0]) // 1000, r[1], r[2], r[3], r[4], r[5]) for r in reversed(rows)]

    def order_book(self, symbol, depth):
        d = self.get(self.url("/market/books", instId=f"{symbol}-USDT", sz=depth))["data"][0]
        return {"bids": [[float(r[0]), float(r[1])] for r in d["bids"]],
                "asks": [[float(r[0]), float(r[1])] for r in d["asks"]]}


class Bybit(Exchange):
    name = "Bybit"
    base = "https://api.bybit.com/v5"

    def tickers(self, symbols):
        wanted = {f"{s}USDT": s for s in symbols}
        out = {}
        for d in self.get(self.url("/market/tickers", category="spot"))["result"]["list"]:
            sym = wanted.get(d.get("symbol"))
            if sym and _f(d.get("lastPrice")):
                change = _f(d.get("price24hPcnt"))
                out[sym] = Quote(_f(d["lastPrice"]), _f(d.get("bid1Price")), _f(d.get("ask1Price")),
                                 change * 100 if change is not None else None,
                                 _f(d.get("highPrice24h")), _f(d.get("lowPrice24h")), _f(d.get("turnover24h")))
        return out


class KuCoin(Exchange):
    name = "KuCoin"
    base = "https://api.kucoin.com/api/v1"

    def tickers(self, symbols):
        wanted = {f"{s}-USDT": s for s in symbols}
        out = {}
        for d in self.get(self.url("/market/allTickers"))["data"]["ticker"]:
            sym = wanted.get(d.get("symbol"))
            if sym and _f(d.get("last")):
                change = _f(d.get("changeRate"))
                out[sym] = Quote(_f(d["last"]), _f(d.get("buy")), _f(d.get("sell")),
                                 change * 100 if change is not None else None,
                                 _f(d.get("high")), _f(d.get("low")), _f(d.get("volValue")))
        return out


class Coinbase(Exchange):
    """Coinbase Exchange : paires en USD, une requête par actif."""
    name = "Coinbase"
    base = "https://api.exchange.coinbase.com"
    candle_intervals = {"1m": "60", "5m": "300", "15m": "900", "1h": "3600", "1d": "86400"}

    def tickers(self, symbols):
        out, last_error = {}, None
        for sym in symbols:
            if sym in self.unsupported:
                continue
            try:
                d = self.get(self.url(f"/products/{sym}-USD/ticker"))
            except Exception as e:  # produit inexistant : on ne le redemandera plus
                if "404" in str(e) or "400" in str(e):
                    self.unsupported.add(sym)
                else:
                    last_error = e
                continue
            if _f(d.get("price")):
                out[sym] = Quote(_f(d["price"]), _f(d.get("bid")), _f(d.get("ask")))
        if not out and last_error is not None:
            raise last_error
        return out

    def candles(self, symbol, interval, limit):
        rows = self.get(self.url(f"/products/{symbol}-USD/candles", granularity=self.candle_intervals[interval]))
        # du plus récent au plus ancien : [horodatage, bas, haut, ouverture, clôture, volume]
        return [_candle(r[0], r[3], r[2], r[1], r[4], r[5]) for r in reversed(rows)][-limit:]


class Binance(Exchange):
    name = "Binance"
    base = "https://data-api.binance.vision/api/v3"
    candle_intervals = {i: i for i in ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]}

    def tickers(self, symbols):
        pairs = json.dumps([f"{s}USDT" for s in symbols], separators=(",", ":"))
        out = {}
        for d in self.get(self.url("/ticker/24hr", symbols=pairs)):
            sym = d["symbol"].removesuffix("USDT")
            out[sym] = Quote(_f(d["lastPrice"]), _f(d.get("bidPrice")), _f(d.get("askPrice")),
                             _f(d.get("priceChangePercent")), _f(d.get("highPrice")), _f(d.get("lowPrice")),
                             _f(d.get("quoteVolume")))
        return out

    def candles(self, symbol, interval, limit):
        rows = self.get(self.url("/klines", symbol=f"{symbol}USDT", interval=interval, limit=limit))
        return [_candle(int(r[0]) // 1000, r[1], r[2], r[3], r[4], r[7]) for r in rows]

    def order_book(self, symbol, depth):
        d = self.get(self.url("/depth", symbol=f"{symbol}USDT", limit=depth))
        return {"bids": [[float(p), float(q)] for p, q in d["bids"]],
                "asks": [[float(p), float(q)] for p, q in d["asks"]]}


def extract(data: object, path: str) -> object:
    """Suit un chemin du type `result.*.c.0` : clé, indice, ou `*` pour le premier élément."""
    for key in [k for k in path.split(".") if k]:
        if key == "*":
            data = next(iter(data.values())) if isinstance(data, dict) else data[0]
        elif isinstance(data, list):
            data = data[int(key)]
        else:
            data = data[key]
    return data


class CustomExchange(Exchange):
    """Une API ajoutée par l'utilisateur : une URL par actif contenant {symbol}, et le chemin du prix dans le JSON."""

    def __init__(self, name: str, url: str, symbol_format: str = "{SYM}USDT", price_path: str = "price",
                 headers: dict | None = None, get=http_get):
        super().__init__(get)
        if "{symbol}" not in url or not url.startswith(("http://", "https://")):
            raise ValueError("l'URL doit commencer par http(s):// et contenir {symbol}")
        self.name = name
        self.url_template = url
        self.symbol_format = symbol_format or "{SYM}USDT"
        self.price_path = price_path or "price"
        self.headers = headers or {}

    def _symbol(self, sym: str) -> str:
        return self.symbol_format.replace("{SYM}", sym.upper()).replace("{sym}", sym.lower())

    def tickers(self, symbols):
        out, last_error = {}, None
        for sym in symbols:
            if sym in self.unsupported:
                continue
            pair = self._symbol(sym)
            url = self.url_template.replace("{symbol}", urllib.parse.quote(pair, safe=""))
            try:
                data = self.get(url, headers=self.headers) if self.headers else self.get(url)
                price = _f(extract(data, self.price_path.replace("{symbol}", pair)))
            except Exception as e:
                last_error = e
                continue
            if price:
                out[sym] = Quote(price)
        if not out and last_error is not None:
            raise last_error
        return out


ALL_EXCHANGES = [Kraken, Gate, Coinbase, OKX, Bybit, KuCoin, Binance]
