from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Crypto Market Health Dashboard",
    layout="wide",
)


def safe_float(value, default=0.0):
    try:
        value = float(value)
        if pd.isna(value):
            return default
        return value
    except Exception:
        return default


def format_usd(value):
    value = safe_float(value)

    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"

    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"

    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    return f"${value:,.2f}"


markets_path = Path("data/processed/latest_markets.csv")
kpis_path = Path("data/processed/latest_kpis.csv")
report_path = Path("data/reports/latest_quality_report.csv")

if not markets_path.exists() or not kpis_path.exists():
    st.warning("Data files not found. Run `python src/pipeline.py` first.")
    st.stop()

markets = pd.read_csv(markets_path, parse_dates=["last_updated"])
kpis = pd.read_csv(kpis_path)
report = pd.read_csv(report_path) if report_path.exists() else pd.DataFrame()

k = kpis.iloc[0]

st.title("Crypto Market Health Dashboard")
st.caption(
    "Business question: Which major crypto assets are liquid, growing, or showing unusual risk?"
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total market cap",
    format_usd(k.get("total_market_cap_usd")),
)

col2.metric(
    "Total 24h volume",
    format_usd(k.get("total_volume_usd")),
)

col3.metric(
    "Avg 24h change",
    f"{safe_float(k.get('average_24h_change_pct')):.2f}%",
)

col4.metric(
    "Risk flags",
    int(safe_float(k.get("risk_flag_count"))),
)

st.write(
    f"Source: {k.get('source', 'unknown')} | "
    f"Coins tracked: {int(safe_float(k.get('number_of_coins')))}"
)

st.divider()

st.subheader("Market overview")

left, right = st.columns(2)

with left:
    top_market = markets.sort_values("market_cap", ascending=False).head(15)

    fig1 = px.bar(
        top_market,
        x="market_cap",
        y="name",
        orientation="h",
        title="Top 15 by market cap",
    )

    fig1.update_layout(
        height=450,
        yaxis={"categoryorder": "total ascending"},
    )

    st.plotly_chart(fig1, width='stretch')

with right:
    fig2 = px.histogram(
        markets,
        x="price_change_percentage_24h",
        nbins=30,
        title="24h change distribution",
    )

    st.plotly_chart(fig2, width='stretch')

positive = markets[
    (markets["market_cap"] > 0) & (markets["total_volume"] > 0)
]

fig3 = px.scatter(
    positive,
    x="market_cap",
    y="total_volume",
    size="current_price",
    hover_name="name",
    log_x=True,
    log_y=True,
    title="Liquidity vs market cap",
)

st.plotly_chart(fig3, width='stretch')

st.divider()

st.subheader("Data quality report")

if report.empty:
    st.info("No quality report found.")
else:
    st.dataframe(report, width='stretch')

    failed = report[report["status"] == "FAIL"]
    warned = report[report["status"] == "WARN"]

    if not failed.empty:
        st.error("Some quality checks failed. Review the report above.")
    elif not warned.empty:
        st.warning("Some quality checks produced warnings.")
    else:
        st.success("All quality checks passed.")

st.divider()

st.subheader("Coin details")

show_cols = [
    "market_cap_rank",
    "name",
    "symbol",
    "current_price",
    "market_cap",
    "total_volume",
    "price_change_percentage_24h",
    "risk_flag",
]

show_cols = [col for col in show_cols if col in markets.columns]

st.dataframe(
    markets[show_cols].sort_values("market_cap", ascending=False),
    width='stretch',
)