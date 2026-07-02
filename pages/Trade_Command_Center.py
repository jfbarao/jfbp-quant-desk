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

import pandas as pd
import streamlit as st


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
    return (
        f'<div class="tcc-card" style="background:{bg};border-color:{border};">'
        f'<div class="tcc-label">{html.escape(str(title))}</div>'
        f'<div class="tcc-value" style="color:{color};">{html.escape(str(value))}</div>'
        f'<div class="tcc-detail">{html.escape(str(detail))}</div>'
        f'</div>'
    )


def render_card_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="tcc-card-grid">']
    for card in cards:
        pieces.append(card_html(card.get("title", ""), card.get("value", ""), card.get("detail", ""), card.get("tone", "neutral")))
    pieces.append("</div>")
    st.markdown("".join(pieces), unsafe_allow_html=True)


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

    preferred = st.session_state.get("trade_command_symbol") or row_symbol(best_scanner_row())

    if symbols:
        index = symbols.index(preferred) if preferred in symbols else 0
        chosen = st.selectbox("Trade command symbol", options=symbols, index=index, key="tcc_symbol_select_v20")
        st.session_state["trade_command_symbol"] = chosen
        return lookup.get(chosen, {})

    manual = st.text_input(
        "Trade command symbol",
        value=st.session_state.get("trade_command_symbol", "AAPL"),
        key="trade_command_manual_symbol_v20",
    ).upper().strip()
    st.session_state["trade_command_symbol"] = manual
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
    else:
        stop = raw_stop if raw_stop > 0 else entry * 0.94
        target_1 = raw_target if raw_target > 0 else entry * 1.10
        target_2 = entry + (abs(entry - stop) * 2.0)

    return {"entry": entry, "stop": stop, "target_1": target_1, "target_2": target_2, "last": price}


