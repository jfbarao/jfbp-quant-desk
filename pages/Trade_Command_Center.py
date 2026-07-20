# 🚧 BUILD MARKER: OP1-0702-A
# =========================================================
# 🎯 TRADE COMMAND CENTER — v3.0
# JFBP Quant Desk
# Institutional trade-planning cockpit connecting Market Pulse,
# Scanner, Research Stock, Options Center, OMS Execution,
# Position Command Center, and Journal.
# v3.0: Final Decision & Execution Center — opportunity assessment, risk validation, execution readiness, OMS ticket preview, and Journal preparation.
# Advisory only — no live routing from this page.
# =========================================================

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from core.trading_preferences import get_trading_preferences

try:
    from engines.earnings_risk import analyze_symbol_earnings_risk
except Exception:
    analyze_symbol_earnings_risk = None


PORTFOLIO_LIMIT_DEFAULTS = {
    "max_portfolio_risk_pct": 5.0,
    "max_open_trades": 10,
    "max_sector_exposure_pct": 35.0,
    "correlation_warning_threshold": 0.85,
    "progress_target_pct_of_tp1": 25.0,
    "progress_within_days": 5,
}


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _account_summary_value(rows: Any, tag: str) -> float:
    tag = str(tag or "").strip()
    for row in _as_list(rows):
        if not isinstance(row, dict):
            continue
        row_tag = str(row.get("tag") or row.get("name") or "").strip()
        if row_tag != tag:
            continue
        return safe_float(row.get("value"), 0.0)
    return 0.0


def _format_clock(ts: Any) -> str:
    text = str(ts or "").strip()
    if not text:
        return "Pending"
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%H:%M:%S")
    except Exception:
        return text[-8:] if len(text) >= 8 else text


def _live_ibkr_connection_active(gateway: Any = None) -> bool:
    status = st.session_state.get("live_ibkr_cached_status")
    if isinstance(status, dict) and "connected" in status:
        return bool(status.get("connected"))

    gateway_obj = gateway if gateway is not None else st.session_state.get("gateway")
    if gateway_obj is not None:
        for attr in ("broker_connected", "ui_connected", "connected"):
            if hasattr(gateway_obj, attr):
                try:
                    return bool(getattr(gateway_obj, attr))
                except Exception:
                    return False

    return False


def resolve_account_context() -> Dict[str, Any]:
    preferences = get_trading_preferences()
    effective = preferences.get("effective", {}) if isinstance(preferences, dict) else {}

    connected = _live_ibkr_connection_active()
    mode = str(st.session_state.get("mode", "SIM") or "SIM").upper().strip()
    snapshot_rows = _as_list(st.session_state.get("broker_snapshot_account_summary", []))
    snapshot_positions = _as_list(st.session_state.get("broker_snapshot_positions", []))
    snapshot_timestamp = str(st.session_state.get("broker_snapshot_timestamp", "") or "")

    net_liquidation = _account_summary_value(snapshot_rows, "NetLiquidation")
    if net_liquidation <= 0:
        net_liquidation = _account_summary_value(snapshot_rows, "NetLiquidationValue")

    buying_power = _account_summary_value(snapshot_rows, "BuyingPower")
    if buying_power <= 0:
        buying_power = _account_summary_value(snapshot_rows, "AvailableFunds")

    cash_balance = _account_summary_value(snapshot_rows, "TotalCashValue")
    if cash_balance <= 0:
        cash_balance = _account_summary_value(snapshot_rows, "CashBalance")

    portfolio_data_source = "Manual/Demo"
    account_source = "⚪ Manual Mode"
    ibkr_connected = False

    if connected:
        ibkr_connected = True
        if mode == "LIVE":
            account_source = "🟢 Live IBKR Connected"
            portfolio_data_source = "IBKR Live"
        else:
            account_source = "🟡 IBKR Paper Connected"
            portfolio_data_source = "IBKR Paper"

    account_size_source = "Source: Manual"
    account_size_editable = True
    account_size = safe_float(preferences.get("account_size"), 100000.0)
    if ibkr_connected and net_liquidation > 0:
        account_size = net_liquidation
        account_size_source = "Source: IBKR"
        account_size_editable = False

    if not ibkr_connected:
        account_size_source = "Source: Manual"

    if ibkr_connected and net_liquidation <= 0:
        account_size_source = "Source: Manual fallback"

    current_positions_count = len([row for row in snapshot_positions if isinstance(row, dict) and str(row.get("symbol") or "").strip()])
    current_portfolio_risk_pct = safe_float(st.session_state.get("portfolio_current_risk_pct"), -1.0)

    return {
        "account_source": account_source,
        "portfolio_data_source": portfolio_data_source,
        "ibkr_connected": ibkr_connected,
        "mode": mode,
        "snapshot_timestamp": snapshot_timestamp,
        "account_size": account_size,
        "account_size_source": account_size_source,
        "account_size_editable": account_size_editable,
        "net_liquidation": net_liquidation,
        "buying_power": buying_power,
        "cash_balance": cash_balance,
        "open_positions_count": current_positions_count,
        "current_portfolio_risk_pct": current_portfolio_risk_pct,
        "risk_pct_default": safe_float(effective.get("risk_per_trade_pct"), 1.0),
        "risk_pct_source": str(preferences.get("risk_profile") or "Balanced"),
        "risk_pct_source_label": f"{str(preferences.get('risk_profile') or 'Balanced')} Profile",
        "portfolio_overlap_threshold": safe_float(effective.get("portfolio_overlap_warning_threshold"), PORTFOLIO_LIMIT_DEFAULTS["correlation_warning_threshold"]),
        "snapshot_rows": snapshot_rows,
        "snapshot_positions": snapshot_positions,
    }


