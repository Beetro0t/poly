"""Streamlit UI for the Polymarket Research Terminal."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from data_engine import PolymarketClient, fetch_market_news
from models import Market
from quant_engine import BetaModel, Side, calculate_effective_price, compute_trade_metrics


st.set_page_config(page_title="Polymarket Research Terminal", layout="wide")


@st.cache_data(ttl=60)
def _load_markets(limit: int) -> list[Market]:
    client = PolymarketClient()
    return client.get_active_markets(limit=limit)


@st.cache_data(ttl=15)
def _load_orderbook(token_id: str):
    client = PolymarketClient()
    return client.get_orderbook(token_id)


@st.cache_data(ttl=300)
def _load_news(query: str):
    return fetch_market_news(query)


st.sidebar.title("Market Selection")
market_limit = st.sidebar.slider("Markets to load", min_value=5, max_value=50, value=20)
markets = _load_markets(market_limit)
market_map = {f"{m.question}": m for m in markets}

if not market_map:
    st.warning("No active markets returned. Please try again later.")
    st.stop()

selected_market_label = st.sidebar.selectbox("Choose a market", list(market_map.keys()))
selected_market = market_map[selected_market_label]

st.title("Polymarket Research Terminal")
st.subheader(selected_market.question)
st.caption(f"Volume: ${selected_market.volume:,.2f}")

col_left, col_right = st.columns([1.1, 1.0])

with col_left:
    st.markdown("### Research")
    st.write(selected_market.question)
    news_items = _load_news(selected_market.question)
    if news_items:
        for item in news_items:
            st.markdown(f"- [{item.title}]({item.url}) — {item.source}")
    else:
        st.info("No recent news found for this market.")

with col_right:
    st.markdown("### Execution & Analysis")
    trade_size = st.slider("Trade Size ($)", min_value=10, max_value=1000, value=250, step=10)
    belief_probability = st.slider(
        "Estimated Probability", min_value=0.0, max_value=1.0, value=0.55, step=0.01
    )
    confidence_strength = st.slider(
        "Confidence Level", min_value=1, max_value=100, value=25, step=1
    )

    yes_token_id = selected_market.token_ids.get("yes") or next(
        iter(selected_market.token_ids.values())
    )
    orderbook = _load_orderbook(yes_token_id)

    try:
        effective_price = calculate_effective_price(
            orderbook, Side.BUY, trade_size_usd=float(trade_size)
        )
        scenario = compute_trade_metrics(
            entry_price=effective_price,
            target_probability=float(belief_probability),
            trade_size=float(trade_size),
        )
        beta_model = BetaModel(
            belief_probability=belief_probability,
            confidence_strength=float(confidence_strength),
        )
        x, y = beta_model.pdf()

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=x, y=y, mode="lines", name="Belief Distribution")
        )
        fig.add_vline(
            x=effective_price,
            line_dash="dash",
            line_color="orange",
            annotation_text="Effective Entry",
        )
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis_title="Density",
            xaxis_title="Probability",
        )

        st.plotly_chart(fig, use_container_width=True)

        ev_color = "green" if scenario.ev_percentage >= 0 else "red"
        st.markdown(
            f"""
            <div style="padding: 16px; border-radius: 12px; background-color: #0f172a;">
                <div style="font-size: 14px; color: #94a3b8;">Expected Value</div>
                <div style="font-size: 32px; color: {ev_color}; font-weight: 700;">
                    {scenario.ev_percentage:.2f}%
                </div>
                <div style="font-size: 14px; color: #94a3b8;">
                    Kelly Fraction: {scenario.kelly_fraction:.2f}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception as exc:
        st.error(f"Unable to compute trade metrics: {exc}")