def build_sizing_plan(symbol: str, signal: str, levels: Dict[str, float], market: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    multiplier = safe_float(market.get("execution_multiplier"), 1.0)
    default_account = safe_float(st.session_state.get("tcc_account_size", 100000.0), 100000.0)
    default_risk = safe_float(st.session_state.get("tcc_risk_pct", 1.0), 1.0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        account_size = st.number_input("Account Size", min_value=1000.0, max_value=10000000.0, value=default_account, step=1000.0, key="tcc_account_size")
    with c2:
        risk_pct = st.number_input("Risk %", min_value=0.05, max_value=10.0, value=default_risk, step=0.05, key="tcc_risk_pct")
    with c3:
        entry = st.number_input("Entry", min_value=0.01, value=float(levels["entry"]), step=0.01, key=f"tcc_entry_{symbol}")
    with c4:
        stop = st.number_input("Stop", min_value=0.01, value=float(levels["stop"]), step=0.01, key=f"tcc_stop_{symbol}")

    target_1_default = float(levels["target_1"])
    target_2_default = float(levels["target_2"])
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        target_1 = st.number_input("Target 1", min_value=0.01, value=target_1_default, step=0.01, key=f"tcc_target1_{symbol}")
    with p2:
        target_2 = st.number_input("Target 2", min_value=0.01, value=target_2_default, step=0.01, key=f"tcc_target2_{symbol}")
    with p3:
        max_position_pct = st.number_input("Max Position %", min_value=0.1, max_value=100.0, value=10.0, step=0.5, key="tcc_max_position_pct")
    with p4:
        planned_qty = safe_float(plan.get("qty"), 0.0)
        use_plan_qty = st.toggle("Use Scanner Qty", value=planned_qty > 0, key=f"tcc_use_plan_qty_{symbol}")

    per_share_risk = abs(entry - stop)
    dollar_risk = account_size * (risk_pct / 100.0) * multiplier
    risk_qty = int(dollar_risk / per_share_risk) if per_share_risk > 0 else 0
    max_value = account_size * (max_position_pct / 100.0)
    max_qty = int(max_value / entry) if entry > 0 else 0
    qty = int(planned_qty) if use_plan_qty and planned_qty > 0 else max(0, min(risk_qty, max_qty))
    position_value = qty * entry
    actual_risk = qty * per_share_risk
    actual_risk_pct = (actual_risk / account_size * 100.0) if account_size > 0 else 0
    rr_1 = (abs(target_1 - entry) / per_share_risk) if per_share_risk > 0 else 0
    rr_2 = (abs(target_2 - entry) / per_share_risk) if per_share_risk > 0 else 0

    return {
        "symbol": symbol,
        "action": "SELL" if signal == "SELL" else "BUY",
        "entry": entry,
        "stop": stop,
        "target_1": target_1,
        "target_2": target_2,
        "qty": qty,
        "position_value": position_value,
        "dollar_risk": actual_risk,
        "risk_pct": actual_risk_pct,
        "risk_budget": dollar_risk,
        "per_share_risk": per_share_risk,
        "rr_1": rr_1,
        "rr_2": rr_2,
        "account_size": account_size,
        "size_multiplier": multiplier,
    }


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
    ticket = {
        "timestamp": now_iso(),
        "source": "Trade_Command_Center_v3_0",
        "status": "PREPARED_NOT_ROUTED",
        "symbol": symbol,
        "action": sizing.get("action", "BUY"),
        "qty": safe_int(sizing.get("qty"), 0),
        "entry": safe_float(sizing.get("entry"), 0.0),
        "stop": safe_float(sizing.get("stop"), 0.0),
        "target_1": safe_float(sizing.get("target_1"), 0.0),
        "target_2": safe_float(sizing.get("target_2"), 0.0),
        "position_value": safe_float(sizing.get("position_value"), 0.0),
        "dollar_risk": safe_float(sizing.get("dollar_risk"), 0.0),
        "risk_reward_1": safe_float(sizing.get("rr_1"), 0.0),
        "risk_reward_2": safe_float(sizing.get("rr_2"), 0.0),
        "decision_label": decision.get("label", ""),
        "decision_score": decision.get("score", 0),
        "scanner_score": safe_float(row.get("opportunity_score_pct"), 0.0),
        "note": "Advisory ticket prepared by Trade Command Center. Confirm in OMS before execution.",
    }
    st.session_state["tcc_prepared_oms_ticket"] = ticket
    st.session_state["oms_prepared_ticket"] = ticket
    st.session_state["oms_order_symbol"] = symbol
    st.session_state["trade_command_symbol"] = symbol
    return ticket


def send_trade_plan_to_journal(symbol: str, sizing: Dict[str, Any], decision: Dict[str, Any], reasons: List[str]) -> Dict[str, Any]:
    note = {
        "timestamp": now_iso(),
        "source": "Trade_Command_Center_v3_0",
        "symbol": symbol,
        "tag": "TRADE_PLAN",
        "setup_grade": "A" if safe_float(decision.get("score"), 0) >= 80 else "B" if safe_float(decision.get("score"), 0) >= 65 else "C",
        "execution_grade": "Planned",
        "notes": " | ".join(reasons),
        "trade_plan": sizing,
        "decision": decision,
    }
    existing = st.session_state.get("tcc_journal_notes", [])
    if not isinstance(existing, list):
        existing = []
    st.session_state["tcc_journal_notes"] = [note] + existing[:49]
    st.session_state["journal_prefill_note"] = note
    return note


# =========================================================
# PAGE
# =========================================================

def run_page() -> None:
    inject_css()

    st.title("🎯 Trade Command Center")
    st.caption("Trade Command Center v7.0 — Institutional Trade Decision Framework. Validate setup quality, risk, readiness, and execution plan before OMS handoff. Advisory only.")

    st.markdown(
        """
        <div class="tcc-flow">
            <strong>Workflow:</strong><br>
            Market Pulse → Scanner → Research Stock → Trade Command Center → OMS Execution → Position Command Center → Journal
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
            5. Review the final recommendation and risk factors before OMS handoff.
            6. Prepare the OMS ticket and Journal note. No live order is sent from this page.
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
        recommendation_text = "Execute Trade"
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
        {"title": "Risk / Reward", "value": f"{preview_rr:.2f}R", "detail": "Preview to Target 2", "tone": "good" if preview_rr >= 2 else "warning"},
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
        {"title": "Risk / Reward", "value": f"{projected_rr:.2f}R", "detail": "Projected to Target 2", "tone": "good" if projected_rr >= 2 else "warning"},
        {"title": "Stop Distance", "value": fmt_pct((abs(projected_entry - projected_stop) / projected_entry * 100.0) if projected_entry > 0 else 0.0), "detail": "Distance from projected entry", "tone": "warning"},
        {"title": "Portfolio Impact", "value": f"{projected_impact:.1f}%", "detail": "Share of current gross exposure", "tone": "warning" if projected_impact >= 20 else "good"},
    ])
    section_close()

    section_open("6) Trade Plan", "Execution bridge from validated setup to OMS handoff.")
    sizing = build_sizing_plan(symbol or "MANUAL", signal, levels, market, plan)
    planner_df = pd.DataFrame([{
        "Symbol": symbol,
        "Action": sizing["action"],
        "Entry": fmt_money(sizing["entry"]),
        "Stop": fmt_money(sizing["stop"]),
        "Target": fmt_money(sizing["target_2"]),
        "Position Size": sizing["qty"],
        "Estimated Risk": fmt_money(sizing["dollar_risk"]),
        "Estimated Reward": f"{sizing['rr_2']:.2f}R",
    }])
    st.dataframe(planner_df, width="stretch", hide_index=True)

    checklist = build_checklist(decision, plan, sizing, execution, market)
    risk_factors = build_risk_factors(row, market, plan, sizing, execution, checklist)
    rec = final_recommendation(decision, checklist, risk_factors)

    if decision_style == "reject":
        action_left, action_right = st.columns(2)
        with action_left:
            if st.button("Continue Monitoring", width="stretch", key="tcc_continue_monitoring_v70"):
                st.info("Monitoring mode active. No OMS routing action was triggered.")
        with action_right:
            if st.button("Save Trade to Journal", width="stretch", key="tcc_save_journal_v70"):
                note = send_trade_plan_to_journal(symbol, sizing, decision, decision.get("reasons", []))
                st.success(f"Trade plan note prepared for Journal: {symbol}")
                st.json(note)
    else:
        if decision_style == "execute":
            oms_bg = "#2563eb"
            oms_text = "#ffffff"
            oms_border = "#1d4ed8"
            oms_hover = "#1e40af"
        else:
            oms_bg = "#f59e0b"
            oms_text = "#111827"
            oms_border = "#d97706"
            oms_hover = "#b45309"

        st.markdown(
            f"""
            <style>
            .st-key-tcc_open_oms_primary_v70 button {{
                background:{oms_bg} !important;
                color:{oms_text} !important;
                border:1px solid {oms_border} !important;
            }}
            .st-key-tcc_open_oms_primary_v70 button:hover {{
                background:{oms_hover} !important;
                color:{oms_text} !important;
                border-color:{oms_border} !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        action_left, action_right = st.columns(2)
        with action_left:
            if st.button("Open OMS With Prepared Ticket", width="stretch", disabled=sizing["qty"] <= 0, key="tcc_open_oms_primary_v70", type="primary"):
                prepare_oms_ticket(symbol, sizing, decision, row)
                navigate_to("OMS Execution")
        with action_right:
            if st.button("Save Trade to Journal", width="stretch", key="tcc_save_journal_v70"):
                note = send_trade_plan_to_journal(symbol, sizing, decision, decision.get("reasons", []))
                st.success(f"Trade plan note prepared for Journal: {symbol}")
                st.json(note)
    section_close()

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
            st.write({
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
            if st.button("Open OMS Execution", width="stretch", key="tcc_open_oms_bottom_v21"):
                prepare_oms_ticket(symbol, sizing, decision, row)
                navigate_to("OMS Execution")
        with a4:
            if st.button("Open Journal", width="stretch", key="tcc_open_journal_v21"):
                navigate_to("Journal")
        with a5:
            if st.button("Refresh", width="stretch", key="tcc_refresh_v21"):
                st.rerun()

    with st.expander("Developer Diagnostics", expanded=False):
        rows = scanner_rows()
        st.write({
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


def page() -> None:
    run_page()
