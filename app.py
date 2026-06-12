"""
PreMarket Movers — AI Market Intelligence Dashboard
Run: streamlit run app.py
"""

import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import SCAN_UNIVERSE, ANTHROPIC_API_KEY

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PreMarket Movers | AI Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS: dark terminal-style theme ───────────────────────────────────────────
st.markdown(
    """
    <style>
    .main { background-color: #0d1117; }
    .block-container { padding-top: 1rem; }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 4px 0;
    }
    .bullish  { color: #00d26a; font-weight: 700; }
    .bearish  { color: #ff4d4d; font-weight: 700; }
    .neutral  { color: #8b949e; }
    .badge    { border-radius: 4px; padding: 2px 8px; font-size: 0.8em; font-weight: 700; }
    .badge-green  { background:#003d1a; color:#00d26a; }
    .badge-red    { background:#3d0000; color:#ff4d4d; }
    .badge-yellow { background:#3d3000; color:#ffd700; }
    .section-label { color:#58a6ff; font-size:0.85em; text-transform:uppercase; letter-spacing:2px; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ PreMarket Movers")
    st.markdown("**AI-Powered Market Intelligence**")
    st.divider()

    if not ANTHROPIC_API_KEY:
        api_key_input = st.text_input(
            "Anthropic API Key", type="password", placeholder="sk-ant-..."
        )
        if api_key_input:
            import os; os.environ["ANTHROPIC_API_KEY"] = api_key_input
            from config import ANTHROPIC_API_KEY  # re-import after env set
    else:
        st.success("API key loaded from .env")

    st.divider()

    custom_tickers = st.text_area(
        "Custom Watchlist (comma-separated)",
        placeholder="AAPL, TSLA, NVDA",
        help="Leave blank to use the default universe",
    )

    run_btn = st.button("🚀 Run Intelligence Scan", type="primary", use_container_width=True)

    st.divider()
    st.markdown(
        """
        **Agents:**
        - 📊 Market Scanner
        - 📉 Volume Analyzer
        - 📰 News Intelligence
        - 🎯 Catalyst Detector
        - 🤖 Prediction Engine
        """
    )
    st.divider()
    st.caption("Data: Yahoo Finance · AI: Claude claude-sonnet-4-6")
    st.caption("Refreshes on demand — not financial advice.")

# ─── Header ───────────────────────────────────────────────────────────────────
now = datetime.now()
market_open = now.hour >= 9 and (now.hour < 16 or (now.hour == 16 and now.minute == 0))
pre_market = 4 <= now.hour < 9 or (now.hour == 9 and now.minute < 30)
after_hours = now.hour >= 16

session_label = (
    "🟡 PRE-MARKET SESSION"
    if pre_market
    else ("🟢 MARKET OPEN" if market_open else "🔵 AFTER-HOURS / CLOSED")
)

col_title, col_session, col_time = st.columns([3, 2, 2])
with col_title:
    st.markdown("# 📈 PreMarket Movers")
    st.markdown("**AI Market Intelligence Platform**")
with col_session:
    st.markdown(f"<br><span style='font-size:1.1em'>{session_label}</span>", unsafe_allow_html=True)
with col_time:
    st.markdown(f"<br><span style='color:#8b949e'>{now.strftime('%A, %B %d %Y  %H:%M:%S')}</span>", unsafe_allow_html=True)

st.divider()

# ─── Main content ─────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📊 Pre-Market Movers",
    "📉 Volume Alerts",
    "📰 News & Sentiment",
    "🎯 Catalyst Calendar",
    "🤖 AI Predictions",
])

# Session state for cached results
if "intel" not in st.session_state:
    st.session_state.intel = None
if "running" not in st.session_state:
    st.session_state.running = False


def run_scan(tickers):
    """Execute the orchestrator and store results in session state."""
    from agents.orchestrator import IntelligenceOrchestrator

    progress_bar = st.progress(0, text="Initialising agents…")
    status_text = st.empty()

    def on_progress(msg, pct):
        progress_bar.progress(pct / 100, text=msg)
        status_text.markdown(f"**{msg}**")

    orch = IntelligenceOrchestrator(tickers=tickers)
    intel = orch.run(progress_callback=on_progress)

    progress_bar.empty()
    status_text.empty()
    return intel


# ── Trigger scan ──────────────────────────────────────────────────────────────
if run_btn:
    tickers = SCAN_UNIVERSE
    if custom_tickers.strip():
        tickers = [t.strip().upper() for t in custom_tickers.split(",") if t.strip()]

    with st.spinner("Running AI intelligence scan…"):
        st.session_state.intel = run_scan(tickers)

intel = st.session_state.intel

# ─── TAB 1: Pre-Market Movers ─────────────────────────────────────────────────
with tabs[0]:
    if intel is None:
        st.info("Click **Run Intelligence Scan** in the sidebar to fetch live data.")
        st.markdown("### What this tab shows:")
        st.markdown(
            "- Top pre-market gainers and losers sorted by % move\n"
            "- Session label (pre-market / after-hours / regular)\n"
            "- AI commentary on likely drivers for each significant move"
        )
    else:
        scan = intel.get("market_scan", {})
        gainers = scan.get("gainers", pd.DataFrame())
        losers = scan.get("losers", pd.DataFrame())
        analysis = scan.get("analysis", "")
        generated = intel.get("generated_at", "")

        st.caption(f"Generated: {generated}")

        # ── Summary metrics ────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        total_df = scan.get("movers_df", pd.DataFrame())
        if not total_df.empty:
            with c1:
                st.metric("Stocks Scanned", len(total_df))
            with c2:
                up = (total_df["change_pct"] > 0).sum()
                st.metric("Advancing", up, delta=None)
            with c3:
                dn = (total_df["change_pct"] < 0).sum()
                st.metric("Declining", dn, delta=None)
            with c4:
                avg = total_df["change_pct"].mean()
                st.metric("Avg Move", f"{avg:+.2f}%")

        st.divider()

        col_gain, col_lose = st.columns(2)

        # Gainers table
        with col_gain:
            st.markdown("### 🟢 Top Gainers")
            if not gainers.empty:
                display_g = gainers[["ticker", "change_pct", "price", "prev_close", "session"]].copy()
                display_g.columns = ["Ticker", "Change %", "Price", "Prev Close", "Session"]
                display_g["Change %"] = display_g["Change %"].apply(lambda x: f"+{x:.2f}%")
                st.dataframe(display_g, use_container_width=True, hide_index=True)
            else:
                st.info("No gainers found.")

        # Losers table
        with col_lose:
            st.markdown("### 🔴 Top Losers")
            if not losers.empty:
                display_l = losers[["ticker", "change_pct", "price", "prev_close", "session"]].copy()
                display_l.columns = ["Ticker", "Change %", "Price", "Prev Close", "Session"]
                display_l["Change %"] = display_l["Change %"].apply(lambda x: f"{x:.2f}%")
                st.dataframe(display_l, use_container_width=True, hide_index=True)
            else:
                st.info("No losers found.")

        # Waterfall chart
        if not total_df.empty:
            st.divider()
            st.markdown("### 📊 Movers Waterfall")
            top_n = total_df.head(20).sort_values("change_pct")
            colors = ["#00d26a" if v > 0 else "#ff4d4d" for v in top_n["change_pct"]]
            fig = go.Figure(go.Bar(
                x=top_n["ticker"],
                y=top_n["change_pct"],
                marker_color=colors,
                text=[f"{v:+.1f}%" for v in top_n["change_pct"]],
                textposition="outside",
            ))
            fig.update_layout(
                paper_bgcolor="#0d1117",
                plot_bgcolor="#161b22",
                font_color="#c9d1d9",
                xaxis=dict(color="#8b949e"),
                yaxis=dict(title="% Change", color="#8b949e", gridcolor="#21262d"),
                showlegend=False,
                margin=dict(t=20, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

        # AI commentary
        if analysis:
            st.divider()
            st.markdown("### 🤖 AI Market Commentary")
            st.markdown(f"<div class='metric-card'>{analysis}</div>", unsafe_allow_html=True)


# ─── TAB 2: Volume Alerts ─────────────────────────────────────────────────────
with tabs[1]:
    if intel is None:
        st.info("Run the scan to see volume alerts.")
    else:
        vol = intel.get("volume", {})
        vol_df = vol.get("volume_df", pd.DataFrame())
        alerts = vol.get("alerts", [])
        vol_analysis = vol.get("analysis", "")

        if alerts:
            st.markdown("### ⚠️ Volume Alerts")
            for alert in alerts:
                st.markdown(f"- {alert}")
            st.divider()

        if not vol_df.empty:
            st.markdown("### 📊 Unusual Volume Details")
            display_v = vol_df.copy()
            display_v["volume_ratio"] = display_v["volume_ratio"].apply(lambda x: f"{x:.1f}×")
            display_v["current_volume"] = display_v["current_volume"].apply(lambda x: f"{x:,}")
            display_v["avg_volume_90d"] = display_v["avg_volume_90d"].apply(lambda x: f"{x:,}")
            display_v["change_pct"] = display_v["change_pct"].apply(lambda x: f"{x:+.2f}%")
            display_v.columns = ["Ticker", "Current Vol", "90d Avg Vol", "Vol Ratio", "Price Chg"]
            st.dataframe(display_v, use_container_width=True, hide_index=True)

            # Bar chart
            top_vol = vol.get("volume_df", pd.DataFrame()).head(12)
            if not top_vol.empty:
                fig2 = px.bar(
                    top_vol, x="ticker", y="volume_ratio",
                    color="volume_ratio",
                    color_continuous_scale=["#21262d", "#ffd700", "#ff4d4d"],
                    labels={"volume_ratio": "Volume Ratio (×avg)", "ticker": "Ticker"},
                    title="Volume Ratio vs 90-Day Average",
                )
                fig2.update_layout(
                    paper_bgcolor="#0d1117",
                    plot_bgcolor="#161b22",
                    font_color="#c9d1d9",
                    coloraxis_showscale=False,
                    margin=dict(t=40, b=20),
                )
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.success("No stocks with unusual volume detected in this scan.")

        if vol_analysis:
            st.divider()
            st.markdown("### 🤖 Volume Analysis")
            st.markdown(f"<div class='metric-card'>{vol_analysis}</div>", unsafe_allow_html=True)


# ─── TAB 3: News & Sentiment ──────────────────────────────────────────────────
with tabs[2]:
    if intel is None:
        st.info("Run the scan to see news and sentiment analysis.")
    else:
        news_data = intel.get("news", {})
        sentiment = news_data.get("sentiment", {"score": 5, "label": "Neutral"})
        market_news = news_data.get("market_news", [])
        ticker_news = news_data.get("ticker_news", {})
        news_analysis = news_data.get("analysis", "")

        # Sentiment gauge
        score = sentiment.get("score", 5)
        label = sentiment.get("label", "Neutral")
        sent_color = "#00d26a" if score >= 6 else ("#ff4d4d" if score <= 4 else "#ffd700")

        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown(
                f"""
                <div class='metric-card' style='text-align:center;'>
                  <div class='section-label'>Market Sentiment</div>
                  <div style='font-size:3rem; color:{sent_color}; font-weight:900;'>{score}/10</div>
                  <div style='font-size:1.3rem; color:{sent_color};'>{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()

        # AI analysis
        if news_analysis:
            st.markdown("### 🤖 AI News Intelligence")
            st.markdown(f"<div class='metric-card'>{news_analysis}</div>", unsafe_allow_html=True)
            st.divider()

        # Raw news feed
        col_market, col_ticker = st.columns(2)

        with col_market:
            st.markdown("### 📰 Market Headlines")
            for art in market_news[:8]:
                with st.expander(art.get("title", ""), expanded=False):
                    st.caption(f"{art.get('source')} · {art.get('published','')}")
                    st.write(art.get("summary", ""))
                    if art.get("link"):
                        st.markdown(f"[Read more]({art['link']})")

        with col_ticker:
            st.markdown("### 🎯 Ticker-Specific News")
            for ticker, articles in ticker_news.items():
                st.markdown(f"**{ticker}**")
                for art in articles[:3]:
                    with st.expander(art.get("title", ""), expanded=False):
                        st.caption(f"{art.get('source')} · {art.get('published','')}")
                        st.write(art.get("summary", ""))
                        if art.get("link"):
                            st.markdown(f"[Read more]({art['link']})")


# ─── TAB 4: Catalyst Calendar ─────────────────────────────────────────────────
with tabs[3]:
    if intel is None:
        st.info("Run the scan to see the catalyst calendar.")
    else:
        cat_data = intel.get("catalysts", {})
        catalysts = cat_data.get("catalysts", [])
        near_term = cat_data.get("near_term", [])
        cat_analysis = cat_data.get("analysis", "")

        if near_term:
            st.markdown("### 🔥 Earnings This Week")
            for c in near_term:
                days = c.get("earnings_days_away", "?")
                badge_color = "badge-red" if days is not None and days <= 2 else "badge-yellow"
                st.markdown(
                    f"<span class='badge {badge_color}'>{c['ticker']}</span>  "
                    f"**{c.get('name', c['ticker'])}** — earnings in **{days} day(s)**  |  "
                    f"Analyst: `{c.get('analyst_rating','N/A')}`  |  "
                    f"Short: `{(c.get('short_pct') or 0):.1%}`",
                    unsafe_allow_html=True,
                )
            st.divider()

        # Full catalyst table
        if catalysts:
            st.markdown("### 📅 Full Catalyst Calendar")
            cat_rows = []
            for c in catalysts:
                days = c.get("earnings_days_away")
                cat_rows.append({
                    "Ticker": c.get("ticker", ""),
                    "Name": c.get("name", ""),
                    "Sector": c.get("sector", ""),
                    "Earnings In": f"{days}d" if days is not None else "—",
                    "Analyst": c.get("analyst_rating", "N/A"),
                    "Short %": f"{(c.get('short_pct') or 0):.1%}",
                    "Target $": c.get("target_price") or "—",
                })
            st.dataframe(pd.DataFrame(cat_rows), use_container_width=True, hide_index=True)

        if cat_analysis:
            st.divider()
            st.markdown("### 🤖 Event-Driven Analysis")
            st.markdown(f"<div class='metric-card'>{cat_analysis}</div>", unsafe_allow_html=True)


# ─── TAB 5: AI Predictions ────────────────────────────────────────────────────
with tabs[4]:
    if intel is None:
        st.info("Run the scan to generate AI predictions.")
    else:
        pred_data = intel.get("predictions", {})
        predictions_text = pred_data.get("predictions", "")
        parsed = pred_data.get("parsed", [])
        market_bias = pred_data.get("market_bias", "")

        # Parsed predictions as cards
        if parsed:
            st.markdown("### 🎯 Trade Setups")
            cols = st.columns(min(len(parsed), 3))
            for i, pred in enumerate(parsed[:6]):
                with cols[i % 3]:
                    direction = pred.get("direction", "Neutral").lower()
                    color = "#00d26a" if "bullish" in direction else ("#ff4d4d" if "bearish" in direction else "#ffd700")
                    conf = pred.get("confidence", 5)
                    st.markdown(
                        f"""
                        <div class='metric-card'>
                          <div style='font-size:1.3rem;font-weight:900;'>{pred.get('ticker','')}</div>
                          <div style='color:{color};font-weight:700;'>{pred.get('direction','')}</div>
                          <div style='color:#8b949e;'>Confidence: {conf}/10</div>
                          <div style='color:#8b949e;font-size:0.85em;'>{pred.get('timeframe','')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.divider()

        # Market bias
        if market_bias:
            st.markdown("### 🌐 Market Outlook")
            st.markdown(f"<div class='metric-card'>{market_bias}</div>", unsafe_allow_html=True)
            st.divider()

        # Full prediction text
        if predictions_text:
            st.markdown("### 📋 Full AI Predictions Report")
            st.text_area(
                label="",
                value=predictions_text,
                height=500,
                label_visibility="collapsed",
            )

        # Disclaimer
        st.divider()
        st.markdown(
            "<span style='color:#8b949e;font-size:0.8em;'>"
            "⚠️ AI predictions are for informational purposes only and do not constitute "
            "financial advice. Always do your own research before trading."
            "</span>",
            unsafe_allow_html=True,
        )
