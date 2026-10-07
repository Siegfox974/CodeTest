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
    threshold: float = 0.0          # seuil de mort : capital confié moins la perte tolérée
    holdings: dict[str, float] = field(default_factory=dict)
    cost_basis: dict[str, float] = field(default_factory=dict)   # USDT dépensés (frais compris) par position
    inherited_from: str | None = None
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

    def open(self, owner: str, capital: float, max_loss: float = 0.0) -> Account:
        with self.lock:
            acc = Account(owner, capital, capital, threshold=capital - max_loss, peak=capital)
            self.accounts[owner] = acc
            return acc

    def inherit(self, heir: str, from_owner: str, max_loss: float) -> Account:
        """Le successeur reprend le portefeuille tel quel. Ce qu'on lui confie, c'est sa valeur à cet instant."""
        with self.lock:
            old = self.accounts[from_owner]
            value = old.value(self.prices())
            acc = Account(heir, value, old.cash, threshold=value - max_loss, holdings=dict(old.holdings),
                          cost_basis=dict(old.cost_basis), inherited_from=from_owner, peak=value)
            self.accounts[heir] = acc
            return acc

    def prices(self) -> dict[str, float]:
        return dict(self.feed.prices)

    def value(self, owner: str) -> float:
        with self.lock:
            return self.accounts[owner].value(self.prices())

    def snapshot(self, owner: str) -> dict:
        with self.lock:
            acc = self.accounts[owner]
            prices = self.prices()
            value = acc.value(prices)
            acc.peak = max(acc.peak, value)
            positions = {}
            for s, q in acc.holdings.items():
                cost = acc.cost_basis.get(s, 0.0)
                positions[s] = {"quantite": q, "prix": prices[s], "valeur_usdt": round(q * prices[s], 2),
                                "prix_moyen_achat": cost / q if q else None,
                                "plus_ou_moins_value_usdt": round(q * prices[s] - cost, 2) if cost else None}
            return {
                "capital_confie": acc.capital,
                "valeur_totale": round(value, 2),
                "perte_toleree": round(acc.capital - acc.threshold, 2),
                "seuil_de_mort": round(acc.threshold, 2),
                "marge_avant_la_mort": round(value - acc.threshold, 2),
                "cash_usdt": round(acc.cash, 2),
                "part_investie_pct": round(acc.exposure(prices) * 100, 1),
                "positions": positions,
                "plus_haut": round(acc.peak, 2),
                "ordres_passes": acc.orders,
                "gele": acc.frozen,
                "herite_de": acc.inherited_from,
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
            acc.cost_basis[symbol] = acc.cost_basis.get(symbol, 0.0) + cost
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
            acc.cost_basis[symbol] = acc.cost_basis.get(symbol, 0.0) * (1 - qty / held)
            if acc.holdings[symbol] <= held * 1e-12:
                del acc.holdings[symbol]
                acc.cost_basis.pop(symbol, None)
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
