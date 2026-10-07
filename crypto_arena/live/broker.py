"""Le courtier fictif : il détient les comptes, exécute les ordres au prix réel du marché et fait foi."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


class OrderRejected(RuntimeError):
    pass


@dataclass
class Account:
    owner: str
    capital: float
    cash: float
    holdings: dict[str, float] = field(default_factory=dict)
    frozen: str | None = None
    orders: int = 0
    peak: float = 0.0

    def value(self, prices: dict[str, float]) -> float:
        return self.cash + sum(q * prices[s] for s, q in self.holdings.items())

    def exposure(self, prices: dict[str, float]) -> float:
        v = self.value(prices)
        return (v - self.cash) / v if v > 0 else 0.0


class PaperBroker:
    def __init__(self, feed, fee_rate: float = 0.001):
        self.feed = feed
        self.fee_rate = fee_rate
        self.accounts: dict[str, Account] = {}
        self.lock = threading.RLock()

    def open(self, owner: str, capital: float) -> Account:
        with self.lock:
            acc = Account(owner, capital, capital, peak=capital)
            self.accounts[owner] = acc
            return acc

    def prices(self) -> dict[str, float]:
        return {s: self.feed.price(s) for s in self.feed.symbols}

    def snapshot(self, owner: str) -> dict:
        with self.lock:
            acc = self.accounts[owner]
            prices = self.prices()
            value = acc.value(prices)
            acc.peak = max(acc.peak, value)
            positions = {
                s: {"quantite": q, "prix": prices[s], "valeur_usdt": round(q * prices[s], 2)}
                for s, q in acc.holdings.items()
            }
            return {
                "capital_confie": acc.capital,
                "valeur_totale": round(value, 2),
                "marge_avant_la_mort": round(value - acc.capital, 2),
                "cash_usdt": round(acc.cash, 2),
                "part_investie_pct": round(acc.exposure(prices) * 100, 1),
                "positions": positions,
                "plus_haut": round(acc.peak, 2),
                "ordres_passes": acc.orders,
                "gele": acc.frozen,
            }

    def buy(self, owner: str, symbol: str, usdt: float) -> dict:
        with self.lock:
            acc = self._active(owner)
            if usdt <= 0:
                raise OrderRejected("le montant doit être positif")
            cost = usdt * (1 + self.fee_rate)
            if cost > acc.cash + 1e-9:
                raise OrderRejected(f"cash insuffisant : {acc.cash:.2f} USDT disponibles (frais compris)")
            price = self.feed.price(symbol)
            qty = usdt / price
            acc.cash -= cost
            acc.holdings[symbol] = acc.holdings.get(symbol, 0.0) + qty
            acc.orders += 1
            return {"achat": symbol, "quantite": qty, "prix": price, "montant_usdt": usdt, "frais": usdt * self.fee_rate}

    def sell(self, owner: str, symbol: str, percent: float) -> dict:
        with self.lock:
            acc = self._active(owner)
            held = acc.holdings.get(symbol, 0.0)
            if held <= 0:
                raise OrderRejected(f"aucune position en {symbol}")
            percent = min(100.0, max(0.0, percent))
            if percent <= 0:
                raise OrderRejected("le pourcentage doit être positif")
            qty = held if percent >= 100 else held * percent / 100
            price = self.feed.price(symbol)
            proceeds = qty * price
            acc.cash += proceeds * (1 - self.fee_rate)
            acc.holdings[symbol] = held - qty
            if acc.holdings[symbol] <= held * 1e-12:
                del acc.holdings[symbol]
            acc.orders += 1
            return {"vente": symbol, "quantite": qty, "prix": price, "montant_usdt": proceeds,
                    "frais": proceeds * self.fee_rate}

    def freeze(self, owner: str, reason: str) -> None:
        with self.lock:
            self.accounts[owner].frozen = reason

    def _active(self, owner: str) -> Account:
        acc = self.accounts[owner]
        if acc.frozen:
            raise OrderRejected(f"compte gelé : {acc.frozen}")
        return acc
