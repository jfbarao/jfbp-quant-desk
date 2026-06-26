# =========================================================
# 🧩 OPTIONS CENTER — v4.3 FREEZE READY
# JFBP Quant Desk
# Scanner-driven options strategy selector
# Strategy guidance only — no live option-chain execution
# v4.2.1: Wheel candidates overlap fix + safer expander spacing
# v4.2.2: fixed Wheel Candidates / Score Breakdown overlap with static scroll tables
# v4.0: Wheel Command Desk + Covered Call Scanner + OMS handoff prep
# v2.0: Strike Builder + Strategy Ranking + Greeks + IV/Volatility + Earnings Risk Engine
# =========================================================

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None


# =========================================================
# HELPERS
# =========================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace("%", "").replace("$", "").replace(",", "").strip()
            if not value:
                return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(safe_float(value, default)))
    except Exception:
        return default


def fmt_score(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "N/A"


def fmt_money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "N/A"


def normalize_signal(value: Any) -> str:
    text = str(value or "").upper().strip()
    mapping = {
        "LONG": "BUY",
        "BUY_LONG": "BUY",
        "ENTER_LONG": "BUY",
        "BULLISH": "BUY",
        "SHORT": "SELL",
        "SELL_SHORT": "SELL",
        "ENTER_SHORT": "SELL",
        "BEARISH": "SELL",
        "NO TRADE": "HOLD",
        "NO_TRADE": "HOLD",
        "WATCH": "WATCH",
        "HOLD": "HOLD",
        "": "HOLD",
    }
    return mapping.get(text, text)


def optionable_symbol(symbol: str) -> bool:
    s = str(symbol or "").upper().strip()
    if not s or s in {"RUN SCANNER", "N/A"}:
        return False
    if s.endswith("=X") or s.endswith("=F") or s.endswith("-USD"):
        return False
    if ".TO" in s:
        return False
    return True


def tone_palette(tone: str) -> Tuple[str, str, str]:
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
        "dark": ("#111827", "#334155", "#ffffff"),
    }
    return palette.get(str(tone), palette["neutral"])


def inject_css() -> None:
    st.markdown(
        """
<style>
.block-container {
    padding-top: 1.4rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1700px !important;
    padding-left: 3rem !important;
    padding-right: 3rem !important;
}
div[data-testid="stDataFrame"] {
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: auto !important;
}
div[data-testid="stHorizontalBlock"] {
    gap: 0.85rem;
    align-items: stretch;
}
div[data-testid="stHorizontalBlock"] > div,
div[data-testid="column"] {
    min-width: 0 !important;
}
.ocx-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 265px), 1fr));
    gap: 0.85rem;
    margin: 0.45rem 0 0.85rem 0;
    width: 100%;
}
.ocx-card {
    border: 1px solid;
    border-radius: 16px;
    padding: 0.95rem 1.0rem;
    min-width: 0;
    min-height: 126px;
    box-sizing: border-box;
    overflow: hidden;
}
.ocx-card-title {
    font-size: 0.74rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748b;
    margin-bottom: 0.34rem;
    line-height: 1.2;
}
.ocx-card-value {
    font-size: clamp(1.22rem, 2.4vw, 1.72rem);
    font-weight: 900;
    line-height: 1.08;
    margin-bottom: 0.35rem;
    overflow-wrap: anywhere;
}
.ocx-card-detail {
    color: #475569;
    font-size: 0.86rem;
    line-height: 1.35;
    overflow-wrap: anywhere;
}
.ocx-mini-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 185px), 1fr));
    gap: 0.65rem;
    margin: 0.45rem 0 0.85rem 0;
}
.ocx-mini {
    background: #f8fafc;
    border: 1px solid #dbe3ef;
    border-radius: 14px;
    padding: 0.72rem 0.82rem;
}
.ocx-mini-label {
    font-size: 0.70rem;
    font-weight: 850;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.25rem;
}
.ocx-mini-value {
    font-size: 1.0rem;
    font-weight: 850;
    color: #111827;
    overflow-wrap: anywhere;
}

.ocx-summary-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 155px), 1fr));
    gap: 0.62rem;
    margin: 0.55rem 0 1.0rem 0;
}
.ocx-summary-item {
    background: #ffffff;
    border: 1px solid #dbe3ef;
    border-radius: 14px;
    padding: 0.68rem 0.75rem;
    min-width: 0;
}
.ocx-summary-label {
    font-size: 0.68rem;
    font-weight: 900;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.045em;
    margin-bottom: 0.24rem;
}
.ocx-summary-value {
    font-size: 0.96rem;
    font-weight: 850;
    color: #111827;
    overflow-wrap: anywhere;
}
.ocx-section-card {
    background: #ffffff;
    border: 1px solid #e5eaf3;
    border-radius: 18px;
    padding: 1rem;
    margin: 0 0 1rem 0;
    overflow: hidden;
}
.ocx-tight-caption {
    color: #64748b;
    font-size: 0.82rem;
    line-height: 1.35;
    margin: -0.2rem 0 0.75rem 0;
}
@media (max-width: 900px) {
    div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    div[data-testid="stHorizontalBlock"] > div {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }
    .ocx-section-card { padding: 0.85rem; border-radius: 15px; }
}

@media (max-width: 1180px) {
    .block-container {
        max-width: 100% !important;
        padding-left: 1.35rem !important;
        padding-right: 1.35rem !important;
    }
    div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    div[data-testid="stHorizontalBlock"] > div {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }
}
@media (max-width: 760px) {
    .block-container {
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }
    .ocx-grid, .ocx-mini-grid { grid-template-columns: 1fr; }
    h1 { font-size: 1.7rem !important; }
}

.ocx-table-wrap {
    width: 100%;
    max-width: 100%;
    overflow-x: auto;
    overflow-y: auto;
    margin: 0.45rem 0 0.95rem 0;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #ffffff;
    clear: both;
    box-sizing: border-box;
}
.ocx-table-wrap.ocx-table-compact { max-height: 260px; }
.ocx-table-wrap.ocx-table-medium { max-height: 360px; }
.ocx-table-wrap.ocx-table-large { max-height: 460px; }
.ocx-table-wrap table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.86rem;
}
.ocx-table-wrap th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: #f8fafc;
    color: #64748b;
    text-align: left;
    font-weight: 800;
    padding: 0.55rem 0.65rem;
    border-bottom: 1px solid #e5e7eb;
    white-space: nowrap;
}
.ocx-table-wrap td {
    padding: 0.55rem 0.65rem;
    border-bottom: 1px solid #eef2f7;
    color: #1f2937;
    vertical-align: top;
    white-space: nowrap;
    max-width: 360px;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ocx-table-wrap tr:last-child td {
    border-bottom: 0;
}
.ocx-spacer-lg {
    height: 26px;
    width: 100%;
    clear: both;
}

</style>
        """,
        unsafe_allow_html=True,
    )


def card_html(title: str, value: Any, detail: str = "", tone: str = "neutral") -> str:
    bg, border, color = tone_palette(tone)
    return (
        f'<div class="ocx-card" style="background:{bg};border-color:{border};">'
        f'<div class="ocx-card-title">{html.escape(str(title))}</div>'
        f'<div class="ocx-card-value" style="color:{color};">{html.escape(str(value))}</div>'
        f'<div class="ocx-card-detail">{html.escape(str(detail))}</div>'
        f'</div>'
    )


def render_card_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="ocx-grid">']
    for card in cards:
        pieces.append(card_html(card.get("title", ""), card.get("value", ""), card.get("detail", ""), card.get("tone", "neutral")))
    pieces.append("</div>")
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_mini_grid(items: List[Tuple[str, Any]]) -> None:
    pieces = ['<div class="ocx-mini-grid">']
    for label, value in items:
        pieces.append(
            f'<div class="ocx-mini">'
            f'<div class="ocx-mini-label">{html.escape(str(label))}</div>'
            f'<div class="ocx-mini-value">{html.escape(str(value))}</div>'
            f'</div>'
        )
    pieces.append("</div>")
    st.markdown("".join(pieces), unsafe_allow_html=True)




def render_static_table(df: pd.DataFrame, max_rows: int | None = None, height: str = "medium") -> None:
    """Render a compact HTML table that stays inside its card/expander.

    This avoids the Streamlit dataframe iframe overlap issue that can make
    tables visually run into the next section on desktop and mobile.
    """
    if df is None or df.empty:
        st.info("No rows to display yet.")
        return
    view = df.copy()
    if max_rows is not None:
        view = view.head(max_rows)
    html_table = view.to_html(index=False, escape=True, border=0)
    safe_height = height if height in {"compact", "medium", "large"} else "medium"
    st.markdown(f'<div class="ocx-table-wrap ocx-table-{safe_height}">{html_table}</div>', unsafe_allow_html=True)


def market_snapshot() -> Dict[str, Any]:
    return {
        "regime": st.session_state.get("market_reaction_regime", "UNKNOWN"),
        "stress_score": st.session_state.get("market_reaction_score", 0),
        "stress_label": st.session_state.get("market_reaction_stress_label", "N/A"),
        "breadth_score": st.session_state.get("market_reaction_breadth_score", 0),
        "breadth_state": st.session_state.get("market_reaction_breadth_state", "N/A"),
        "execution_multiplier": st.session_state.get("market_reaction_execution_multiplier", 1.0),
        "buy_allowed": st.session_state.get("market_reaction_buy_allowed", True),
    }


