"""Data ingestion layer for Polymarket markets and news."""
from __future__ import annotations

from datetime import datetime
from typing import List
import importlib.util

import httpx

from models import Market, NewsItem, Orderbook, OrderbookLevel


class PolymarketClient:
    """Client for Polymarket Gamma (metadata) and CLOB (orderbook) APIs."""

    gamma_base_url = "https://gamma-api.polymarket.com"
    clob_base_url = "https://clob.polymarket.com"

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def get_active_markets(self, limit: int = 20) -> List[Market]:
        """Fetch active markets from the Gamma API, ordered by volume."""
        url = f"{self.gamma_base_url}/events"
        params = {"limit": limit, "active": "true"}
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPError:
            return []

        data = response.json()
        markets: List[Market] = []
        for event in data:
            for market in event.get("markets", []):
                token_map = {}
                for token in market.get("tokens", []):
                    outcome = str(token.get("outcome", "")).lower()
                    token_id = token.get("token_id")
                    if outcome and token_id:
                        token_map[outcome] = str(token_id)
                if not token_map:
                    continue
                markets.append(
                    Market(
                        id=str(market.get("id", "")),
                        question=str(market.get("question", "")),
                        slug=str(market.get("slug", "")),
                        volume=float(market.get("volume", 0.0) or 0.0),
                        token_ids=token_map,
                    )
                )
        markets.sort(key=lambda m: m.volume, reverse=True)
        return markets[:limit]

    def get_orderbook(self, token_id: str) -> Orderbook:
        """Fetch the live orderbook for a given CLOB token ID."""
        url = f"{self.clob_base_url}/book"
        params = {"token_id": token_id}
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPError:
            return Orderbook()

        payload = response.json()
        bids = [
            OrderbookLevel(price=float(level[0]), size=float(level[1]))
            for level in payload.get("bids", [])
        ]
        asks = [
            OrderbookLevel(price=float(level[0]), size=float(level[1]))
            for level in payload.get("asks", [])
        ]
        return Orderbook(bids=bids, asks=asks)


def fetch_market_news(query: str) -> List[NewsItem]:
    """Fetch recent news related to a market question via DuckDuckGo."""
    if not query.strip():
        return []

    if importlib.util.find_spec("duckduckgo_search") is None:
        return []

    from duckduckgo_search import DDGS

    news_items: List[NewsItem] = []
    with DDGS() as search:
        for result in search.text(query, max_results=5):
            news_items.append(
                NewsItem(
                    title=result.get("title", ""),
                    url=result.get("href", ""),
                    source=result.get("source", "DuckDuckGo"),
                    published_date=_parse_news_date(result.get("date")),
                )
            )
    return news_items


def _parse_news_date(value: str | None) -> datetime | None:
    """Parse a news date string into a datetime if possible."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%b %d, %Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
