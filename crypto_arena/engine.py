"""Portefeuille, session de trading et backtest : la même boucle sert en direct et en simulation."""

from __future__ import annotations

from dataclasses import dataclass, field

from .market import Market

# Code de sortie d'un agent qui s'élimine lui-même après avoir enfreint la règle
DEATH_EXIT_CODE = 66


@dataclass
class Context:
    """Ce que l'agent sait de lui-même au moment de décider."""
    capital: float
    value: float
    peak: float
    weights: dict[str, float]


@dataclass
class Portfolio:
    cash: float
    holdings: dict[str, float] = field(default_factory=dict)

    def value(self, prices: dict[str, float]) -> float:
        return self.cash + sum(q * prices[s] for s, q in self.holdings.items())

    def weights(self, prices: dict[str, float]) -> dict[str, float]:
        v = self.value(prices)
        return {s: q * prices[s] / v for s, q in self.holdings.items() if q > 0} if v > 0 else {}

    def rebalance(self, targets: dict[str, float], prices: dict[str, float],
                  fee_rate: float, band: float) -> int:
        """Ramène le portefeuille vers les poids cibles (long uniquement). Renvoie le nombre d'ordres."""
        targets = {s: max(0.0, float(w)) for s, w in targets.items() if s in prices}
        total = sum(targets.values())
        if total > 1.0:
            targets = {s: w / total for s, w in targets.items()}
        v = self.value(prices)
        orders = 0
        diffs = {}
        for sym in prices:
            current = self.holdings.get(sym, 0.0) * prices[sym]
            target = targets.get(sym, 0.0) * v
            if target == 0.0 and current > 0.0:
                diffs[sym] = -current
            elif abs(target - current) >= band * v:
                diffs[sym] = target - current
        for sym, diff in diffs.items():
            if diff < 0:
                qty = self.holdings.get(sym, 0.0) if targets.get(sym, 0.0) == 0.0 else min(
                    self.holdings.get(sym, 0.0), -diff / prices[sym])
                if qty <= 0:
                    continue
                self.cash += qty * prices[sym] * (1.0 - fee_rate)
                self.holdings[sym] = self.holdings.get(sym, 0.0) - qty
                if self.holdings[sym] <= 1e-15:
                    del self.holdings[sym]
                orders += 1
        for sym, diff in diffs.items():
            if diff > 0:
                notional = min(diff, self.cash / (1.0 + fee_rate))
                if notional <= 0:
                    continue
                self.holdings[sym] = self.holdings.get(sym, 0.0) + notional / prices[sym]
                self.cash -= notional * (1.0 + fee_rate)
                orders += 1
        return orders


class TradingSession:
    def __init__(self, brain, market: Market, capital: float, fee_rate: float):
        self.brain = brain
        self.market = market
        self.capital = capital
        self.fee_rate = fee_rate
        self.portfolio = Portfolio(cash=capital)
        self.peak = capital
        self.orders = 0

    def mark(self, t: int) -> float:
        value = self.portfolio.value(self.market.prices_at(t))
        self.peak = max(self.peak, value)
        return value

    def breaks_rule(self, value: float) -> bool:
        """La règle : passer sous le capital confié, ne serait-ce que d'un centime, est fatal."""
        return value < self.capital

    def act(self, t: int, value: float) -> int:
        prices = self.market.prices_at(t)
        ctx = Context(self.capital, value, self.peak, self.portfolio.weights(prices))
        targets = self.brain.decide(self.market, t, ctx)
        n = self.portfolio.rebalance(targets, prices, self.fee_rate, getattr(self.brain, "rebalance_band", 0.01))
        self.orders += n
        return n


@dataclass
class SimResult:
    start: int
    end: int
    died_at: int | None
    final_value: float
    peak: float
    orders: int

    @property
    def ticks_lived(self) -> int:
        return (self.died_at if self.died_at is not None else self.end) - self.start

    def fitness(self, capital: float) -> float:
        """Survivre vaut plus que tout ; ensuite on départage au rendement.
        Un agent qui n'investit jamais survit mais ne sert à rien : il est pénalisé."""
        span = max(1, self.end - self.start)
        if self.died_at is not None:
            return 0.99 * self.ticks_lived / span
        if self.orders == 0:
            return 0.5
        return 1.0 + (self.final_value - capital) / capital


def simulate(brain, market: Market, start: int, end: int, capital: float, fee_rate: float) -> SimResult:
    session = TradingSession(brain, market, capital, fee_rate)
    value = capital
    for t in range(start, end):
        value = session.mark(t)
        if session.breaks_rule(value):
            return SimResult(start, end, t, value, session.peak, session.orders)
        session.act(t, value)
    return SimResult(start, end, None, value, session.peak, session.orders)