def risk_snapshot() -> Dict[str, Any]:
    risk_engine = st.session_state.get("risk_engine")
    if risk_engine and hasattr(risk_engine, "snapshot"):
        try:
            snap = risk_engine.snapshot()
            return snap if isinstance(snap, dict) else {}
        except Exception:
            return {}
    return {}


def scanner_rows() -> List[Dict[str, Any]]:
    rows = st.session_state.get("scanner_last_raw_signals", [])
    if isinstance(rows, list):
        return [r for r in rows if isinstance(r, dict)]
    return []


def risk_plan_rows() -> List[Dict[str, Any]]:
    rows = st.session_state.get("scanner_last_risk_plan", [])
    if isinstance(rows, list):
        return [r for r in rows if isinstance(r, dict)]
    return []


def best_scanner_row() -> Dict[str, Any]:
    rows = scanner_rows()
    if not rows:
        return {}
    return sorted(
        rows,
        key=lambda r: (
            safe_float(r.get("opportunity_score_pct"), 0.0),
            safe_float(r.get("model_score"), 0.0),
            safe_float(r.get("rs_score"), 0.0),
        ),
        reverse=True,
    )[0]


def selected_candidate() -> Dict[str, Any]:
    rows = scanner_rows()

    def normalize_symbol(value: Any) -> str:
        return str(value or "").upper().strip().split(" ")[0].strip()

    def symbol_from_ticket(ticket: Any) -> str:
        if isinstance(ticket, dict):
            return normalize_symbol(
                ticket.get("symbol")
                or ticket.get("underlying")
                or ticket.get("display_symbol")
                or ticket.get("Symbol")
                or ticket.get("Opportunity")
                or ticket.get("opportunity")
            )
        return ""

    # Read the exact handoff published by Opportunity Center first.
    handoff_symbol = ""
    for key in (
        "options_selected_opportunity",
        "opportunity_center_handoff_ticket",
        "opportunity_center_selected",
        "options_handoff_ticket",
    ):
        handoff_symbol = symbol_from_ticket(st.session_state.get(key))
        if handoff_symbol:
            break

    # Fallback to the shared symbol keys used across the app.
    if not handoff_symbol:
        for key in (
            "options_manual_symbol",
            "options_symbol",
            "selected_symbol",
            "trade_command_symbol",
            "research_symbol",
            "research_ticker",
            "oms_order_symbol",
        ):
            handoff_symbol = normalize_symbol(st.session_state.get(key))
            if handoff_symbol:
                break

    symbols = []
    lookup = {}

    for row in rows:
        symbol = normalize_symbol(row.get("display_symbol") or row.get("symbol"))
        if symbol and symbol not in lookup:
            symbols.append(symbol)
            lookup[symbol] = row

    if symbols:
        if handoff_symbol and handoff_symbol in lookup:
            default_symbol = handoff_symbol
        else:
            best = best_scanner_row()
            default_symbol = normalize_symbol(best.get("display_symbol") or best.get("symbol"))
            if default_symbol not in lookup:
                default_symbol = symbols[0]

        chosen = st.selectbox(
            "Options candidate",
            options=symbols,
            index=symbols.index(default_symbol),
            key="options_candidate_select_v5_2",
        )

        chosen = normalize_symbol(chosen)
        st.session_state["options_manual_symbol"] = chosen
        st.session_state["options_symbol"] = chosen
        st.session_state["selected_symbol"] = chosen

        return lookup.get(chosen, {})

    manual = st.text_input(
        "Options candidate",
        value=handoff_symbol or st.session_state.get("options_manual_symbol", "AAPL"),
        key="options_manual_symbol",
    )

    manual_symbol = normalize_symbol(manual)
    st.session_state["options_symbol"] = manual_symbol
    st.session_state["selected_symbol"] = manual_symbol

    return {
        "symbol": manual_symbol,
        "display_symbol": manual_symbol,
        "trade_recommendation": "WATCH",
        "opportunity_score_pct": 0,
        "overall_rating": "N/A",
        "sector": "Manual",
    }


def infer_price(row: Dict[str, Any]) -> float:
    for key in ("price", "last_price", "close", "entry_price"):
        value = safe_float(row.get(key), 0.0)
        if value > 0:
            return value
    symbol = str(row.get("symbol") or row.get("display_symbol") or "").upper().strip()
    if yf is not None and symbol and optionable_symbol(symbol):
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if hist is not None and not hist.empty:
                return float(hist["Close"].dropna().iloc[-1])
        except Exception:
            return 0.0
    return 0.0


def derive_option_context(row: Dict[str, Any], market: Dict[str, Any]) -> Dict[str, Any]:
    symbol = str(row.get("display_symbol") or row.get("symbol") or "").upper().strip()
    signal = normalize_signal(row.get("trade_recommendation") or row.get("recommendation") or row.get("scanner_action") or row.get("signal"))
    score = safe_float(row.get("opportunity_score_pct") or row.get("model_score") or 0, 0.0)
    rating = str(row.get("overall_rating") or "N/A")
    sector = str(row.get("sector") or "N/A")
    regime = str(market.get("regime") or "UNKNOWN").upper().strip()
    stress = safe_float(market.get("stress_score"), 0.0)
    buy_allowed = bool(market.get("buy_allowed", True))
    multiplier = safe_float(market.get("execution_multiplier"), 1.0)
    price = infer_price(row)
    optionable = optionable_symbol(symbol)

    if not optionable:
        stance = "Not Optionable"
        strategy = "No options structure"
        alternative = "Use Scanner / futures / FX rules instead."
        risk = "Options Center v2.0 supports optionable US stocks and ETFs for options structures."
        tone = "neutral"
    elif stress >= 70 or not buy_allowed or regime in {"RISK_OFF", "RISK-OFF", "DEFENSIVE"}:
        stance = "Defense First"
        strategy = "No New Long Premium"
        alternative = "Covered Call only if you already own shares; otherwise wait."
        risk = "Market regime is defensive. Avoid forcing new option exposure."
        tone = "risk"
    elif signal == "BUY" and score >= 85:
        stance = "Bullish — Strong"
        strategy = "Bull Call Spread"
        alternative = "Long Call for aggressive traders only."
        risk = "Defined-risk debit spread preferred; avoid oversized premium."
        tone = "good"
    elif signal == "BUY":
        stance = "Bullish — Qualified"
        strategy = "Bull Call Spread"
        alternative = "Long Call only if liquidity and trend are excellent."
        risk = "Use reduced premium and confirm liquidity before entry."
        tone = "good"
    elif signal == "WATCH" and score >= 65:
        stance = "Watchlist Setup"
        strategy = "Cash-Secured Put"
        alternative = "Covered Call if already long shares."
        risk = "Use only if you are willing to own the stock near support."
        tone = "warning"
    elif signal == "SELL":
        stance = "Bearish / Hedge"
        strategy = "Bear Put Spread"
        alternative = "Long Put for aggressive downside exposure."
        risk = "Defined-risk put spread preferred; watch implied volatility."
        tone = "risk"
    else:
        stance = "Monitor Only"
        strategy = "No Options Trade"
        alternative = "Wait for BUY / SELL / strong WATCH confirmation."
        risk = "The current signal does not justify an options position."
        tone = "warning"

    return {
        "symbol": symbol or "Run Scanner",
        "signal": signal,
        "score": score,
        "rating": rating,
        "sector": sector,
        "regime": regime,
        "stress": stress,
        "multiplier": multiplier,
        "price": price,
        "optionable": optionable,
        "stance": stance,
        "strategy": strategy,
        "alternative": alternative,
        "risk": risk,
        "tone": tone,
    }



def rating_points(rating: Any) -> int:
    """Convert scanner/research rating into Options Opportunity Score points."""
    key = str(rating or "").upper().strip()
    mapping = {
        "A+": 25,
        "A": 23,
        "A-": 21,
        "B+": 18,
        "B": 16,
        "B-": 14,
        "C+": 10,
        "C": 8,
        "C-": 6,
        "D": 3,
        "F": 0,
    }
    return mapping.get(key, 8 if key not in {"", "N/A", "NONE"} else 0)


def market_points(ctx: Dict[str, Any], market: Dict[str, Any]) -> int:
    """Score market suitability for options exposure."""
    regime = str(ctx.get("regime") or market.get("regime") or "UNKNOWN").upper().strip()
    stress = safe_float(ctx.get("stress", market.get("stress_score", 0)), 0.0)
    buy_allowed = bool(market.get("buy_allowed", True))

    if stress >= 70 or regime in {"RISK_OFF", "RISK-OFF", "DEFENSIVE"}:
        return 2
    if not buy_allowed:
        return 5
    if regime in {"RISK_ON", "RISK-ON"}:
        return 20
    if regime in {"SELECTIVE", "NEUTRAL", "UNKNOWN"}:
        return 12
    return 15


