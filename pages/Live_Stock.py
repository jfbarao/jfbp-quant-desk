# =========================================================
# 📡 JFBP MARKET HUB PAGE — v1.0 FREEZE READY
# CACHE-ONLY MARKET HUB + SYMBOL HANDOFF WORKFLOW
# JFBP Quant Desk
# =========================================================

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from core.bootstrap import init_core
from core.responsive import inject_responsive_css as jfbp_inject_responsive_css
from core.responsive import columns as jfbp_columns
from core.ui_cards import inject_card_css as jfbp_inject_card_css
from core.ui_cards import metric_card as jfbp_metric_card
from core.ui_cards import hero_card as jfbp_hero_card


# =========================================================
# RESPONSIVE CSS
# =========================================================

def inject_live_stock_responsive_css() -> None:
    """Visual-only mobile guardrails for Market Hub.

    Keeps the page cache-only and preserves the existing behavior while making
    the controls, cards, and tables behave cleanly on iPhone/Safari and narrow
    desktop windows.
    """

    jfbp_inject_responsive_css(max_width=1500)
    jfbp_inject_card_css()
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1500px !important;
                padding-top: 1.4rem !important;
                padding-bottom: 2.5rem !important;
                padding-left: clamp(0.9rem, 2.4vw, 2.25rem) !important;
                padding-right: clamp(0.9rem, 2.4vw, 2.25rem) !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            h1 {
                font-size: var(--jfbp-type-h1, clamp(1.75rem, 3.6vw, 2.45rem)) !important;
                line-height: 1.12 !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
            }

            h2, h3 {
                font-size: var(--jfbp-type-section, clamp(1.02rem, 1.9vw, 1.22rem)) !important;
                line-height: 1.18 !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
                margin-top: 0.55rem !important;
                margin-bottom: 0.28rem !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.72rem !important;
                align-items: stretch !important;
            }

            div[data-testid="stHorizontalBlock"] > div,
            div[data-testid="column"] {
                min-width: 0 !important;
            }

            div[data-testid="stMetric"] {
                background: #f7fbff;
                border: 1px solid #d9e8ff;
                border-radius: 14px;
                padding: 14px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
                min-height: 92px;
            }

            [data-testid="stMetricLabel"],
            [data-testid="stMetricValue"] {
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
                overflow-wrap: anywhere !important;
            }

            div[data-testid="stMetricLabel"] {
                font-size: 0.82rem !important;
                font-weight: 800 !important;
                color: #48617a !important;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }

            div[data-testid="stMetricValue"] {
                font-size: 1.25rem !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
            }

            div[data-testid="stDataFrame"] {
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
                border-radius: 12px !important;
            }

            div[data-testid="stDataFrame"] * {
                overflow-wrap: anywhere !important;
            }

            .stButton > button {
                border-radius: 10px !important;
                font-weight: 750 !important;
                min-height: 40px !important;
                border: 1px solid #d7e3f5 !important;
            }

            .jfbp-live-card {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 1.0rem 1.1rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
                margin-bottom: 0.68rem;
                overflow-wrap: anywhere;
            }

            .jfbp-live-card-title {
                font-size: 0.76rem;
                font-weight: 850;
                color: #52677d;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                margin-bottom: 0.35rem;
            }

            .jfbp-live-card-value {
                font-size: 1.45rem;
                font-weight: 900;
                color: #1f2937;
                line-height: 1.12;
            }

            .jfbp-live-card-note {
                font-size: 0.84rem;
                color: #64748b;
                margin-top: 0.35rem;
                line-height: 1.35;
            }

            .jfbp-live-status-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                border-radius: 999px;
                padding: 0.28rem 0.62rem;
                font-weight: 780;
                font-size: 0.84rem;
                background: #eff6ff;
                color: #1d4ed8;
                border: 1px solid #bfdbfe;
                margin: 0.20rem 0 0.60rem 0;
                overflow-wrap: anywhere;
            }

            @media (max-width: 1180px) {
                .block-container {
                    max-width: 100% !important;
                    padding-left: 1.25rem !important;
                    padding-right: 1.25rem !important;
                }

                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                }

                div[data-testid="stHorizontalBlock"] > div,
                div[data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem !important;
                    padding-right: 0.9rem !important;
                }

                div[data-testid="stMetric"] {
                    padding: 11px 12px !important;
                    min-height: 82px !important;
                }

                div[data-testid="stMetricValue"] {
                    font-size: 1.08rem !important;
                }

                div[data-testid="stDataFrame"] {
                    font-size: 0.82rem !important;
                }

                .jfbp-live-card {
                    padding: 0.9rem 0.95rem;
                }

                .jfbp-live-card-value {
                    font-size: 1.25rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# HELPERS
# =========================================================

def safe_price_text(value) -> str:
    if value is None:
        return "N/A"

    try:
        numeric = float(value)
        return f"${numeric:,.2f}"
    except Exception:
        text = str(value or "").strip()
        return text if text else "N/A"


def compact_card(label: str, value, note: str = "") -> None:
    note_html = ""
    if note:
        note_html = f'<div class="jfbp-live-card-note">{html.escape(str(note))}</div>'

    st.markdown(
        f"""
        <div class="jfbp-live-card">
            <div class="jfbp-live-card-title">{html.escape(str(label))}</div>
            <div class="jfbp-live-card-value">{html.escape(str(value))}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )




def live_stock_tip(text: str) -> None:
    """Small educational helper used across Market Hub."""
    st.caption(f"💡 {text}")


def live_stock_help_expander(title: str, body: str) -> None:
    """Compact explanatory expander for the Market Hub page."""
    with st.expander(f"ℹ️ {title}", expanded=False):
        st.markdown(body)

def read_market_snapshot(market) -> dict:
    snapshot = {}

    if market is None:
        return snapshot

    for attr in (
        "prices",
        "last_prices",
        "data",
        "snapshot_cache",
        "cache",
        "last_snapshot",
    ):
        try:
            value = getattr(market, attr, None)

            if isinstance(value, dict):
                snapshot = value
                break

        except Exception:
            pass

    return snapshot if isinstance(snapshot, dict) else {}


def normalize_symbol_payload(payload) -> dict:
    if isinstance(payload, dict):
        return payload

    if payload is None:
        return {}

    return {"price": payload}


def build_market_snapshot_df(snapshot: dict) -> pd.DataFrame:
    rows = []

    for sym, payload in snapshot.items():
        payload = normalize_symbol_payload(payload)

        row = {
            "Symbol": str(sym).upper().strip(),
            "Price": safe_price_text(payload.get("price", "N/A")),
        }

        for optional_col in ("bid", "ask", "last", "volume", "timestamp"):
            if optional_col in payload:
                label = optional_col.replace("_", " ").title()
                row[label] = payload.get(optional_col)

        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=["Symbol", "Price"])

    return pd.DataFrame(rows).sort_values("Symbol").reset_index(drop=True)


# =========================================================
# COMMANDER LAYER — MARKET HUB v1.0
# =========================================================

def inject_live_stock_commander_css() -> None:
    """Institutional command-center visual layer for Market Hub v1.0."""

    st.markdown(
        """
        <style>
            .jfbp-live-workflow {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 12px;
                padding: 0.72rem 0.82rem;
                color: #1d4ed8;
                font-weight: 750;
                margin: 0.50rem 0 0.78rem 0;
                line-height: 1.4;
            }

            .jfbp-live-hero {
                border: 1px solid #bbf7d0;
                background: #ecfdf5;
                border-radius: 18px;
                padding: 0.70rem 0.78rem;
                margin: 0.46rem 0 0.64rem 0;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
            }
            .jfbp-live-hero.watch {
                border-color: #fde68a;
                background: #fffbeb;
            }
            .jfbp-live-hero.risk {
                border-color: #fecaca;
                background: #fef2f2;
            }
            .jfbp-live-hero.info {
                border-color: #bfdbfe;
                background: #eff6ff;
            }

            .jfbp-live-hero.cache-compact {
                padding: 0.58rem 0.66rem;
                margin: 0.34rem 0 0.52rem 0;
            }

            .jfbp-live-kicker {
                font-size: var(--jfbp-type-card-label, 0.72rem);
                letter-spacing: 0.055em;
                text-transform: uppercase;
                color: #64748b;
                font-weight: 850;
                margin-bottom: 0.24rem;
            }

            .jfbp-live-hero-title {
                font-size: clamp(1.22rem, 2.35vw, 1.62rem);
                line-height: 1.14;
                font-weight: 880;
                color: #166534;
                margin-bottom: 0.30rem;
            }
            .jfbp-live-hero.watch .jfbp-live-hero-title { color: #92400e; }
            .jfbp-live-hero.risk .jfbp-live-hero-title { color: #991b1b; }
            .jfbp-live-hero.info .jfbp-live-hero-title { color: #1d4ed8; }

            .jfbp-live-summary {
                font-size: var(--jfbp-type-body, 0.94rem);
                color: #1f2937;
                font-weight: 700;
                line-height: 1.38;
            }

            .jfbp-live-action {
                margin-top: 0.36rem;
                background: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                padding: 0.60rem 0.78rem;
                color: #111827;
                font-size: var(--jfbp-type-body, 0.94rem);
                font-weight: 820;
                line-height: 1.35;
            }

            .jfbp-live-table-guard {
                margin-bottom: 0.90rem;
            }

            @media (max-width: 760px) {
                .jfbp-live-workflow {
                    font-size: 0.86rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def live_stock_metric_card(label: str, value, detail: str = "", tone: str = "neutral") -> None:
    """Shared JFBP card wrapper for Market Hub command metrics."""
    jfbp_metric_card(label, value, detail, tone=tone)


def _payload_timestamp(payload: dict) -> str:
    if not isinstance(payload, dict):
        return "N/A"

    for key in ("timestamp", "time", "updated", "last_update", "last_updated"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)

    return "N/A"


def _payload_volume(payload: dict) -> str:
    if not isinstance(payload, dict):
        return "N/A"

    value = payload.get("volume")
    if value in (None, ""):
        return "N/A"

    try:
        return f"{float(value):,.0f}"
    except Exception:
        return str(value)


def _payload_bid_ask(payload: dict) -> str:
    if not isinstance(payload, dict):
        return "N/A"

    bid = payload.get("bid")
    ask = payload.get("ask")

    if bid in (None, "") and ask in (None, ""):
        return "N/A"

    return f"{safe_price_text(bid)} / {safe_price_text(ask)}"


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _payload_move_pct(payload: dict) -> float | None:
    if not isinstance(payload, dict):
        return None

    price = payload.get("price")
    last = payload.get("last")

    try:
        price_v = float(price)
        last_v = float(last)
    except Exception:
        return None

    if last_v == 0:
        return None

    return (price_v - last_v) / last_v * 100.0


def _symbol_sector(symbol: str) -> str:
    key = str(symbol or "").upper().strip()

    sector_map = {
        "XLF": "Financials",
        "XLK": "Technology",
        "XLE": "Energy",
        "XLV": "Healthcare",
        "XLY": "Consumer Discretionary",
        "XLP": "Consumer Staples",
        "XLI": "Industrials",
        "XLB": "Materials",
        "XLRE": "Real Estate",
        "XLU": "Utilities",
        "XLC": "Communication Services",
        "SMH": "Semiconductors",
        "SOXX": "Semiconductors",
    }

    return sector_map.get(key, "Other")


def _asset_class(symbol: str) -> str:
    key = str(symbol or "").upper().strip()

    equity_index = {"SPY", "QQQ", "IWM", "DIA", "VTI", "VEQT.TO", "XEQT.TO", "VFV.TO", "VCN.TO"}
    fixed_income = {"TLT", "IEF", "SHY", "BND", "VAB.TO", "AGG", "HYG", "LQD"}
    commodities = {"GLD", "SLV", "USO", "DBA", "XLE"}
    fx = {"UUP", "FXE", "FXY", "USDCAD=X"}

    if key in equity_index:
        return "Equity Index"
    if key in fixed_income:
        return "Fixed Income"
    if key in commodities:
        return "Commodities"
    if key in fx:
        return "FX"
    return "Equities"


def build_market_analytics_df(snapshot: dict) -> pd.DataFrame:
    rows = []

    for symbol, payload_raw in (snapshot or {}).items():
        payload = normalize_symbol_payload(payload_raw)
        symbol_text = str(symbol or "").upper().strip()
        price = _safe_float(payload.get("price"), 0.0)
        last = _safe_float(payload.get("last"), 0.0)
        bid = _safe_float(payload.get("bid"), 0.0)
        ask = _safe_float(payload.get("ask"), 0.0)
        volume = _safe_float(payload.get("volume"), 0.0)
        move_pct = _payload_move_pct(payload)

        spread_pct = 0.0
        if bid > 0 and ask > 0 and price > 0:
            spread_pct = abs(ask - bid) / price * 100.0

        rows.append(
            {
                "Symbol": symbol_text,
                "Price": price,
                "Move %": move_pct,
                "Volume": volume,
                "Spread %": spread_pct,
                "Sector": _symbol_sector(symbol_text),
                "Asset Class": _asset_class(symbol_text),
                "Timestamp": _payload_timestamp(payload),
                "Last": last,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Symbol", "Price", "Move %", "Volume", "Spread %",
                "Sector", "Asset Class", "Timestamp", "Last",
            ]
        )

    return pd.DataFrame(rows)


def render_market_opportunity_dashboard(analytics_df: pd.DataFrame) -> None:
    st.subheader("Institutional Opportunity Dashboard")
    st.caption("Sector and asset-class leadership map to direct immediate attention.")

    if analytics_df.empty:
        st.info("No cached symbol analytics available for opportunity mapping.")
        return

    sector_df = analytics_df.dropna(subset=["Move %"]).copy()
    sector_rollup = pd.DataFrame(columns=["Sector", "Move %"])

    if not sector_df.empty:
        sector_rollup = (
            sector_df.groupby("Sector", as_index=False)["Move %"]
            .mean()
            .sort_values("Move %", ascending=False)
        )

    best_sector = sector_rollup.iloc[0]["Sector"] if not sector_rollup.empty else "N/A"
    weakest_sector = sector_rollup.iloc[-1]["Sector"] if not sector_rollup.empty else "N/A"

    strong_industry = best_sector
    leadership_rollup = (
        analytics_df.groupby("Asset Class", as_index=False)["Move %"]
        .mean()
        .sort_values("Move %", ascending=False, na_position="last")
    )
    asset_leader = leadership_rollup.iloc[0]["Asset Class"] if not leadership_rollup.empty else "N/A"

    top_mean = sector_rollup.head(3)["Move %"].mean() if not sector_rollup.empty else 0.0
    bottom_mean = sector_rollup.tail(3)["Move %"].mean() if not sector_rollup.empty else 0.0
    rotation = top_mean - bottom_mean
    rel_strength = analytics_df["Move %"].dropna().mean() if analytics_df["Move %"].notna().any() else 0.0

    r1 = jfbp_columns(3)
    with r1[0]:
        live_stock_metric_card("Best Sector", best_sector, "Highest average move", tone="good")
    with r1[1]:
        live_stock_metric_card("Weakest Sector", weakest_sector, "Lowest average move", tone="warning")
    with r1[2]:
        live_stock_metric_card("Strongest Industry", strong_industry, "Sector leadership proxy", tone="info")

    r2 = jfbp_columns(3)
    with r2[0]:
        live_stock_metric_card("Asset-Class Leader", asset_leader, "Relative leadership", tone="info")
    with r2[1]:
        live_stock_metric_card("Rotation", f"{rotation:.2f}%", "Top vs bottom sector spread", tone="good" if rotation >= 0 else "warning")
    with r2[2]:
        live_stock_metric_card("Relative Strength", f"{rel_strength:.2f}%", "Average symbol move", tone="good" if rel_strength >= 0 else "warning")


def render_market_radar(analytics_df: pd.DataFrame) -> None:
    st.subheader("Market Radar")
    st.caption("Leaders, laggards, movers, and unusual activity from cached universe.")

    if analytics_df.empty:
        st.info("No cached symbols available for radar diagnostics.")
        return

    movers = analytics_df.dropna(subset=["Move %"]).copy()
    leaders = movers.sort_values("Move %", ascending=False).head(5)
    laggards = movers.sort_values("Move %", ascending=True).head(5)
    unusual = analytics_df.sort_values("Spread %", ascending=False).head(5)
    volume_leaders = analytics_df.sort_values("Volume", ascending=False).head(5)

    top_leader = leaders.iloc[0]["Symbol"] if not leaders.empty else "N/A"
    top_laggard = laggards.iloc[0]["Symbol"] if not laggards.empty else "N/A"
    top_volume = volume_leaders.iloc[0]["Symbol"] if not volume_leaders.empty else "N/A"
    top_unusual = unusual.iloc[0]["Symbol"] if not unusual.empty else "N/A"

    row = jfbp_columns(4)
    with row[0]:
        live_stock_metric_card("Today's Leaders", top_leader, "Top positive mover", tone="good")
    with row[1]:
        live_stock_metric_card("Today's Laggards", top_laggard, "Top negative mover", tone="warning")
    with row[2]:
        live_stock_metric_card("Volume Leader", top_volume, "Highest cached volume", tone="info")
    with row[3]:
        live_stock_metric_card("Unusual Activity", top_unusual, "Widest bid/ask spread", tone="warning")

    with st.expander("Radar Detail", expanded=False):
        c1, c2 = jfbp_columns(2)
        with c1:
            st.markdown("**Leaders**")
            st.dataframe(leaders[["Symbol", "Move %", "Price"]], width="stretch", hide_index=True)
            st.markdown("**Laggards**")
            st.dataframe(laggards[["Symbol", "Move %", "Price"]], width="stretch", hide_index=True)
        with c2:
            st.markdown("**Biggest Movers (Abs)**")
            biggest = movers.assign(**{"Abs Move": movers["Move %"].abs()}).sort_values("Abs Move", ascending=False).head(8)
            st.dataframe(biggest[["Symbol", "Move %", "Abs Move"]], width="stretch", hide_index=True)
            st.markdown("**Volume Leaders**")
            st.dataframe(volume_leaders[["Symbol", "Volume", "Price"]], width="stretch", hide_index=True)


def render_market_watchlists(symbol: str, analytics_df: pd.DataFrame) -> None:
    st.subheader("Watchlists")
    st.caption("Existing watchlists, favorites, and recent symbol handoff context.")

    existing_watchlists = st.session_state.get("watchlist_symbols", [])
    favorites = st.session_state.get("favorite_symbols", [])

    recent_candidates = [
        st.session_state.get("selected_symbol", ""),
        st.session_state.get("scanner_focus_symbol", ""),
        st.session_state.get("research_symbol", ""),
        st.session_state.get("trade_command_symbol", ""),
        st.session_state.get("oms_order_symbol", ""),
        st.session_state.get("position_command_symbol", ""),
    ]
    recent = [str(value).upper().strip() for value in recent_candidates if str(value).strip()]
    recent = list(dict.fromkeys(recent))[:12]

    if not existing_watchlists and not favorites and not recent:
        st.info("No watchlist/favorites state detected. Use Scanner and handoff controls to build active symbol context.")

    r1, r2, r3 = jfbp_columns(3)

    with r1:
        items = existing_watchlists[:8] if isinstance(existing_watchlists, list) else []
        text = ", ".join(map(str, items)) if items else "N/A"
        live_stock_metric_card("Existing Watchlists", len(items), text, tone="info" if items else "neutral")

    with r2:
        items = favorites[:8] if isinstance(favorites, list) else []
        text = ", ".join(map(str, items)) if items else symbol
        live_stock_metric_card("Favorites", len(items) if items else 1, text, tone="good" if items else "neutral")

    with r3:
        text = ", ".join(recent[:5]) if recent else "N/A"
        live_stock_metric_card("Recent Additions", len(recent), text, tone="warning" if recent else "neutral")

    if not analytics_df.empty:
        with st.expander("Watchlist Candidates From Cache", expanded=False):
            candidates = analytics_df.sort_values(["Volume", "Spread %"], ascending=[False, False]).head(20)
            st.dataframe(candidates[["Symbol", "Price", "Move %", "Volume", "Sector"]], width="stretch", hide_index=True)


def render_market_trend_section(symbol: str, data: dict, snapshot: dict, analytics_df: pd.DataFrame) -> None:
    st.subheader("Market Trend")
    st.caption("Performance visualization and market-cache historical context.")

    if analytics_df.empty:
        st.info("No cached analytics available for trend visualization.")
    else:
        trend_df = analytics_df.copy()
        move_df = trend_df.dropna(subset=["Move %"]).sort_values("Move %", ascending=False).head(15)
        if not move_df.empty:
            st.markdown("**Move Distribution (Top 15)**")
            st.bar_chart(move_df.set_index("Symbol")[["Move %"]], height=320, use_container_width=True)

        vol_df = trend_df.sort_values("Volume", ascending=False).head(15)
        if (vol_df["Volume"] > 0).any():
            st.markdown("**Volume Leadership (Top 15)**")
            st.bar_chart(vol_df.set_index("Symbol")[["Volume"]], height=280, use_container_width=True)

    render_live_stock_snapshot_tables(
        symbol=symbol,
        selected_price=data.get("price", "N/A") if data else "N/A",
        selected_status="ACTIVE" if data else "NO DATA",
        snapshot=snapshot,
    )


def _live_stock_status(snapshot: dict, data: dict) -> tuple[str, str, str, str]:
    if not snapshot:
        return (
            "CACHE EMPTY",
            "risk",
            "No market symbols are currently cached.",
            "Open Scanner, Research Stock, or another market page to populate the cache.",
        )

    if data:
        return (
            "ACTIVE",
            "good",
            "Selected symbol is present in the market cache.",
            "Use Market Hub to verify cached price state before moving to Research Stock or Scanner.",
        )

    return (
        "NO DATA",
        "warning",
        "Selected symbol is not present in the current market cache.",
        "Load this symbol from Scanner or Research Stock, then return here to verify the cache.",
    )


def render_live_stock_commander_report(symbol: str, data: dict, snapshot: dict) -> None:
    status, tone, summary, action = _live_stock_status(snapshot, data)
    hero_class = "risk" if tone == "risk" else "watch" if tone == "warning" else ""

    price = safe_price_text(data.get("price", "N/A")) if data else "N/A"
    hub_size = len(snapshot)

    st.subheader("Institutional Market Summary")
    st.caption("Fast single-symbol read: cache state, price, hub size, and next action.")

    st.markdown(
        f"""
        <div class="jfbp-live-hero {hero_class}">
            <div class="jfbp-live-kicker">Institutional Market Hub Command · Cache-Only</div>
            <div class="jfbp-live-hero-title">📡 MARKET HUB STATUS: {html.escape(status)}</div>
            <div class="jfbp-live-summary">
                Symbol: {html.escape(symbol)} ·
                Cached Price: {html.escape(price)} ·
                Hub Size: {hub_size} symbol(s) ·
                Render Mode: CACHE ONLY ·
                Live Fetch: OFF
            </div>
            <div class="jfbp-live-action">ACTION: {html.escape(action)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_live_stock_command_brief(symbol: str, data: dict, snapshot: dict) -> None:
    status, tone, _, _ = _live_stock_status(snapshot, data)
    analytics_df = build_market_analytics_df(snapshot)

    breadth_total = len(analytics_df)
    breadth_up = int((analytics_df["Move %"].fillna(0.0) > 0).sum()) if not analytics_df.empty else 0
    breadth_text = f"{breadth_up}/{breadth_total}" if breadth_total > 0 else "N/A"

    volatility = analytics_df["Spread %"].mean() if not analytics_df.empty else 0.0
    momentum = _payload_move_pct(data) if data else None
    risk_level = "ELEVATED" if volatility >= 0.75 else "MODERATE" if volatility >= 0.35 else "LOW"
    strength = analytics_df["Move %"].dropna().mean() if not analytics_df.empty and analytics_df["Move %"].notna().any() else 0.0

    st.subheader("Executive Market Brief")
    st.caption("Institutional quick read on breadth, volatility, risk, momentum, and market strength.")

    c1, c2, c3, c4 = jfbp_columns(4)

    with c1:
        live_stock_metric_card(
            "Breadth",
            breadth_text,
            "Advancers / cached symbols",
            tone="good" if breadth_total > 0 and breadth_up >= breadth_total / 2 else "warning",
        )

    with c2:
        live_stock_metric_card(
            "Volatility",
            f"{volatility:.2f}%",
            "Average bid/ask spread",
            tone="warning" if volatility >= 0.75 else "neutral",
        )

    with c3:
        live_stock_metric_card(
            "Risk Level",
            risk_level,
            f"Hub status: {status}",
            tone="risk" if risk_level == "ELEVATED" else "warning" if risk_level == "MODERATE" else "good",
        )

    with c4:
        live_stock_metric_card(
            "Momentum",
            f"{momentum:.2f}%" if momentum is not None else "N/A",
            f"Selected symbol: {symbol}",
            tone="good" if (momentum or 0) >= 0 and momentum is not None else "warning",
        )

    d1, d2, d3, d4 = jfbp_columns(4)

    with d1:
        live_stock_metric_card(
            "Market Strength",
            f"{strength:.2f}%",
            "Average move across hub",
            tone="good" if strength >= 0 else "warning",
        )

    with d2:
        live_stock_metric_card(
            "Hub Size",
            len(snapshot),
            "Cached market symbols",
            tone="info" if snapshot else "warning",
        )

    with d3:
        live_stock_metric_card(
            "Timestamp",
            _payload_timestamp(data),
            "Cached update marker",
            tone="info" if data and _payload_timestamp(data) != "N/A" else "neutral",
        )

    with d4:
        live_stock_metric_card(
            "Data Quality",
            "GOOD" if data else "MISSING",
            "Selected symbol cache check",
            tone=tone,
        )


def render_live_stock_handoff_center(symbol: str, data: dict) -> None:
    st.subheader("Symbol Handoff Center")
    st.caption("Prepare the selected symbol for the next page in the research and execution workflow.")

    h1, h2, h3, h4, h5 = jfbp_columns(5)

    with h1:
        if st.button("Research", width="stretch", key="live_stock_send_research"):
            st.session_state["selected_symbol"] = symbol
            st.session_state["research_symbol"] = symbol
            st.session_state["research_ticker"] = symbol
            st.session_state["research_ticker_input"] = symbol
            st.session_state["jfbp_main_navigation"] = "Research Stock"
            st.rerun()

    with h2:
        if st.button("Scanner", width="stretch", key="live_stock_send_scanner"):
            st.session_state["selected_symbol"] = symbol
            st.session_state["scanner_focus_symbol"] = symbol
            st.session_state["jfbp_main_navigation"] = "Scanner"
            st.rerun()

    with h3:
        if st.button("Trade Command", width="stretch", key="live_stock_send_trade_command"):
            st.session_state["selected_symbol"] = symbol
            st.session_state["trade_command_symbol"] = symbol
            st.session_state["jfbp_main_navigation"] = "Trade Command Center"
            st.rerun()

    with h4:
        if st.button("OMS", width="stretch", key="live_stock_send_oms"):
            st.session_state["selected_symbol"] = symbol
            st.session_state["oms_order_symbol"] = symbol
            st.session_state["jfbp_main_navigation"] = "OMS Execution"
            st.rerun()

    with h5:
        if st.button("Position Command", width="stretch", key="live_stock_send_position_command"):
            st.session_state["selected_symbol"] = symbol
            st.session_state["position_command_symbol"] = symbol
            st.session_state["jfbp_main_navigation"] = "Position Command Center"
            st.rerun()

    if not data:
        st.warning(
            "Selected symbol is not cached yet. Open Scanner or Research Stock first if you need a cached price before handoff."
        )


def _cache_last_update(snapshot: dict) -> str:
    """Return the most recent timestamp-like value found in the market cache."""
    if not snapshot:
        return "N/A"

    timestamps = []

    for payload in snapshot.values():
        payload = normalize_symbol_payload(payload)
        value = _payload_timestamp(payload)
        if value != "N/A":
            timestamps.append(str(value))

    if not timestamps:
        return "N/A"

    return sorted(timestamps)[-1]


def _cache_command_status(snapshot: dict, symbol: str, data: dict) -> tuple[str, str, str]:
    """Classify the market-cache command state for the diagnostic universe table."""
    if not snapshot:
        return (
            "EMPTY",
            "risk",
            "No market cache available. Run Scanner, Research Stock, or Market Pulse first.",
        )

    if data:
        return (
            "OPERATIONAL",
            "good",
            f"{len(snapshot)} symbols cached and {symbol} is available for handoff.",
        )

    return (
        "PARTIAL",
        "warning",
        f"{len(snapshot)} symbols cached, but {symbol} is not in the cache yet.",
    )


def render_market_cache_command_center(symbol: str, data: dict, snapshot: dict) -> None:
    """Institutional cache command module above the full market snapshot table."""
    cache_status, tone, message = _cache_command_status(snapshot, symbol, data)
    hero_class = "risk" if tone == "risk" else "watch" if tone == "warning" else ""
    last_update = _cache_last_update(snapshot)

    st.subheader("Market Cache Command Center")
    st.caption(
        "Command view of symbols currently held in the JFBP market cache (verification only)."
    )

    st.markdown(
        f"""
        <div class="jfbp-live-hero {hero_class} cache-compact">
            <div class="jfbp-live-kicker">Institutional Market Cache Command</div>
            <div class="jfbp-live-hero-title">📡 CACHE STATUS: {html.escape(cache_status)}</div>
            <div class="jfbp-live-summary">{html.escape(message)}</div>
            <div class="jfbp-live-action">ACTION: Use Scanner and Research Stock for analysis. Use Market Hub for verification and symbol handoff.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = jfbp_columns(4)

    with c1:
        live_stock_metric_card(
            "Cached Symbols",
            len(snapshot),
            "Market-cache universe size",
            tone="info" if snapshot else "warning",
        )

    with c2:
        live_stock_metric_card(
            "Active Symbol",
            symbol,
            "Cached" if data else "Not cached",
            tone="good" if data else "warning",
        )

    with c3:
        live_stock_metric_card(
            "Cache Health",
            "GOOD" if data else "PARTIAL" if snapshot else "EMPTY",
            "Selected-symbol check",
            tone=tone,
        )

    with c4:
        live_stock_metric_card(
            "Last Cache Update",
            last_update,
            "Latest timestamp marker" if last_update != "N/A" else "No timestamp in cache",
            tone="info" if last_update != "N/A" else "neutral",
        )

def render_live_stock_snapshot_tables(symbol: str, selected_price, selected_status: str, snapshot: dict) -> None:
    data = normalize_symbol_payload(snapshot.get(symbol, {})) if snapshot else {}

    render_market_cache_command_center(symbol, data, snapshot)

    with st.expander("📡 Cached Market Universe", expanded=False):
        live_stock_tip(
            "Symbols currently available in the JFBP market cache. Use Scanner and Research Stock for analysis. Use Market Hub for verification and handoff."
        )

        if snapshot:
            market_df = build_market_snapshot_df(snapshot)

            st.dataframe(
                market_df,
                width="stretch",
                hide_index=True,
                height=min(520, max(220, 38 * (len(market_df) + 1))),
            )

            st.caption(
                "Cached market universe is diagnostic. For full analysis, use Research Stock. For rankings, use Scanner."
            )

        else:
            st.warning(
                "Market snapshot cache is empty. "
                "No live market fetch was performed during page render."
            )


# =========================================================
# PAGE
# =========================================================

def run_page():

    inject_live_stock_responsive_css()

    gateway, market, oms, portfolio_engine = init_core()

    inject_live_stock_commander_css()

    st.title("Market Hub")
    st.caption(
        "Institutional live-market monitor for cache verification and decision workflow handoff."
    )

    st.markdown(
        """
        <div class="jfbp-live-workflow">
            Workflow: Symbol → Institutional Market Summary → Symbol Handoff Center → Executive Market Brief → Institutional Opportunity Dashboard → Market Radar → Watchlists → Market Cache Command Center
        </div>
        """,
        unsafe_allow_html=True,
    )

    symbol = st.text_input(
        "Symbol",
        value=st.session_state.get("selected_symbol", "AAPL"),
        help="Uses the local market cache only. No live market fetch is performed during page render.",
    ).upper().strip()

    if not symbol:
        symbol = "AAPL"

    st.session_state["selected_symbol"] = symbol

    snapshot = read_market_snapshot(market)

    data = normalize_symbol_payload(snapshot.get(symbol, {}))
    selected_price = data.get("price", "N/A") if data else "N/A"
    selected_status = "ACTIVE" if data else "NO DATA"

    status_text = "Cache Active" if snapshot else "Cache Empty"
    st.markdown(
        f"""
        <div class="jfbp-live-status-pill">
            <span>📡</span>
            <span>{html.escape(status_text)}</span>
            <span style="color:#64748b;">{len(snapshot)} symbol(s)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


    live_stock_tip(
        "Market Hub reads from the app's existing market cache only. Use it to verify what the app already knows, not to force a new quote download."
    )

    analytics_df = build_market_analytics_df(snapshot)

    # Institutional flow order v2.3
    render_live_stock_commander_report(symbol, data, snapshot)
    render_live_stock_handoff_center(symbol, data)
    render_live_stock_command_brief(symbol, data, snapshot)
    render_market_opportunity_dashboard(analytics_df)
    render_market_radar(analytics_df)
    render_market_watchlists(symbol, analytics_df)
    render_live_stock_snapshot_tables(
        symbol=symbol,
        selected_price=selected_price,
        selected_status=selected_status,
        snapshot=snapshot,
    )

    live_stock_help_expander(
        "How to use this page",
        """
        **Market Hub is the single-symbol cache command center.** It verifies the data already loaded by the app and does not fetch new live data while the page renders, keeping the page fast and stable.

        **Symbol** shows the selected ticker from the current market cache. If the ticker exists in the cache, the page shows its cached price and marks it **ACTIVE**.

        **Hub Size** shows how many symbols are currently stored in the local market cache. A larger hub means other parts of the app have already loaded more market data.

        **Simulate Tick** is only a local test button. It nudges the cached price slightly so you can confirm that the cache and refresh logic are working.
        """,
    )


def page() -> None:
    run_page()


if __name__ == "__main__":
    run_page()
