"""Pydantic data models for the Polymarket Research Terminal."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class Market(BaseModel):
    """Represents a Polymarket market and its core metadata."""

    id: str = Field(..., description="Polymarket market ID")
    question: str = Field(..., description="Human-readable market question")
    slug: str = Field(..., description="URL-friendly market slug")
    volume: float = Field(..., description="Total market volume")
    token_ids: Dict[str, str] = Field(
        ..., description="Mapping of outcome labels to CLOB token IDs (e.g., yes/no)"
    )


class OrderbookLevel(BaseModel):
    """Represents a single price level in the orderbook."""

    price: float = Field(..., description="Price at this level")
    size: float = Field(..., description="Available size at this level")


class Orderbook(BaseModel):
    """Represents the full orderbook snapshot."""

    bids: List[OrderbookLevel] = Field(
        default_factory=list, description="Bid levels sorted by descending price"
    )
    asks: List[OrderbookLevel] = Field(
        default_factory=list, description="Ask levels sorted by ascending price"
    )


class TradeScenario(BaseModel):
    """Captures inputs and outputs for a modeled trade scenario."""

    trade_size_usd: float = Field(..., description="Trade notional size in USD")
    belief_probability: float = Field(..., description="Trader belief probability")
    effective_entry_price: float = Field(
        ..., description="Slippage-adjusted entry price"
    )
    ev_percentage: float = Field(
        ..., description="Expected value as a percentage of notional"
    )
    kelly_fraction: float = Field(
        ..., description="Kelly criterion sizing fraction"
    )


class NewsItem(BaseModel):
    """Represents a news article relevant to a market."""

    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    source: str = Field(..., description="Publisher or source name")
    published_date: datetime | None = Field(
        default=None, description="Publish date if available"
    )