def liquidity_points(ctx: Dict[str, Any]) -> int:
    """v1.1 proxy liquidity score until broker option chain liquidity is wired."""
    if not bool(ctx.get("optionable", False)):
        return 0

    symbol = str(ctx.get("symbol") or "").upper().strip()
    price = safe_float(ctx.get("price"), 0.0)

    # Highly liquid broad ETFs / mega-cap proxies receive full points.
    if symbol in {"SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "NVDA", "AMD", "AMZN", "META", "TSLA", "GOOGL", "GOOG", "AVGO"}:
        return 15

    if price >= 20:
        return 12

    return 8


def earnings_risk_points(row: Dict[str, Any]) -> tuple[int, str]:
    """Use scanner earnings fields when available; otherwise default to neutral-safe."""
    row = row if isinstance(row, dict) else {}
    risk_label = str(
        row.get("earnings_risk_label")
        or row.get("earnings_label")
        or row.get("event_risk_label")
        or row.get("combined_event_risk")
        or "NONE"
    ).upper().strip()

    days_raw = (
        row.get("earnings_days_until")
        or row.get("days_until_earnings")
        or row.get("earnings_days")
        or row.get("days_until")
    )
    days_until = safe_float(days_raw, 999.0)

    if risk_label in {"EXTREME", "HIGH"} or days_until <= 3:
        return 0, "High earnings/event risk"
    if risk_label in {"MEDIUM"} or days_until <= 7:
        return 5, "Medium earnings/event risk"
    if risk_label in {"LOW"} or days_until <= 14:
        return 8, "Low earnings/event risk"
    return 10, "No near-term earnings/event risk found"


def build_options_opportunity_score(ctx: Dict[str, Any], market: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    """Institutional-style Options Opportunity Score v1.1."""
    scanner_component = max(0, min(30, int(round(safe_float(ctx.get("score"), 0.0) * 0.30))))
    rating_component = rating_points(ctx.get("rating"))
    market_component = market_points(ctx, market)
    liquidity_component = liquidity_points(ctx)
    earnings_component, earnings_note = earnings_risk_points(row)

    if not bool(ctx.get("optionable", False)):
        scanner_component = min(scanner_component, 10)
        rating_component = min(rating_component, 8)
        market_component = min(market_component, 8)

    total = int(max(0, min(100, scanner_component + rating_component + market_component + liquidity_component + earnings_component)))

    if total >= 80:
        label = "🟢 HIGH CONVICTION"
        tone = "good"
    elif total >= 60:
        label = "🟡 WATCHLIST"
        tone = "warning"
    else:
        label = "🔴 AVOID"
        tone = "risk"

    return {
        "total": total,
        "label": label,
        "tone": tone,
        "earnings_note": earnings_note,
        "components": [
            {"Component": "Scanner Score", "Points": scanner_component, "Max": 30},
            {"Component": "Research / Rating", "Points": rating_component, "Max": 25},
            {"Component": "Market Pulse", "Points": market_component, "Max": 20},
            {"Component": "Liquidity Proxy", "Points": liquidity_component, "Max": 15},
            {"Component": "Earnings / Event Risk", "Points": earnings_component, "Max": 10},
        ],
    }


def opportunity_grade_from_score(scorecard: Dict[str, Any]) -> Tuple[str, str, str]:
    score = safe_float((scorecard or {}).get("total"), 0.0)
    if score >= 80:
        return "🟢 TRADEABLE", "good", "High-quality options candidate worth considering."
    if score >= 60:
        return "🟡 DEVELOPING", "warning", "Options setup is forming but still needs confirmation."
    return "🔴 AVOID", "risk", "Options opportunity quality is not strong enough yet."


def institutional_grade_from_options(ctx: Dict[str, Any], scorecard: Dict[str, Any], market: Dict[str, Any], event_ctx: Dict[str, Any]) -> Tuple[str, str, str]:
    strategy = str((ctx or {}).get("strategy") or "")
    score = safe_float((scorecard or {}).get("total"), 0.0)
    stress = safe_float((market or {}).get("stress_score"), 0.0)
    buy_allowed = bool((market or {}).get("buy_allowed", True))
    event_status = str((event_ctx or {}).get("status") or "")
    optionable = bool((ctx or {}).get("optionable", False))

    if not optionable or strategy in {"No options structure", "No Options Trade", "No New Long Premium"}:
        return "🟡 PENDING CONFIRMATION", "warning", "No executable options structure has cleared the final gate."
    if stress >= 70 or not buy_allowed or event_status.startswith("🔴"):
        return "🔴 BLOCKED", "risk", "Risk, market, or event filters block institutional execution."
    if score >= 80:
        return "🔵 READY", "good", "Options structure and risk filters are sufficiently aligned."
    if score >= 60:
        return "🟡 PENDING CONFIRMATION", "warning", "Opportunity exists, but institutional confirmation is not complete."
    return "⚪ STAND BY", "neutral", "Insufficient confirmation for options deployment."


def grade_explainer() -> str:
    return (
        "JFBP separates opportunity quality from execution readiness. "
        "Opportunity Grade asks whether the options idea is worth considering. "
        "Institutional Grade asks whether the trade is ready for disciplined capital deployment."
    )


def strategy_confidence_reasons(ctx: Dict[str, Any], market: Dict[str, Any], scorecard: Dict[str, Any]) -> str:
    reasons: List[str] = []

    if safe_float(ctx.get("score"), 0.0) >= 80:
        reasons.append("Strong Scanner score")
    elif safe_float(ctx.get("score"), 0.0) >= 65:
        reasons.append("Constructive Scanner score")
    else:
        reasons.append("Scanner score is not yet strong")

    if str(ctx.get("rating") or "").upper().strip() in {"A+", "A", "A-"}:
        reasons.append("High quality rating")

    if bool(ctx.get("optionable", False)):
        reasons.append("US stock/ETF option candidate")
    else:
        reasons.append("Not supported for options in v2.0")

    if bool(market.get("buy_allowed", True)):
        reasons.append("Market allows new exposure")
    else:
        reasons.append("Market filter is blocking new exposure")

    if safe_float(ctx.get("multiplier"), 1.0) >= 1.0:
        reasons.append("Full sizing allowed")
    else:
        reasons.append(f"Reduced sizing: {safe_float(ctx.get('multiplier'), 1.0):.2f}x")

    if scorecard.get("earnings_note"):
        reasons.append(str(scorecard.get("earnings_note")))

    return " | ".join(reasons)


# =========================================================
# OPTIONS CENTER v2.0 — STRIKE / IV / GREEKS / RANKING ENGINE
# =========================================================

def round_to_option_increment(value: Any, price: Any = 0.0) -> float:
    """Round estimated strike to a practical listed-option increment."""
    value = safe_float(value, 0.0)
    price = safe_float(price, value)
    if value <= 0:
        return 0.0
    if price >= 500:
        step = 10.0
    elif price >= 150:
        step = 5.0
    elif price >= 50:
        step = 2.5
    else:
        step = 1.0
    return round(round(value / step) * step, 2)


def pct_between(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def support_from_row(row: Dict[str, Any], ctx: Dict[str, Any]) -> float:
    price = safe_float(ctx.get("price"), 0.0)
    for key in ("support", "key_support", "low_20d", "twenty_day_low"):
        value = safe_float(row.get(key), 0.0)
        if value > 0:
            return value
    return price * 0.95 if price > 0 else 0.0


def resistance_from_row(row: Dict[str, Any], ctx: Dict[str, Any]) -> float:
    price = safe_float(ctx.get("price"), 0.0)
    for key in ("resistance", "key_resistance", "high_20d", "twenty_day_high"):
        value = safe_float(row.get(key), 0.0)
        if value > 0:
            return value
    return price * 1.08 if price > 0 else 0.0


def volatility_proxy(ctx: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    """Use scanner ATR/price as a volatility proxy until broker IV rank is wired."""
    price = safe_float(ctx.get("price"), 0.0)
    atr = safe_float(row.get("atr") or row.get("ATR") or row.get("average_true_range"), 0.0)
    if price <= 0 or atr <= 0:
        iv_proxy = 0.0
        regime = "UNKNOWN"
        premium_bias = "Neutral / wait for live chain"
        note = "ATR or price unavailable; use broker IV rank before entry."
    else:
        # ATR/price annualized is not true IV. It is a practical v2 fallback.
        iv_proxy = pct_between((atr / price) * (252 ** 0.5) * 100.0, 1.0, 250.0)
        if iv_proxy >= 65:
            regime = "HIGH VOL"
            premium_bias = "Prefer selling premium / credit spreads"
        elif iv_proxy <= 25:
            regime = "LOW VOL"
            premium_bias = "Prefer buying premium / debit spreads"
        else:
            regime = "NORMAL VOL"
            premium_bias = "Either debit or credit structures can work"
        note = "ATR-based volatility proxy until IBKR IV Rank is connected."
    return {
        "iv_proxy": round(iv_proxy, 1),
        "regime": regime,
        "premium_bias": premium_bias,
        "note": note,
    }


def earnings_risk_context_v2(row: Dict[str, Any]) -> Dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    label = str(
        row.get("earnings_risk_label")
        or row.get("earnings_label")
        or row.get("event_risk_label")
        or row.get("combined_event_risk")
        or "NONE"
    ).upper().strip()
    days = safe_float(
        row.get("earnings_days_until")
        or row.get("days_until_earnings")
        or row.get("earnings_days")
        or row.get("days_until"),
        999.0,
    )
    if days <= 3 or label in {"EXTREME", "HIGH"}:
        status = "🔴 ELEVATED"
        guidance = "Avoid naked long premium and avoid assignment-risk income trades into the event."
        tone = "risk"
    elif days <= 7 or label == "MEDIUM":
        status = "🟡 CAUTION"
        guidance = "Use defined-risk spreads or wait until after earnings."
        tone = "warning"
    elif days <= 14 or label == "LOW":
        status = "🟢 ACCEPTABLE"
        guidance = "Event risk is visible but not urgent; keep size disciplined."
        tone = "good"
    else:
        status = "🟢 CLEAR"
        guidance = "No near-term earnings/event risk found in Scanner fields."
        tone = "good"
    return {
        "label": label or "NONE",
        "days_until": None if days >= 999 else int(days),
        "status": status,
        "guidance": guidance,
        "tone": tone,
    }


def build_strike_builder(ctx: Dict[str, Any], row: Dict[str, Any], vol_ctx: Dict[str, Any]) -> Dict[str, Any]:
    price = safe_float(ctx.get("price"), 0.0)
    strategy = str(ctx.get("strategy") or "No Options Trade")
    support = support_from_row(row, ctx)
    resistance = resistance_from_row(row, ctx)
    optionable = bool(ctx.get("optionable", False))

    dte = "30–45 DTE" if strategy in {"Cash-Secured Put", "Covered Call"} else "30–60 DTE"
    target_delta = "0.20–0.35" if strategy in {"Cash-Secured Put", "Covered Call"} else "0.55–0.70 / 0.25–0.40"

    if not optionable or price <= 0 or strategy in {"No options structure", "No Options Trade", "No New Long Premium"}:
        rows = [{"Field": "Status", "Value": "No strike built", "Why": "Symbol or setup is not option-ready."}]
        return {"summary": "No strike built", "rows": rows, "cards": []}

    if strategy == "Cash-Secured Put":
        sell_put = round_to_option_increment(min(support, price * 0.95), price)
        assignment_cost = sell_put * 100
        rows = [
            {"Field": "Structure", "Value": "Sell Cash-Secured Put", "Why": "WATCH setup; enter only if willing to own shares."},
            {"Field": "Target DTE", "Value": dte, "Why": "Balances premium decay and event risk."},
            {"Field": "Target Strike", "Value": fmt_money(sell_put), "Why": "Near support / below current price."},
            {"Field": "Target Delta", "Value": target_delta, "Why": "Income entry zone, not aggressive directional exposure."},
            {"Field": "Max Assignment Cost", "Value": fmt_money(assignment_cost), "Why": "Approx. strike × 100 shares before premium."},
        ]
        cards = [
            {"title": "Target Strike", "value": fmt_money(sell_put), "detail": "Sell put near support", "tone": "warning"},
            {"title": "Assignment Cost", "value": fmt_money(assignment_cost), "detail": "Before collected premium", "tone": "info"},
            {"title": "Premium Bias", "value": vol_ctx.get("premium_bias", "N/A"), "detail": vol_ctx.get("regime", "UNKNOWN"), "tone": "info"},
        ]
    elif strategy == "Covered Call":
        sell_call = round_to_option_increment(max(resistance, price * 1.05), price)
        rows = [
            {"Field": "Structure", "Value": "Sell Covered Call", "Why": "Use only against shares already owned."},
            {"Field": "Target DTE", "Value": dte, "Why": "Income / risk reduction window."},
            {"Field": "Target Strike", "Value": fmt_money(sell_call), "Why": "Above resistance to avoid selling upside too cheaply."},
            {"Field": "Target Delta", "Value": target_delta, "Why": "Conservative income zone."},
        ]
        cards = [
            {"title": "Target Call", "value": fmt_money(sell_call), "detail": "Sell above resistance", "tone": "warning"},
            {"title": "Upside Cap", "value": fmt_money(sell_call), "detail": "Shares can be called away", "tone": "info"},
        ]
    elif strategy == "Bull Call Spread":
        buy_call = round_to_option_increment(price * 1.00, price)
        sell_call = round_to_option_increment(max(resistance, price * 1.08), price)
        width = max(0.0, sell_call - buy_call)
        rows = [
            {"Field": "Structure", "Value": "Buy Call / Sell Higher Call", "Why": "Defined-risk bullish expression."},
            {"Field": "Target DTE", "Value": dte, "Why": "Enough time for trend follow-through."},
            {"Field": "Buy Call", "Value": fmt_money(buy_call), "Why": "Near current price / 0.55–0.70 delta guide."},
            {"Field": "Sell Call", "Value": fmt_money(sell_call), "Why": "Near resistance / 0.25–0.40 delta guide."},
            {"Field": "Spread Width", "Value": fmt_money(width), "Why": "Maximum payoff width before debit paid."},
        ]
        cards = [
            {"title": "Buy Call", "value": fmt_money(buy_call), "detail": "Long leg", "tone": "good"},
            {"title": "Sell Call", "value": fmt_money(sell_call), "detail": "Short leg", "tone": "warning"},
            {"title": "Width", "value": fmt_money(width), "detail": "Max reward cap before debit", "tone": "info"},
        ]
    elif strategy == "Bear Put Spread":
        buy_put = round_to_option_increment(price * 1.00, price)
        sell_put = round_to_option_increment(min(support, price * 0.92), price)
        width = max(0.0, buy_put - sell_put)
        rows = [
            {"Field": "Structure", "Value": "Buy Put / Sell Lower Put", "Why": "Defined-risk bearish expression."},
            {"Field": "Target DTE", "Value": dte, "Why": "Enough time for downside follow-through."},
            {"Field": "Buy Put", "Value": fmt_money(buy_put), "Why": "Near current price / 0.55–0.70 delta guide."},
            {"Field": "Sell Put", "Value": fmt_money(sell_put), "Why": "Near support / 0.25–0.40 delta guide."},
            {"Field": "Spread Width", "Value": fmt_money(width), "Why": "Maximum payoff width before debit paid."},
        ]
        cards = [
            {"title": "Buy Put", "value": fmt_money(buy_put), "detail": "Long leg", "tone": "risk"},
            {"title": "Sell Put", "value": fmt_money(sell_put), "detail": "Short leg", "tone": "warning"},
            {"title": "Width", "value": fmt_money(width), "detail": "Max reward cap before debit", "tone": "info"},
        ]
    elif strategy == "Long Call":
        strike = round_to_option_increment(price * 1.00, price)
        rows = [
            {"Field": "Structure", "Value": "Buy Call", "Why": "Aggressive bullish exposure."},
            {"Field": "Target DTE", "Value": "45–90 DTE", "Why": "Gives long premium more time to work."},
            {"Field": "Target Strike", "Value": fmt_money(strike), "Why": "Near current price / 0.55–0.70 delta guide."},
            {"Field": "Risk", "Value": "Premium paid", "Why": "100% of debit can be lost."},
        ]
        cards = [{"title": "Target Call", "value": fmt_money(strike), "detail": "Aggressive long premium", "tone": "good"}]
    elif strategy == "Long Put":
        strike = round_to_option_increment(price * 1.00, price)
        rows = [
            {"Field": "Structure", "Value": "Buy Put", "Why": "Aggressive bearish exposure."},
            {"Field": "Target DTE", "Value": "30–60 DTE", "Why": "Fast downside thesis window."},
            {"Field": "Target Strike", "Value": fmt_money(strike), "Why": "Near current price / 0.55–0.70 delta guide."},
            {"Field": "Risk", "Value": "Premium paid", "Why": "100% of debit can be lost."},
        ]
        cards = [{"title": "Target Put", "value": fmt_money(strike), "detail": "Aggressive long premium", "tone": "risk"}]
    else:
        rows = [{"Field": "Status", "Value": "PENDING CONFIRMATION", "Why": "No valid options structure selected."}]
        cards = []

    return {"summary": strategy, "rows": rows, "cards": cards}


def greek_profile(strategy: str) -> pd.DataFrame:
    strategy = str(strategy or "").strip()
    profiles = {
        "Cash-Secured Put": [
            ("Delta", "+0.20 to +0.35", "Benefits if stock rises or stays above strike."),
            ("Theta", "Positive", "Time decay works for the seller."),
            ("Gamma", "Negative", "Fast adverse moves can hurt."),
            ("Vega", "Negative", "Falling IV helps after entry."),
        ],
        "Covered Call": [
            ("Delta", "Positive, capped", "Stock gains help, but upside is capped."),
            ("Theta", "Positive", "Time decay helps the short call."),
            ("Gamma", "Slightly negative", "Fast upside can create assignment risk."),
            ("Vega", "Negative", "Falling IV helps the short call."),
        ],
        "Bull Call Spread": [
            ("Delta", "Positive", "Benefits from rising stock prices."),
            ("Theta", "Mixed", "Debit spreads reduce but do not remove time decay."),
            ("Gamma", "Moderate", "Directional sensitivity is controlled."),
            ("Vega", "Moderate positive", "Higher IV can help, but short leg offsets some vega."),
        ],
        "Bear Put Spread": [
            ("Delta", "Negative", "Benefits from falling stock prices."),
            ("Theta", "Mixed", "Debit spread reduces long-put time decay."),
            ("Gamma", "Moderate", "Directional sensitivity is controlled."),
            ("Vega", "Moderate positive", "Higher IV can help, but short leg offsets some vega."),
        ],
        "Long Call": [
            ("Delta", "Positive", "Benefits from rising stock prices."),
            ("Theta", "Negative", "Position loses value each day if price does not move."),
            ("Gamma", "Positive", "Delta improves if the stock rises quickly."),
            ("Vega", "Positive", "Benefits from rising implied volatility."),
        ],
        "Long Put": [
            ("Delta", "Negative", "Benefits from falling stock prices."),
            ("Theta", "Negative", "Position loses value each day if price does not move."),
            ("Gamma", "Positive", "Delta improves if the stock falls quickly."),
            ("Vega", "Positive", "Benefits from rising implied volatility."),
        ],
    }
    rows = profiles.get(strategy, [("Delta", "N/A", "No options trade selected."), ("Theta", "N/A", "No options trade selected."), ("Gamma", "N/A", "No options trade selected."), ("Vega", "N/A", "No options trade selected.")])
    return pd.DataFrame(rows, columns=["Greek", "Profile", "Plain English"])


def strategy_ranking_table(ctx: Dict[str, Any], scorecard: Dict[str, Any], vol_ctx: Dict[str, Any], earnings_ctx: Dict[str, Any]) -> pd.DataFrame:
    signal = str(ctx.get("signal") or "HOLD").upper().strip()
    base = safe_int(scorecard.get("total"), 0)
    vol_regime = str(vol_ctx.get("regime") or "UNKNOWN").upper()
    earnings_bad = str(earnings_ctx.get("status") or "").startswith("🔴")
    optionable = bool(ctx.get("optionable", False))

    strategies = [
        ("Bull Call Spread", "Defined-risk bullish debit spread"),
        ("Long Call", "Aggressive bullish premium"),
        ("Cash-Secured Put", "Income/entry if willing to own shares"),
        ("Covered Call", "Income against existing shares"),
        ("Bear Put Spread", "Defined-risk bearish debit spread"),
        ("Long Put", "Aggressive bearish premium"),
    ]
    output = []
    for strategy, use_case in strategies:
        score = base
        if not optionable:
            score = 0
        elif signal == "BUY":
            score += 10 if strategy == "Bull Call Spread" else 2 if strategy == "Long Call" else -10
        elif signal == "WATCH":
            score += 10 if strategy == "Cash-Secured Put" else 4 if strategy == "Covered Call" else -8
        elif signal == "SELL":
            score += 10 if strategy == "Bear Put Spread" else 2 if strategy == "Long Put" else -12
        else:
            score -= 15

        if vol_regime == "HIGH VOL":
            score += 8 if strategy in {"Cash-Secured Put", "Covered Call"} else -4 if strategy in {"Long Call", "Long Put"} else 2
        elif vol_regime == "LOW VOL":
            score += 6 if strategy in {"Long Call", "Long Put", "Bull Call Spread", "Bear Put Spread"} else -4

        if earnings_bad and strategy in {"Cash-Secured Put", "Long Call", "Long Put"}:
            score -= 20
        elif earnings_bad and "Spread" in strategy:
            score -= 5

        score = int(max(0, min(100, score)))
        if score >= 80:
            status = "Primary Candidate"
        elif score >= 60:
            status = "Secondary"
        elif score >= 40:
            status = "Watch Only"
        else:
            status = "Avoid"
        output.append({"Strategy": strategy, "Score": score, "Use Case": use_case, "Status": status})

    return pd.DataFrame(sorted(output, key=lambda r: r["Score"], reverse=True))

def build_strategy_table(ctx: Dict[str, Any]) -> pd.DataFrame:
    price = safe_float(ctx.get("price"), 0.0)
    dte_preferred = "30–60 DTE"
    dte_income = "21–45 DTE"
    call_long = "0.55–0.70 delta"
    call_short = "0.25–0.40 delta"
    put_long = "0.55–0.70 delta"
    put_short = "0.25–0.40 delta"

    rows = [
        {
            "Strategy": "Bull Call Spread",
            "Use When": "BUY signal, strong score, controlled risk",
            "DTE": dte_preferred,
            "Strike Guide": f"Buy {call_long} call / sell {call_short} call",
            "Risk Profile": "Defined risk debit",
            "Status": "Primary" if "Bull Call Spread" == ctx.get("strategy") else "Secondary",
        },
        {
            "Strategy": "Long Call",
            "Use When": "Very strong BUY, high conviction, accepts premium decay",
            "DTE": "45–90 DTE",
            "Strike Guide": "0.55–0.70 delta call",
            "Risk Profile": "Premium at risk",
            "Status": "Aggressive alternative" if ctx.get("signal") == "BUY" else "Avoid for now",
        },
        {
            "Strategy": "Cash-Secured Put",
            "Use When": "WATCH setup, willing to own shares lower",
            "DTE": dte_income,
            "Strike Guide": "0.20–0.35 delta put near support",
            "Risk Profile": "Assignment risk / stock ownership",
            "Status": "Primary" if "Cash-Secured Put" == ctx.get("strategy") else "Income alternative",
        },
        {
            "Strategy": "Covered Call",
            "Use When": "Already own shares and want income / risk reduction",
            "DTE": dte_income,
            "Strike Guide": "0.20–0.35 delta call above resistance",
            "Risk Profile": "Upside capped",
            "Status": "Position management",
        },
        {
            "Strategy": "Bear Put Spread",
            "Use When": "SELL signal, downside thesis, defined risk preferred",
            "DTE": dte_preferred,
            "Strike Guide": f"Buy {put_long} put / sell {put_short} put",
            "Risk Profile": "Defined risk debit",
            "Status": "Primary" if "Bear Put Spread" == ctx.get("strategy") else "Hedge alternative",
        },
        {
            "Strategy": "Long Put",
            "Use When": "Strong SELL and fast downside expected",
            "DTE": "30–60 DTE",
            "Strike Guide": "0.55–0.70 delta put",
            "Risk Profile": "Premium at risk",
            "Status": "Aggressive alternative" if ctx.get("signal") == "SELL" else "Avoid for now",
        },
    ]

    df = pd.DataFrame(rows)
    if price > 0:
        df.insert(1, "Underlying", fmt_money(price))
    return df


def build_candidates_table() -> pd.DataFrame:
    rows = scanner_rows()
    output = []
    market = market_snapshot()
    for row in rows[:30]:
        ctx = derive_option_context(row, market)
        output.append(
            {
                "Symbol": ctx["symbol"],
                "Signal": ctx["signal"],
                "Score": round(ctx["score"], 1),
                "Rating": ctx["rating"],
                "Sector": ctx["sector"],
                "Optionable": "YES" if ctx["optionable"] else "NO",
                "Options Stance": ctx["stance"],
                "Primary Strategy": ctx["strategy"],
                "Size Multiplier": f"{ctx['multiplier']:.2f}x",
            }
        )
    return pd.DataFrame(output)


def option_chain_preview(symbol: str) -> Tuple[pd.DataFrame, str]:
    if yf is None or not optionable_symbol(symbol):
        return pd.DataFrame(), "Option chain unavailable."
    try:
        ticker = yf.Ticker(symbol)
        expirations = list(ticker.options or [])
        if not expirations:
            return pd.DataFrame(), "No option expirations returned by data provider."
        expiry = expirations[min(2, len(expirations) - 1)]
        chain = ticker.option_chain(expiry)
        calls = chain.calls.copy() if hasattr(chain, "calls") else pd.DataFrame()
        puts = chain.puts.copy() if hasattr(chain, "puts") else pd.DataFrame()
        calls["Type"] = "CALL"
        puts["Type"] = "PUT"
        df = pd.concat([calls, puts], ignore_index=True)
        keep = [c for c in ["Type", "contractSymbol", "strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"] if c in df.columns]
        df = df[keep].head(40) if keep else pd.DataFrame()
        return df, f"Preview expiry: {expiry}. Use broker data before placing any real option order."
    except Exception as exc:
        return pd.DataFrame(), f"Option chain preview unavailable: {exc}"




# =========================================================
# OPTIONS CENTER v4.2 — WHEEL + RESPONSIVE UI HELPERS
# =========================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def section_open(title: str, caption: str = "") -> None:
    st.markdown('<div class="ocx-section-card">', unsafe_allow_html=True)
    if title:
        st.markdown(f"### {title}")
    if caption:
        st.markdown(f'<div class="ocx-tight-caption">{html.escape(str(caption))}</div>', unsafe_allow_html=True)


def section_close() -> None:
    st.markdown('</div>', unsafe_allow_html=True)


def render_summary_strip(items: List[Tuple[str, Any]]) -> None:
    pieces = ['<div class="ocx-summary-strip">']
    for label, value in items:
        pieces.append(
            f'<div class="ocx-summary-item">'
            f'<div class="ocx-summary-label">{html.escape(str(label))}</div>'
            f'<div class="ocx-summary-value">{html.escape(str(value))}</div>'
            f'</div>'
        )
    pieces.append('</div>')
    st.markdown(''.join(pieces), unsafe_allow_html=True)


def wheel_stage_for_symbol(symbol: str, position: Dict[str, Any] | None = None) -> str:
    symbol = str(symbol or "").upper().strip()
    lifecycle = st.session_state.get("options_wheel_lifecycle", {})
    if isinstance(lifecycle, dict) and symbol in lifecycle:
        stage = str(lifecycle.get(symbol, {}).get("stage") or "").upper().strip()
        mapping = {
            "CASH": "🟢 CASH",
            "CSP": "🟡 CSP OPEN",
            "CSP OPEN": "🟡 CSP OPEN",
            "ASSIGNED": "🟠 ASSIGNED",
            "COVERED CALL": "🔵 COVERED CALL",
            "CC": "🔵 COVERED CALL",
            "CALLED AWAY": "✅ CALLED AWAY",
        }
        if stage:
            return mapping.get(stage, stage)
    qty = safe_float((position or {}).get("Qty"), 0.0)
    if qty >= 100:
        return "🔵 COVERED CALL"
    return "🟢 CASH"


def get_position_sources() -> Dict[str, Dict[str, Any]]:
    sources: Dict[str, Dict[str, Any]] = {}

    def add_position(symbol: Any, row: Any, source: str) -> None:
        sym = str(symbol or "").upper().strip()
        if not sym:
            return
        if isinstance(row, dict):
            qty = row.get("signed_qty", row.get("qty", row.get("quantity", row.get("shares", 0))))
            side = str(row.get("side") or "").upper().strip()
            signed = safe_float(qty, 0.0)
            if side == "SHORT":
                signed = -abs(signed)
            last_price = safe_float(row.get("last_price") or row.get("market_price") or row.get("price") or row.get("avg_price"), 0.0)
            avg_price = safe_float(row.get("avg_price") or row.get("avg_cost") or last_price, 0.0)
        else:
            signed = safe_float(row, 0.0)
            last_price = 0.0
            avg_price = 0.0
        if abs(signed) <= 1e-9:
            return
        sources[sym] = {"Symbol": sym, "Signed Qty": signed, "Qty": abs(signed), "Side": "LONG" if signed > 0 else "SHORT", "Last Price": last_price, "Avg Price": avg_price, "Source": source}

    def consume(obj: Any, source: str) -> None:
        if isinstance(obj, dict):
            for sym, row in obj.items():
                real = row.get("symbol") if isinstance(row, dict) else sym
                add_position(real or sym, row, source)
        elif isinstance(obj, list):
            for row in obj:
                if isinstance(row, dict):
                    add_position(row.get("symbol") or row.get("ticker"), row, source)

    for key in ("portfolio_positions", "private_portfolio_positions", "positions", "ibkr_positions", "live_positions", "broker_positions", "scanner_positions_snapshot"):
        consume(st.session_state.get(key), f"session:{key}")
    for obj_key in ("portfolio_engine", "gateway", "risk_engine"):
        obj = st.session_state.get(obj_key)
        if obj is None:
            continue
        for method in ("snapshot", "positions_snapshot", "get_positions", "positions", "broker_positions_snapshot"):
            try:
                candidate = getattr(obj, method, None)
                if candidate is None:
                    continue
                data = candidate() if callable(candidate) else candidate
                if isinstance(data, dict) and isinstance(data.get("positions"), dict):
                    consume(data.get("positions"), f"{obj_key}.{method}.positions")
                else:
                    consume(data, f"{obj_key}.{method}")
            except Exception:
                continue
    return sources


def option_contract_qty_from_shares(shares: Any) -> int:
    return max(0, int(safe_float(shares, 0.0) // 100))


def wheel_candidate_score(row: Dict[str, Any], ctx: Dict[str, Any], vol_ctx: Dict[str, Any], event_ctx: Dict[str, Any], owned_shares: float = 0.0) -> Dict[str, Any]:
    scanner_raw = safe_float(ctx.get("score"), 0.0)
    scanner_component = max(0, min(25, int(round(scanner_raw * 0.25))))
    rating_component = min(10, rating_points(ctx.get("rating")) // 3)
    market_component = market_points(ctx, market_snapshot())
    vol_regime = str(vol_ctx.get("regime") or "UNKNOWN").upper()
    vol_component = 20 if vol_regime == "HIGH VOL" else 14 if vol_regime == "NORMAL VOL" else 8 if vol_regime == "LOW VOL" else 10
    event_status = str(event_ctx.get("status") or "")
    event_component = 4 if event_status.startswith("🔴") else 8 if event_status.startswith("🟡") else 15
    price = safe_float(ctx.get("price"), 0.0)
    fit_component = 20 if owned_shares >= 100 else 10
    if price > 0:
        if 20 <= price <= 250:
            fit_component += 5
        elif price > 750:
            fit_component -= 8
        elif price > 400:
            fit_component -= 4
    signal = str(ctx.get("signal") or "").upper()
    if signal == "SELL":
        fit_component -= 12
    elif signal == "BUY":
        fit_component -= 3
    total = int(max(0, min(100, scanner_component + rating_component + market_component + vol_component + event_component + fit_component)))
    if total >= 80:
        label, tone = "🟢 PRIME WHEEL CANDIDATE", "good"
    elif total >= 60:
        label, tone = "🟡 WHEEL WATCHLIST", "warning"
    else:
        label, tone = "🔴 WHEEL AVOID", "risk"
    return {"total": total, "label": label, "tone": tone, "components": [
        {"Component": "Scanner Quality", "Points": scanner_component, "Max": 25},
        {"Component": "Rating Quality", "Points": rating_component, "Max": 10},
        {"Component": "Market Pulse", "Points": market_component, "Max": 20},
        {"Component": "Volatility / Premium", "Points": vol_component, "Max": 20},
        {"Component": "Earnings / Event Safety", "Points": event_component, "Max": 15},
        {"Component": "Wheel Fit", "Points": fit_component, "Max": 25},
    ]}


def build_wheel_candidates() -> pd.DataFrame:
    market = market_snapshot()
    output = []
    for row in scanner_rows()[:50]:
        ctx = derive_option_context(row, market)
        if not ctx.get("optionable"):
            continue
        symbol = str(ctx.get("symbol") or "").upper().strip()
        price = safe_float(ctx.get("price"), 0.0)
        if not symbol or price <= 0:
            continue
        vol = volatility_proxy(ctx, row)
        event = earnings_risk_context_v2(row)
        support = support_from_row(row, ctx)
        put_strike = round_to_option_increment(min(support, price * 0.95), price)
        assignment_cost = put_strike * 100
        score = wheel_candidate_score(row, ctx, vol, event, owned_shares=0.0)
        signal = str(ctx.get("signal") or "HOLD").upper()
        setup = "Cash-Secured Put" if signal in {"WATCH", "HOLD"} else "Cash-Secured Put / Wait" if signal == "BUY" else "Avoid CSP"
        status = "🟢 Candidate" if score["total"] >= 75 and signal != "SELL" else "🟡 Watch" if score["total"] >= 55 and signal != "SELL" else "🔴 Avoid"
        output.append({"Symbol": symbol, "Setup": setup, "Scanner Signal": signal, "Price": fmt_money(price), "Target Put": fmt_money(put_strike), "Assignment Cost": fmt_money(assignment_cost), "DTE": "30–45", "Vol Regime": vol.get("regime", "UNKNOWN"), "Earnings Risk": event.get("status", "N/A"), "Wheel Score": score["total"], "Status": status})
    return pd.DataFrame(sorted(output, key=lambda r: safe_float(r.get("Wheel Score"), 0.0), reverse=True)) if output else pd.DataFrame()


def build_covered_call_candidates() -> pd.DataFrame:
    positions = get_position_sources()
    market = market_snapshot()
    scanner_lookup = {str(r.get("display_symbol") or r.get("symbol") or "").upper().strip(): r for r in scanner_rows() if isinstance(r, dict)}
    output = []
    for symbol, pos in positions.items():
        shares = safe_float(pos.get("Qty"), 0.0)
        contracts = option_contract_qty_from_shares(shares)
        if contracts <= 0 or not optionable_symbol(symbol):
            continue
        row = scanner_lookup.get(symbol, {"symbol": symbol, "display_symbol": symbol, "trade_recommendation": "WATCH", "sector": "Position"})
        ctx = derive_option_context(row, market)
        if safe_float(ctx.get("price"), 0.0) <= 0:
            ctx["price"] = safe_float(pos.get("Last Price") or pos.get("Avg Price"), 0.0)
        vol = volatility_proxy(ctx, row)
        event = earnings_risk_context_v2(row)
        price = safe_float(ctx.get("price"), 0.0)
        target_call = round_to_option_increment(max(resistance_from_row(row, ctx), price * 1.05), price)
        score = wheel_candidate_score(row, ctx, vol, event, owned_shares=shares)
        output.append({"Symbol": symbol, "Shares": round(shares, 4), "Contracts": contracts, "Last Price": fmt_money(price), "Target Call": fmt_money(target_call), "DTE": "21–45", "Vol Regime": vol.get("regime", "UNKNOWN"), "Earnings Risk": event.get("status", "N/A"), "Score": score["total"], "Status": "🟢 Candidate" if score["total"] >= 75 else "🟡 Watch" if score["total"] >= 55 else "🔴 Avoid"})
    return pd.DataFrame(sorted(output, key=lambda r: safe_float(r.get("Score"), 0.0), reverse=True)) if output else pd.DataFrame()


def build_wheel_dashboard_rows() -> pd.DataFrame:
    positions = get_position_sources()
    lifecycle = st.session_state.get("options_wheel_lifecycle", {})
    lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
    symbols = set(positions.keys()) | set(str(k).upper().strip() for k in lifecycle.keys())
    rows = []
    for symbol in sorted([s for s in symbols if s]):
        pos = positions.get(symbol, {})
        life = lifecycle.get(symbol, {}) if isinstance(lifecycle.get(symbol, {}), dict) else {}
        shares = safe_float(pos.get("Qty"), 0.0)
        rows.append({"Symbol": symbol, "Stage": wheel_stage_for_symbol(symbol, pos), "Shares": shares, "Contracts": option_contract_qty_from_shares(shares), "Strike": fmt_money(life.get("strike")) if safe_float(life.get("strike"), 0.0) > 0 else "—", "DTE": life.get("dte") or "—", "Premium Collected": fmt_money(life.get("premium_collected")) if safe_float(life.get("premium_collected"), 0.0) > 0 else "—", "Status": life.get("status") or ("Covered Call Eligible" if shares >= 100 else "CSP Candidate"), "Source": pos.get("Source", "manual/lifecycle")})
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def publish_options_best_opportunity(ctx: Dict[str, Any], scorecard: Dict[str, Any], vol_ctx: Dict[str, Any], event_ctx: Dict[str, Any]) -> None:
    allowed = bool(ctx.get("optionable")) and str(ctx.get("strategy")) not in {"No options structure", "No Options Trade", "No New Long Premium"}
    opp_grade, _, _ = opportunity_grade_from_score(scorecard)
    inst_grade, _, _ = institutional_grade_from_options(ctx, scorecard, market_snapshot(), event_ctx)
    st.session_state["options_best_opportunity"] = {"timestamp": now_iso(), "symbol": ctx.get("symbol"), "strategy": ctx.get("strategy"), "score": scorecard.get("total"), "allowed": allowed and safe_int(scorecard.get("total"), 0) >= 60, "opportunity_grade": opp_grade, "institutional_grade": inst_grade, "reason": strategy_confidence_reasons(ctx, market_snapshot(), scorecard), "volatility_regime": vol_ctx.get("regime"), "event_risk": event_ctx.get("status"), "source": "Options_Center_v5_1_freezer_ready"}


def prepare_options_oms_ticket(symbol: str, strategy: str, strike_plan: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    ticket = {"timestamp": now_iso(), "symbol": str(symbol or "").upper().strip(), "strategy": strategy, "underlying_price": safe_float(ctx.get("price"), 0.0), "dte": "30–60" if strategy not in {"Cash-Secured Put", "Covered Call"} else "21–45", "status": "PREPARED_NOT_ROUTED", "source": "Options_Center_v5_1_freezer_ready", "note": "Advisory options ticket only. Confirm live option chain, liquidity, bid/ask, IV, and risk before routing.", "legs": []}
    for item in strike_plan.get("rows", []) if isinstance(strike_plan, dict) else []:
        field = str(item.get("Field") or "")
        if field in {"Buy Call", "Sell Call", "Buy Put", "Sell Put", "Target Strike", "Target Call"}:
            ticket["legs"].append({"field": field, "value": item.get("Value"), "why": item.get("Why", "")})
    st.session_state["options_prepared_oms_ticket"] = ticket
    st.session_state["oms_options_ticket"] = ticket
    st.session_state["oms_order_symbol"] = ticket["symbol"]
    return ticket


def render_options_handoff_panel(ctx: Dict[str, Any], strike_plan: Dict[str, Any]) -> None:
    section_open("📤 Options Workflow Handoff", "Prepares advisory tickets and sends symbols to Trade Command, Research, or OMS without retyping.")
    h1, h2, h3, h4 = st.columns(4)
    with h1:
        if st.button("Send to Trade Command", width="stretch", key="ocx42_tcc"):
            st.session_state["trade_command_symbol"] = ctx.get("symbol")
            st.session_state["jfbp_main_navigation"] = "Trade Command Center"
            st.rerun()
    with h2:
        if st.button("Send to Research", width="stretch", key="ocx42_research"):
            st.session_state["research_ticker"] = ctx.get("symbol")
            st.session_state["research_ticker_input"] = ctx.get("symbol")
            st.session_state["research_symbol"] = ctx.get("symbol")
            st.session_state["jfbp_main_navigation"] = "Research Stock"
            st.rerun()
    with h3:
        if st.button("Prepare OMS Ticket", width="stretch", key="ocx42_ticket"):
            ticket = prepare_options_oms_ticket(ctx.get("symbol"), ctx.get("strategy"), strike_plan, ctx)
            st.success(f"Prepared advisory options OMS ticket for {ticket.get('symbol')}.")
            st.json(ticket)
    with h4:
        if st.button("Open OMS", width="stretch", key="ocx42_oms"):
            prepare_options_oms_ticket(ctx.get("symbol"), ctx.get("strategy"), strike_plan, ctx)
            st.session_state["jfbp_main_navigation"] = "OMS Execution"
            st.rerun()
    section_close()


def render_wheel_management(ctx: Dict[str, Any], row: Dict[str, Any], vol_ctx: Dict[str, Any], event_ctx: Dict[str, Any]) -> Dict[str, Any]:
    positions = get_position_sources()
    current_pos = positions.get(str(ctx.get("symbol") or "").upper().strip(), {})
    shares = safe_float(current_pos.get("Qty"), 0.0)
    wheel_score = wheel_candidate_score(row, ctx, vol_ctx, event_ctx, owned_shares=shares)
    cc_df = build_covered_call_candidates()
    wheel_df = build_wheel_candidates()
    dash_df = build_wheel_dashboard_rows()
    cc_candidates = len(cc_df) if not cc_df.empty else 0
    csp_candidates = len(wheel_df[wheel_df["Status"].astype(str).str.contains("Candidate", na=False)]) if not wheel_df.empty else 0
    capital_watch = sum(safe_float(v, 0.0) for v in (wheel_df["Assignment Cost"].head(5) if not wheel_df.empty and "Assignment Cost" in wheel_df.columns else []))

    section_open("🛞 Wheel Command Desk", "Compact Wheel manager: stage, covered-call eligibility, and ranked CSP candidates.")
    render_card_grid([
        {"title": "Wheel Score", "value": f"{wheel_score['total']}/100", "detail": wheel_score["label"], "tone": wheel_score["tone"]},
        {"title": "Current Stage", "value": wheel_stage_for_symbol(ctx.get("symbol"), current_pos), "detail": f"Owned shares: {shares:g} | Contracts: {option_contract_qty_from_shares(shares)}", "tone": "good" if shares >= 100 else "warning"},
        {"title": "Covered Calls", "value": cc_candidates, "detail": "100+ shares required.", "tone": "good" if cc_candidates else "neutral"},
        {"title": "CSP Watchlist", "value": csp_candidates, "detail": f"Top-5 capital: {fmt_money(capital_watch)}", "tone": "warning" if csp_candidates else "neutral"},
    ])

    with st.expander("Wheel Lifecycle + Score Breakdown", expanded=False):
        if dash_df.empty:
            st.info("No Wheel lifecycle or 100-share equity positions detected yet.")
        else:
            render_static_table(dash_df, height="compact")
        st.markdown("##### Wheel Score Breakdown")
        render_static_table(pd.DataFrame(wheel_score["components"]), max_rows=None, height="compact")

    with st.expander("Covered Call Scanner", expanded=False):
        if cc_df.empty:
            st.info("No covered-call candidates detected.")
        else:
            render_static_table(cc_df, max_rows=8, height="compact")

    with st.expander("Cash-Secured Put / Wheel Candidates", expanded=False):
        if wheel_df.empty:
            st.info("No Wheel candidates found yet. Run Scanner on an optionable stock/ETF universe first.")
        else:
            if st.button("Prepare Top Cash-Secured Put OMS Ticket", width="stretch", key="ocx421_csp_ticket"):
                top = wheel_df.iloc[0].to_dict()
                st.session_state["options_prepared_oms_ticket"] = {
                    "timestamp": now_iso(),
                    "symbol": top.get("Symbol"),
                    "strategy": "Cash-Secured Put",
                    "target_put": top.get("Target Put"),
                    "assignment_cost": top.get("Assignment Cost"),
                    "dte": top.get("DTE"),
                    "status": "PREPARED_NOT_ROUTED",
                    "source": "Options_Center_v5_1_freezer_ready_wheel_scanner",
                }
                st.session_state["oms_options_ticket"] = st.session_state["options_prepared_oms_ticket"]
                st.session_state["oms_order_symbol"] = str(top.get("Symbol") or "").upper().strip()
                st.success(f"Prepared CSP OMS ticket for {top.get('Symbol')}.")

            render_static_table(wheel_df, max_rows=5, height="compact")

    st.markdown("<div class='ocx-spacer-lg'></div>", unsafe_allow_html=True)

    section_close()
    return {
        "wheel_score": wheel_score["total"],
        "cc_candidates": cc_candidates,
        "csp_candidates": csp_candidates,
        "stage": wheel_stage_for_symbol(ctx.get("symbol"), current_pos),
        "capital_watch": capital_watch,
    }

# =========================================================
# PAGE
# =========================================================

def run_page() -> None:
    inject_css()

    st.title("🧩 Options Center")
    st.caption(
    "Analyze options opportunities, evaluate strategies, build strike frameworks, "
    "manage Wheel positions, and prepare OMS handoffs. "
    "Advisory only — no live option-chain execution."
)

    st.info(
    "Workflow: Scanner → Options Analysis → Strike Builder → "
    "Wheel Review → Research / Trade Command → OMS"
)

    with st.expander("ℹ️ How to use Options Center", expanded=False):
        st.markdown(
            """
            **Workflow**

            1. Run **Market Pulse** and **Scanner** first.
            2. Return here and select an options candidate.
            3. Review the **Command Summary**, Wheel score, strike builder, strategy ranking, and risk/volatility checks.
            4. Prepare an advisory OMS ticket only after confirming live broker option chain, liquidity, bid/ask spread, IV, cash/margin, and assignment risk.
            """
        )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("Market Pulse", width="stretch", key="ocx42_market"):
            st.session_state["jfbp_main_navigation"] = "Market Pulse"
            st.rerun()
    with c2:
        if st.button("Scanner", width="stretch", key="ocx42_scanner"):
            st.session_state["jfbp_main_navigation"] = "Scanner"
            st.rerun()
    with c3:
        if st.button("Research Stock", width="stretch", key="ocx42_research_top"):
            st.session_state["jfbp_main_navigation"] = "Research Stock"
            st.rerun()
    with c4:
        if st.button("Refresh Options Center", width="stretch", key="ocx42_refresh"):
            st.rerun()

    market = market_snapshot()
    risk = risk_snapshot()
    row = selected_candidate()
    ctx = derive_option_context(row, market)
    scorecard = build_options_opportunity_score(ctx, market, row)
    vol_ctx = volatility_proxy(ctx, row)
    event_ctx = earnings_risk_context_v2(row)
    opp_grade, opp_tone, opp_detail = opportunity_grade_from_score(scorecard)
    inst_grade, inst_tone, inst_detail = institutional_grade_from_options(ctx, scorecard, market, event_ctx)
    strike_plan = build_strike_builder(ctx, row, vol_ctx)
    ranking_df = strategy_ranking_table(ctx, scorecard, vol_ctx, event_ctx)
    publish_options_best_opportunity(ctx, scorecard, vol_ctx, event_ctx)

    cc_count = len(build_covered_call_candidates())
    wheel_df_summary = build_wheel_candidates()
    csp_count = len(wheel_df_summary[wheel_df_summary["Status"].astype(str).str.contains("Candidate", na=False)]) if not wheel_df_summary.empty else 0
    current_wheel_score = wheel_candidate_score(row, ctx, vol_ctx, event_ctx, 0.0)["total"]
    oms_ready = "YES" if st.session_state.get("pipeline") or st.session_state.get("mode", "SIM") == "SIM" else "REVIEW"

    st.subheader("Command Summary")
    render_summary_strip([
        ("Best Strategy", ctx["strategy"]),
        ("Opportunity Grade", opp_grade),
        ("Institutional Grade", inst_grade),
        ("Options Score", f"{scorecard['total']}/100"),
        ("Wheel Score", f"{current_wheel_score}/100"),
        ("CSP Candidates", csp_count),
        ("Covered Calls", cc_count),
        ("Market Regime", ctx["regime"]),
        ("OMS Ready", oms_ready),
    ])

    st.subheader("Options Command Brief")
    render_card_grid([
        {"title": "Candidate", "value": ctx["symbol"], "detail": f"{ctx['sector']} | Signal {ctx['signal']} | Rating {ctx['rating']} | Score {fmt_score(ctx['score'])}", "tone": ctx["tone"]},
        {"title": "Opportunity Grade", "value": opp_grade, "detail": opp_detail, "tone": opp_tone},
        {"title": "Institutional Grade", "value": inst_grade, "detail": inst_detail, "tone": inst_tone},
        {"title": "Recommended Structure", "value": ctx["strategy"], "detail": ctx["alternative"], "tone": ctx["tone"]},
        {"title": "Market Filter", "value": ctx["regime"], "detail": f"Stress {safe_int(ctx['stress'])}/100 | Size {ctx['multiplier']:.2f}x | Buy allowed: {'YES' if market.get('buy_allowed', True) else 'NO'}", "tone": "risk" if safe_float(ctx["stress"]) >= 70 else "warning" if ctx["regime"] in {"SELECTIVE", "UNKNOWN"} else "good"},
        {"title": "Options Readiness", "value": "Ready" if ctx["optionable"] else "Not Optionable", "detail": ctx["risk"], "tone": "info" if ctx["optionable"] else "neutral"},
    ])

    st.info(grade_explainer())

    score_left, score_right = st.columns([0.62, 0.38])
    with score_left:
        section_open("🎯 Opportunity Grade Score")
        render_static_table(pd.DataFrame(scorecard["components"]), height="compact")
        section_close()
    with score_right:
        section_open("Strategy Confidence")
        render_card_grid([
            {"title": "Opportunity Grade", "value": opp_grade, "detail": f"Options Score {scorecard['total']}/100 | {scorecard['label']}", "tone": opp_tone},
            {"title": "Institutional Grade", "value": inst_grade, "detail": inst_detail, "tone": inst_tone},
            {"title": "Primary Structure", "value": ctx["strategy"], "detail": strategy_confidence_reasons(ctx, market, scorecard), "tone": scorecard["tone"]},
        ])
        section_close()

    left_col, right_col = st.columns([0.70, 0.30], gap="large")
    with left_col:
        render_options_handoff_panel(ctx, strike_plan)

        section_open("🧱 Strike Builder Engine", "Builds the advisory strike framework before any Wheel or OMS workflow.")
        if strike_plan.get("cards"):
            render_card_grid(strike_plan["cards"])
        render_static_table(pd.DataFrame(strike_plan["rows"]), height="compact")
        section_close()

        render_wheel_management(ctx, row, vol_ctx, event_ctx)

        with st.expander("Scanner Candidates → Options Structures", expanded=False):
            candidates = build_candidates_table()
            if candidates.empty:
                st.info("No Scanner rows found yet. Open Scanner, run a stock or ETF universe, then return here.")
            else:
                render_static_table(candidates, height="medium")

        with st.expander("📊 Live Option Chain Preview", expanded=False):
            st.caption("Convenience preview only. Broker option-chain data is the source of truth before any real trade.")
            if ctx["optionable"]:
                if st.button("Load Option Chain Preview", width="stretch", key="ocx42_chain"):
                    chain_df, note = option_chain_preview(ctx["symbol"])
                    st.info(note)
                    if chain_df.empty:
                        st.warning("No option-chain rows available from the preview provider.")
                    else:
                        render_static_table(chain_df, height="medium")
            else:
                st.info("This symbol is not supported because it is not a US stock/ETF option candidate.")

        with st.expander("Options Center Guardrails", expanded=False):
            st.markdown(
                """
                - **BUY + strong score:** Prefer defined-risk bullish structures first.
                - **WATCH:** Prefer income/entry structures only if you are willing to own the stock.
                - **SELL:** Prefer defined-risk bearish structures or hedges.
                - **Risk-Off / high stress:** Avoid new long premium unless there is a very specific hedge thesis.
                - **No live routing:** Options Center v5.1 prepares advisory OMS tickets only. Execution stays controlled by OMS and broker confirmations.
                """
            )

        with st.expander("Developer Diagnostics", expanded=False):
            st.write({
                "Context": ctx,
                "Market Snapshot": market,
                "Risk Snapshot": risk,
                "Scanner Rows": len(scanner_rows()),
                "Risk Plan Rows": len(risk_plan_rows()),
                "Options Opportunity Score": scorecard,
                "Volatility Context": vol_ctx,
                "Earnings/Event Context": event_ctx,
                "Strike Plan": strike_plan,
                "Prepared OMS Ticket": st.session_state.get("options_prepared_oms_ticket", {}),
                "Options Best Opportunity": st.session_state.get("options_best_opportunity", {}),
                "Version": "Options Center v5.1 freezer-ready compressed 70/30 scroll-safe layout",
                "Updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })

    with right_col:
        with st.expander("🏆 Strategy Library", expanded=False):
            st.caption("Strategy Ranking + Playbook")
            render_static_table(ranking_df, height="compact")
            render_static_table(build_strategy_table(ctx), height="compact")

        with st.expander("📊 Advanced Analytics", expanded=False):
            st.markdown("##### Greeks Dashboard")
            render_static_table(greek_profile(ctx["strategy"]), height="compact")
            st.markdown("##### IV / Volatility + Earnings Risk")
            render_card_grid([
                {"title": "Volatility Regime", "value": vol_ctx["regime"], "detail": f"Proxy IV {vol_ctx['iv_proxy']}% | {vol_ctx['premium_bias']}", "tone": "warning" if vol_ctx["regime"] == "HIGH VOL" else "info" if vol_ctx["regime"] == "UNKNOWN" else "good"},
                {"title": "Earnings / Event Risk", "value": event_ctx["status"], "detail": f"Label {event_ctx['label']} | Days: {event_ctx['days_until'] if event_ctx['days_until'] is not None else 'N/A'} | {event_ctx['guidance']}", "tone": event_ctx["tone"]},
            ])
            st.caption(vol_ctx["note"])
            st.markdown("##### Risk & Structure Rules")
            render_mini_grid([
                ("Underlying Price", fmt_money(ctx["price"]) if ctx["price"] else "N/A"),
                ("Preferred DTE", "30–60 days"),
                ("Max Premium Risk", "Small defined-risk debit"),
                ("Avoid", "Wide spreads / no volume"),
                ("Risk Engine", risk.get("risk_state", "N/A")),
                ("Gross Exposure", fmt_money(risk.get("gross_exposure", 0))),
            ])

def page() -> None:
    run_page()
