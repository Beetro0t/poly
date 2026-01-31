"""Quantitative analytics for slippage, beliefs, and expected value."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Tuple

import numpy as np
from scipy.stats import beta as beta_dist

from models import Orderbook, TradeScenario


class Side(StrEnum):
    """Trade direction for orderbook walking."""

    BUY = "buy"
    SELL = "sell"


class OrderbookDepthError(RuntimeError):
    """Raised when an orderbook cannot fill the requested trade size."""


@dataclass
class BetaModel:
    """Beta distribution model for binary event beliefs."""

    belief_probability: float
    confidence_strength: float

    def parameters(self) -> Tuple[float, float]:
        """Convert belief inputs to alpha/beta parameters."""
        belief = np.clip(self.belief_probability, 0.0, 1.0)
        strength = np.clip(self.confidence_strength, 1.0, 100.0)
        alpha = belief * strength + 1.0
        beta = (1.0 - belief) * strength + 1.0
        return alpha, beta

    def pdf(self, points: int = 200) -> Tuple[np.ndarray, np.ndarray]:
        """Return x/y arrays for plotting the beta PDF."""
        alpha, beta = self.parameters()
        x = np.linspace(0.0, 1.0, points)
        y = beta_dist.pdf(x, alpha, beta)
        return x, y


def calculate_effective_price(
    orderbook: Orderbook, side: Side, trade_size_usd: float
) -> float:
    """Walk the orderbook and compute the VWAP for the trade size."""
    if trade_size_usd <= 0:
        raise ValueError("Trade size must be positive")

    levels = orderbook.asks if side == Side.BUY else orderbook.bids
    remaining_notional = trade_size_usd
    total_cost = 0.0
    total_shares = 0.0

    for level in levels:
        level_notional = level.price * level.size
        if level_notional <= 0:
            continue
        if remaining_notional <= level_notional:
            fill_shares = remaining_notional / level.price
            total_cost += remaining_notional
            total_shares += fill_shares
            remaining_notional = 0.0
            break
        total_cost += level_notional
        total_shares += level.size
        remaining_notional -= level_notional

    if remaining_notional > 0:
        raise OrderbookDepthError("Orderbook depth insufficient for trade size")
    if total_shares <= 0:
        raise OrderbookDepthError("Orderbook has no liquidity")
    return total_cost / total_shares


def compute_trade_metrics(
    entry_price: float, target_probability: float, trade_size: float
) -> TradeScenario:
    """Compute expected value and Kelly sizing for a trade."""
    price = float(np.clip(entry_price, 0.0, 1.0))
    probability = float(np.clip(target_probability, 0.0, 1.0))
    ev = (probability * 1.0) - price
    denominator = max(1.0 - price, 1e-6)
    kelly_fraction = max(0.0, ev / denominator)

    return TradeScenario(
        trade_size_usd=trade_size,
        belief_probability=probability,
        effective_entry_price=price,
        ev_percentage=ev * 100.0,
        kelly_fraction=kelly_fraction,
    )