def _portfolio_positions_from_rows(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    exposure: Dict[str, float] = {}
    for row in _as_list(rows):
        if not isinstance(row, dict):
            continue
        sym = row_symbol(row)
        if not sym:
            continue
        value = safe_float(
            row.get("market_value")
            or row.get("marketValue")
            or row.get("position_value")
            or row.get("exposure")
            or 0.0,
            0.0,
        )
        if value <= 0:
            qty = safe_float(
                row.get("signed_qty")
                or row.get("qty")
                or row.get("quantity")
                or row.get("position")
                or 0.0,
                0.0,
            )
            price = safe_float(
                row.get("last_price")
                or row.get("market_price")
                or row.get("last")
                or row.get("price")
                or row.get("avg_cost")
                or row.get("avgCost")
                or 0.0,
                0.0,
            )
            value = abs(qty * price)
        if value > 0:
            exposure[sym] = value
    return exposure


def _source_badge_text(account_context: Dict[str, Any]) -> str:
    source = str(account_context.get("account_source") or "⚪ Manual Mode")
    net_liq = safe_float(account_context.get("net_liquidation"), 0.0)
    buying_power = safe_float(account_context.get("buying_power"), 0.0)
    cash_balance = safe_float(account_context.get("cash_balance"), 0.0)
    last_updated = _format_clock(account_context.get("snapshot_timestamp"))
    if "Live IBKR" in source or "Paper" in source:
        return (
            f"{source}\n"
            f"Net Liquidation: {fmt_money(net_liq)}\n"
            f"Buying Power: {fmt_money(buying_power)}\n"
            f"Cash: {fmt_money(cash_balance)}\n"
            f"Last Updated: {last_updated}"
        )
    return f"{source}\nAccount Size: {fmt_money(safe_float(account_context.get('account_size'), 100000.0))}"


def render_account_source_banner(account_context: Dict[str, Any]) -> None:
    bg, border, color = tone_palette("good" if account_context.get("ibkr_connected") else "info")
    badge_lines = _source_badge_text(account_context).splitlines()
    headline = badge_lines[0] if badge_lines else "⚪ Manual Mode"
    details = " | ".join(part for part in badge_lines[1:] if part)
    st.markdown(
        f'<div class="tcc-banner" style="background:{bg};border-color:{border};">'
        f'<div class="tcc-banner-label">Account Source</div>'
        f'<div class="tcc-banner-value" style="color:{color};">{html.escape(headline)}</div>'
        f'<div class="tcc-banner-detail">{html.escape(details or "No broker snapshot available. Manual sizing remains enabled.")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _portfolio_rows_for_context(account_context: Dict[str, Any], fallback_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not account_context.get("ibkr_connected"):
        return fallback_rows
    normalized: List[Dict[str, Any]] = []
    for row in _as_list(account_context.get("snapshot_positions", [])):
        if not isinstance(row, dict):
            continue
        symbol = row_symbol(row)
        if not symbol:
            continue
        qty = safe_float(row.get("qty") or row.get("position") or row.get("signed_qty") or 0.0, 0.0)
        avg_cost = safe_float(row.get("avg_cost") or row.get("avgCost") or 0.0, 0.0)
        normalized.append({
            "symbol": symbol,
            "sector": str(row.get("sector") or row.get("Sector") or "Unknown").strip() or "Unknown",
            "position": qty,
            "qty": qty,
            "signed_qty": qty,
            "avg_cost": avg_cost,
            "avgCost": avg_cost,
            "position_value": abs(qty * avg_cost),
            "market_value": abs(qty * avg_cost),
            "source": "ibkr_snapshot_positions",
        })
    return normalized or fallback_rows


def _ensure_widget_default(key: str, default: Any) -> Any:
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def _is_admin_user() -> bool:
    try:
        from pages.SaaS_Core import get_current_user, admin_access_allowed

        current_user = get_current_user()
        allowed, _reason = admin_access_allowed(current_user)
        return bool(allowed)
    except Exception:
        return False


def _developer_mode_enabled() -> bool:
    if not _is_admin_user():
        return False
    _ensure_widget_default("tcc_developer_mode", False)
    return bool(
        st.toggle(
            "Developer Mode (Admin)",
            key="tcc_developer_mode",
            help="Show internal debug packets for Monitoring and Journal actions.",
        )
    )


def _trade_risk_pct_source_label(current_risk_pct: float, default_risk_pct: float) -> str:
    if abs(safe_float(current_risk_pct, 0.0) - safe_float(default_risk_pct, 0.0)) > 0.0001:
        return "Source: Custom for this trade"
    return "Source: Trading Preferences"


def _current_trade_risk_pct_source_label() -> str:
    return str(st.session_state.get("tcc_risk_pct_source_label", "Source: Trading Preferences"))


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


def fmt_money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "0.00%"


def fmt_score(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "N/A"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_signal(value: Any) -> str:
    text = str(value or "").upper().strip()
    mapping = {
        "LONG": "BUY",
        "BUY_LONG": "BUY",
        "ENTER_LONG": "BUY",
        "OPEN_LONG": "BUY",
        "BULLISH": "BUY",
        "SHORT": "SELL",
        "SELL_SHORT": "SELL",
        "ENTER_SHORT": "SELL",
        "OPEN_SHORT": "SELL",
        "BEARISH": "SELL",
        "NO TRADE": "WATCH",
        "NO_TRADE": "WATCH",
        "HOLD": "WATCH",
        "NONE": "WATCH",
        "": "WATCH",
    }
    return mapping.get(text, text)


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
    padding-left: clamp(0.9rem, 2.2vw, 2.75rem) !important;
    padding-right: clamp(0.9rem, 2.2vw, 2.75rem) !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
h1 { font-size: clamp(1.85rem, 3.5vw, 2.55rem) !important; font-weight: 900 !important; color:#1f2937 !important; }
h2, h3 { font-size: clamp(1.12rem, 2.2vw, 1.50rem) !important; font-weight: 850 !important; color:#1f2937 !important; }
div[data-testid="stHorizontalBlock"] { gap: 0.85rem !important; align-items: stretch !important; }
div[data-testid="stHorizontalBlock"] > div, div[data-testid="column"] { min-width: 0 !important; }
div[data-testid="stDataFrame"] { width:100% !important; max-width:100% !important; overflow-x:auto !important; border-radius:12px !important; }
div[data-testid="stDataFrame"] * { white-space: normal !important; overflow-wrap: anywhere !important; }
.stButton > button { border-radius: 10px !important; font-weight: 750 !important; min-height: 38px !important; border:1px solid #d7e3f5 !important; }
.tcc-flow { background:#eff6ff; border:1px solid #bfdbfe; border-radius:14px; padding:0.85rem 1rem; margin:0.75rem 0 1rem 0; color:#334155; }
.tcc-card-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap:0.85rem; margin:0.45rem 0 1rem 0; }
.tcc-card { border:1px solid; border-radius:16px; padding:0.95rem 1rem; min-height:112px; overflow:hidden; box-sizing:border-box; }
.tcc-label { color:#64748b; font-size:0.72rem; font-weight:900; letter-spacing:0.05em; text-transform:uppercase; margin-bottom:0.32rem; }
.tcc-value { font-size:clamp(1.12rem, 2.2vw, 1.55rem); font-weight:950; line-height:1.08; margin-bottom:0.35rem; overflow-wrap:anywhere; }
.tcc-detail { color:#475569; font-size:0.83rem; line-height:1.35; overflow-wrap:anywhere; }
.tcc-mini-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 170px), 1fr)); gap:0.65rem; margin:0.45rem 0 1rem 0; }
.tcc-mini { background:#f8fafc; border:1px solid #dbe3ef; border-radius:14px; padding:0.72rem 0.82rem; }
.tcc-mini-label { color:#64748b; font-size:0.68rem; font-weight:900; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.25rem; }
.tcc-mini-value { color:#111827; font-size:0.98rem; font-weight:900; overflow-wrap:anywhere; }
.tcc-position-source-card { display:flex; flex-direction:column; justify-content:center; align-items:stretch; min-height:100%; background:#ffffff; border:1px solid #dbe3ef; border-radius:14px; padding:0.72rem 0.82rem; box-sizing:border-box; }
.tcc-position-source-label { color:#64748b; font-size:0.68rem; font-weight:900; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.25rem; }
.tcc-position-source-value { color:#111827; font-size:clamp(1.2rem, 1.8vw, 2rem); line-height:1.15; font-weight:700; white-space:normal; overflow-wrap:break-word; word-break:normal; hyphens:none; max-width:24ch; }
.tcc-section-card { background:#ffffff; border:1px solid #e5eaf3; border-radius:18px; padding:1rem; margin:0 0 1rem 0; overflow:hidden; }
.tcc-reason-panel { background:#ffffff; border:1px solid #dbe3ef; border-radius:14px; overflow:hidden; margin:0.35rem 0 1rem 0; }
.tcc-reason-row { padding:0.72rem 0.90rem; border-bottom:1px solid #e5e7eb; font-size:0.92rem; line-height:1.38; color:#1f2937; overflow-wrap:anywhere; }
.tcc-reason-row:last-child { border-bottom:0; }
.tcc-reason-header { background:#f8fafc; color:#64748b; font-weight:900; text-transform:uppercase; letter-spacing:0.03em; font-size:0.74rem; }
.tcc-checklist { display:grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap:0.55rem; margin-top:0.4rem; }
.tcc-check { border:1px solid #dbe3ef; border-radius:12px; background:#f8fafc; padding:0.58rem 0.7rem; font-weight:800; color:#334155; }

.tcc-banner { border:1px solid; border-radius:18px; padding:1rem 1.1rem; margin:0.65rem 0 1rem 0; overflow:hidden; }
.tcc-banner-label { font-size:0.72rem; font-weight:950; letter-spacing:0.06em; text-transform:uppercase; color:#64748b; margin-bottom:0.28rem; }
.tcc-banner-value { font-size:clamp(1.20rem, 2.2vw, 1.68rem); font-weight:950; line-height:1.08; margin-bottom:0.35rem; overflow-wrap:anywhere; }
.tcc-banner-detail { font-size:0.90rem; line-height:1.42; color:#475569; overflow-wrap:anywhere; }
.tcc-risk-list { margin:0.4rem 0 0.2rem 0; padding-left:1.2rem; color:#334155; line-height:1.5; }
.tcc-ticket-table { width:100%; border-collapse:collapse; margin-top:0.35rem; font-size:0.88rem; }
.tcc-ticket-table td { border-bottom:1px solid #e5eaf3; padding:0.48rem 0.25rem; vertical-align:top; overflow-wrap:anywhere; }
.tcc-ticket-table td:first-child { color:#64748b; font-weight:900; text-transform:uppercase; font-size:0.70rem; letter-spacing:0.04em; width:38%; }
.tcc-gauge-wrap { background:#f1f5f9; border:1px solid #dbe3ef; border-radius:999px; height:0.72rem; overflow:hidden; margin:0.4rem 0 0.55rem 0; }
.tcc-gauge-fill { height:100%; border-radius:999px; }
.tcc-hero-badges { display:flex; flex-wrap:wrap; gap:0.46rem; margin:0.10rem 0 0.50rem 0; }
.tcc-pill { display:inline-flex; align-items:center; gap:0.34rem; border-radius:999px; padding:0.30rem 0.58rem; border:1px solid; line-height:1.12; }
.tcc-pill-label { font-size:0.68rem; font-weight:880; letter-spacing:0.05em; text-transform:uppercase; opacity:0.92; }
.tcc-pill-value { font-size:0.82rem; font-weight:900; }
.tcc-pill-status { background:#ecfdf3; border-color:#86efac; color:#166534; }
.tcc-pill-grade { background:#eff6ff; border-color:#93c5fd; color:#1d4ed8; }
.tcc-pill-direction { background:#f8fafc; border-color:#dbe3ef; color:#0f172a; }
.tcc-pill-risk { background:#fffbeb; border-color:#fcd34d; color:#b45309; }

@media (max-width:1180px) {
    div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    div[data-testid="stHorizontalBlock"] > div, div[data-testid="column"] { min-width:100% !important; flex:1 1 100% !important; width:100% !important; }
    .tcc-section-card { padding:0.85rem; border-radius:15px; }
}
@media (max-width:760px) {
    .tcc-card-grid, .tcc-mini-grid, .tcc-checklist { grid-template-columns:1fr; }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def card_html(title: str, value: Any, detail: str = "", tone: str = "neutral") -> str:
    bg, border, color = tone_palette(tone)
    help_text = ""
    if isinstance(value, dict):
        help_text = str(value.get("help", "") or "")
        value = value.get("text", "")
    value_lines = [html.escape(str(part)) for part in str(value).splitlines() if str(part).strip()]
    value_html = "<br>".join(value_lines) if value_lines else html.escape(str(value))
    title_attr = f' title="{html.escape(help_text)}"' if help_text else ""
    return (
        f'<div class="tcc-card" style="background:{bg};border-color:{border};"{title_attr}>'
        f'<div class="tcc-label">{html.escape(str(title))}</div>'
        f'<div class="tcc-value" style="color:{color};">{value_html}</div>'
        f'<div class="tcc-detail">{html.escape(str(detail))}</div>'
        f'</div>'
    )


def render_card_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="tcc-card-grid">']
    for card in cards:
        pieces.append(card_html(card.get("title", ""), card.get("value", ""), card.get("detail", ""), card.get("tone", "neutral")))
    pieces.append("</div>")
    st.markdown("".join(pieces), unsafe_allow_html=True)


def risk_reward_card_value(ratio: float) -> Dict[str, str]:
    ratio_value = max(0.0, safe_float(ratio, 0.0))
    beginner_line = f"{ratio_value:.1f} : 1"
    professional_line = f"{ratio_value:.0f}R — Reward is {ratio_value:.0f}× the risk" if ratio_value > 0 else "Pending"
    help_text = (
        "R means risk unit. 1R = your planned loss if the stop is hit. "
        "2R = potential reward is twice your planned risk."
    )
    return {
        "text": f"{beginner_line}\n{professional_line}",
        "help": help_text,
    }


def render_mini_grid(items: List[Tuple[str, Any]]) -> None:
    pieces = ['<div class="tcc-mini-grid">']
    for label, value in items:
        pieces.append(
            f'<div class="tcc-mini"><div class="tcc-mini-label">{html.escape(str(label))}</div>'
            f'<div class="tcc-mini-value">{html.escape(str(value))}</div></div>'
        )
    pieces.append("</div>")
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_reason_panel(reasons: List[str]) -> None:
    clean = [str(item).strip() for item in reasons if str(item).strip()]
    if not clean:
        st.info("No decision reasons available yet.")
        return
    pieces = ['<div class="tcc-reason-panel">']
    pieces.append('<div class="tcc-reason-row tcc-reason-header">Reason</div>')
    for reason in clean:
        pieces.append(f'<div class="tcc-reason-row">{html.escape(reason)}</div>')
    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def section_open(title: str, caption: str = "") -> None:
    st.markdown('<div class="tcc-section-card">', unsafe_allow_html=True)
    if title:
        st.markdown(f"### {title}")
    if caption:
        st.caption(caption)


def section_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def navigate_to(page_key: str) -> None:
    st.session_state["jfbp_main_navigation"] = page_key
    st.rerun()


# =========================================================
# DATA SNAPSHOTS
# =========================================================

def market_snapshot() -> Dict[str, Any]:
    return {
        "regime": st.session_state.get("market_reaction_regime", "UNKNOWN"),
        "playbook": st.session_state.get("market_reaction_playbook", ""),
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
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def risk_plan_rows() -> List[Dict[str, Any]]:
    rows = st.session_state.get("scanner_last_risk_plan", [])
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def hold_rows() -> List[Dict[str, Any]]:
    rows = st.session_state.get("scanner_last_hold_rows", [])
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def row_symbol(row: Dict[str, Any]) -> str:
    return str(row.get("display_symbol") or row.get("symbol") or "").upper().strip()


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


def select_trade_symbol() -> Dict[str, Any]:
    rows = scanner_rows()
    lookup: Dict[str, Dict[str, Any]] = {}
    symbols: List[str] = []

    for row in rows:
        symbol = row_symbol(row)
        if symbol and symbol not in lookup:
            lookup[symbol] = row
            symbols.append(symbol)

    handoff_symbol = str(st.session_state.get("handoff_symbol") or "").upper().strip()
    trade_command_symbol = str(st.session_state.get("trade_command_symbol") or "").upper().strip()
    selected_symbol = str(st.session_state.get("selected_symbol") or "").upper().strip()
    preferred = handoff_symbol or trade_command_symbol or selected_symbol or row_symbol(best_scanner_row())

    if preferred and preferred not in lookup:
        lookup[preferred] = {
            "symbol": preferred,
            "display_symbol": preferred,
            "sector": str(st.session_state.get("handoff_asset_class") or "Manual").strip() or "Manual",
            "trade_recommendation": "WATCH",
            "opportunity_score_pct": 0,
            "overall_rating": "N/A",
            "source": str(st.session_state.get("handoff_source") or "Manual").strip() or "Manual",
        }
        symbols.insert(0, preferred)

    if symbols:
        if handoff_symbol and handoff_symbol in symbols:
            st.session_state["tcc_symbol_select_v20"] = handoff_symbol
            st.session_state["trade_command_symbol"] = handoff_symbol
            st.session_state["selected_symbol"] = handoff_symbol
            st.session_state["tcc_symbol"] = handoff_symbol
            st.session_state.pop("handoff_symbol", None)
            st.session_state.pop("handoff_source", None)

        default_symbol = preferred if preferred in symbols else symbols[0]
        if "tcc_symbol_select_v20" not in st.session_state:
            st.session_state["tcc_symbol_select_v20"] = default_symbol
        elif str(st.session_state.get("tcc_symbol_select_v20") or "").upper().strip() not in symbols:
            st.session_state["tcc_symbol_select_v20"] = default_symbol

        chosen = st.selectbox("Trade command symbol", options=symbols, key="tcc_symbol_select_v20")
        st.session_state["trade_command_symbol"] = chosen
        st.session_state["selected_symbol"] = chosen
        st.session_state["tcc_symbol"] = chosen
        return lookup.get(chosen, {})

    manual_default = preferred or st.session_state.get("trade_command_symbol") or st.session_state.get("selected_symbol") or "AAPL"
    _ensure_widget_default("trade_command_manual_symbol_v20", manual_default)
    manual = st.text_input(
        "Trade command symbol",
        key="trade_command_manual_symbol_v20",
    ).upper().strip()
    st.session_state["trade_command_symbol"] = manual
    st.session_state["selected_symbol"] = manual
    st.session_state["tcc_symbol"] = manual
    return {
        "symbol": manual,
        "display_symbol": manual,
        "trade_recommendation": "WATCH",
        "opportunity_score_pct": 0,
        "overall_rating": "N/A",
        "sector": "Manual",
        "price": 0,
    }


def matching_plan_row(symbol: str) -> Dict[str, Any]:
    symbol = str(symbol or "").upper().strip()
    for row in risk_plan_rows():
        if row_symbol(row) == symbol or str(row.get("symbol") or "").upper().strip() == symbol:
            return row
    return {}


def matching_hold_row(symbol: str) -> Dict[str, Any]:
    symbol = str(symbol or "").upper().strip()
    for row in hold_rows():
        if row_symbol(row) == symbol or str(row.get("symbol") or "").upper().strip() == symbol:
            return row
    return {}


def execution_snapshot() -> Dict[str, Any]:
    risk = risk_snapshot()
    return {
        "mode": str(st.session_state.get("mode", "SIM")).upper().strip(),
        "pipeline": "READY" if st.session_state.get("pipeline") else "MISSING",
        "armed": bool(st.session_state.get("live_trading_armed", False)),
        "kill_switch": bool(st.session_state.get("risk_kill_switch", False)),
        "risk_state": risk.get("risk_state", "NORMAL"),
        "gross_exposure": risk.get("gross_exposure", 0),
        "open_positions": risk.get("open_positions", 0),
    }


def optionable_symbol(symbol: str) -> bool:
    s = str(symbol or "").upper().strip()
    if not s or s in {"RUN SCANNER", "N/A"}:
        return False
    if s.endswith("=X") or s.endswith("=F") or s.endswith("-USD"):
        return False
    if ".TO" in s:
        return False
    return True


def suggested_options_structure(row: Dict[str, Any], market: Dict[str, Any]) -> Tuple[str, str, str]:
    symbol = row_symbol(row)
    signal = normalize_signal(row.get("trade_recommendation") or row.get("scanner_action") or row.get("signal"))
    score = safe_float(row.get("opportunity_score_pct") or row.get("model_score"), 0.0)
    stress = safe_float(market.get("stress_score"), 0.0)
    buy_allowed = bool(market.get("buy_allowed", True))
    regime = str(market.get("regime") or "UNKNOWN").upper().strip()

    if not optionable_symbol(symbol):
        return "No options structure", "Not optionable in v2", "neutral"
    if stress >= 70 or not buy_allowed or regime in {"RISK_OFF", "RISK-OFF", "DEFENSIVE"}:
        return "No New Long Premium", "Defense first; covered call only if already long shares", "risk"
    if signal == "BUY" and score >= 85:
        return "Bull Call Spread", "Defined-risk bullish structure", "good"
    if signal == "BUY":
        return "Bull Call Spread", "Qualified bullish setup; confirm liquidity", "good"
    if signal == "SELL":
        return "Bear Put Spread", "Defined-risk bearish / hedge structure", "risk"
    if signal == "WATCH" and score >= 65:
        return "Cash-Secured Put", "Entry/income structure only if willing to own shares", "warning"
    return "No Options Trade", "Wait for stronger confirmation", "warning"


def opportunity_grade(score: Any, rating: Any = "", signal: Any = "") -> Tuple[str, str, str]:
    s = safe_float(score, 0.0)
    r = str(rating or "").upper().strip()
    sig = normalize_signal(signal)
    if sig in {"AVOID", "SELL"} and s < 60:
        return "🔴 AVOID", "risk", "Opportunity quality is weak or adverse."
    if s >= 85 or (s >= 75 and r in {"A+", "A", "A-"}):
        return "🟢 TRADEABLE", "good", "High-quality candidate worth considering."
    if s >= 60:
        return "🟡 DEVELOPING", "warning", "Candidate is forming but still needs confirmation."
    return "⚪ MONITOR", "neutral", "Watch only until the opportunity improves."


def institutional_grade(decision: Dict[str, Any], checklist: List[Tuple[str, bool]] | None = None, plan: Dict[str, Any] | None = None) -> Tuple[str, str, str]:
    label = str((decision or {}).get("label", "")).upper()
    score = safe_float((decision or {}).get("score"), 0.0)
    plan = plan if isinstance(plan, dict) else {}
    executable = bool(plan.get("executable")) or str(plan.get("position_action") or "").upper().startswith("OPEN")
    passed = sum(1 for _, ok in (checklist or []) if ok)

    if "BLOCKED" in label:
        return "🔴 BLOCKED", "risk", "Risk controls do not allow execution."
    if "TRADE READY" in label and (executable or passed >= 7):
        return "🔵 READY", "good", "Institutional execution criteria are aligned."
    if score >= 60 or "WATCH" in label or "REVIEW" in label:
        return "🟡 PENDING CONFIRMATION", "warning", "Opportunity exists, but full institutional confirmation is not complete."
    return "⚪ STAND BY", "neutral", "Insufficient confirmation for capital deployment."


def grade_explainer() -> str:
    return (
        "JFBP Quant Desk protects capital first and pursues opportunity second. "
        "Opportunity Grade measures whether the candidate is worth considering. "
        "Institutional Grade measures whether the setup is ready for capital deployment."
    )


def decision_score(row: Dict[str, Any], market: Dict[str, Any], plan: Dict[str, Any], risk: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    reasons: List[str] = []

    scanner_score = safe_float(row.get("opportunity_score_pct"), 0.0)
    scanner_component = max(0, min(35, int(round(scanner_score * 0.35))))
    score += scanner_component
    reasons.append(f"Scanner contributes {scanner_component}/35")

    rating = str(row.get("overall_rating") or "").upper().strip()
    rating_map = {"A+": 20, "A": 18, "A-": 16, "B+": 13, "B": 11, "B-": 9, "C": 6, "D": 3, "F": 0}
    rating_component = rating_map.get(rating, 5 if rating else 0)
    score += rating_component
    reasons.append(f"Rating contributes {rating_component}/20")

    market_stress = safe_float(market.get("stress_score"), 0.0)
    buy_allowed = bool(market.get("buy_allowed", True))
    regime = str(market.get("regime") or "UNKNOWN").upper().strip()

    if market_stress >= 70 or not buy_allowed or regime in {"RISK_OFF", "RISK-OFF", "DEFENSIVE"}:
        market_component = 4
        reasons.append("Market filter is defensive")
    elif regime in {"RISK_ON", "RISK-ON"}:
        market_component = 20
        reasons.append("Market filter supports risk exposure")
    else:
        market_component = 12
        reasons.append("Market filter is selective/neutral")
    score += market_component

    executable = bool(plan.get("executable")) or str(plan.get("position_action") or "").upper().startswith("OPEN")
    plan_component = 15 if executable else 5
    score += plan_component
    reasons.append("Risk plan is executable" if executable else "Risk plan is not executable yet")

    risk_state = str(risk.get("risk_state") or "NORMAL").upper().strip()
    if risk_state in {"NORMAL", "OK", "GREEN", "READY", "UNKNOWN", ""}:
        risk_component = 10
        reasons.append("Risk engine is normal")
    else:
        risk_component = 2
        reasons.append(f"Risk engine state: {risk_state}")
    score += risk_component

    score = int(max(0, min(100, score)))

    signal = normalize_signal(row.get("trade_recommendation") or row.get("scanner_action") or row.get("signal"))
    executable_action = str(plan.get("execution_action") or plan.get("scanner_action") or plan.get("action") or "").upper().strip()

    if risk_state not in {"NORMAL", "OK", "GREEN", "READY", "UNKNOWN", ""} or bool(st.session_state.get("risk_kill_switch", False)):
        label, tone = "🔴 BLOCKED", "risk"
    elif score >= 80 and executable:
        label, tone = "🟢 TRADE READY", "good"
    elif signal == "WATCH" and executable_action in {"BUY", "SELL"}:
        label, tone = "🟡 REVIEW SETUP", "warning"
    elif score >= 60:
        label, tone = "🟡 WATCH ONLY", "warning"
    else:
        label, tone = "⚪ WAIT", "neutral"

    return {"score": score, "label": label, "tone": tone, "reasons": reasons}


def top_decision_reasons(decision: Dict[str, Any], limit: int = 3) -> List[str]:
    reasons = decision.get("reasons", []) if isinstance(decision, dict) else []
    return [str(item).strip() for item in reasons if str(item).strip()][:limit]


def scanner_plan_mismatch_warning(signal: str, plan: Dict[str, Any]) -> str:
    signal = normalize_signal(signal)
    plan = plan if isinstance(plan, dict) else {}
    plan_action = str(plan.get("execution_action") or plan.get("scanner_action") or plan.get("action") or "").upper().strip()
    plan_executable = bool(plan.get("executable")) or str(plan.get("position_action") or "").upper().startswith("OPEN")

    if signal == "WATCH" and plan_executable and plan_action in {"BUY", "SELL"}:
        return "Scanner is WATCH, but the Risk-Aware Plan has approved execution. Review Research Stock, Options Center, and OMS before routing."
    if signal == "SELL" and plan_action == "BUY":
        return "Scanner and Risk-Aware Plan actions do not match. Review before routing."
    if signal == "BUY" and plan_action == "SELL":
        return "Scanner and Risk-Aware Plan actions do not match. Review before routing."
    return ""


# =========================================================
# TRADE PLANNING ENGINE
# =========================================================

def derive_trade_levels(row: Dict[str, Any], plan: Dict[str, Any], signal: str) -> Dict[str, float]:
    price = safe_float(row.get("price") or row.get("last_price") or row.get("close"), 0.0)
    if price <= 0:
        price = safe_float(plan.get("price") or plan.get("entry") or plan.get("entry_price"), 0.0)
    if price <= 0:
        price = 100.0

    entry = safe_float(plan.get("entry") or plan.get("entry_price"), price)
    if entry <= 0:
        entry = price

    raw_stop = safe_float(plan.get("stop") or plan.get("stop_price"), 0.0)
    raw_target = safe_float(plan.get("target") or plan.get("target_price"), 0.0)

    if signal == "SELL":
        stop = raw_stop if raw_stop > 0 else entry * 1.06
        target_1 = raw_target if raw_target > 0 else entry * 0.92
        target_2 = entry - (abs(stop - entry) * 2.0)
        target_3 = entry - (abs(stop - entry) * 3.0)
    else:
        stop = raw_stop if raw_stop > 0 else entry * 0.94
        target_1 = raw_target if raw_target > 0 else entry * 1.10
        target_2 = entry + (abs(entry - stop) * 2.0)
        target_3 = entry + (abs(entry - stop) * 3.0)

    return {
        "entry": entry,
        "stop": stop,
        "target_1": target_1,
        "target_2": target_2,
        "target_3": target_3,
        "last": price,
    }


def render_section_guidance(lines: List[str], tip: str = "") -> None:
    body = "<br>".join(html.escape(str(line)) for line in (lines or []) if str(line).strip())
    if body:
        st.markdown(
            (
                "<div style='border:1px solid #dbe3ea; background:#f8fafc; "
                "border-radius:10px; padding:0.55rem 0.7rem; margin:0.2rem 0 0.55rem 0; "
                "font-size:0.86rem; color:#475569; line-height:1.4;'>"
                f"{body}</div>"
            ),
            unsafe_allow_html=True,
        )
    if tip:
        st.caption(f"Tip: {tip}")


def _trailing_method_copy(method: str) -> dict[str, str]:
    method_key = str(method or "").strip().upper()
    copies = {
        "PERCENTAGE": {
            "label": "Percentage",
            "summary": "Keeps the stop a fixed percentage below the highest price reached.",
            "best_for": "Best for: Simple momentum trading | Beginners",
            "pros": "Pros | Easy to understand | Automatically locks in profits",
            "cons": "Cons | Does not adapt to market volatility.",
            "active": "✓ Percentage Trailing Stop Active",
            "active_body": "Your stop will trail by a fixed percentage below the highest price reached.",
        },
        "ATR": {
            "label": "ATR (Recommended)",
            "summary": "Uses Average True Range (ATR) to adjust the stop based on the stock's normal daily volatility.",
            "best_for": "Best for: Swing trading | Volatile stocks | Professional trading",
            "pros": "Pros | Adapts to market volatility | Reduces unnecessary stop-outs | Widely used by professional traders",
            "cons": "Cons | Requires ATR-based interpretation of price movement.",
            "active": "✓ ATR Trailing Stop Active",
            "active_body": "Your stop will automatically adjust based on the stock's normal daily volatility.",
        },
        "SWING LOW": {
            "label": "Swing Low",
            "summary": "Moves the stop below each new significant swing low.",
            "best_for": "Best for: Trend following | Price action trading",
            "pros": "Pros | Follows market structure | Gives trends room to develop",
            "cons": "Cons | Can give back more open profit during pullbacks.",
            "active": "✓ Swing Low Trailing Stop Active",
            "active_body": "Your stop will track below each new significant swing low.",
        },
        "EMA 21": {
            "label": "EMA 21",
            "summary": "Trails the stop using the 21-period Exponential Moving Average.",
            "best_for": "Best for: Medium-term trend trades | Growth stocks",
            "pros": "Pros | Smooths market noise | Keeps you in strong trends longer",
            "cons": "Cons | Can lag during fast reversals.",
            "active": "✓ EMA 21 Trailing Stop Active",
            "active_body": "Your stop will follow the 21-period Exponential Moving Average.",
        },
        "EMA 50": {
            "label": "EMA 50",
            "summary": "Trails the stop using the 50-period Exponential Moving Average.",
            "best_for": "Best for: Long-term investing | Position trading",
            "pros": "Pros | Avoids reacting to short-term price fluctuations | Lets major trends develop",
            "cons": "Cons | Gives the trade more room, which can increase drawdown.",
            "active": "✓ EMA 50 Trailing Stop Active",
            "active_body": "Your stop will follow the 50-period Exponential Moving Average.",
        },
    }
    return copies.get(method_key, copies["ATR"])


def build_sizing_plan(symbol: str, signal: str, levels: Dict[str, float], market: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    preferences = get_trading_preferences()
    preference_effective = preferences.get("effective", {}) if isinstance(preferences, dict) else {}
    account_context = resolve_account_context()
    multiplier = safe_float(market.get("execution_multiplier"), 1.0)
    default_account_size = safe_float(account_context.get("account_size"), safe_float(preferences.get("account_size"), 100000.0))
    default_risk_pct = safe_float(preference_effective.get("risk_per_trade_pct"), 1.0)
    manual_mode = not bool(account_context.get("ibkr_connected", False))
    account_size_key = f"tcc_manual_account_size_{symbol}"
    risk_pct_key = f"tcc_trade_risk_pct_{symbol}"
    if account_size_key not in st.session_state:
        st.session_state[account_size_key] = default_account_size
    if risk_pct_key not in st.session_state:
        st.session_state[risk_pct_key] = default_risk_pct
    st.session_state[account_size_key] = max(0.0, safe_float(st.session_state.get(account_size_key), default_account_size))
    st.session_state[risk_pct_key] = min(5.0, max(0.0, safe_float(st.session_state.get(risk_pct_key), default_risk_pct)))

    st.markdown("#### Entry & Risk")
    render_section_guidance(
        [
            "Define your account size, entry price, stop loss, and maximum risk.",
            "This section determines your position size and keeps risk within your plan.",
        ],
        tip="Many professional traders risk only 0.5%-1% of account equity per trade.",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if manual_mode:
            account_size = st.number_input(
                "Account Size",
                min_value=0.0,
                step=1000.0,
                format="%.2f",
                key=account_size_key,
                disabled=False,
            )
        else:
            account_size = safe_float(account_context.get("net_liquidation"), default_account_size)
            st.metric("Account Size", f"${account_size:,.2f}", help="Loaded from IBKR Net Liquidation")
        st.caption(f"{account_context.get('account_size_source')} | {account_context.get('account_source')}")
        if account_context.get("ibkr_connected") and safe_float(account_context.get("net_liquidation"), 0.0) <= 0:
            st.warning("IBKR is connected, but no usable Net Liquidation snapshot is available yet. Manual sizing remains enabled until the broker snapshot is populated.")
    with c2:
        risk_pct = st.number_input(
            "Risk %",
            min_value=0.0,
            max_value=5.0,
            step=0.25,
            format="%.2f",
            key=risk_pct_key,
            disabled=False,
        )
        st.caption(_trade_risk_pct_source_label(risk_pct, default_risk_pct))
    with c3:
        _ensure_widget_default(f"tcc_entry_{symbol}", float(levels["entry"]))
        st.session_state[f"tcc_entry_{symbol}"] = max(0.01, safe_float(st.session_state.get(f"tcc_entry_{symbol}"), float(levels["entry"])))
        entry = st.number_input("Entry", min_value=0.01, step=0.01, key=f"tcc_entry_{symbol}")
    with c4:
        _ensure_widget_default(f"tcc_stop_{symbol}", float(levels["stop"]))
        st.session_state[f"tcc_stop_{symbol}"] = max(0.01, safe_float(st.session_state.get(f"tcc_stop_{symbol}"), float(levels["stop"])))
        stop = st.number_input("Stop", min_value=0.01, step=0.01, key=f"tcc_stop_{symbol}")

    per_share_risk_pre = abs(entry - stop)
    risk_budget_pre = account_size * (risk_pct / 100.0) * multiplier
    max_position_pct_default = safe_float(preference_effective.get("max_position_size_pct"), 8.0)
    max_position_value_pre = account_size * (safe_float(st.session_state.get("tcc_max_position_pct"), max_position_pct_default) / 100.0)
    risk_qty_pre = int(risk_budget_pre / per_share_risk_pre) if per_share_risk_pre > 0 else 0
    max_qty_pre = int(max_position_value_pre / entry) if entry > 0 else 0
    qty_pre = max(0, min(risk_qty_pre, max_qty_pre))

    if per_share_risk_pre <= 0:
        st.error("Entry and Stop cannot be equal. Define a valid stop distance.")
    else:
        st.caption(
            f"Position Size Preview: {qty_pre:,} | Dollar Risk Budget: {fmt_money(risk_budget_pre)} | "
            f"Per-Share Risk: {fmt_money(per_share_risk_pre)}"
        )

    target_1_default = float(levels["target_1"])
    target_2_default = float(levels["target_2"])
    target_3_default = float(levels.get("target_3", target_2_default))
    st.markdown("#### Profit Targets")
    render_section_guidance(
        [
            "Choose where to take profits and how much to sell at each target.",
            "Scaling out can reduce emotional decisions while leaving room for trend continuation.",
        ]
    )
    p1, p2, p3, p4, p5 = st.columns(5)
    with p1:
        _ensure_widget_default(f"tcc_target1_{symbol}", target_1_default)
        st.session_state[f"tcc_target1_{symbol}"] = max(0.01, safe_float(st.session_state.get(f"tcc_target1_{symbol}"), target_1_default))
        target_1 = st.number_input("Target 1", min_value=0.01, step=0.01, key=f"tcc_target1_{symbol}")
    with p2:
        _ensure_widget_default(f"tcc_target2_{symbol}", target_2_default)
        st.session_state[f"tcc_target2_{symbol}"] = max(0.01, safe_float(st.session_state.get(f"tcc_target2_{symbol}"), target_2_default))
        target_2 = st.number_input("Target 2", min_value=0.01, step=0.01, key=f"tcc_target2_{symbol}")
    with p3:
        _ensure_widget_default(f"tcc_target3_{symbol}", target_3_default)
        st.session_state[f"tcc_target3_{symbol}"] = max(0.01, safe_float(st.session_state.get(f"tcc_target3_{symbol}"), target_3_default))
        target_3 = st.number_input("Target 3", min_value=0.01, step=0.01, key=f"tcc_target3_{symbol}")
    with p4:
        max_position_pct = safe_float(st.session_state.get("tcc_max_position_pct"), max_position_pct_default)
        st.metric("Max Position %", f"{max_position_pct:.1f}%")
        st.caption("Loaded from Trading Preferences")
    with p5:
        planned_qty = max(0, safe_int(plan.get("qty"), 0))
        scanner_qty_seed_key = f"tcc_scanner_qty_seed_{symbol}"
        sizing_seed_key = f"tcc_sizing_seed_{symbol}"
        position_size_source_key = f"tcc_position_size_source_{symbol}"

        if scanner_qty_seed_key not in st.session_state:
            st.session_state[scanner_qty_seed_key] = planned_qty
        scanner_qty = max(0, safe_int(st.session_state.get(scanner_qty_seed_key), planned_qty))

        current_signature = {
            "account_size": round(safe_float(account_size, 0.0), 6),
            "risk_pct": round(safe_float(risk_pct, 0.0), 6),
            "entry": round(safe_float(entry, 0.0), 6),
            "stop": round(safe_float(stop, 0.0), 6),
            "max_position_pct": round(safe_float(max_position_pct, max_position_pct_default), 6),
        }
        if sizing_seed_key not in st.session_state:
            st.session_state[sizing_seed_key] = current_signature

        seed_signature = st.session_state.get(sizing_seed_key, current_signature)
        if not isinstance(seed_signature, dict):
            seed_signature = current_signature
            st.session_state[sizing_seed_key] = current_signature

        watched_fields = ["account_size", "risk_pct", "entry", "stop", "max_position_pct"]
        inputs_changed = any(
            abs(safe_float(current_signature.get(field), 0.0) - safe_float(seed_signature.get(field), 0.0)) > 1e-6
            for field in watched_fields
        )

        if position_size_source_key not in st.session_state:
            if scanner_qty > 0:
                st.session_state[position_size_source_key] = "Using Scanner Recommendation"
            else:
                st.session_state[position_size_source_key] = "Recalculated from Trade Management Plan"

        position_size_source = str(st.session_state.get(position_size_source_key) or "Recalculated from Trade Management Plan")
        if inputs_changed or scanner_qty <= 0:
            position_size_source = "Recalculated from Trade Management Plan"
            st.session_state[position_size_source_key] = position_size_source
        elif position_size_source not in {"Using Scanner Recommendation", "Recalculated from Trade Management Plan"}:
            position_size_source = "Using Scanner Recommendation"
            st.session_state[position_size_source_key] = position_size_source

        st.markdown(
            f"""
            <div class="tcc-position-source-card">
                <div class="tcc-position-source-label">Position Size Source</div>
                <div class="tcc-position-source-value">{html.escape(position_size_source)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "The Scanner recommendation is used as the starting point. "
            "If you change risk, entry, stop, or account settings, JFBP Quant Desk recalculates the position size automatically."
        )

    rr2_preview = (abs(target_2 - entry) / per_share_risk_pre) if per_share_risk_pre > 0 else 0.0
    target_sequence_ok = True
    if str(signal).upper() == "SELL":
        target_sequence_ok = target_2 < target_1 and target_3 < target_2
    else:
        target_sequence_ok = target_2 > target_1 and target_3 > target_2

    if not target_sequence_ok:
        if str(signal).upper() == "SELL":
            st.warning("Target sequence invalid for SELL setup: Target 1 > Target 2 > Target 3 is required.")
        else:
            st.warning("Target sequence invalid: Target 1 < Target 2 < Target 3 is required.")

    if rr2_preview < 2.0:
        st.warning(f"Reward/Risk below preferred minimum (2.0R). Current R/R to Target 2: {rr2_preview:.2f}R")
    else:
        st.success(f"Reward/Risk check passed: {rr2_preview:.2f}R to Target 2")

    st.session_state["tcc_risk_pct_source_label"] = _trade_risk_pct_source_label(risk_pct, default_risk_pct)

    m1, m2, m3 = st.columns(3)
    with m1:
        _ensure_widget_default(f"tcc_tp1_allocation_{symbol}", safe_float(st.session_state.get("tcc_tp1_allocation_default"), 50.0))
        st.session_state[f"tcc_tp1_allocation_{symbol}"] = min(100.0, max(0.0, safe_float(st.session_state.get(f"tcc_tp1_allocation_{symbol}"), 50.0)))
        tp1_allocation = st.number_input("TP1 Allocation (%)", min_value=0.0, max_value=100.0, step=1.0, key=f"tcc_tp1_allocation_{symbol}")
    with m2:
        _ensure_widget_default(f"tcc_tp2_allocation_{symbol}", safe_float(st.session_state.get("tcc_tp2_allocation_default"), 40.0))
        st.session_state[f"tcc_tp2_allocation_{symbol}"] = min(100.0, max(0.0, safe_float(st.session_state.get(f"tcc_tp2_allocation_{symbol}"), 40.0)))
        tp2_allocation = st.number_input("TP2 Allocation (%)", min_value=0.0, max_value=100.0, step=1.0, key=f"tcc_tp2_allocation_{symbol}")
    with m3:
        _ensure_widget_default(f"tcc_tp3_allocation_{symbol}", safe_float(st.session_state.get("tcc_tp3_allocation_default"), 10.0))
        st.session_state[f"tcc_tp3_allocation_{symbol}"] = min(100.0, max(0.0, safe_float(st.session_state.get(f"tcc_tp3_allocation_{symbol}"), 10.0)))
        tp3_allocation = st.number_input("TP3 Allocation (%)", min_value=0.0, max_value=100.0, step=1.0, key=f"tcc_tp3_allocation_{symbol}")

    allocation_total = safe_float(tp1_allocation, 0.0) + safe_float(tp2_allocation, 0.0) + safe_float(tp3_allocation, 0.0)
    allocations_valid = abs(allocation_total - 100.0) < 0.0001
    if allocations_valid:
        st.success("TP allocation check passed: TP1 + TP2 + TP3 = 100%")
    else:
        st.error(f"TP allocation mismatch: TP1 + TP2 + TP3 = {allocation_total:.1f}% (must equal 100%).")

    max_portfolio_risk_limit = safe_float(st.session_state.get("tcc_max_portfolio_risk_pct"), PORTFOLIO_LIMIT_DEFAULTS["max_portfolio_risk_pct"])
    current_portfolio_risk = safe_float(st.session_state.get("portfolio_current_risk_pct"), 0.0)
    projected_portfolio_risk = current_portfolio_risk + risk_pct
    if projected_portfolio_risk > max_portfolio_risk_limit:
        st.warning(
            "Risk exceeds your configured portfolio limit. Suggested fixes: Reduce Risk %, move Stop closer only if technically valid, or skip this trade."
        )

    with st.container(border=True):
        st.markdown("#### Stop Management")
        render_section_guidance(
            [
                "Choose how your stop loss will be managed after the trade moves in your favor.",
                "Step 1: Optionally move your stop to breakeven once the trade has made sufficient progress.",
                "Step 2: Choose ONE trailing stop method to protect profits while allowing the trend to continue.",
            ],
            tip="ATR is the recommended default because it adapts to volatility.",
        )
        sm1, sm2 = st.columns(2)
        move_to_be_key = f"tcc_move_to_be_{symbol}"
        trailing_enabled_key = f"tcc_trailing_enabled_{symbol}"
        trailing_method_key = f"tcc_trailing_method_{symbol}"
        trailing_percent_key = f"tcc_trailing_percent_{symbol}"
        atr_multiple_key = f"tcc_atr_multiple_{symbol}"

        _ensure_widget_default(move_to_be_key, bool(st.session_state.get("tcc_move_to_be_default", True)))
        _ensure_widget_default(trailing_enabled_key, bool(st.session_state.get("tcc_trailing_enabled_default", False)))

        with sm1:
            move_to_break_even = st.checkbox(
                "Move Stop to Breakeven",
                key=move_to_be_key,
            )
        with sm2:
            trailing_enabled_prev_key = f"tcc_trailing_enabled_prev_{symbol}"
            was_trailing_enabled = bool(st.session_state.get(trailing_enabled_prev_key, False))
            trailing_enabled = st.checkbox(
                "Trailing Stop",
                key=trailing_enabled_key,
            )

        trailing_method_default = str(st.session_state.get("tcc_trailing_method_default", "ATR") or "ATR")
        atr_multiple_default = safe_float(st.session_state.get("tcc_atr_multiple_default"), 2.0)
        _ensure_widget_default(trailing_method_key, trailing_method_default)
        _ensure_widget_default(trailing_percent_key, 5.0)
        _ensure_widget_default(atr_multiple_key, atr_multiple_default)
        st.session_state[trailing_percent_key] = min(100.0, max(0.1, safe_float(st.session_state.get(trailing_percent_key), 5.0)))
        st.session_state[atr_multiple_key] = min(20.0, max(0.1, safe_float(st.session_state.get(atr_multiple_key), atr_multiple_default)))
        trailing_method = str(st.session_state.get(trailing_method_key, trailing_method_default))
        trailing_percent = safe_float(st.session_state.get(trailing_percent_key), 5.0)
        atr_multiple = safe_float(st.session_state.get(atr_multiple_key), atr_multiple_default)

        if trailing_enabled and not was_trailing_enabled:
            trailing_method = "ATR"
            atr_multiple = atr_multiple_default
            st.session_state[trailing_method_key] = trailing_method
            st.session_state[atr_multiple_key] = atr_multiple
        elif trailing_enabled and trailing_method not in {"Percentage", "ATR", "Swing Low", "EMA 21", "EMA 50"}:
            trailing_method = trailing_method_default
            st.session_state[trailing_method_key] = trailing_method

        if trailing_enabled:
            trailing_options = ["ATR", "Percentage", "Swing Low", "EMA 21", "EMA 50"]
            if str(st.session_state.get(trailing_method_key, trailing_method_default)) not in set(trailing_options):
                st.session_state[trailing_method_key] = trailing_method_default
            trailing_method = st.radio(
                "Trailing Method",
                options=trailing_options,
                format_func=lambda option: "ATR (Recommended)" if option == "ATR" else option,
                key=trailing_method_key,
                horizontal=True,
            )
            if trailing_method == "Percentage":
                trailing_percent = st.number_input(
                    "Trailing %",
                    min_value=0.1,
                    max_value=100.0,
                    step=0.1,
                    key=trailing_percent_key,
                )
            elif trailing_method == "ATR":
                atr_multiple = st.number_input(
                    "ATR Multiplier",
                    min_value=0.1,
                    max_value=20.0,
                    step=0.1,
                    key=atr_multiple_key,
                )

            method_copy = _trailing_method_copy(trailing_method)
            st.markdown(
                f"""
                <div style='border:1px solid #dbe3ea; background:#f8fafc; border-radius:10px; padding:0.7rem 0.8rem; margin-top:0.4rem;'>
                    <div style='font-weight:800; margin-bottom:0.25rem;'>{method_copy['label']}</div>
                    <div style='color:#334155; line-height:1.45; margin-bottom:0.35rem;'>{method_copy['summary']}</div>
                    <div style='color:#475569; line-height:1.45; margin-bottom:0.25rem;'><strong>{method_copy['best_for']}</strong></div>
                    <div style='color:#475569; line-height:1.45; margin-bottom:0.15rem;'>{method_copy['pros']}</div>
                    <div style='color:#475569; line-height:1.45;'>{method_copy['cons']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if trailing_enabled:
            st.success(f"{method_copy['active']}")
            st.caption(method_copy["active_body"])
        else:
            st.caption("Trailing stop is currently disabled.")

        st.session_state[trailing_enabled_prev_key] = trailing_enabled

    stop_adjustment_method_map = {
        "ATR": "ATR",
        "Percentage": "Percentage",
        "Swing Low": "Swing Low",
        "EMA 21": "EMA21",
        "EMA 50": "EMA50",
    }
    stop_adjustment_method = stop_adjustment_method_map.get(str(trailing_method), "ATR")

    with st.container(border=True):
        st.markdown("#### Time Stop")
        render_section_guidance(
            [
                "Choose how long you allow the trade to develop.",
                "If progress is not meaningful within this window, the position should be flagged for review.",
            ]
        )
        time_stop_enabled_key = f"tcc_time_stop_enabled_{symbol}"
        time_stop_days_key = f"tcc_time_stop_days_{symbol}"
        _ensure_widget_default(time_stop_enabled_key, bool(st.session_state.get("tcc_time_stop_enabled_default", True)))
        _ensure_widget_default(time_stop_days_key, max(1, safe_int(st.session_state.get("tcc_time_stop_days_default"), 10)))
        st.session_state[time_stop_days_key] = min(252, max(1, safe_int(st.session_state.get(time_stop_days_key), 10)))
        time_stop_enabled = st.checkbox(
            "Enable Time Stop",
            key=time_stop_enabled_key,
        )
        time_stop_days = safe_int(st.session_state.get(time_stop_days_key), safe_int(st.session_state.get("tcc_time_stop_days_default"), 10))
        if time_stop_enabled:
            time_stop_days = st.number_input(
                "Exit After (Trading Days)",
                min_value=1,
                max_value=252,
                step=1,
                key=time_stop_days_key,
            )
            st.success(f"Time Stop Enabled. Trade will be reviewed after {int(time_stop_days)} trading days if progress is insufficient.")
        else:
            st.caption("Time Stop is disabled.")

    with st.container(border=True):
        st.markdown("#### Earnings & Weekend Protection")
        render_section_guidance(
            [
                "Scheduled events can create overnight gaps that bypass stop losses.",
                "Enable these options if you want reduced exposure before earnings or weekends.",
            ]
        )
        next_earnings_text = "Pending"
        earnings_date_iso = ""
        if analyze_symbol_earnings_risk is not None and str(symbol).strip():
            try:
                event = analyze_symbol_earnings_risk(str(symbol).strip().upper())
                earnings_date = getattr(event, "earnings_date", None)
                if earnings_date is not None:
                    next_earnings_text = earnings_date.strftime("%b %d")
                    earnings_date_iso = earnings_date.isoformat()
            except Exception:
                next_earnings_text = "Pending"
        st.markdown(f"**Next Earnings:** {next_earnings_text}")

        exit_before_earnings_key = f"tcc_exit_before_earnings_{symbol}"
        avoid_weekend_key = f"tcc_avoid_weekend_{symbol}"
        _ensure_widget_default(exit_before_earnings_key, bool(st.session_state.get("tcc_exit_before_earnings_default", True)))
        _ensure_widget_default(avoid_weekend_key, bool(st.session_state.get("tcc_avoid_weekend_default", False)))

        ep1, ep2 = st.columns(2)
        with ep1:
            exit_before_earnings = st.checkbox(
                "Exit Before Earnings",
                key=exit_before_earnings_key,
            )
        with ep2:
            avoid_weekend_hold = st.checkbox(
                "Avoid Holding Over Weekend",
                key=avoid_weekend_key,
            )

        if exit_before_earnings:
            st.success("Earnings Protection Enabled")
        else:
            days_to_earnings = None
            if earnings_date_iso:
                try:
                    days_to_earnings = max((date.fromisoformat(earnings_date_iso) - date.today()).days, 0)
                except Exception:
                    days_to_earnings = None
            if days_to_earnings is not None and days_to_earnings <= 5:
                st.warning(f"Earnings are in {days_to_earnings} days. Consider enabling Exit Before Earnings.")
            else:
                st.warning("Exit Before Earnings is disabled.")

    with st.container(border=True):
        st.markdown("#### Progress Requirement")
        render_section_guidance(
            [
                "Define the minimum progress expected within a set timeframe.",
                "Example: 25% of Target 1 within 5 trading days, or the trade is flagged as losing momentum.",
            ]
        )
        pr1, pr2 = st.columns(2)
        progress_pct_key = f"tcc_progress_pct_{symbol}"
        progress_days_key = f"tcc_progress_days_{symbol}"
        _ensure_widget_default(progress_pct_key, safe_float(st.session_state.get("tcc_progress_pct_default"), PORTFOLIO_LIMIT_DEFAULTS["progress_target_pct_of_tp1"]))
        _ensure_widget_default(progress_days_key, safe_int(st.session_state.get("tcc_progress_days_default"), PORTFOLIO_LIMIT_DEFAULTS["progress_within_days"]))
        st.session_state[progress_pct_key] = min(100.0, max(1.0, safe_float(st.session_state.get(progress_pct_key), PORTFOLIO_LIMIT_DEFAULTS["progress_target_pct_of_tp1"])))
        st.session_state[progress_days_key] = min(60, max(1, safe_int(st.session_state.get(progress_days_key), PORTFOLIO_LIMIT_DEFAULTS["progress_within_days"])))
        with pr1:
            progress_requirement_pct = st.number_input(
                "Required % of Target 1",
                min_value=1.0,
                max_value=100.0,
                step=1.0,
                key=progress_pct_key,
            )
        with pr2:
            progress_requirement_days = st.number_input(
                "Within Trading Days",
                min_value=1,
                max_value=60,
                step=1,
                key=progress_days_key,
            )
        st.caption("If the trade does not reach the required progress threshold within this window, monitoring should flag: Trade Losing Momentum.")
        if progress_requirement_pct >= 60 and progress_requirement_days <= 5:
            st.warning("Progress threshold may be difficult to achieve. Consider extending the review period or lowering required progress.")
        elif progress_requirement_pct >= 40 and progress_requirement_days <= 3:
            st.warning("Progress requirement looks aggressive for the selected timeframe.")

    per_share_risk = abs(entry - stop)
    dollar_risk = account_size * (risk_pct / 100.0) * multiplier
    risk_qty = int(dollar_risk / per_share_risk) if per_share_risk > 0 else 0
    max_value = account_size * (max_position_pct / 100.0)
    max_qty = int(max_value / entry) if entry > 0 else 0
    calculated_qty = max(0, min(risk_qty, max_qty))
    if position_size_source == "Using Scanner Recommendation" and scanner_qty > 0:
        qty = scanner_qty
    else:
        qty = calculated_qty
        position_size_source = "Recalculated from Trade Management Plan"
        st.session_state[position_size_source_key] = position_size_source
    final_qty = safe_int(qty, 0)
    position_value = qty * entry
    actual_risk = qty * per_share_risk
    actual_risk_pct = (actual_risk / account_size * 100.0) if account_size > 0 else 0
    rr_1 = (abs(target_1 - entry) / per_share_risk) if per_share_risk > 0 else 0
    rr_2 = (abs(target_2 - entry) / per_share_risk) if per_share_risk > 0 else 0
    rr_3 = (abs(target_3 - entry) / per_share_risk) if per_share_risk > 0 else 0

    return {
        "symbol": symbol,
        "action": "SELL" if signal == "SELL" else "BUY",
        "entry": entry,
        "stop": stop,
        "target_1": target_1,
        "target_2": target_2,
        "target_3": target_3,
        "qty": qty,
        "position_value": position_value,
        "dollar_risk": actual_risk,
        "risk_pct": actual_risk_pct,
        "risk_budget": dollar_risk,
        "per_share_risk": per_share_risk,
        "position_size_source": position_size_source,
        "scanner_qty": safe_int(scanner_qty, 0),
        "calculated_qty": safe_int(calculated_qty, 0),
        "final_qty": safe_int(final_qty, 0),
        "rr_1": rr_1,
        "rr_2": rr_2,
        "rr_3": rr_3,
        "account_size": account_size,
        "size_multiplier": multiplier,
        "tp1_allocation": safe_float(tp1_allocation, 50.0),
        "tp2_allocation": safe_float(tp2_allocation, 50.0),
        "tp3_allocation": safe_float(tp3_allocation, 0.0),
        "tp_allocations_valid": allocations_valid,
        "move_to_break_even": bool(move_to_break_even),
        "trailing_enabled": bool(trailing_enabled),
        "trailing_method": trailing_method,
        "trailing_percent": safe_float(trailing_percent, 5.0),
        "atr_multiple": safe_float(atr_multiple, 2.0),
        "stop_adjustment_method": str(stop_adjustment_method),
        "time_stop_enabled": bool(time_stop_enabled),
        "time_stop_days": int(time_stop_days) if bool(time_stop_enabled) else 10,
        "exit_before_earnings": bool(exit_before_earnings),
        "next_earnings": next_earnings_text,
        "next_earnings_date": earnings_date_iso,
        "avoid_weekend_hold": bool(avoid_weekend_hold),
        "progress_requirement_pct": safe_float(progress_requirement_pct, PORTFOLIO_LIMIT_DEFAULTS["progress_target_pct_of_tp1"]),
        "progress_requirement_days": safe_int(progress_requirement_days, PORTFOLIO_LIMIT_DEFAULTS["progress_within_days"]),
    }


def _portfolio_positions_from_risk(risk: Dict[str, Any]) -> Dict[str, float]:
    risk = risk if isinstance(risk, dict) else {}
    positions = risk.get("positions", {})
    if isinstance(positions, dict):
        return {str(k).upper().strip(): safe_float(v, 0.0) for k, v in positions.items() if str(k).strip()}
    return {}


def _symbol_sector_map(rows: List[Dict[str, Any]], hold: List[Dict[str, Any]]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for row in (rows or []) + (hold or []):
        if not isinstance(row, dict):
            continue
        sym = row_symbol(row)
        sec = str(row.get("sector") or row.get("Sector") or "Unknown").strip() or "Unknown"
        if sym and sym not in mapping:
            mapping[sym] = sec
    return mapping


def _symbol_exposure_map(risk: Dict[str, Any], hold: List[Dict[str, Any]]) -> Dict[str, float]:
    risk = risk if isinstance(risk, dict) else {}
    qty_map = _portfolio_positions_from_risk(risk)
    price_map = risk.get("last_prices", {}) if isinstance(risk.get("last_prices", {}), dict) else {}
    exposure: Dict[str, float] = {}

    for sym, qty in qty_map.items():
        px = safe_float(price_map.get(sym), 0.0)
        if px > 0 and abs(qty) > 0:
            exposure[sym] = abs(qty * px)

    for row in hold or []:
        if not isinstance(row, dict):
            continue
        sym = row_symbol(row)
        if not sym:
            continue
        if exposure.get(sym, 0.0) > 0:
            continue
        value_candidates = [
            row.get("position_value"),
            row.get("market_value"),
            row.get("notional"),
            row.get("exposure"),
        ]
        for candidate in value_candidates:
            val = abs(safe_float(candidate, 0.0))
            if val > 0:
                exposure[sym] = val
                break
    return exposure


def _estimated_current_portfolio_risk_pct(exposure_map: Dict[str, float], account_size: float) -> float:
    if account_size <= 0:
        return 0.0
    explicit = safe_float(st.session_state.get("portfolio_current_risk_pct"), -1.0)
    if explicit >= 0:
        return explicit
    per_position_risk_assumption = safe_float(st.session_state.get("portfolio_assumed_risk_per_position_pct"), 0.5)
    open_count = sum(1 for v in exposure_map.values() if v > 0)
    return max(0.0, open_count * per_position_risk_assumption)


def _sector_exposure_percentages(exposure_map: Dict[str, float], sector_map: Dict[str, str]) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    total_exposure = sum(v for v in exposure_map.values() if v > 0)
    if total_exposure <= 0:
        return {}
    for sym, value in exposure_map.items():
        sec = sector_map.get(sym, "Unknown") or "Unknown"
        totals[sec] = totals.get(sec, 0.0) + max(0.0, value)
    return {k: (v / total_exposure) * 100.0 for k, v in totals.items()}


def _heuristic_correlation_score(proposed_symbol: str, existing_symbol: str, proposed_sector: str, existing_sector: str) -> float:
    p = str(proposed_symbol or "").upper().strip()
    e = str(existing_symbol or "").upper().strip()
    ps = str(proposed_sector or "").strip().lower()
    es = str(existing_sector or "").strip().lower()
    if not p or not e:
        return 0.0
    if p == e:
        return 1.0
    if ps and es and ps == es:
        return 0.90
    thematic = {
        "QQQ": "technology",
        "XLK": "technology",
        "SMH": "technology",
        "SOXX": "technology",
        "XLF": "financial",
        "XLV": "healthcare",
    }
    if thematic.get(e, "") and thematic.get(e, "") == ps:
        return 0.88
    if p[:2] and p[:2] == e[:2]:
        return 0.72
    return 0.35


def build_portfolio_management_context(
    symbol: str,
    row: Dict[str, Any],
    sizing: Dict[str, Any],
    risk: Dict[str, Any],
    holds: List[Dict[str, Any]],
    scanner: List[Dict[str, Any]],
) -> Dict[str, Any]:
    account_size = safe_float(sizing.get("account_size"), 0.0)
    trade_risk_pct = safe_float(sizing.get("risk_pct"), 0.0)
    new_trade_exposure = safe_float(sizing.get("position_value"), 0.0)

    exposure_map = _symbol_exposure_map(risk, holds)
    sector_map = _symbol_sector_map(scanner, holds)

    current_portfolio_risk_pct = _estimated_current_portfolio_risk_pct(exposure_map, account_size)
    total_portfolio_risk_after = current_portfolio_risk_pct + trade_risk_pct

    current_open_trades = max(safe_int(risk.get("open_positions"), 0), len([v for v in exposure_map.values() if v > 0]))
    open_trades_after = current_open_trades + (1 if str(symbol or "").upper().strip() not in exposure_map else 0)

    current_sector_pct = _sector_exposure_percentages(exposure_map, sector_map)
    total_capital_allocated = sum(v for v in exposure_map.values() if v > 0)
    total_after_trade = total_capital_allocated + max(new_trade_exposure, 0.0)
    proposed_sector = str(row.get("sector") or "Unknown") or "Unknown"
    proposed_sector_current_value = current_sector_pct.get(proposed_sector, 0.0)
    if total_after_trade > 0:
        proposed_sector_current_dollars = (proposed_sector_current_value / 100.0) * max(total_capital_allocated, 0.0)
        proposed_sector_after_pct = ((proposed_sector_current_dollars + max(new_trade_exposure, 0.0)) / total_after_trade) * 100.0
    else:
        proposed_sector_after_pct = 0.0

    correlations = []
    for existing_symbol in sorted(exposure_map.keys()):
        score = _heuristic_correlation_score(
            str(symbol or "").upper().strip(),
            existing_symbol,
            proposed_sector,
            sector_map.get(existing_symbol, "Unknown"),
        )
        correlations.append({"symbol": existing_symbol, "score": score})
    correlations = sorted(correlations, key=lambda item: safe_float(item.get("score"), 0.0), reverse=True)

    largest_position_symbol = "Pending"
    largest_position_value = 0.0
    if exposure_map:
        largest_position_symbol, largest_position_value = max(exposure_map.items(), key=lambda item: item[1])

    largest_sector = "Pending"
    largest_sector_pct = 0.0
    if current_sector_pct:
        largest_sector, largest_sector_pct = max(current_sector_pct.items(), key=lambda item: item[1])

    cash_remaining = max(account_size - total_after_trade, 0.0) if account_size > 0 else 0.0

    return {
        "proposed_symbol": str(symbol or "").upper().strip(),
        "account_size": account_size,
        "trade_risk_pct": trade_risk_pct,
        "new_trade_exposure": new_trade_exposure,
        "current_portfolio_risk_pct": current_portfolio_risk_pct,
        "total_portfolio_risk_after": total_portfolio_risk_after,
        "current_open_trades": current_open_trades,
        "open_trades_after": open_trades_after,
        "sector_exposure_pct": current_sector_pct,
        "proposed_sector": proposed_sector,
        "proposed_sector_current_pct": proposed_sector_current_value,
        "proposed_sector_after_pct": proposed_sector_after_pct,
        "correlations": correlations,
        "total_capital_allocated": total_capital_allocated,
        "cash_remaining": cash_remaining,
        "largest_position_symbol": largest_position_symbol,
        "largest_position_value": largest_position_value,
        "largest_sector": largest_sector,
        "largest_sector_pct": largest_sector_pct,
    }


def render_portfolio_risk_controls(context: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    max_portfolio_risk_pct = safe_float(st.session_state.get("tcc_max_portfolio_risk_pct"), PORTFOLIO_LIMIT_DEFAULTS["max_portfolio_risk_pct"])
    max_open_trades = safe_int(st.session_state.get("tcc_max_open_trades"), PORTFOLIO_LIMIT_DEFAULTS["max_open_trades"])

    with st.container(border=True):
        st.markdown("#### Portfolio Risk Controls")
        render_section_guidance(
            [
                "Before opening a position, verify it fits within total portfolio risk.",
                "These controls monitor total risk, open trades, concentration, and diversification.",
            ]
        )
        r1, r2 = st.columns(2)
        with r1:
            st.metric("Maximum Portfolio Risk %", f"{max_portfolio_risk_pct:.2f}%")
            st.caption("Loaded from Trading Preferences")
            st.caption(
                f"Current Portfolio Risk: {context['current_portfolio_risk_pct']:.2f}% | "
                f"New Trade: {context['trade_risk_pct']:.2f}% | "
                f"Total: {context['total_portfolio_risk_after']:.2f}%"
            )
        with r2:
            st.metric("Maximum Open Trades", f"{max_open_trades}")
            st.caption("Loaded from Trading Preferences")
            st.caption(
                f"Current Open Trades: {context['current_open_trades']} | "
                f"After Trade: {context['open_trades_after']}"
            )

        portfolio_risk_exceeded = context["total_portfolio_risk_after"] > max_portfolio_risk_pct
        max_open_trades_exceeded = context["open_trades_after"] > max_open_trades

        if portfolio_risk_exceeded:
            st.warning("⚠ Portfolio Risk Exceeded")
            st.markdown(
                "- Current Portfolio Risk: "
                f"**{context['current_portfolio_risk_pct']:.2f}%**  \n"
                "- New Trade: "
                f"**{context['trade_risk_pct']:.2f}%**  \n"
                "- Total: "
                f"**{context['total_portfolio_risk_after']:.2f}%**  \n"
                "- Maximum Allowed: "
                f"**{max_portfolio_risk_pct:.2f}%**"
            )
            st.caption("Recommended Actions: Reduce Risk %, close another trade, or increase portfolio limit if consistent with your plan.")
        else:
            st.success("✓ Within Limit")

        if max_open_trades_exceeded:
            st.warning("⚠ Maximum Position Count Reached")
            st.markdown(
                "- Current Open Trades: "
                f"**{context['current_open_trades']}**  \n"
                "- After This Trade: "
                f"**{context['open_trades_after']}**  \n"
                "- Maximum Allowed: "
                f"**{max_open_trades}**"
            )
            st.caption("Recommended Actions: Close an existing trade or increase Maximum Open Trades.")

        st.caption("⚙ Change Trading Preferences")

    return {
        "max_portfolio_risk_pct": max_portfolio_risk_pct,
        "max_open_trades": max_open_trades,
        "portfolio_risk_exceeded": portfolio_risk_exceeded,
        "max_open_trades_exceeded": max_open_trades_exceeded,
    }


def render_sector_exposure_card(context: Dict[str, Any]) -> Dict[str, Any]:
    with st.container(border=True):
        st.markdown("#### Sector Exposure")
        _ensure_widget_default(
            "tcc_max_sector_exposure_pct",
            safe_float(st.session_state.get("tcc_max_sector_exposure_pct_default"), PORTFOLIO_LIMIT_DEFAULTS["max_sector_exposure_pct"]),
        )
        st.session_state["tcc_max_sector_exposure_pct"] = min(
            100.0,
            max(1.0, safe_float(st.session_state.get("tcc_max_sector_exposure_pct"), PORTFOLIO_LIMIT_DEFAULTS["max_sector_exposure_pct"])),
        )
        max_sector_exposure_pct = st.number_input(
            "Maximum Sector Exposure %",
            min_value=1.0,
            max_value=100.0,
            step=1.0,
            key="tcc_max_sector_exposure_pct",
        )

        sector_rows = sorted(
            context.get("sector_exposure_pct", {}).items(),
            key=lambda item: item[1],
            reverse=True,
        )
        if sector_rows:
            render_mini_grid([(sector, f"{pct:.1f}%") for sector, pct in sector_rows[:8]])
        else:
            st.caption("Sector exposure data is pending.")

        st.markdown(f"**{context.get('proposed_sector', 'Unknown')}**")
        st.caption(
            f"Current: {safe_float(context.get('proposed_sector_current_pct'), 0.0):.1f}% | "
            f"After Trade: {safe_float(context.get('proposed_sector_after_pct'), 0.0):.1f}%"
        )
        sector_warning = safe_float(context.get("proposed_sector_after_pct"), 0.0) > max_sector_exposure_pct
        if sector_warning:
            st.warning("⚠ Sector Concentration Warning")
            st.caption(
                f"{context.get('proposed_sector', 'Sector')} exposure would increase to "
                f"{safe_float(context.get('proposed_sector_after_pct'), 0.0):.1f}%. Consider improving diversification."
            )

    return {
        "max_sector_exposure_pct": max_sector_exposure_pct,
        "sector_warning": sector_warning,
        "proposed_sector": str(context.get("proposed_sector") or "Unknown"),
    }


def render_correlation_analysis_card(context: Dict[str, Any]) -> Dict[str, Any]:
    def overlap_status(score: float, high_threshold: float) -> Tuple[str, str, str, bool]:
        moderate_threshold = max(high_threshold - 0.20, 0.45)
        if score >= high_threshold:
            return "🔶 High Overlap", "warning", "high", True
        if score >= moderate_threshold:
            return "🟡 Moderate Overlap", "neutral", "moderate", True
        return "🟢 Low Overlap", "neutral", "low", False

    with st.container(border=True):
        st.markdown("#### Portfolio Overlap")
        st.caption("Checks whether this trade overlaps too much with positions you already own.")
        threshold = safe_float(
            st.session_state.get("tcc_correlation_warning_threshold"),
            PORTFOLIO_LIMIT_DEFAULTS["correlation_warning_threshold"],
        )
        correlations = context.get("correlations", []) or []
        if correlations:
            cards = []
            overlap_items = []
            for item in correlations[:8]:
                symbol = str(item.get("symbol", "")).upper().strip() or "OPEN POSITION"
                score = safe_float(item.get("score"), 0.0)
                status_label, tone, severity, meaningful = overlap_status(score, threshold)
                cards.append(
                    {
                        "title": symbol,
                        "value": f"{score:.2f}",
                        "detail": status_label,
                        "tone": tone,
                    }
                )
                overlap_items.append(
                    {
                        "symbol": symbol,
                        "score": score,
                        "status_label": status_label,
                        "severity": severity,
                        "meaningful": meaningful,
                    }
                )
            render_card_grid(cards)
        else:
            overlap_items = []
            st.caption("No open positions were found for correlation comparison.")

        high_overlap_positions = [item for item in overlap_items if item.get("severity") == "high"]
        top_overlap = high_overlap_positions[0] if high_overlap_positions else None
        if top_overlap:
            proposed_symbol = str(context.get("proposed_symbol") or "This trade").upper().strip() or "THIS TRADE"
            top_symbol = str(top_overlap.get("symbol") or "OPEN POSITION")
            st.warning("⚠ High Portfolio Overlap Detected")
            st.markdown("**What this means**")
            st.write(f"{proposed_symbol} and {top_symbol} tend to move similarly.")
            st.write("Owning both may increase your exposure to the same market movement.")
            st.markdown("**Recommended Actions**")
            st.markdown("- Proceed if the increased exposure is intentional.")
            st.markdown("- Reduce the position size.")
            st.markdown("- Replace an existing overlapping position.")
            st.markdown("- Ignore the warning if it aligns with your investment strategy.")
            st.caption("This is a warning for diversification review, not a trade blocker.")
        elif any(item.get("severity") == "moderate" for item in overlap_items):
            st.info("Some existing holdings move similarly to this trade. Review diversification, but no major overlap warning is active.")

        st.caption("This overlap review is designed to expand later into sector, industry, ETF, and geographic diversification guidance.")

    return {
        "correlation_warning_threshold": threshold,
        "correlated_positions": high_overlap_positions,
        "overlap_items": overlap_items,
        "overlap_warning": bool(top_overlap),
        "top_overlap_symbol": str((top_overlap or {}).get("symbol") or ""),
        "top_overlap_score": safe_float((top_overlap or {}).get("score"), 0.0),
    }


def render_institutional_review_panel(
    context: Dict[str, Any],
    sizing: Dict[str, Any],
    portfolio_controls: Dict[str, Any],
    sector_controls: Dict[str, Any],
    correlation_controls: Dict[str, Any],
) -> Dict[str, Any]:
    context = context if isinstance(context, dict) else {}
    correlated = correlation_controls.get("correlated_positions", []) or []
    overlap_warning = bool(correlation_controls.get("overlap_warning", False))
    top_overlap_symbol = str(correlation_controls.get("top_overlap_symbol") or "").upper().strip()
    proposed_symbol = str(context.get("proposed_symbol") or sizing.get("symbol") or "This trade").upper().strip() or "THIS TRADE"
    action_items = []
    see_sections = []

    if bool(portfolio_controls.get("portfolio_risk_exceeded", False)):
        action_items.append("Portfolio Risk")
        if "Portfolio Risk Controls" not in see_sections:
            see_sections.append("Portfolio Risk Controls")
    if bool(portfolio_controls.get("max_open_trades_exceeded", False)):
        action_items.append("Maximum Open Trades")
        if "Portfolio Risk Controls" not in see_sections:
            see_sections.append("Portfolio Risk Controls")
    if overlap_warning:
        action_items.append("Portfolio Overlap")
        if "Advanced Portfolio Controls" not in see_sections:
            see_sections.append("Advanced Portfolio Controls")
    if bool(sector_controls.get("sector_warning", False)):
        action_items.append("Sector Exposure")
        if "Advanced Portfolio Controls" not in see_sections:
            see_sections.append("Advanced Portfolio Controls")

    rr_pass = safe_float(sizing.get("rr_2"), 0.0) >= 2.0
    earnings_pass = bool(sizing.get("exit_before_earnings", True))
    time_stop_pass = bool(sizing.get("time_stop_enabled", False))
    sector_pass = not bool(sector_controls.get("sector_warning", False))

    if not rr_pass:
        action_items.append("Reward / Risk")
        if "Entry & Risk" not in see_sections:
            see_sections.append("Entry & Risk")
    if not earnings_pass:
        action_items.append("Earnings Protection")
        if "Earnings & Weekend Protection" not in see_sections:
            see_sections.append("Earnings & Weekend Protection")
    if not time_stop_pass:
        action_items.append("Time Stop")
        if "Time Stop" not in see_sections:
            see_sections.append("Time Stop")

    critical_failures = int(bool(portfolio_controls.get("portfolio_risk_exceeded", False))) + int(bool(portfolio_controls.get("max_open_trades_exceeded", False)))
    warnings = max(len(action_items) - critical_failures, 0)

    if critical_failures > 0:
        status_text = "RED"
        status_color = "#b91c1c"
        status_bg = "#fef2f2"
        status_border = "#fecaca"
    elif len(action_items) > 0:
        status_text = "YELLOW"
        status_color = "#b45309"
        status_bg = "#fffbeb"
        status_border = "#fde68a"
    else:
        status_text = "GREEN"
        status_color = "#15803d"
        status_bg = "#f0fdf4"
        status_border = "#bbf7d0"

    st.markdown(
        "<div style='border:1px solid " + status_border + "; background:" + status_bg + "; border-radius:12px; padding:0.72rem 0.88rem; margin:0.35rem 0 0.5rem 0;'>"
        "<div style='font-size:0.78rem; font-weight:800; color:#475569; letter-spacing:0.04em; text-transform:uppercase;'>Institutional Review</div>"
        "<div style='font-size:1.3rem; font-weight:900; color:" + status_color + "; line-height:1.08; margin-top:0.2rem;'>" + status_text + "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    if action_items:
        st.warning(f"{len(action_items)} Action Items Remaining")
        if see_sections:
            st.markdown("See:")
            for section_name in see_sections:
                st.markdown(f"- {section_name}")
    else:
        st.success("All validation checks passed. Trade is ready for direct broker routing.")

    if overlap_warning and top_overlap_symbol:
        st.warning(
            f"🟡 Portfolio Overlap\n\n{proposed_symbol} overlaps significantly with your existing position in {top_overlap_symbol}.\n\nReview if this additional exposure is intentional."
        )

    st.markdown("Passed")
    if rr_pass:
        st.markdown("- ✓ Reward/Risk")
    if earnings_pass:
        st.markdown("- ✓ Earnings Protection")
    if time_stop_pass:
        st.markdown("- ✓ Time Stop")
    if sector_pass:
        st.markdown("- ✓ Sector Exposure")

    return {
        "status": status_text,
        "critical_failures": critical_failures,
        "warnings": warnings,
        "action_items": action_items,
        "see_sections": see_sections,
        "passed": {
            "reward_risk": rr_pass,
            "earnings_protection": earnings_pass,
            "time_stop": time_stop_pass,
            "sector_exposure": sector_pass,
        },
    }


def publish_portfolio_dashboard_snapshot(
    context: Dict[str, Any],
    portfolio_controls: Dict[str, Any],
    sector_controls: Dict[str, Any],
    correlation_controls: Dict[str, Any],
) -> Dict[str, Any]:
    top_correlation = safe_float((context.get("correlations", [{}])[0] or {}).get("score"), 0.0) if context.get("correlations") else 0.0
    snapshot = {
        "timestamp": now_iso(),
        "source": "Trade_Command_Center_v3_0",
        "current_portfolio_risk_pct": safe_float(context.get("current_portfolio_risk_pct"), 0.0),
        "sector_exposure": context.get("sector_exposure_pct", {}),
        "correlation_score": top_correlation,
        "open_trades": safe_int(context.get("current_open_trades"), 0),
        "capital_allocated": safe_float(context.get("total_capital_allocated"), 0.0),
        "cash_remaining": safe_float(context.get("cash_remaining"), 0.0),
        "largest_position": {
            "symbol": context.get("largest_position_symbol", "Pending"),
            "value": safe_float(context.get("largest_position_value"), 0.0),
        },
        "largest_sector": {
            "name": context.get("largest_sector", "Pending"),
            "pct": safe_float(context.get("largest_sector_pct"), 0.0),
        },
        "risk_remaining": max(
            safe_float(portfolio_controls.get("max_portfolio_risk_pct"), PORTFOLIO_LIMIT_DEFAULTS["max_portfolio_risk_pct"]) - safe_float(context.get("total_portfolio_risk_after"), 0.0),
            0.0,
        ),
        "limits": {
            "max_portfolio_risk_pct": safe_float(portfolio_controls.get("max_portfolio_risk_pct"), PORTFOLIO_LIMIT_DEFAULTS["max_portfolio_risk_pct"]),
            "max_open_trades": safe_int(portfolio_controls.get("max_open_trades"), PORTFOLIO_LIMIT_DEFAULTS["max_open_trades"]),
            "max_sector_exposure_pct": safe_float(sector_controls.get("max_sector_exposure_pct"), PORTFOLIO_LIMIT_DEFAULTS["max_sector_exposure_pct"]),
            "correlation_warning_threshold": safe_float(correlation_controls.get("correlation_warning_threshold"), PORTFOLIO_LIMIT_DEFAULTS["correlation_warning_threshold"]),
        },
    }
    st.session_state["tcc_portfolio_dashboard_snapshot"] = snapshot
    return snapshot


def build_checklist(decision: Dict[str, Any], plan: Dict[str, Any], sizing: Dict[str, Any], execution: Dict[str, Any], market: Dict[str, Any]) -> List[Tuple[str, bool]]:
    executable = bool(plan.get("executable")) or str(plan.get("position_action") or "").upper().startswith("OPEN")
    return [
        ("Market Pulse checked", str(market.get("regime", "UNKNOWN")).upper() != "UNKNOWN"),
        ("Scanner candidate selected", bool(sizing.get("symbol"))),
        ("Research reviewed", bool(st.session_state.get("research_last_analyze") or st.session_state.get("research_ticker"))),
        ("Stop defined", safe_float(sizing.get("stop"), 0.0) > 0),
        ("Position size verified", safe_int(sizing.get("qty"), 0) > 0),
        ("Risk-aware plan approved", executable),
        ("Kill switch OFF", not bool(execution.get("kill_switch"))),
        ("Decision not blocked", "BLOCKED" not in str(decision.get("label", ""))),
    ]


def render_checklist(items: List[Tuple[str, bool]]) -> None:
    pieces = ['<div class="tcc-checklist">']
    for label, ok in items:
        pieces.append(f'<div class="tcc-check">{"✅" if ok else "⬜"} {html.escape(label)}</div>')
    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def conviction_label(decision: Dict[str, Any], row: Dict[str, Any], market: Dict[str, Any], plan: Dict[str, Any]) -> Tuple[str, str]:
    score = safe_float(decision.get("score"), 0.0)
    scanner_score = safe_float(row.get("opportunity_score_pct") or row.get("model_score"), 0.0)
    rating = str(row.get("overall_rating") or "").upper().strip()
    regime = str(market.get("regime") or "UNKNOWN").upper().strip()
    executable = bool(plan.get("executable")) or str(plan.get("position_action") or "").upper().startswith("OPEN")

    bonus = 0
    if rating in {"A+", "A"}:
        bonus += 5
    if regime in {"RISK_ON", "RISK-ON"}:
        bonus += 5
    if executable:
        bonus += 5

    blended = min(100, max(0, (score * 0.65) + (scanner_score * 0.35) + bonus))
    if blended >= 88:
        return "EXCEPTIONAL", "good"
    if blended >= 76:
        return "HIGH", "good"
    if blended >= 58:
        return "MEDIUM", "warning"
    return "LOW", "risk" if blended < 40 else "warning"


def readiness_status(checklist: List[Tuple[str, bool]]) -> Dict[str, Any]:
    total = max(1, len(checklist))
    passed = sum(1 for _, ok in checklist if ok)
    pct = passed / total * 100.0
    if passed <= 3:
        label, tone, text = "🔴 NOT READY", "risk", "Do not send to OMS yet. Several required controls are missing."
    elif passed <= 6:
        label, tone, text = "🟡 REVIEW REQUIRED", "warning", "Checklist is close, but the trade still needs review before OMS."
    else:
        label, tone, text = "🟢 OMS READY", "good", "Checklist is complete enough for advisory OMS handoff."
    return {"passed": passed, "total": total, "pct": pct, "label": label, "tone": tone, "text": text}


def final_recommendation(decision: Dict[str, Any], checklist: List[Tuple[str, bool]], risk_factors: List[str]) -> Dict[str, str]:
    ready = readiness_status(checklist)
    label_text = str(decision.get("label", ""))
    if "BLOCKED" in label_text:
        return {"label": "FINAL RECOMMENDATION", "value": "DO NOT TRADE", "detail": "Decision is blocked by risk controls. Resolve the block before any OMS handoff.", "tone": "risk"}
    if ready["passed"] >= 7 and "TRADE READY" in label_text:
        return {"label": "FINAL RECOMMENDATION", "value": "PROCEED TO OMS EXECUTION", "detail": "Checklist is strong, risk plan is approved, and the trade is ready for final OMS confirmation.", "tone": "good"}
    if ready["passed"] >= 7 and "REVIEW" in label_text:
        return {"label": "FINAL RECOMMENDATION", "value": "REVIEW, THEN OMS", "detail": "Most controls pass, but the decision label still calls for review. Confirm Research and risk-aware plan before routing.", "tone": "warning"}
    if ready["passed"] >= 4:
        return {"label": "FINAL RECOMMENDATION", "value": "WAIT FOR CONFIRMATION", "detail": "Trade is not blocked, but required confirmations remain open. Review the risk factors before OMS.", "tone": "warning"}
    return {"label": "FINAL RECOMMENDATION", "value": "STAND DOWN", "detail": "The setup is not ready. Complete the checklist and reduce unresolved risk factors first.", "tone": "risk" if risk_factors else "neutral"}


def build_risk_factors(row: Dict[str, Any], market: Dict[str, Any], plan: Dict[str, Any], sizing: Dict[str, Any], execution: Dict[str, Any], checklist: List[Tuple[str, bool]]) -> List[str]:
    factors: List[str] = []
    regime = str(market.get("regime") or "UNKNOWN").upper().strip()
    stress = safe_float(market.get("stress_score"), 0.0)
    breadth = safe_float(market.get("breadth_score"), 0.0)
    signal = normalize_signal(row.get("trade_recommendation") or row.get("scanner_action") or row.get("signal"))
    scanner_score = safe_float(row.get("opportunity_score_pct") or row.get("model_score"), 0.0)
    executable = bool(plan.get("executable")) or str(plan.get("position_action") or "").upper().startswith("OPEN")

    if regime in {"SELECTIVE", "NEUTRAL", "UNKNOWN"}:
        factors.append(f"Market regime is {regime}; avoid oversized trades.")
    if regime in {"RISK_OFF", "RISK-OFF", "DEFENSIVE"}:
        factors.append("Market regime is defensive/risk-off.")
    if stress >= 50:
        factors.append(f"Market stress is elevated at {stress:.0f}/100.")
    if 0 < breadth < 50:
        factors.append(f"Breadth is below 50 at {breadth:.1f}/100.")
    if signal == "WATCH":
        factors.append("Scanner signal is WATCH, not a clean BUY/SELL.")
    if scanner_score < 75:
        factors.append(f"Scanner score is below high-conviction range: {scanner_score:.1f}.")
    if not executable:
        factors.append("Risk-aware plan is not executable yet.")
    if bool(execution.get("kill_switch")):
        factors.append("OMS kill switch is ON.")
    if safe_float(sizing.get("rr_2"), 0.0) < 2.0:
        factors.append("Risk/reward to Target 2 is below 2R.")
    if safe_float(sizing.get("risk_pct"), 0.0) > 1.5:
        factors.append("Actual account risk is above 1.5%.")
    for label, ok in checklist:
        if not ok and label in {"Research reviewed", "Position size verified", "Risk-aware plan approved"}:
            factors.append(f"Checklist missing: {label}.")
    return factors[:8]


def render_recommendation_banner(rec: Dict[str, str]) -> None:
    bg, border, color = tone_palette(rec.get("tone", "neutral"))
    st.markdown(
        f'<div class="tcc-banner" style="background:{bg};border-color:{border};">'
        f'<div class="tcc-banner-label">{html.escape(rec.get("label", "FINAL RECOMMENDATION"))}</div>'
        f'<div class="tcc-banner-value" style="color:{color};">{html.escape(rec.get("value", ""))}</div>'
        f'<div class="tcc-banner-detail">{html.escape(rec.get("detail", ""))}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_readiness_gauge(status: Dict[str, Any]) -> None:
    bg, border, color = tone_palette(status.get("tone", "neutral"))
    pct = max(0, min(100, safe_float(status.get("pct"), 0.0)))
    st.markdown(
        f'<div class="tcc-banner" style="background:{bg};border-color:{border};">'
        f'<div class="tcc-banner-label">Readiness Gauge</div>'
        f'<div class="tcc-banner-value" style="color:{color};">{html.escape(str(status.get("label", "")))}</div>'
        f'<div class="tcc-gauge-wrap"><div class="tcc-gauge-fill" style="width:{pct:.1f}%;background:{color};"></div></div>'
        f'<div class="tcc-banner-detail">{status.get("passed", 0)}/{status.get("total", 0)} checklist items complete. {html.escape(str(status.get("text", "")))}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_risk_factors(factors: List[str]) -> None:
    if not factors:
        st.success("No major risk factors detected from the current command inputs.")
        return
    pieces = ['<ul class="tcc-risk-list">']
    for item in factors:
        pieces.append(f'<li>{html.escape(str(item))}</li>')
    pieces.append('</ul>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_trade_management_guidance() -> None:
    with st.expander("▶ How to Use Trade Management Plan", expanded=False):
        st.markdown("**Welcome!**")
        st.markdown("This page helps you convert a validated trading idea into a complete Trade Management Plan.")
        st.markdown("Work through each section from top to bottom:")
        st.markdown("1. Entry & Risk")
        st.markdown("2. Profit Targets")
        st.markdown("3. Stop Management")
        st.markdown("4. Time Stop")
        st.markdown("5. Earnings & Weekend Protection")
        st.markdown("6. Progress Requirement")
        st.markdown("7. Portfolio Risk Controls")
        st.markdown("8. Institutional Review")
        st.caption(
            "Each section includes its own explanation directly below the heading, "
            "so you can learn while building your trade plan."
        )


def render_ticket_preview(ticket: Dict[str, Any]) -> None:
    rows = [
        ("Symbol", ticket.get("symbol", "")),
        ("Action", ticket.get("action", "")),
        ("Qty", ticket.get("qty", 0)),
        ("Entry", fmt_money(ticket.get("entry", 0))),
        ("Stop", fmt_money(ticket.get("stop", 0))),
        ("Target 1", fmt_money(ticket.get("target_1", 0))),
        ("Target 2", fmt_money(ticket.get("target_2", 0))),
        ("Risk", fmt_money(ticket.get("dollar_risk", 0))),
        ("R/R 2", f"{safe_float(ticket.get('risk_reward_2'), 0):.2f}R"),
    ]
    pieces = ['<table class="tcc-ticket-table">']
    for label, value in rows:
        pieces.append(f'<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>')
    pieces.append('</table>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def prepare_oms_ticket(symbol: str, sizing: Dict[str, Any], decision: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    management = _resolve_trade_management_fields(sizing)
    account_context = resolve_account_context()
    ticket = {
        "timestamp": now_iso(),
        "source": "Trade_Command_Center_v3_0",
        "status": "PREPARED_NOT_ROUTED",
        "symbol": symbol,
        "action": sizing.get("action", "BUY"),
        "qty": safe_int(sizing.get("qty"), 0),
        "position_size_source": str(sizing.get("position_size_source") or management.get("position_size_source") or "Recalculated from Trade Management Plan"),
        "scanner_qty": safe_int(sizing.get("scanner_qty"), 0),
        "calculated_qty": safe_int(sizing.get("calculated_qty"), 0),
        "final_qty": safe_int(sizing.get("final_qty", sizing.get("qty")), 0),
        "entry": safe_float(sizing.get("entry"), 0.0),
        "stop": safe_float(sizing.get("stop"), 0.0),
        "target_1": safe_float(sizing.get("target_1"), 0.0),
        "target_2": safe_float(sizing.get("target_2"), 0.0),
        "target_3": safe_float(sizing.get("target_3"), 0.0),
        "position_value": safe_float(sizing.get("position_value"), 0.0),
        "dollar_risk": safe_float(sizing.get("dollar_risk"), 0.0),
        "risk_reward_1": safe_float(sizing.get("rr_1"), 0.0),
        "risk_reward_2": safe_float(sizing.get("rr_2"), 0.0),
        "risk_reward_3": safe_float(sizing.get("rr_3"), 0.0),
        "management": management,
        "decision_label": decision.get("label", ""),
        "decision_score": decision.get("score", 0),
        "scanner_score": safe_float(row.get("opportunity_score_pct"), 0.0),
        "account_source": account_context.get("account_source", "⚪ Manual Mode"),
        "account_size": safe_float(account_context.get("account_size"), 0.0),
        "net_liquidation": safe_float(account_context.get("net_liquidation"), 0.0),
        "buying_power": safe_float(account_context.get("buying_power"), 0.0),
        "cash_balance": safe_float(account_context.get("cash_balance"), 0.0),
        "risk_pct_source": _current_trade_risk_pct_source_label(),
        "portfolio_data_source": account_context.get("portfolio_data_source", "Manual/Demo"),
        "ibkr_connected": bool(account_context.get("ibkr_connected", False)),
        "note": "Advisory ticket prepared by Trade Command Center. Confirm in OMS before execution.",
    }
    st.session_state["tcc_prepared_oms_ticket"] = ticket
    st.session_state["oms_prepared_ticket"] = ticket
    st.session_state["oms_order_symbol"] = symbol
    st.session_state["trade_command_symbol"] = symbol
    return ticket


def _resolve_trade_management_fields(sizing: Dict[str, Any]) -> Dict[str, Any]:
    sizing = sizing if isinstance(sizing, dict) else {}
    tp1 = safe_float(sizing.get("tp1_allocation"), 50.0)
    tp2 = safe_float(sizing.get("tp2_allocation"), 50.0)
    tp3 = safe_float(sizing.get("tp3_allocation"), 0.0)
    total = tp1 + tp2 + tp3
    trailing_method_raw = str(sizing.get("trailing_method") or "ATR")
    stop_adjustment_method_map = {
        "ATR": "ATR",
        "Percentage": "Percentage",
        "Swing Low": "Swing Low",
        "EMA 21": "EMA21",
        "EMA 50": "EMA50",
    }
    trailing_method = trailing_method_raw if trailing_method_raw in set(stop_adjustment_method_map.keys()) else "ATR"
    position_size_source = str(sizing.get("position_size_source") or "Recalculated from Trade Management Plan")
    if position_size_source not in {"Using Scanner Recommendation", "Recalculated from Trade Management Plan"}:
        position_size_source = "Recalculated from Trade Management Plan"
    return {
        "move_to_break_even": bool(sizing.get("move_to_break_even", True)),
        "trailing_enabled": bool(sizing.get("trailing_enabled", False)),
        "trailing_method": trailing_method,
        "trailing_percent": safe_float(sizing.get("trailing_percent"), 5.0),
        "atr_multiple": safe_float(sizing.get("atr_multiple"), 2.0),
        "stop_adjustment_method": stop_adjustment_method_map.get(trailing_method, "ATR"),
        "time_stop_enabled": bool(sizing.get("time_stop_enabled", False)),
        "time_stop_days": safe_int(sizing.get("time_stop_days"), 10),
        "exit_before_earnings": bool(sizing.get("exit_before_earnings", True)),
        "next_earnings": str(sizing.get("next_earnings") or "Pending"),
        "next_earnings_date": str(sizing.get("next_earnings_date") or ""),
        "avoid_weekend_hold": bool(sizing.get("avoid_weekend_hold", False)),
        "progress_requirement_pct": safe_float(sizing.get("progress_requirement_pct"), PORTFOLIO_LIMIT_DEFAULTS["progress_target_pct_of_tp1"]),
        "progress_requirement_days": safe_int(sizing.get("progress_requirement_days"), PORTFOLIO_LIMIT_DEFAULTS["progress_within_days"]),
        "tp1_allocation": tp1,
        "tp2_allocation": tp2,
        "tp3_allocation": tp3,
        "tp_allocations_valid": abs(total - 100.0) < 0.0001,
        "position_size_source": position_size_source,
        "scanner_qty": safe_int(sizing.get("scanner_qty"), 0),
        "calculated_qty": safe_int(sizing.get("calculated_qty"), 0),
        "final_qty": safe_int(sizing.get("final_qty", sizing.get("qty")), 0),
    }


def build_monitoring_payload(symbol: str, sizing: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    management = _resolve_trade_management_fields(sizing)
    account_context = resolve_account_context()
    portfolio_snapshot = st.session_state.get("tcc_portfolio_dashboard_snapshot", {})
    if not isinstance(portfolio_snapshot, dict):
        portfolio_snapshot = {}
    payload = {
        "timestamp": now_iso(),
        "source": "Trade_Command_Center_v3_0",
        "symbol": str(symbol or "").upper().strip(),
        "status": "MONITORING",
        "decision_label": decision.get("label", ""),
        "entry": safe_float(sizing.get("entry"), 0.0),
        "stop": safe_float(sizing.get("stop"), 0.0),
        "tp1": safe_float(sizing.get("target_1"), 0.0),
        "tp2": safe_float(sizing.get("target_2"), 0.0),
        "tp3": safe_float(sizing.get("target_3"), 0.0),
        "tp1_allocation": management["tp1_allocation"],
        "tp2_allocation": management["tp2_allocation"],
        "tp3_allocation": management["tp3_allocation"],
        "tp_allocations": {
            "tp1_allocation": management["tp1_allocation"],
            "tp2_allocation": management["tp2_allocation"],
            "tp3_allocation": management["tp3_allocation"],
        },
        "move_to_be": management["move_to_break_even"],
        "move_to_break_even": management["move_to_break_even"],
        "trailing_enabled": management["trailing_enabled"],
        "trailing_method": management["trailing_method"],
        "trailing_percent": management["trailing_percent"],
        "atr_multiple": management["atr_multiple"],
        "stop_adjustment_method": management["stop_adjustment_method"],
        "time_stop_enabled": management["time_stop_enabled"],
        "time_stop_days": management["time_stop_days"],
        "exit_before_earnings": management["exit_before_earnings"],
        "next_earnings": management["next_earnings"],
        "next_earnings_date": management["next_earnings_date"],
        "avoid_weekend_hold": management["avoid_weekend_hold"],
        "progress_requirement_pct": management["progress_requirement_pct"],
        "progress_requirement_days": management["progress_requirement_days"],
        "risk_pct": safe_float(sizing.get("risk_pct"), 0.0),
        "position_size": safe_int(sizing.get("qty"), 0),
        "position_size_source": management["position_size_source"],
        "scanner_qty": management["scanner_qty"],
        "calculated_qty": management["calculated_qty"],
        "final_qty": management["final_qty"],
        "account_source": account_context.get("account_source", "⚪ Manual Mode"),
        "account_size": safe_float(account_context.get("account_size"), 0.0),
        "net_liquidation": safe_float(account_context.get("net_liquidation"), 0.0),
        "buying_power": safe_float(account_context.get("buying_power"), 0.0),
        "cash_balance": safe_float(account_context.get("cash_balance"), 0.0),
        "risk_pct_source": _current_trade_risk_pct_source_label(),
        "portfolio_data_source": account_context.get("portfolio_data_source", "Manual/Demo"),
        "ibkr_connected": bool(account_context.get("ibkr_connected", False)),
        "portfolio_snapshot": portfolio_snapshot,
        "trade_plan": {
            **(sizing if isinstance(sizing, dict) else {}),
            **management,
        },
    }
    return payload


def send_trade_plan_to_journal(
    symbol: str,
    sizing: Dict[str, Any],
    decision: Dict[str, Any],
    reasons: List[str],
    trade_status: str = "PLANNED",
    workflow_decision: str = "TRADE_PLAN",
    pass_reason: str = "",
    pass_notes: str = "",
) -> Dict[str, Any]:
    management = _resolve_trade_management_fields(sizing)
    account_context = resolve_account_context()
    normalized_status = str(trade_status or "PLANNED").upper().strip()
    normalized_decision = str(workflow_decision or "TRADE_PLAN").upper().strip()
    note = {
        "timestamp": now_iso(),
        "source": "Trade_Command_Center_v3_0",
        "symbol": symbol,
        "tag": "TRADE_PASS" if normalized_status == "PASSED" else "TRADE_PLAN",
        "status": normalized_status,
        "workflow_decision": normalized_decision,
        "setup_grade": "A" if safe_float(decision.get("score"), 0) >= 80 else "B" if safe_float(decision.get("score"), 0) >= 65 else "C",
        "execution_grade": "Executed" if normalized_status == "EXECUTED" else "Passed" if normalized_status == "PASSED" else "Planned",
        "notes": " | ".join(reasons),
        "pass_reason": str(pass_reason or "").strip(),
        "pass_notes": str(pass_notes or "").strip(),
        "trade_plan": {
            **(sizing if isinstance(sizing, dict) else {}),
            **management,
        },
        "decision": decision,
        "move_to_break_even": management["move_to_break_even"],
        "trailing_enabled": management["trailing_enabled"],
        "trailing_method": management["trailing_method"],
        "trailing_percent": management["trailing_percent"],
        "atr_multiple": management["atr_multiple"],
        "time_stop_enabled": management["time_stop_enabled"],
        "time_stop_days": management["time_stop_days"],
        "stop_adjustment_method": management["stop_adjustment_method"],
        "exit_before_earnings": management["exit_before_earnings"],
        "next_earnings": management["next_earnings"],
        "next_earnings_date": management["next_earnings_date"],
        "avoid_weekend_hold": management["avoid_weekend_hold"],
        "progress_requirement_pct": management["progress_requirement_pct"],
        "progress_requirement_days": management["progress_requirement_days"],
        "tp1_allocation": management["tp1_allocation"],
        "tp2_allocation": management["tp2_allocation"],
        "tp3_allocation": management["tp3_allocation"],
        "position_size_source": management["position_size_source"],
        "scanner_qty": management["scanner_qty"],
        "calculated_qty": management["calculated_qty"],
        "final_qty": management["final_qty"],
        "account_source": account_context.get("account_source", "⚪ Manual Mode"),
        "account_size": safe_float(account_context.get("account_size"), 0.0),
        "net_liquidation": safe_float(account_context.get("net_liquidation"), 0.0),
        "buying_power": safe_float(account_context.get("buying_power"), 0.0),
        "cash_balance": safe_float(account_context.get("cash_balance"), 0.0),
        "risk_pct_source": _current_trade_risk_pct_source_label(),
        "portfolio_data_source": account_context.get("portfolio_data_source", "Manual/Demo"),
        "ibkr_connected": bool(account_context.get("ibkr_connected", False)),
    }
    existing = st.session_state.get("tcc_journal_notes", [])
    if not isinstance(existing, list):
        existing = []
    st.session_state["tcc_journal_notes"] = [note] + existing[:49]
    st.session_state["journal_prefill_note"] = note
    return note


def _resolve_execution_subscription_tier() -> str:
    tier_candidates: List[str] = []

    for key in ["saas_plan", "subscription_plan", "plan", "account_plan", "workspace_plan"]:
        value = st.session_state.get(key)
        if value is not None:
            tier_candidates.append(str(value))

    for key in ["saas_user", "current_user", "user"]:
        obj = st.session_state.get(key)
        if isinstance(obj, dict):
            tier_candidates.extend([str(obj.get("plan") or ""), str(obj.get("subscription_plan") or "")])
        elif obj is not None:
            tier_candidates.extend([str(getattr(obj, "plan", "") or ""), str(getattr(obj, "subscription_plan", "") or "")])

    for raw in tier_candidates:
        normalized = str(raw or "").strip().upper()
        if normalized in {"ELITE", "PRO", "STARTER"}:
            return normalized

    return "STARTER"


def _execution_route_label_for_tier(tier: str) -> str:
    normalized = str(tier or "STARTER").strip().upper()
    if normalized == "ELITE":
        return "Send to Live IBKR"
    if normalized == "PRO":
        return "Send to Paper Account"
    return "Export Trade Plan"


def _build_execution_validation_checks(
    account_context: Dict[str, Any],
    sizing: Dict[str, Any],
    management: Dict[str, Any],
    portfolio_controls: Dict[str, Any],
    sector_controls: Dict[str, Any],
    institutional_review: Dict[str, Any],
    tp_allocation_ok: bool,
) -> Dict[str, bool]:
    buying_power = safe_float(account_context.get("buying_power"), 0.0)
    position_value = safe_float(sizing.get("position_value"), 0.0)
    qty = safe_int(sizing.get("qty"), 0)

    buying_power_ok = buying_power <= 0 or position_value <= buying_power
    position_size_ok = qty > 0
    risk_limits_ok = not bool(portfolio_controls.get("portfolio_risk_exceeded", False))
    portfolio_limits_ok = (
        not bool(portfolio_controls.get("portfolio_risk_exceeded", False))
        and not bool(portfolio_controls.get("max_open_trades_exceeded", False))
        and not bool(sector_controls.get("sector_warning", False))
    )
    earnings_rules_ok = bool(management.get("exit_before_earnings", True))
    time_stop_ok = bool(management.get("time_stop_enabled", False)) and safe_int(management.get("time_stop_days"), 0) > 0
    trade_management_plan_ok = bool(
        tp_allocation_ok
        and safe_float(sizing.get("entry"), 0.0) > 0
        and safe_float(sizing.get("stop"), 0.0) > 0
        and safe_float(sizing.get("target_1"), 0.0) > 0
        and qty > 0
    )

    review_status = str(institutional_review.get("status") or "").upper().strip()
    institutional_review_ok = review_status in {"GREEN", "YELLOW"}

    return {
        "institutional_review": institutional_review_ok,
        "buying_power": buying_power_ok,
        "position_size": position_size_ok,
        "risk_limits": risk_limits_ok,
        "portfolio_limits": portfolio_limits_ok,
        "earnings_rules": earnings_rules_ok,
        "time_stop": time_stop_ok,
        "trade_management_plan": trade_management_plan_ok,
    }


def _build_execution_gateway_packet(
    symbol: str,
    sizing: Dict[str, Any],
    decision: Dict[str, Any],
    row: Dict[str, Any],
    management: Dict[str, Any],
    institutional_review: Dict[str, Any],
    validation_checks: Dict[str, bool],
    tier: str,
    route_label: str,
    monitoring_payload: Dict[str, Any] | None,
    journal_note: Dict[str, Any] | None,
    oms_ticket: Dict[str, Any] | None,
    portfolio_update: Dict[str, Any] | None,
    status: str,
) -> Dict[str, Any]:
    packet = {
        "timestamp": now_iso(),
        "source": "Trade_Command_Center_v3_0",
        "packet_type": "EXECUTION_PACKET",
        "status": str(status or "PENDING").upper().strip(),
        "symbol": str(symbol or "").upper().strip(),
        "tier": str(tier or "STARTER").upper().strip(),
        "route": route_label,
        "decision_label": str(decision.get("label") or ""),
        "decision_score": safe_float(decision.get("score"), 0.0),
        "scanner_score": safe_float(row.get("opportunity_score_pct"), 0.0),
        "institutional_review": institutional_review,
        "validation_checks": validation_checks,
        "trade_plan": {
            **(sizing if isinstance(sizing, dict) else {}),
            **(management if isinstance(management, dict) else {}),
        },
        "monitoring_plan": monitoring_payload,
        "journal_entry": journal_note,
        "oms_order": oms_ticket,
        "portfolio_update": portfolio_update,
    }
    st.session_state["tcc_execution_packet"] = packet
    st.session_state["tcc_last_execution_packet"] = packet
    return packet


def _execution_issue_text(issue: str) -> str:
    mapping = {
        "Portfolio Risk": "Maximum portfolio risk exceeded.",
        "Maximum Open Trades": "Maximum portfolio position count exceeded.",
        "Portfolio Overlap": "Portfolio overlap exceeds threshold.",
        "Sector Exposure": "Sector exposure exceeds preferred limit.",
        "Reward / Risk": "Reward / Risk is below the institutional minimum.",
        "Earnings Protection": "Earnings protection requirement is not satisfied.",
        "Time Stop": "Time stop requirement is not satisfied.",
        "Buying Power": "Buying power validation failed.",
        "Position Size": "Position size validation failed.",
        "Risk Limits": "Risk limit validation failed.",
        "Portfolio Limits": "Portfolio limit validation failed.",
        "Earnings Rules": "Earnings rules validation failed.",
        "Trade Management Plan": "Trade Management Plan validation failed.",
    }
    text = str(issue or "").strip()
    return mapping.get(text, text if text.endswith(".") else f"{text}.") if text else ""


def _build_final_execution_recommendation(
    institutional_review: Dict[str, Any],
    risk_factors: List[str],
    failed_execution_checks: List[str],
) -> Dict[str, Any]:
    review_status = str(institutional_review.get("status") or "").upper().strip()
    action_items = institutional_review.get("action_items", []) if isinstance(institutional_review, dict) else []
    normalized_action_items = [str(item).strip() for item in action_items if str(item).strip()]

    primary_issues: List[str] = []
    for item in normalized_action_items:
        issue_text = _execution_issue_text(item)
        if issue_text and issue_text not in primary_issues:
            primary_issues.append(issue_text)

    for item in failed_execution_checks:
        issue_text = _execution_issue_text(item)
        if issue_text and issue_text not in primary_issues:
            primary_issues.append(issue_text)

    for item in risk_factors:
        text = str(item or "").strip()
        if text and text not in primary_issues:
            primary_issues.append(text if text.endswith(".") else f"{text}.")

    primary_issues = primary_issues[:3]

    if review_status == "GREEN":
        return {
            "tone": "good",
            "headline": "🟢 EXECUTE TRADE",
            "detail": "All institutional checks passed.",
            "primary_issues": primary_issues,
            "can_send": not bool(failed_execution_checks),
        }
    if review_status == "YELLOW":
        return {
            "tone": "warning",
            "headline": "🟡 EXECUTE WITH CAUTION",
            "detail": "One or more warnings remain. Review the items below before sending.",
            "primary_issues": primary_issues,
            "can_send": not bool(failed_execution_checks),
        }
    return {
        "tone": "risk",
        "headline": "🔴 DO NOT EXECUTE",
        "detail": "One or more critical institutional checks failed.",
        "primary_issues": primary_issues,
        "can_send": False,
    }


def _resolve_gateway() -> Any:
    return st.session_state.get("gateway")


def _resolve_oms() -> Any:
    return st.session_state.get("oms")


def _is_gateway_connected(gateway: Any) -> bool:
    return _live_ibkr_connection_active(gateway)


def _market_is_open_note() -> Tuple[bool, str]:
    now_utc = datetime.now(timezone.utc)
    try:
        now_et = now_utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        now_et = now_utc

    if now_et.weekday() >= 5:
        return False, "Market is closed (weekend)."

    minutes = now_et.hour * 60 + now_et.minute
    market_open = 9 * 60 + 30
    market_close = 16 * 60

    if market_open <= minutes <= market_close:
        return True, "Market is open."

    return False, "Market is outside regular trading hours (09:30-16:00 ET)."


def _validate_direct_ibkr_execution(
    account_context: Dict[str, Any],
    sizing: Dict[str, Any],
    symbol: str,
) -> List[str]:
    issues: List[str] = []
    gateway = _resolve_gateway()

    clean_symbol = str(symbol or "").upper().strip()
    if not clean_symbol:
        issues.append("Symbol is missing.")

    if not _is_gateway_connected(gateway):
        issues.append("Broker connection is not active.")

    mode = str(st.session_state.get("mode", "SIM") or "SIM").upper().strip()
    if mode != "LIVE":
        issues.append("Execution mode must be LIVE.")

    if not bool(st.session_state.get("live_trading_armed", False)):
        issues.append("LIVE trading is not armed.")

    if safe_float(account_context.get("net_liquidation"), 0.0) <= 0:
        issues.append("Account validation failed: Net Liquidation is unavailable.")

    position_value = safe_float(sizing.get("position_value"), 0.0)
    buying_power = safe_float(account_context.get("buying_power"), 0.0)
    if buying_power > 0 and position_value > buying_power:
        issues.append("Buying power validation failed for this position size.")

    is_open, market_note = _market_is_open_note()
    if not is_open:
        issues.append(f"Market status validation failed: {market_note}")

    if safe_int(sizing.get("qty"), 0) <= 0:
        issues.append("Position size validation failed: quantity must be greater than zero.")

    return issues


def _build_institutional_order(symbol: str, sizing: Dict[str, Any]) -> Dict[str, Any]:
    action = str(sizing.get("action") or "BUY").upper().strip()
    if action not in {"BUY", "SELL"}:
        action = "BUY"

    return {
        "symbol": str(symbol or "").upper().strip(),
        "action": action,
        "side": action,
        "qty": max(1, safe_int(sizing.get("qty"), 0)),
        "quantity": max(1, safe_int(sizing.get("qty"), 0)),
        "order_type": "MKT",
        "mode": "LIVE",
        "source": "trade_command_center_direct_send",
        "timestamp": now_iso(),
    }


def _submit_order_to_broker(order_payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
    oms = _resolve_oms()
    gateway = _resolve_gateway()

    if oms is not None and hasattr(oms, "set_mode"):
        try:
            oms.set_mode("LIVE")
        except Exception:
            pass

    if oms is not None and hasattr(oms, "execute_signal"):
        try:
            result = oms.execute_signal(order_payload)
            if isinstance(result, dict) and result:
                return True, result, ""
            rejection = getattr(oms, "last_rejection", None)
            rejection_reason = str((rejection or {}).get("reason") or getattr(oms, "last_error", "") or "OMS broker route failed.")
            return False, {}, rejection_reason
        except Exception as exc:
            return False, {}, str(exc)

    if gateway is not None and hasattr(gateway, "submit_order"):
        try:
            result = gateway.submit_order(
                symbol=order_payload.get("symbol"),
                qty=safe_int(order_payload.get("qty"), 0),
                side=order_payload.get("action"),
                order_type=order_payload.get("order_type", "MKT"),
            )
            if isinstance(result, dict) and result:
                return True, result, ""
            return False, {}, "Gateway returned an empty order response."
        except Exception as exc:
            return False, {}, str(exc)

    return False, {}, "No OMS or broker gateway is available for direct submission."


def _sync_live_execution_state(order_state: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(order_state, dict) or not order_state:
        return {}

    gateway = _resolve_gateway()
    if not _is_gateway_connected(gateway):
        return order_state

    state = dict(order_state)
    broker_order_id = str(state.get("broker_order_id") or "").strip()
    local_order_id = str(state.get("order_id") or "").strip()
    symbol = str(state.get("symbol") or "").upper().strip()

    open_orders: List[Dict[str, Any]] = []
    if gateway is not None and hasattr(gateway, "refresh_open_orders"):
        try:
            open_orders = _as_list(gateway.refresh_open_orders())
        except Exception:
            open_orders = _as_list(getattr(gateway, "open_orders_cache", []))

    matched_open: Dict[str, Any] = {}
    for row in open_orders:
        if not isinstance(row, dict):
            continue
        row_broker_id = str(row.get("broker_order_id") or row.get("broker_id") or row.get("order_id") or "").strip()
        row_symbol = str(row.get("symbol") or "").upper().strip()
        if broker_order_id and row_broker_id == broker_order_id:
            matched_open = row
            break
        if not broker_order_id and symbol and row_symbol == symbol:
            matched_open = row
            break

    if matched_open:
        state["status"] = str(matched_open.get("status") or state.get("status") or "SUBMITTED").upper().strip()
        state["filled_qty"] = safe_float(matched_open.get("filled_qty"), safe_float(state.get("filled_qty"), 0.0))
        state["remaining_qty"] = safe_float(matched_open.get("remaining_qty"), safe_float(state.get("remaining_qty"), 0.0))
        state["avg_fill_price"] = safe_float(matched_open.get("avg_fill_price"), safe_float(state.get("avg_fill_price"), 0.0))
        state["broker_order_id"] = str(matched_open.get("broker_order_id") or broker_order_id or "").strip()
    else:
        fills: List[Dict[str, Any]] = []
        if gateway is not None and hasattr(gateway, "get_execution_cache"):
            try:
                fills = _as_list(gateway.get_execution_cache())
            except Exception:
                fills = _as_list(getattr(gateway, "execution_detail_cache", []))

        total_filled = 0.0
        total_value = 0.0
        for fill in fills:
            if not isinstance(fill, dict):
                continue
            fill_symbol = str(fill.get("symbol") or "").upper().strip()
            fill_broker_id = str(fill.get("broker_order_id") or fill.get("order_id") or "").strip()
            if symbol and fill_symbol != symbol:
                continue
            if broker_order_id and fill_broker_id and fill_broker_id != broker_order_id:
                continue
            qty = safe_float(fill.get("filled_qty") or fill.get("execution_qty") or fill.get("qty"), 0.0)
            price = safe_float(fill.get("execution_price") or fill.get("fill_price") or fill.get("price"), 0.0)
            if qty <= 0:
                continue
            total_filled += qty
            total_value += qty * max(price, 0.0)

        target_qty = max(0.0, safe_float(state.get("qty"), 0.0))
        if total_filled > 0:
            avg_fill = (total_value / total_filled) if total_filled > 0 else 0.0
            remaining = max(0.0, target_qty - total_filled)
            state["filled_qty"] = total_filled
            state["remaining_qty"] = remaining
            state["avg_fill_price"] = avg_fill
            state["status"] = "FILLED" if remaining <= 0.0 else "PARTIALLY_FILLED"

    state["updated_at"] = now_iso()
    return state


def _start_direct_ibkr_execution(
    symbol: str,
    sizing: Dict[str, Any],
    decision: Dict[str, Any],
    row: Dict[str, Any],
    management: Dict[str, Any],
    institutional_review: Dict[str, Any],
    execution_checks: Dict[str, Any],
) -> Tuple[bool, str]:
    order_payload = _build_institutional_order(symbol, sizing)
    ok, broker_result, error_text = _submit_order_to_broker(order_payload)

    if not ok:
        return False, error_text

    monitoring_payload = build_monitoring_payload(symbol, sizing, decision)
    st.session_state["tcc_monitoring_payload"] = monitoring_payload
    st.session_state["pending_trade_review"] = [monitoring_payload]

    oms_ticket = prepare_oms_ticket(symbol, sizing, decision, row)
    oms_ticket["route"] = "Direct IBKR"
    oms_ticket["status"] = "SENT_TO_BROKER"
    if isinstance(broker_result, dict):
        oms_ticket["broker_result"] = broker_result

    broker_order_id = str(
        (broker_result or {}).get("broker_order_id")
        or (broker_result or {}).get("orderId")
        or (broker_result or {}).get("order_id")
        or ""
    ).strip()
    order_id = str((broker_result or {}).get("order_id") or broker_order_id or "").strip()

    live_state = {
        "symbol": str(symbol or "").upper().strip(),
        "action": str(order_payload.get("action") or "BUY").upper().strip(),
        "qty": safe_int(order_payload.get("qty"), 0),
        "status": str((broker_result or {}).get("status") or (broker_result or {}).get("order_status") or "TRANSMITTING_ORDER").upper().strip(),
        "order_id": order_id,
        "broker_order_id": broker_order_id,
        "filled_qty": safe_float((broker_result or {}).get("filled_qty"), 0.0),
        "remaining_qty": safe_float((broker_result or {}).get("remaining_qty"), safe_float(order_payload.get("qty"), 0.0)),
        "avg_fill_price": safe_float((broker_result or {}).get("avg_fill_price"), 0.0),
        "submitted_at": now_iso(),
        "updated_at": now_iso(),
    }
    st.session_state[f"tcc_live_execution_{symbol}"] = live_state

    journal_note = send_trade_plan_to_journal(
        symbol,
        sizing,
        decision,
        decision.get("reasons", []),
        trade_status="ORDER_SUBMITTED",
        workflow_decision="SEND_TO_IBKR",
    )

    _build_execution_gateway_packet(
        symbol=symbol,
        sizing=sizing,
        decision=decision,
        row=row,
        management=management,
        institutional_review=institutional_review,
        validation_checks=execution_checks,
        tier="ELITE",
        route_label="Direct IBKR",
        monitoring_payload=monitoring_payload,
        journal_note=journal_note,
        oms_ticket=oms_ticket,
        portfolio_update=None,
        status="ORDER_SUBMITTED",
    )

    st.session_state["tcc_trade_workflow_status"] = "ORDER_SUBMITTED"
    st.session_state["tcc_trade_workflow_closed"] = True
    return True, ""


# =========================================================
# PAGE
# =========================================================

def run_page() -> None:
    get_trading_preferences()
    inject_css()
    account_context = resolve_account_context()

    st.title("🎯 Trade Command Center")
    st.caption("Trade Command Center v7.0 — Institutional Trade Decision Framework. Validate setup quality, risk, readiness, and send directly to IBKR when execution checks pass.")
    render_account_source_banner(account_context)
    developer_mode = _developer_mode_enabled()

    st.markdown(
        """
        <div class="tcc-flow">
            <strong>Workflow:</strong><br>
            Market Pulse → Scanner → Research Stock → Trade Command Center → Send Order → Broker → Position Command Center → Journal
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("ℹ️ How to use Trade Command Center", expanded=False):
        st.markdown(
            """
            1. Start from **Market Pulse**, **Scanner**, and **Research Stock**.
            2. Review the selected symbol in **Opportunity Assessment**.
            3. Validate entry, stop, targets, position size, and risk/reward.
            4. Confirm the **Execution Readiness** checklist and readiness gauge.
            5. Review the final recommendation and risk factors before broker routing.
            6. Send order directly from this page when broker connectivity and execution checks pass.
            """
        )

    q1, q2, q3, q4, q5 = st.columns(5)
    with q1:
        if st.button("Market Pulse", width="stretch", key="tcc_nav_market_v21"):
            navigate_to("Market Pulse")
    with q2:
        if st.button("Scanner", width="stretch", key="tcc_nav_scanner_v21"):
            navigate_to("Scanner")
    with q3:
        if st.button("Research", width="stretch", key="tcc_nav_research_v21"):
            navigate_to("Research Stock")
    with q4:
        if st.button("Options", width="stretch", key="tcc_nav_options_v21"):
            navigate_to("Options Center")
    with q5:
        if st.button("OMS", width="stretch", key="tcc_nav_oms_v21"):
            navigate_to("OMS Execution")

    row = select_trade_symbol()
    symbol = row_symbol(row)
    market = market_snapshot()
    risk = risk_snapshot()
    plan = matching_plan_row(symbol)
    hold = matching_hold_row(symbol)
    execution = execution_snapshot()
    decision = decision_score(row, market, plan, risk)
    option_strategy, option_detail, option_tone = suggested_options_structure(row, market)

    signal = normalize_signal(row.get("trade_recommendation") or row.get("scanner_action") or row.get("signal"))
    scanner_score = safe_float(row.get("opportunity_score_pct"), 0.0)
    rating = row.get("overall_rating", "N/A")
    sector = row.get("sector", "N/A")
    leadership = row.get("leadership_tier", "N/A")
    price = row.get("price") or row.get("last_price") or row.get("close")
    levels = derive_trade_levels(row, plan, signal)
    conviction, conviction_tone = conviction_label(decision, row, market, plan)
    opp_grade, opp_tone, opp_detail = opportunity_grade(scanner_score, rating, signal)
    inst_grade, inst_tone, inst_detail = institutional_grade(decision, None, plan)

    def professional_text(value: Any, fallback: str = "Not Available") -> str:
        text = str(value or "").strip()
        if text.upper() in {"", "N/A", "NA", "NONE", "NULL", "UNKNOWN", "-", "—"}:
            return fallback
        return text

    def recommendation_style(decision_label: str, decision_score_value: float, signal_value: str) -> str:
        label = decision_label.upper()
        sig = signal_value.upper()
        if "BLOCKED" in label or sig == "SELL":
            return "reject"
        if "TRADE READY" in label and decision_score_value >= 80:
            return "execute"
        return "wait"

    mismatch_warning = scanner_plan_mismatch_warning(signal, plan)
    if mismatch_warning:
        st.warning(mismatch_warning)

    decision_style = recommendation_style(str(decision.get("label", "")), safe_float(decision.get("score"), 0.0), signal)
    direction_text = "Short" if signal == "SELL" else "Long"
    trade_status = "Approved" if decision_style == "execute" else "Waiting" if decision_style == "wait" else "Rejected"
    risk_classification = "Moderate" if decision_style == "execute" else "Elevated" if decision_style == "wait" else "High"

    if decision_style == "execute":
        action_text = "Proceed With Trade"
        action_color = "#166534"
        recommendation_text = "Send Order"
        recommendation_tone = "good"
    elif decision_style == "wait":
        action_text = "Wait For Better Entry"
        action_color = "#b45309"
        recommendation_text = "Wait For Better Entry"
        recommendation_tone = "warning"
    else:
        action_text = "Reject Trade"
        action_color = "#b91c1c"
        recommendation_text = "Reject Trade"
        recommendation_tone = "risk"

    preview_rr = abs(levels["target_2"] - levels["entry"]) / max(abs(levels["entry"] - levels["stop"]), 0.01)
    trend_text = professional_text(market.get("regime"), "Awaiting Confirmation")
    rs_text = professional_text(row.get("rs_score"), "Pending")

    section_open("1) Trade Brief", "Immediate institutional read before committing capital.")
    st.markdown(
        f"""
        <div class="tcc-banner" style="background:#f8fafc;border-color:#dbe3ef;">
            <div class="tcc-banner-label">Institutional Trade Brief</div>
            <div class="tcc-banner-value" style="color:#111827;">Trade: {html.escape(symbol or 'Not Available')}</div>
            <div class="tcc-hero-badges">
                <div class="tcc-pill tcc-pill-status"><span class="tcc-pill-label">Status</span><span class="tcc-pill-value">{html.escape(trade_status)}</span></div>
                <div class="tcc-pill tcc-pill-grade"><span class="tcc-pill-label">Grade</span><span class="tcc-pill-value">{html.escape(inst_grade)}</span></div>
                <div class="tcc-pill tcc-pill-direction"><span class="tcc-pill-label">Direction</span><span class="tcc-pill-value">{html.escape(direction_text)}</span></div>
                <div class="tcc-pill tcc-pill-risk"><span class="tcc-pill-label">Risk</span><span class="tcc-pill-value">{html.escape(risk_classification)}</span></div>
            </div>
            <div class="tcc-banner-detail" style="font-size:1rem; font-weight:900; color:{action_color};">Action: {html.escape(action_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    section_close()

    section_open("2) Trade Readiness", "Institutional decision cards replacing metric walls.")
    render_card_grid([
        {"title": "Market Alignment", "value": trend_text, "detail": f"Stress {safe_int(market.get('stress_score'), 0)}/100", "tone": "good" if decision_style == "execute" else "warning"},
        {"title": "Technical Alignment", "value": professional_text(signal, "Pending"), "detail": f"Rating {professional_text(rating, 'Pending')}", "tone": "good" if signal == "BUY" else "warning" if signal == "WATCH" else "risk"},
        {"title": "Institutional Confirmation", "value": inst_grade, "detail": inst_detail, "tone": inst_tone},
        {"title": "Relative Strength", "value": rs_text, "detail": f"Leadership {professional_text(leadership, 'Not Available')}", "tone": "info"},
        {"title": "Risk / Reward", "value": risk_reward_card_value(preview_rr), "detail": "Preview to Target 2", "tone": "good" if preview_rr >= 2 else "warning"},
        {"title": "Entry Quality", "value": opp_grade, "detail": opp_detail, "tone": opp_tone},
    ])
    section_close()

    section_open("3) Executive Recommendation")
    rec_bg, rec_border, rec_color = tone_palette(recommendation_tone)
    st.markdown(
        f"""
        <div style="text-align:center; padding:0.9rem 0.6rem; border:1px solid {rec_border}; border-radius:14px; background:{rec_bg};">
            <div class="tcc-label">Today's Recommendation</div>
            <div style="font-size:clamp(1.55rem, 2.8vw, 2.2rem); font-weight:950; color:{rec_color}; line-height:1.12;">
                {html.escape(recommendation_text)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    section_close()

    section_open("4) Why?", "Concise institutional rationale for this recommendation.")
    decision_reasons = top_decision_reasons(decision, 5)
    if not decision_reasons:
        decision_reasons = [
            "Market regime is still being validated.",
            "Current setup needs additional institutional confirmation.",
            "Risk controls should remain primary before execution.",
        ]
    for reason in decision_reasons:
        st.markdown(f"- {reason}")
    section_close()

    section_open("5) Risk Dashboard", "Executive risk snapshot before detailed trade planning.")
    projected_qty = safe_float(plan.get("qty"), 0.0)
    projected_entry = safe_float(levels.get("entry"), 0.0)
    projected_stop = safe_float(levels.get("stop"), 0.0)
    projected_exposure = projected_qty * projected_entry
    projected_risk = projected_qty * abs(projected_entry - projected_stop)
    projected_rr = abs(safe_float(levels.get("target_2"), 0.0) - projected_entry) / max(abs(projected_entry - projected_stop), 0.01)
    gross_exposure = max(safe_float(execution.get("gross_exposure"), 0.0), 1.0)
    projected_impact = (projected_exposure / gross_exposure) * 100.0 if projected_exposure > 0 else 0.0
    render_card_grid([
        {"title": "Position Size", "value": f"{int(projected_qty):,}" if projected_qty > 0 else "Pending", "detail": "Scanner/risk-plan projected quantity", "tone": "info"},
        {"title": "Maximum Risk", "value": fmt_money(projected_risk), "detail": "Projected stop-based dollar risk", "tone": "warning" if projected_risk > 0 else "neutral"},
        {"title": "Dollar Exposure", "value": fmt_money(projected_exposure), "detail": "Projected notional exposure", "tone": "info"},
        {"title": "Risk / Reward", "value": risk_reward_card_value(projected_rr), "detail": "Projected to Target 2", "tone": "good" if projected_rr >= 2 else "warning"},
        {"title": "Stop Distance", "value": fmt_pct((abs(projected_entry - projected_stop) / projected_entry * 100.0) if projected_entry > 0 else 0.0), "detail": "Distance from projected entry", "tone": "warning"},
        {"title": "Portfolio Impact", "value": f"{projected_impact:.1f}%", "detail": "Share of current gross exposure", "tone": "warning" if projected_impact >= 20 else "good"},
    ])
    section_close()

    section_open("6) Trade Management Plan", "Execution bridge from validated setup to complete trade management.")
    render_trade_management_guidance()
    sizing = build_sizing_plan(symbol or "MANUAL", signal, levels, market, plan)
    portfolio_rows = _portfolio_rows_for_context(account_context, hold_rows())
    portfolio_context = build_portfolio_management_context(
        symbol=symbol,
        row=row,
        sizing=sizing,
        risk=risk,
        holds=portfolio_rows,
        scanner=scanner_rows(),
    )
    portfolio_controls = render_portfolio_risk_controls(portfolio_context, symbol)
    with st.expander("Advanced Portfolio Controls", expanded=False):
        render_section_guidance(
            [
                "Advanced settings for portfolio overlap, sector exposure, capital allocation, and portfolio-wide risk.",
                "Most users can keep these controls at their default values.",
            ]
        )
        sector_controls = render_sector_exposure_card(portfolio_context)
        correlation_controls = render_correlation_analysis_card(portfolio_context)
    dashboard_snapshot = publish_portfolio_dashboard_snapshot(
        portfolio_context,
        portfolio_controls,
        sector_controls,
        correlation_controls,
    )

    planner_df = pd.DataFrame([{
        "Symbol": symbol,
        "Action": sizing["action"],
        "Entry": fmt_money(sizing["entry"]),
        "Stop": fmt_money(sizing["stop"]),
        "TP1": fmt_money(sizing["target_1"]),
        "TP2": fmt_money(sizing["target_2"]),
        "TP3": fmt_money(sizing.get("target_3", 0.0)),
        "Position Size": sizing["qty"],
        "Estimated Risk": fmt_money(sizing["dollar_risk"]),
        "Estimated Reward": f"{sizing['rr_2']:.2f}R",
    }])
    st.dataframe(planner_df, width="stretch", hide_index=True)

    checklist = build_checklist(decision, plan, sizing, execution, market)
    risk_factors = build_risk_factors(row, market, plan, sizing, execution, checklist)
    rec = final_recommendation(decision, checklist, risk_factors)

    tp_allocation_ok = bool(sizing.get("tp_allocations_valid", False))
    no_critical_portfolio_violations = not bool(portfolio_controls.get("portfolio_risk_exceeded", False) or portfolio_controls.get("max_open_trades_exceeded", False))
    can_proceed = bool(tp_allocation_ok and no_critical_portfolio_violations)
    management = _resolve_trade_management_fields(sizing)
    institutional_review = render_institutional_review_panel(
        context=portfolio_context,
        sizing=sizing,
        portfolio_controls=portfolio_controls,
        sector_controls=sector_controls,
        correlation_controls=correlation_controls,
    )
    st.session_state["tcc_institutional_review"] = institutional_review
    st.session_state["tcc_portfolio_limits"] = {
        **portfolio_controls,
        **sector_controls,
        **correlation_controls,
        "dashboard_snapshot": dashboard_snapshot,
    }

    execution_checks = _build_execution_validation_checks(
        account_context=account_context,
        sizing=sizing,
        management=management,
        portfolio_controls=portfolio_controls,
        sector_controls=sector_controls,
        institutional_review=institutional_review,
        tp_allocation_ok=tp_allocation_ok,
    )
    failed_execution_checks = [
        label
        for key, label in [
            ("buying_power", "Buying Power"),
            ("position_size", "Position Size"),
            ("risk_limits", "Risk Limits"),
            ("portfolio_limits", "Portfolio Limits"),
            ("earnings_rules", "Earnings Rules"),
            ("time_stop", "Time Stop"),
            ("trade_management_plan", "Trade Management Plan"),
        ]
        if not bool(execution_checks.get(key, False))
    ]
    final_exec_recommendation = _build_final_execution_recommendation(
        institutional_review,
        risk_factors,
        failed_execution_checks,
    )
    live_execution_key = f"tcc_live_execution_{symbol}"
    live_execution_state = _sync_live_execution_state(st.session_state.get(live_execution_key, {}))
    if live_execution_state:
        st.session_state[live_execution_key] = live_execution_state

    section_open("7) Trade Checklist", "Institutional confidence checklist before execution handoff.")
    render_checklist(checklist)
    readiness = readiness_status(checklist)
    passed = sum(1 for _, ok in checklist if ok)
    total = len(checklist)
    if passed == total:
        st.success(f"Checklist complete: {passed}/{total}")
    elif passed >= total - 2:
        st.warning(f"Checklist nearly complete: {passed}/{total}")
    else:
        st.error(f"Checklist incomplete: {passed}/{total}")
    section_close()

    st.subheader("8) Supporting Evidence")
    st.caption("Secondary analytics are collapsed to preserve a decision-first execution workflow.")

    with st.expander("▼ Trend Analysis", expanded=False):
        render_mini_grid([
            ("Market Regime", professional_text(market.get("regime"), "Awaiting Confirmation")),
            ("Trend Bias", professional_text(signal, "Pending")),
            ("Conviction", professional_text(conviction, "Pending")),
            ("Decision", professional_text(decision.get("label"), "Pending")),
        ])

    with st.expander("▼ Momentum", expanded=False):
        render_card_grid([
            {"title": "Scanner Score", "value": fmt_score(scanner_score), "detail": "Opportunity momentum", "tone": "good" if scanner_score >= 80 else "warning"},
            {"title": "Rating", "value": professional_text(rating, "Pending"), "detail": "Quality tier", "tone": "info"},
            {"title": "Leadership", "value": professional_text(leadership, "Not Available"), "detail": "Leadership context", "tone": "info"},
        ])

    with st.expander("▼ Breadth", expanded=False):
        render_mini_grid([
            ("Breadth Score", f"{fmt_score(market.get('breadth_score'))}/100"),
            ("Breadth State", professional_text(market.get("breadth_state"), "Not Available")),
            ("Stress", f"{safe_int(market.get('stress_score'))}/100"),
        ])

    with st.expander("▼ Relative Strength", expanded=False):
        render_mini_grid([
            ("RS Score", rs_text),
            ("Opportunity Grade", opp_grade),
            ("Institutional Grade", inst_grade),
        ])

    with st.expander("▼ Institutional Signals", expanded=False):
        render_recommendation_banner(rec)
        if mismatch_warning:
            st.warning(mismatch_warning)

    with st.expander("▼ Technical Details", expanded=False):
        render_mini_grid([
            ("Entry", fmt_money(sizing.get("entry", 0))),
            ("Stop", fmt_money(sizing.get("stop", 0))),
            ("Target 1", fmt_money(sizing.get("target_1", 0))),
            ("Target 2", fmt_money(sizing.get("target_2", 0))),
            ("Risk/Reward", f"{safe_float(sizing.get('rr_2'), 0.0):.2f}R"),
            ("Per Share Risk", fmt_money(sizing.get("per_share_risk", 0))),
        ])

    with st.expander("▼ Statistics", expanded=False):
        stats_left, stats_right = st.columns(2)
        with stats_left:
            st.markdown("##### Scanner Candidates")
            rows = scanner_rows()
            if not rows:
                st.info("No Scanner rows found yet.")
            else:
                view_rows = []
                for r in rows[:40]:
                    view_rows.append({
                        "Symbol": row_symbol(r),
                        "Signal": normalize_signal(r.get("trade_recommendation") or r.get("scanner_action") or r.get("signal")),
                        "Score": safe_float(r.get("opportunity_score_pct"), 0.0),
                        "Rating": r.get("overall_rating", "N/A"),
                        "Sector": r.get("sector", "N/A"),
                        "Leadership": r.get("leadership_tier", "N/A"),
                    })
                st.dataframe(pd.DataFrame(view_rows), width="stretch", hide_index=True, height=320)

        with stats_right:
            st.markdown("##### Diagnostics")
            render_mini_grid([
                ("Version", "Trade Command Center v7.0"),
                ("Updated", now_iso()),
                ("Selected Symbol", symbol or "N/A"),
                ("Monitoring Packet", "Prepared" if isinstance(st.session_state.get("tcc_monitoring_payload"), dict) else "Not Prepared"),
                ("OMS Ticket", "Prepared" if isinstance(st.session_state.get("tcc_prepared_oms_ticket"), dict) else "Not Prepared"),
            ])
            if developer_mode:
                with st.expander("Debug Packet", expanded=False):
                    st.json({
                        "Selected Row": row,
                        "Risk Plan Row": plan,
                        "Hold Row": hold,
                        "Market Snapshot": market,
                        "Risk Snapshot": risk,
                        "Execution Snapshot": execution,
                        "Prepared OMS Ticket": st.session_state.get("tcc_prepared_oms_ticket", {}),
                        "Version": "Trade Command Center v7.0",
                        "Updated": now_iso(),
                    })

    section_open("9) Final Recommendation & Execution", "Final approval, broker routing, and live order status.")
    gateway = _resolve_gateway()
    broker_connected = bool(account_context.get("ibkr_connected", False)) and _is_gateway_connected(gateway)
    broker_name = "Interactive Brokers" if broker_connected else "None"

    order_status = str((live_execution_state or {}).get("status") or "").upper().strip()
    status_aliases = {
        "TRANSMITTING_ORDER": "TRANSMITTING ORDER...",
        "LIVE_SENT": "TRANSMITTING ORDER...",
        "PENDING_SUBMIT": "TRANSMITTING ORDER...",
        "PENDING": "TRANSMITTING ORDER...",
        "SUBMITTED": "ORDER ACCEPTED",
        "ROUTED": "ORDER ACCEPTED",
        "ACKNOWLEDGED": "ORDER ACCEPTED",
        "PRESUBMITTED": "WORKING",
        "WORKING": "WORKING",
        "PARTIALLY_FILLED": "PARTIALLY FILLED",
        "FILLED": "FILLED",
        "CANCELLED": "CANCELLED",
        "REJECTED": "REJECTED",
    }
    display_status = status_aliases.get(order_status, order_status or "PENDING")
    is_working = order_status in {"WORKING", "SUBMITTED", "ROUTED", "ACKNOWLEDGED", "PRESUBMITTED", "PENDING_SUBMIT", "PENDING", "PARTIALLY_FILLED", "LIVE_SENT", "TRANSMITTING_ORDER"}
    is_filled = order_status == "FILLED"

    left_col, right_col = st.columns([1.55, 1.0], gap="small")

    with left_col:
        final_bg, final_border, final_color = tone_palette(final_exec_recommendation.get("tone", "neutral"))
        issues_markup = "".join(
            f"<li>{html.escape(str(item))}</li>"
            for item in final_exec_recommendation.get("primary_issues", [])
        )
        issues_block = (
            "<div style='font-size:0.8rem; font-weight:800; color:#475569; margin-top:0.55rem;'>Primary Issues</div>"
            f"<ul style='margin:0.25rem 0 0 1.1rem; padding:0; color:#334155; line-height:1.45;'>{issues_markup}</ul>"
        ) if issues_markup else ""
        st.markdown(
            f"""
            <div class="tcc-banner" style="background:{final_bg};border-color:{final_border}; margin-bottom:0.75rem;">
                <div class="tcc-banner-label">FINAL RECOMMENDATION</div>
                <div class="tcc-banner-value" style="color:{final_color};">{html.escape(str(final_exec_recommendation.get('headline', '')))}</div>
                <div class="tcc-banner-detail">{html.escape(str(final_exec_recommendation.get('detail', '')))}</div>
                <div class="tcc-banner-detail" style="margin-top:0.4rem;">
                    Risk: {html.escape(fmt_money(safe_float(sizing.get('dollar_risk'), 0.0)))}<br>
                    Position Size: {html.escape(str(safe_int(sizing.get('qty'), 0)))}<br>
                    Entry: {html.escape(fmt_money(safe_float(sizing.get('entry'), 0.0)))}<br>
                    Stop Loss: {html.escape(fmt_money(safe_float(sizing.get('stop'), 0.0)))}<br>
                    Take Profit: {html.escape(fmt_money(safe_float(sizing.get('target_2'), 0.0)))}<br>
                    Risk / Reward: {html.escape(f"{safe_float(sizing.get('rr_2'), 0.0):.2f}R")}
                </div>
                {issues_block}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if failed_execution_checks and not ((is_working or is_filled) and live_execution_state):
            st.warning("Execution prerequisites are incomplete:")
            for check_label in failed_execution_checks:
                st.markdown(f"- {check_label}")

        if not ((is_working or is_filled) and live_execution_state):
            primary_label = "SEND ORDER" if broker_connected else "CONNECT BROKER"
            send_clicked = st.button(
                primary_label,
                width="stretch",
                key=f"tcc_send_to_broker_{symbol}",
                type="primary",
                disabled=sizing["qty"] <= 0,
            )

            if send_clicked:
                if not broker_connected:
                    navigate_to("Live IBKR")
                else:
                    broker_issues = _validate_direct_ibkr_execution(account_context, sizing, symbol)
                    if broker_issues:
                        st.error("Order was not sent. Resolve the following checks first:")
                        for issue in broker_issues:
                            st.markdown(f"- {issue}")
                    elif not bool(final_exec_recommendation.get("can_send", False)):
                        st.error("Institutional checks do not permit broker submission yet.")
                    else:
                        ok, error_text = _start_direct_ibkr_execution(
                            symbol=symbol,
                            sizing=sizing,
                            decision=decision,
                            row=row,
                            management=management,
                            institutional_review=institutional_review,
                            execution_checks=execution_checks,
                        )
                        if ok:
                            st.success("TRANSMITTING ORDER...")
                            st.rerun()
                        else:
                            st.error(f"Order submission failed: {error_text}")

    with right_col:
        with st.container(border=True):
            st.markdown("### Broker")
            if broker_connected:
                st.markdown("🟢 Interactive Brokers Connected")
            else:
                st.markdown("⚪ No Broker Connected")
                st.caption("Connect broker to route orders.")

            st.markdown("### Order Status")

            if (is_working or is_filled) and live_execution_state:
                if is_filled:
                    st.markdown("✓ POSITION OPEN")
                else:
                    st.markdown(display_status)
                st.markdown(f"- Order ID: {live_execution_state.get('order_id') or 'Pending'}")
                st.markdown(f"- Status: {display_status}")
                st.markdown(f"- Filled: {safe_float(live_execution_state.get('filled_qty'), 0.0):.0f}")
                st.markdown(f"- Remaining: {safe_float(live_execution_state.get('remaining_qty'), 0.0):.0f}")
                st.markdown(f"- Average Fill: {fmt_money(safe_float(live_execution_state.get('avg_fill_price'), 0.0))}")

                if is_working:
                    modify_qty_key = f"tcc_modify_qty_{symbol}"
                    _ensure_widget_default(modify_qty_key, max(1, safe_int(live_execution_state.get("qty"), safe_int(sizing.get("qty"), 1))))
                    st.number_input("Modify quantity", min_value=1, step=1, key=modify_qty_key)

                    mod_col, cancel_col = st.columns(2)
                    with mod_col:
                        modify_clicked = st.button("MODIFY ORDER", width="stretch", key=f"tcc_modify_order_{symbol}")
                    with cancel_col:
                        cancel_clicked = st.button("CANCEL ORDER", width="stretch", key=f"tcc_cancel_order_{symbol}")

                    if modify_clicked:
                        replacement_qty = max(1, safe_int(st.session_state.get(modify_qty_key), safe_int(sizing.get("qty"), 1)))
                        broker_id = str(live_execution_state.get("broker_order_id") or "").strip()
                        if not broker_connected:
                            st.error("Broker connection is not active.")
                        else:
                            cancel_ok = True
                            if broker_id and gateway is not None and hasattr(gateway, "cancel_order"):
                                try:
                                    cancel_ok = bool(gateway.cancel_order(broker_id))
                                except Exception:
                                    cancel_ok = False
                            if not cancel_ok:
                                st.error("Failed to cancel the working order before replacement.")
                            else:
                                replacement_sizing = dict(sizing)
                                replacement_sizing["qty"] = replacement_qty
                                ok, error_text = _start_direct_ibkr_execution(
                                    symbol=symbol,
                                    sizing=replacement_sizing,
                                    decision=decision,
                                    row=row,
                                    management=management,
                                    institutional_review=institutional_review,
                                    execution_checks=execution_checks,
                                )
                                if ok:
                                    st.success("TRANSMITTING ORDER...")
                                    st.rerun()
                                else:
                                    st.error(f"Replacement order failed: {error_text}")

                    if cancel_clicked:
                        broker_id = str(live_execution_state.get("broker_order_id") or "").strip()
                        if not broker_id:
                            st.error("Broker order ID is missing.")
                        elif gateway is None or not hasattr(gateway, "cancel_order"):
                            st.error("Broker gateway does not support order cancellation.")
                        else:
                            try:
                                canceled = bool(gateway.cancel_order(broker_id))
                            except Exception:
                                canceled = False
                            if canceled:
                                live_execution_state["status"] = "CANCELLED"
                                st.session_state[live_execution_key] = live_execution_state
                                st.success("Order cancelled.")
                            else:
                                st.error("Order cancellation failed.")

                if is_filled:
                    auto_open_key = f"tcc_auto_open_pcc_{symbol}_{live_execution_state.get('order_id') or live_execution_state.get('broker_order_id') or ''}"
                    if not bool(st.session_state.get(auto_open_key, False)):
                        st.session_state[auto_open_key] = True
                        navigate_to("Position Command Center")

                    if st.button("OPEN POSITION COMMAND CENTER", width="stretch", key=f"tcc_open_pcc_filled_{symbol}"):
                        navigate_to("Position Command Center")
            else:
                st.markdown("TRANSMITTING ORDER..." if st.session_state.get(f"tcc_send_to_broker_{symbol}") else "Awaiting order transmission")

    section_close()

    st.markdown("---")
    with st.expander("▼ Quick Navigation", expanded=False):
        a1, a2, a3, a4, a5 = st.columns(5)
        with a1:
            if st.button("Send to Research Stock", width="stretch", key="tcc_send_research_v21"):
                st.session_state["research_ticker"] = symbol
                st.session_state["research_ticker_input"] = symbol
                st.session_state["research_last_analyze"] = True
                navigate_to("Research Stock")
        with a2:
            if st.button("Send to Options Center", width="stretch", key="tcc_send_options_v21"):
                st.session_state["options_manual_symbol"] = symbol
                st.session_state["trade_command_symbol"] = symbol
                navigate_to("Options Center")
        with a3:
            if st.button("Open Position Command Center", width="stretch", key="tcc_open_pcc_bottom_v21"):
                navigate_to("Position Command Center")
        with a4:
            if st.button("Open Journal", width="stretch", key="tcc_open_journal_v21"):
                navigate_to("Journal")
        with a5:
            if st.button("Refresh", width="stretch", key="tcc_refresh_v21"):
                st.rerun()

    if developer_mode:
        with st.expander("Developer Diagnostics", expanded=False):
            rows = scanner_rows()
            st.json({
                "Selected Row": row,
                "Risk Plan Row": plan,
                "Hold Row": hold,
                "Market Snapshot": market,
                "Risk Snapshot": risk,
                "Execution Snapshot": execution,
                "Prepared OMS Ticket": st.session_state.get("tcc_prepared_oms_ticket", {}),
                "Scanner Rows Count": len(rows),
                "Version": "Trade Command Center v7.0",
                "Updated": now_iso(),
            })


def page() -> None:
    run_page()
