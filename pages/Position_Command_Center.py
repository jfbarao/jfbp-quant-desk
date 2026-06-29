# =========================================================
# 🎯 POSITION COMMAND CENTER
# JFBP Quant Desk
# Institutional position-management console for open positions,
# exposure, scanner alignment, OMS handoff prep, and Journal notes.
# Advisory only — no live routing from this page.
# =========================================================

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

from core.bootstrap import init_core
from core.responsive import inject_responsive_css
from core.ui_cards import inject_card_css


# =========================================================
# HELPERS
# =========================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "").replace("%", "").strip()
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
    inject_responsive_css(max_width=1500)
    inject_card_css()
    st.markdown(
        """
<style>
.block-container {
    padding-top: 1.4rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1500px !important;
    padding-left: clamp(0.9rem, 2.2vw, 2.75rem) !important;
    padding-right: clamp(0.9rem, 2.2vw, 2.75rem) !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
h1 { font-size: var(--jfbp-type-h1, clamp(1.75rem, 3.6vw, 2.45rem)) !important; font-weight: 850 !important; color:#1f2937 !important; line-height:1.12 !important; }
h2, h3 { font-size: var(--jfbp-type-h2, clamp(1.08rem, 2.2vw, 1.45rem)) !important; font-weight: 850 !important; color:#1f2937 !important; line-height:1.18 !important; }
div[data-testid="stHorizontalBlock"] { gap: 0.85rem !important; align-items: stretch !important; }
div[data-testid="stHorizontalBlock"] > div, div[data-testid="column"] { min-width: 0 !important; }
div[data-testid="stDataFrame"] { width:100% !important; max-width:100% !important; overflow-x:auto !important; border-radius:12px !important; }
div[data-testid="stDataFrame"] * { white-space: normal !important; overflow-wrap: anywhere !important; }
.stButton > button { border-radius: 10px !important; font-weight: 750 !important; min-height: 38px !important; border:1px solid #d7e3f5 !important; }
.pcc-card-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 245px), 1fr)); gap:0.85rem; margin:0.45rem 0 1.0rem 0; }
.pcc-card-grid--compact { margin-top:0.16rem; margin-bottom:0.72rem; }
.pcc-card { border:1px solid; border-radius:14px; padding:0.82rem 0.92rem; min-height:100px; overflow:hidden; box-sizing:border-box; }
.pcc-label { color:#64748b; font-size:var(--jfbp-type-card-label, 0.72rem); font-weight:850; letter-spacing:0.05em; text-transform:uppercase; margin-bottom:0.30rem; }
.pcc-value { font-size:var(--jfbp-type-card-value, clamp(1.05rem, 2.2vw, 1.35rem)); font-weight:880; line-height:1.14; margin-bottom:0.30rem; overflow-wrap:anywhere; }
.pcc-detail { color:#475569; font-size:var(--jfbp-type-caption, 0.82rem); line-height:1.35; overflow-wrap:anywhere; }
.pcc-hero-metrics { display:flex; flex-wrap:wrap; gap:0.42rem; margin:0.12rem 0 0.34rem 0; }
.pcc-hero-metric { flex:1 1 140px; min-width:140px; background:rgba(255,255,255,0.70); border:1px solid rgba(148,163,184,0.36); border-radius:12px; padding:0.42rem 0.58rem; box-sizing:border-box; }
.pcc-hero-metric-label { display:block; color:#64748b; font-size:0.68rem; font-weight:850; letter-spacing:0.05em; text-transform:uppercase; line-height:1.05; margin-bottom:0.18rem; }
.pcc-hero-metric-value { display:block; color:#111827; font-size:0.98rem; font-weight:880; line-height:1.12; overflow-wrap:anywhere; }
.pcc-section-card { background:#ffffff; border:1px solid #e5eaf3; border-radius:14px; padding:0.88rem 0.94rem; margin:0 0 0.82rem 0; overflow:hidden; }
.pcc-mini-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 170px), 1fr)); gap:0.65rem; margin:0.45rem 0 1rem 0; }
.pcc-mini { background:#f8fafc; border:1px solid #dbe3ef; border-radius:14px; padding:0.72rem 0.82rem; }
.pcc-mini-label { color:#64748b; font-size:var(--jfbp-type-card-label, 0.72rem); font-weight:850; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.25rem; }
.pcc-mini-value { color:#111827; font-size:var(--jfbp-type-card-value, clamp(1.05rem, 2.2vw, 1.35rem)); font-weight:880; overflow-wrap:anywhere; }
.pcc-checklist-card { background:#fffdf2; border:1px solid #f2d98d; border-radius:12px; padding:0.72rem 0.84rem; margin:0.34rem 0 0.22rem 0; }
.pcc-checklist-title { color:#78350f; font-size:0.76rem; font-weight:900; letter-spacing:0.055em; text-transform:uppercase; margin-bottom:0.28rem; }
.pcc-checklist-item { color:#1f2937; font-size:0.92rem; font-weight:700; line-height:1.4; margin:0.08rem 0; }
.pcc-flow { background:#eff6ff; border:1px solid #bfdbfe; border-radius:12px; padding:0.72rem 0.82rem; margin:0.50rem 0 0.78rem 0; color:#334155; }
.pcc-hero { border:1px solid; border-radius:18px; padding:0.88rem 0.92rem; margin:0.60rem 0 0.82rem 0; box-shadow:0 2px 10px rgba(15, 23, 42, 0.05); }
.pcc-hero-kicker { font-size:var(--jfbp-type-card-label, 0.72rem); font-weight:850; letter-spacing:0.055em; text-transform:uppercase; color:#64748b; margin-bottom:0.24rem; }
.pcc-hero-title { font-size:clamp(1.22rem, 2.35vw, 1.62rem); font-weight:880; line-height:1.14; margin:0 0 0.30rem 0; }
.pcc-hero-text { font-size:var(--jfbp-type-body, 0.94rem); font-weight:700; color:#334155; line-height:1.38; margin-bottom:0.36rem; }
.pcc-hero-badges { display:flex; flex-wrap:wrap; gap:0.46rem; margin:0.08rem 0 0.46rem 0; }
.pcc-pill { display:inline-flex; align-items:center; gap:0.36rem; border-radius:999px; padding:0.30rem 0.58rem; border:1px solid; line-height:1.12; }
.pcc-pill-label { font-size:0.68rem; font-weight:880; letter-spacing:0.05em; text-transform:uppercase; opacity:0.92; }
.pcc-pill-value { font-size:0.82rem; font-weight:900; }
.pcc-pill-status { background:#fff7ed; border-color:#fdba74; color:#9a3412; }
.pcc-pill-conviction { background:#eff6ff; border-color:#93c5fd; color:#1d4ed8; }
.pcc-pill-risk { background:#fef2f2; border-color:#fca5a5; color:#991b1b; }
.pcc-hero-action { border-radius:12px; padding:0.60rem 0.78rem; background:rgba(255,255,255,0.72); border:1px solid rgba(148,163,184,0.35); font-size:var(--jfbp-type-body, 0.94rem); font-weight:820; color:#111827; }

.pcc-summary-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap:0.85rem; margin:0.45rem 0 1.0rem 0; }
.pcc-summary-card { background:#ffffff; border:1px solid #e5eaf3; border-radius:14px; padding:0.82rem 0.92rem; min-height:96px; box-shadow:0 1px 2px rgba(15, 23, 42, 0.04); overflow:hidden; }
.pcc-summary-symbol { font-size:var(--jfbp-type-card-value, clamp(1.05rem, 2.2vw, 1.35rem)); line-height:1.14; font-weight:880; color:#111827; margin-bottom:0.28rem; }
.pcc-summary-state { font-size:var(--jfbp-type-body, 0.94rem); font-weight:700; color:#334155; margin-bottom:0.30rem; overflow-wrap:anywhere; }
.pcc-summary-detail { font-size:var(--jfbp-type-caption, 0.82rem); line-height:1.35; color:#64748b; overflow-wrap:anywhere; }
.pcc-summary-action { display:inline-flex; align-items:center; gap:0.3rem; border-radius:999px; padding:0.18rem 0.55rem; font-size:0.74rem; font-weight:900; margin-top:0.3rem; background:#f8fafc; border:1px solid #dbe3ef; color:#111827; }

@media (max-width:1180px) {
    div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    div[data-testid="stHorizontalBlock"] > div, div[data-testid="column"] { min-width:100% !important; flex:1 1 100% !important; width:100% !important; }
    .pcc-section-card { padding:0.85rem; border-radius:15px; }
}
@media (max-width:760px) {
    .pcc-card-grid, .pcc-mini-grid { grid-template-columns:1fr; }
    .pcc-desktop-only { display:none !important; }
    .pcc-hero-metric { min-width:100%; }
}
@media (min-width:761px) {
    .pcc-mobile-only { display:none !important; }
}
div[data-testid="stSelectbox"] { margin-bottom:0.12rem !important; }
</style>
        """,
        unsafe_allow_html=True,
    )


def card_html(title: str, value: Any, detail: str = "", tone: str = "neutral") -> str:
    bg, border, color = tone_palette(tone)
    return (
        f'<div class="pcc-card" style="background:{bg};border-color:{border};">'
        f'<div class="pcc-label">{html.escape(str(title))}</div>'
        f'<div class="pcc-value" style="color:{color};">{html.escape(str(value))}</div>'
        f'<div class="pcc-detail">{html.escape(str(detail))}</div>'
        f'</div>'
    )


def render_card_grid(cards: List[Dict[str, Any]], compact: bool = False) -> None:
    class_name = "pcc-card-grid pcc-card-grid--compact" if compact else "pcc-card-grid"
    pieces = [f'<div class="{class_name}">']
    for card in cards:
        pieces.append(card_html(card.get("title", ""), card.get("value", ""), card.get("detail", ""), card.get("tone", "neutral")))
    pieces.append("</div>")
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_mini_grid(items: List[Tuple[str, Any]]) -> None:
    pieces = ['<div class="pcc-mini-grid">']
    for label, value in items:
        pieces.append(
            f'<div class="pcc-mini"><div class="pcc-mini-label">{html.escape(str(label))}</div>'
            f'<div class="pcc-mini-value">{html.escape(str(value))}</div></div>'
        )
    pieces.append("</div>")
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_hero_metrics(metrics: List[Tuple[str, Any]]) -> None:
    pieces = ['<div class="pcc-hero-metrics">']
    for label, value in metrics:
        pieces.append(
            '<div class="pcc-hero-metric">'
            f'<span class="pcc-hero-metric-label">{html.escape(str(label))}</span>'
            f'<span class="pcc-hero-metric-value">{html.escape(str(value))}</span>'
            '</div>'
        )
    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)

def health_badge(score: Any) -> str:
    value = safe_float(score, 0.0)
    if value >= 80:
        return f"🟢 {value:.0f}/100"
    if value >= 60:
        return f"🟡 {value:.0f}/100"
    if value >= 40:
        return f"🟠 {value:.0f}/100"
    return f"🔴 {value:.0f}/100"


def action_badge(action: str) -> str:
    action = str(action or "").upper().strip()
    if action == "HOLD":
        return "🟢 HOLD"
    if action == "TRIM":
        return "🟡 TRIM"
    if action == "TIGHTEN STOP":
        return "🟠 TIGHTEN STOP"
    if action == "EXIT":
        return "🔴 EXIT"
    return action or "—"


def action_tone(count: int, action: str) -> str:
    if count <= 0:
        return "good"
    action = str(action or "").upper()
    if action == "EXIT":
        return "risk"
    if action in {"TRIM", "TIGHTEN STOP"}:
        return "warning"
    return "info"



def section_open(title: str, caption: str = "") -> None:
    st.markdown('<div class="pcc-section-card">', unsafe_allow_html=True)
    if title:
        st.markdown(f"### {title}")
    if caption:
        st.caption(caption)


def section_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_exit_rules_checklist(reasons: Any) -> None:
    if isinstance(reasons, (list, tuple, set)):
        items = [str(item).strip() for item in reasons if str(item).strip()]
    elif reasons:
        items = [str(reasons).strip()]
    else:
        items = []

    if not items:
        items = ["No rule text available."]

    normalized_items = []
    for item in items:
        lowered = item.lower()
        if "under entry" in lowered:
            normalized_items.append("Entry complete")
        elif "market regime" in lowered and "selective" in lowered:
            normalized_items.append("Market supports position")
        elif "market stress" in lowered and ("calm" in lowered or "stable" in lowered):
            normalized_items.append("Stress acceptable")
        else:
            normalized_items.append(item[0].upper() + item[1:] if item else item)

    checklist_html = ['<div class="pcc-checklist-card">', '<div class="pcc-checklist-title">Exit Checklist</div>']
    for item in normalized_items:
        checklist_html.append(f'<div class="pcc-checklist-item">✓ {html.escape(str(item))}</div>')
    checklist_html.append('</div>')
    st.markdown("".join(checklist_html), unsafe_allow_html=True)


# =========================================================
# DATA SOURCES
# =========================================================

def normalize_position_row(symbol_hint: str, pos: Any) -> Dict[str, Any] | None:
    if pos is None:
        return None

    if isinstance(pos, dict):
        contract = pos.get("contract")
        symbol = pos.get("symbol") or pos.get("ticker") or pos.get("contract_symbol") or symbol_hint
        if not symbol and contract is not None:
            symbol = getattr(contract, "symbol", None)
        qty = pos.get("signed_qty", pos.get("position", pos.get("qty", pos.get("quantity", pos.get("shares", 0)))))
        side = str(pos.get("side") or "").upper().strip()
        avg_price = pos.get("avg_price", pos.get("avg_cost", pos.get("average_cost", pos.get("avgPrice", pos.get("avgCost", 0)))))
        last_price = pos.get("last_price", pos.get("market_price", pos.get("marketPrice", pos.get("price", pos.get("last", 0)))))
        market_value = pos.get("position_value", pos.get("market_value", pos.get("marketValue", 0)))
        realized_pnl = pos.get("realized_pnl", pos.get("realized", 0))
    else:
        contract = getattr(pos, "contract", None)
        symbol = getattr(pos, "symbol", None) or getattr(contract, "symbol", None) or symbol_hint
        qty = getattr(pos, "signed_qty", None) or getattr(pos, "position", None) or getattr(pos, "qty", None) or 0
        side = str(getattr(pos, "side", "") or "").upper().strip()
        avg_price = getattr(pos, "avg_price", None) or getattr(pos, "avgCost", None) or getattr(pos, "avg_cost", None) or 0
        last_price = getattr(pos, "last_price", None) or getattr(pos, "marketPrice", None) or getattr(pos, "price", None) or 0
        market_value = getattr(pos, "marketValue", None) or getattr(pos, "position_value", None) or 0
        realized_pnl = getattr(pos, "realized_pnl", None) or 0

    symbol = str(symbol or "").upper().strip()
    if not symbol:
        return None

    qty = safe_float(qty, 0.0)
    if side == "SHORT" and qty > 0:
        qty = -abs(qty)
    elif side == "LONG" and qty < 0:
        qty = abs(qty)

    if abs(qty) <= 1e-9:
        return None

    avg_price = safe_float(avg_price, 0.0)
    last_price = safe_float(last_price, 0.0)
    market_value = safe_float(market_value, 0.0)
    realized_pnl = safe_float(realized_pnl, 0.0)

    if last_price <= 0 and market_value > 0 and abs(qty) > 0:
        last_price = abs(market_value / qty)
    if last_price <= 0:
        last_price = avg_price

    position_value = abs(market_value) if market_value > 0 else abs(qty) * last_price
    cost_basis = abs(qty) * avg_price
    unrealized = position_value - cost_basis if qty > 0 else cost_basis - position_value

    return {
        "symbol": symbol,
        "side": "LONG" if qty > 0 else "SHORT",
        "qty": abs(qty),
        "signed_qty": qty,
        "avg_price": avg_price,
        "last_price": last_price,
        "position_value": position_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": unrealized,
        "realized_pnl": realized_pnl,
        "total_pnl": unrealized + realized_pnl,
    }


def normalize_positions(raw_positions: Any) -> Dict[str, Dict[str, Any]]:
    if raw_positions is None:
        return {}
    if isinstance(raw_positions, pd.DataFrame):
        raw_positions = raw_positions.to_dict("records")
    if isinstance(raw_positions, dict):
        if all(isinstance(v, dict) for v in raw_positions.values()):
            iterable = raw_positions.items()
        else:
            iterable = [(raw_positions.get("symbol", ""), raw_positions)]
    elif isinstance(raw_positions, (list, tuple, set)):
        iterable = [("", x) for x in raw_positions]
    else:
        iterable = [("", raw_positions)]

    out: Dict[str, Dict[str, Any]] = {}
    for key, row in iterable:
        normalized = normalize_position_row(str(key), row)
        if normalized:
            out[normalized["symbol"]] = normalized
    return out


def pull_positions(gateway=None, portfolio_engine=None) -> Tuple[Dict[str, Dict[str, Any]], str]:
    live_mode = st.session_state.get("mode") == "LIVE"

    if live_mode:
        for source, obj, methods in [
            ("IBKR_GATEWAY", gateway, ("get_positions", "positions", "positions_snapshot", "broker_positions", "broker_positions_snapshot", "positions_cache")),
        ]:
            if obj is None:
                continue
            for method in methods:
                if hasattr(obj, method):
                    try:
                        data = getattr(obj, method)
                        data = data() if callable(data) else data
                        rows = normalize_positions(data)
                        if rows:
                            return rows, source
                    except Exception:
                        continue
        for key in ("broker_snapshot_positions", "broker_positions", "ibkr_positions", "live_positions"):
            rows = normalize_positions(st.session_state.get(key))
            if rows:
                return rows, f"SESSION:{key}"
        return {}, "LIVE_NO_POSITIONS"

    for source, obj, methods in [
        ("PORTFOLIO_ENGINE", portfolio_engine, ("get_all_positions", "positions_snapshot", "open_positions", "snapshot", "positions")),
        ("GATEWAY_FALLBACK", gateway, ("get_positions", "positions", "positions_snapshot", "broker_positions", "broker_positions_snapshot")),
    ]:
        if obj is None:
            continue
        for method in methods:
            if hasattr(obj, method):
                try:
                    data = getattr(obj, method)
                    data = data() if callable(data) else data
                    rows = normalize_positions(data)
                    if rows:
                        return rows, source
                except Exception:
                    continue

    for key in ("portfolio_positions", "positions", "ibkr_positions", "live_positions"):
        rows = normalize_positions(st.session_state.get(key))
        if rows:
            return rows, f"SESSION:{key}"

    return {}, "NONE"


def pull_ledger(portfolio_engine=None) -> List[Dict[str, Any]]:
    if portfolio_engine is None:
        return []
    for method in ("ledger_snapshot", "ledger"):
        if hasattr(portfolio_engine, method):
            try:
                data = getattr(portfolio_engine, method)
                data = data() if callable(data) else data
                if isinstance(data, list):
                    return [x for x in data if isinstance(x, dict)]
            except Exception:
                continue
    return []


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
    if risk_engine is not None and hasattr(risk_engine, "snapshot"):
        try:
            snap = risk_engine.snapshot()
            return snap if isinstance(snap, dict) else {}
        except Exception:
            return {}
    return {}


def scanner_lookup() -> Dict[str, Dict[str, Any]]:
    rows = st.session_state.get("scanner_last_raw_signals", [])
    lookup: Dict[str, Dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                symbol = str(row.get("display_symbol") or row.get("symbol") or "").upper().strip()
                if symbol:
                    lookup[symbol] = row
    return lookup


# =========================================================
# POSITION HEALTH ENGINE
# =========================================================

def position_pnl_pct(row: Dict[str, Any]) -> float:
    cost = safe_float(row.get("cost_basis"), 0.0)
    if cost <= 0:
        return 0.0
    return safe_float(row.get("unrealized_pnl"), 0.0) / cost * 100.0


def infer_stop_target(row: Dict[str, Any]) -> Tuple[float, float]:
    avg_price = safe_float(row.get("avg_price"), 0.0)
    last_price = safe_float(row.get("last_price"), 0.0)
    side = str(row.get("side") or "LONG").upper()
    base = avg_price if avg_price > 0 else last_price
    if base <= 0:
        return 0.0, 0.0
    if side == "SHORT":
        return base * 1.06, base * 0.90
    return base * 0.94, base * 1.12


def score_position(row: Dict[str, Any], market: Dict[str, Any], scanner_row: Dict[str, Any] | None = None) -> Dict[str, Any]:
    side = str(row.get("side") or "LONG").upper()
    pnl_pct = position_pnl_pct(row)
    last_price = safe_float(row.get("last_price"), 0.0)
    stop, target = infer_stop_target(row)
    regime = str(market.get("regime") or "UNKNOWN").upper().strip()
    stress = safe_float(market.get("stress_score"), 0.0)
    scanner_row = scanner_row or {}
    scanner_signal = str(scanner_row.get("trade_recommendation") or scanner_row.get("signal") or scanner_row.get("recommendation") or "UNKNOWN").upper().strip()
    scanner_score = safe_float(scanner_row.get("opportunity_score_pct") or scanner_row.get("model_score") or 0, 0.0)

    score = 50
    reasons: List[str] = []

    if pnl_pct >= 8:
        score += 18; reasons.append("Strong open profit")
    elif pnl_pct >= 3:
        score += 10; reasons.append("Positive open profit")
    elif pnl_pct <= -6:
        score -= 22; reasons.append("Loss beyond normal tolerance")
    elif pnl_pct < 0:
        score -= 8; reasons.append("Position is under entry")

    if side == "LONG":
        if regime in {"RISK_ON", "RISK-ON"}:
            score += 12; reasons.append("Market regime supports long exposure")
        elif regime in {"RISK_OFF", "RISK-OFF", "DEFENSIVE"}:
            score -= 16; reasons.append("Market regime conflicts with long exposure")
        elif regime in {"SELECTIVE", "NEUTRAL", "UNKNOWN"}:
            score += 2; reasons.append("Market regime is selective/neutral")
    else:
        if regime in {"RISK_OFF", "RISK-OFF", "DEFENSIVE"}:
            score += 10; reasons.append("Market regime supports defensive/short exposure")
        elif regime in {"RISK_ON", "RISK-ON"}:
            score -= 10; reasons.append("Risk-on regime conflicts with short exposure")

    if stress >= 75:
        score -= 18; reasons.append("Market stress is elevated")
    elif stress >= 50:
        score -= 8; reasons.append("Market stress is moderate")
    else:
        score += 6; reasons.append("Market stress is calm")

    if scanner_signal in {"BUY", "LONG", "BULLISH"}:
        score += 10 if side == "LONG" else -10
        reasons.append("Scanner supports long bias" if side == "LONG" else "Scanner conflicts with short position")
    elif scanner_signal in {"SELL", "SHORT", "BEARISH"}:
        score += 10 if side == "SHORT" else -14
        reasons.append("Scanner supports short bias" if side == "SHORT" else "Scanner conflicts with long position")
    elif scanner_signal == "WATCH":
        score += 3; reasons.append("Scanner is watch/hold, not a strong exit")
    elif scanner_signal not in {"", "UNKNOWN"}:
        score -= 4; reasons.append("Scanner signal is not supportive")

    if scanner_score >= 85:
        score += 8; reasons.append("High opportunity score")
    elif 0 < scanner_score < 60:
        score -= 8; reasons.append("Low opportunity score")

    stop_warning = False
    target_hit = False
    if last_price > 0 and stop > 0:
        if side == "LONG" and last_price <= stop:
            stop_warning = True
        elif side == "SHORT" and last_price >= stop:
            stop_warning = True
    if last_price > 0 and target > 0:
        if side == "LONG" and last_price >= target:
            target_hit = True
        elif side == "SHORT" and last_price <= target:
            target_hit = True

    if stop_warning:
        score -= 35; reasons.append("Stop zone has been breached")
    if target_hit:
        score += 6; reasons.append("Target zone has been reached")

    score = int(max(0, min(100, score)))

    if stop_warning or score < 35:
        action, health, tone = "EXIT", "🔴 Exit Candidate", "risk"
    elif score < 55:
        action, health, tone = "TIGHTEN STOP", "🟠 Weakening", "warning"
    elif target_hit and pnl_pct > 0:
        action, health, tone = "TRIM", "🟡 Target/Profit Zone", "warning"
    elif score >= 78:
        action, health, tone = "HOLD", "🟢 Strong", "good"
    else:
        action, health, tone = "HOLD", "🟡 Healthy", "info"

    if not reasons:
        reasons.append("Neutral position state")

    return {
        "health_score": score,
        "health_label": health,
        "tone": tone,
        "action": action,
        "stop": stop,
        "target": target,
        "pnl_pct": pnl_pct,
        "stop_warning": stop_warning,
        "target_hit": target_hit,
        "reasons": reasons[:5],
    }


def build_position_rows(positions: Dict[str, Dict[str, Any]], market: Dict[str, Any]) -> pd.DataFrame:
    lookup = scanner_lookup()
    rows: List[Dict[str, Any]] = []
    for symbol, row in positions.items():
        health = score_position(row, market, lookup.get(symbol, {}))
        rows.append({
            "Symbol": symbol,
            "Side": row.get("side", ""),
            "Qty": safe_float(row.get("qty"), 0.0),
            "Entry": fmt_money(row.get("avg_price")),
            "Last": fmt_money(row.get("last_price")),
            "Value": fmt_money(row.get("position_value")),
            "Unrealized P&L": fmt_money(row.get("unrealized_pnl")),
            "P&L %": fmt_pct(health["pnl_pct"]),
            "Stop": fmt_money(health["stop"]),
            "Target": fmt_money(health["target"]),
            "Health": health_badge(health["health_score"]),
            "State": health["health_label"],
            "Action Raw": health["action"],
            "Action": action_badge(health["action"]),
            "Reason": " | ".join(health["reasons"]),
        })
    if not rows:
        return pd.DataFrame()
    action_rank = {"EXIT": 0, "TIGHTEN STOP": 1, "TRIM": 2, "HOLD": 3}
    df = pd.DataFrame(rows)
    df["_Action Rank"] = df["Action Raw"].map(action_rank).fillna(9)
    df = df.sort_values(["_Action Rank", "Symbol"], ascending=[True, True]).drop(columns=["_Action Rank"])
    return df


def portfolio_heat(positions: Dict[str, Dict[str, Any]], risk: Dict[str, Any]) -> Dict[str, Any]:
    gross = sum(abs(safe_float(row.get("position_value"), 0.0)) for row in positions.values())
    risk_gross = safe_float(risk.get("gross_exposure"), 0.0)
    if risk_gross > gross:
        gross = risk_gross
    max_notional = safe_float(
        risk.get("max_gross_exposure") or risk.get("buying_power") or risk.get("equity") or risk.get("account_value"),
        0.0,
    )
    if max_notional <= 0:
        max_notional = max(gross * 2.0, 1.0)
    heat = gross / max_notional * 100.0 if max_notional > 0 else 0.0
    max_allowed = 60.0
    if heat >= max_allowed:
        label, tone = "HOT", "risk"
    elif heat >= max_allowed * 0.70:
        label, tone = "ELEVATED", "warning"
    else:
        label, tone = "NORMAL", "good"
    return {"gross": gross, "max_notional": max_notional, "heat": heat, "max_allowed": max_allowed, "label": label, "tone": tone}


def build_exit_watchlist(position_df: pd.DataFrame) -> pd.DataFrame:
    if position_df is None or position_df.empty:
        return pd.DataFrame()
    action_col = "Action Raw" if "Action Raw" in position_df.columns else "Action"
    mask = position_df[action_col].astype(str).isin(["EXIT", "TIGHTEN STOP", "TRIM"])
    cols = ["Symbol", "Side", "Unrealized P&L", "P&L %", "Health", "State", "Action", "Reason"]
    return position_df.loc[mask, [c for c in cols if c in position_df.columns]].copy()



def parse_health_score(value: Any) -> float:
    text = str(value or "")
    for icon in ("🟢", "🟡", "🟠", "🔴"):
        text = text.replace(icon, "")
    text = text.strip().split("/")[0]
    return safe_float(text, 0.0)


def exposure_snapshot(positions: Dict[str, Dict[str, Any]], risk: Dict[str, Any]) -> Dict[str, Any]:
    long_exposure = 0.0
    short_exposure = 0.0
    values: List[Tuple[str, float]] = []

    for symbol, row in positions.items():
        value = abs(safe_float(row.get("position_value"), 0.0))
        side = str(row.get("side") or "LONG").upper()
        if side == "SHORT":
            short_exposure += value
        else:
            long_exposure += value
        values.append((symbol, value))

    gross = long_exposure + short_exposure
    net = long_exposure - short_exposure
    account_value = safe_float(
        risk.get("equity") or risk.get("account_value") or risk.get("net_liquidation") or risk.get("buying_power"),
        0.0,
    )
    if account_value <= 0:
        account_value = max(gross * 2.0, 1.0)

    values = sorted(values, key=lambda x: x[1], reverse=True)
    largest_symbol = values[0][0] if values else "—"
    largest_value = values[0][1] if values else 0.0
    top3 = sum(v for _, v in values[:3])
    buying_power = safe_float(risk.get("buying_power"), 0.0)

    return {
        "long_exposure": long_exposure,
        "short_exposure": short_exposure,
        "net_exposure": net,
        "gross_exposure": gross,
        "account_value": account_value,
        "largest_symbol": largest_symbol,
        "largest_value": largest_value,
        "largest_pct": largest_value / account_value * 100.0 if account_value > 0 else 0.0,
        "top3_pct": top3 / account_value * 100.0 if account_value > 0 else 0.0,
        "buying_power": buying_power,
    }


def total_realized_pnl(positions: Dict[str, Dict[str, Any]], ledger: List[Dict[str, Any]]) -> float:
    realized = sum(safe_float(row.get("realized_pnl"), 0.0) for row in positions.values())
    if abs(realized) > 1e-9:
        return realized
    total = 0.0
    for row in ledger or []:
        if not isinstance(row, dict):
            continue
        for key in ("realized_pnl", "realized", "closed_pnl", "pnl_realized", "pnl"):
            if key in row:
                total += safe_float(row.get(key), 0.0)
                break
    return total


def largest_winner_loser(positions: Dict[str, Dict[str, Any]]) -> Tuple[str, float, str, float]:
    winner_symbol, winner_value = "—", 0.0
    loser_symbol, loser_value = "—", 0.0
    for symbol, row in positions.items():
        pnl = safe_float(row.get("unrealized_pnl"), 0.0)
        if winner_symbol == "—" or pnl > winner_value:
            winner_symbol, winner_value = symbol, pnl
        if loser_symbol == "—" or pnl < loser_value:
            loser_symbol, loser_value = symbol, pnl
    return winner_symbol, winner_value, loser_symbol, loser_value


def sector_for_symbol(symbol: str) -> str:
    symbol = str(symbol or "").upper().strip()
    lookup = scanner_lookup()
    row = lookup.get(symbol, {})
    for key in ("sector", "Sector", "sector_name", "gics_sector"):
        value = row.get(key)
        if value:
            return str(value)
    sector_map = {
        "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology", "AVGO": "Technology",
        "AMD": "Technology", "MU": "Technology", "GOOGL": "Communication Services", "GOOG": "Communication Services",
        "META": "Communication Services", "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
        "HD": "Consumer Discretionary", "COST": "Consumer Staples", "WMT": "Consumer Staples",
        "PG": "Consumer Staples", "XOM": "Energy", "CVX": "Energy", "JPM": "Financials",
        "BAC": "Financials", "WFC": "Financials", "GE": "Industrials", "CAT": "Industrials",
        "UNH": "Health Care", "JNJ": "Health Care", "LLY": "Health Care", "SPY": "Index",
        "QQQ": "Index", "IWM": "Index",
    }
    return sector_map.get(symbol, "Unclassified")


def build_sector_exposure(positions: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    rows: Dict[str, float] = {}
    gross = sum(abs(safe_float(row.get("position_value"), 0.0)) for row in positions.values())
    for symbol, row in positions.items():
        sector = sector_for_symbol(symbol)
        value = abs(safe_float(row.get("position_value"), 0.0))
        rows[sector] = rows.get(sector, 0.0) + value
    out = []
    for sector, value in sorted(rows.items(), key=lambda x: x[1], reverse=True):
        out.append({"Sector": sector, "Exposure": fmt_money(value), "Weight": fmt_pct((value / gross * 100.0) if gross else 0.0)})
    return pd.DataFrame(out)


def build_position_ledger_df(positions: Dict[str, Dict[str, Any]], position_df: pd.DataFrame) -> pd.DataFrame:
    if not positions:
        return pd.DataFrame()
    health_lookup: Dict[str, Dict[str, Any]] = {}
    if position_df is not None and not position_df.empty:
        for _, row in position_df.iterrows():
            symbol = str(row.get("Symbol", "")).upper().strip()
            if symbol:
                health_lookup[symbol] = row.to_dict()
    rows: List[Dict[str, Any]] = []
    for symbol, row in sorted(positions.items()):
        health = health_lookup.get(symbol, {})
        rows.append({
            "Symbol": symbol,
            "Side": row.get("side", "N/A"),
            "Qty": f"{safe_float(row.get('qty')):,.2f}",
            "Entry": fmt_money(row.get("avg_price")),
            "Last": fmt_money(row.get("last_price")),
            "Market Value": fmt_money(row.get("position_value")),
            "Cost Basis": fmt_money(row.get("cost_basis")),
            "Unrealized P&L": fmt_money(row.get("unrealized_pnl")),
            "Realized P&L": fmt_money(row.get("realized_pnl")),
            "Health": health.get("Health", "N/A"),
            "Action": health.get("Action", "N/A"),
        })
    return pd.DataFrame(rows)


def build_closed_trades_archive(ledger: List[Dict[str, Any]]) -> pd.DataFrame:
    if not ledger:
        return pd.DataFrame()
    rows: List[Dict[str, Any]] = []
    close_words = ("CLOSE", "CLOSED", "EXIT", "SELL", "COVER", "REALIZED")
    for item in ledger:
        if not isinstance(item, dict):
            continue
        text_blob = " ".join(str(item.get(k, "")) for k in ("action", "type", "status", "tag", "note", "notes")).upper()
        has_realized = any(k in item for k in ("realized_pnl", "realized", "closed_pnl", "pnl_realized", "pnl"))
        if not has_realized and not any(word in text_blob for word in close_words):
            continue
        realized = 0.0
        for key in ("realized_pnl", "realized", "closed_pnl", "pnl_realized", "pnl"):
            if key in item:
                realized = safe_float(item.get(key), 0.0)
                break
        rows.append({
            "Date": item.get("timestamp") or item.get("date") or item.get("time") or "—",
            "Symbol": str(item.get("symbol") or item.get("ticker") or item.get("Symbol") or "—").upper(),
            "Action": item.get("action") or item.get("type") or item.get("status") or "Closed/Review",
            "Qty": item.get("qty") or item.get("quantity") or item.get("shares") or "—",
            "Realized P&L": fmt_money(realized),
            "Notes": item.get("note") or item.get("notes") or item.get("reason") or "",
        })
    return pd.DataFrame(rows[:100])


def build_risk_alerts(report: Dict[str, Any], heat: Dict[str, Any], exposure: Dict[str, Any], alignment_df: pd.DataFrame) -> List[Tuple[str, str]]:
    alerts: List[Tuple[str, str]] = []
    if safe_float(heat.get("heat")) >= safe_float(heat.get("max_allowed"), 60.0):
        alerts.append(("🔴 Portfolio heat above guide", "Avoid adding exposure until gross exposure is reduced."))
    elif safe_float(heat.get("heat")) >= safe_float(heat.get("max_allowed"), 60.0) * 0.70:
        alerts.append(("🟡 Portfolio heat elevated", "New trades should be selective and smaller than normal."))
    if safe_float(exposure.get("largest_pct")) >= 25:
        alerts.append(("🔴 Largest position concentration", f"{exposure.get('largest_symbol', '—')} is above the 25% guide."))
    elif safe_float(exposure.get("largest_pct")) >= 20:
        alerts.append(("🟡 Largest position approaching concentration guide", f"{exposure.get('largest_symbol', '—')} should be watched."))
    if safe_float(exposure.get("top3_pct")) >= 40:
        alerts.append(("🔴 Top-3 concentration risk", "Top three positions exceed the 40% guide."))
    if safe_int(report.get("exit_candidates"), 0) > 0:
        symbols = ", ".join(report.get("exit_symbols", [])[:5]) or "review list"
        alerts.append(("🔴 Exit candidates present", f"Review {symbols} before adding new exposure."))
    if alignment_df is not None and not alignment_df.empty:
        conflicts = alignment_df[alignment_df["Alignment"].astype(str).str.contains("Conflict|Risk", case=False, regex=True)]
        if not conflicts.empty:
            symbols = ", ".join(conflicts["Symbol"].astype(str).head(5).tolist())
            alerts.append(("🔴 Scanner conflict / position risk", f"Scanner alignment flags: {symbols}."))
    if not alerts:
        alerts.append(("🟢 No major risk alerts", "Position book is within the current guide."))
    return alerts


def build_position_ranking(position_df: pd.DataFrame) -> pd.DataFrame:
    if position_df is None or position_df.empty:
        return pd.DataFrame()
    df = position_df.copy()
    df["Score Raw"] = df["Health"].apply(parse_health_score) if "Health" in df.columns else 0.0
    df = df.sort_values(["Score Raw", "Symbol"], ascending=[False, True]).reset_index(drop=True)
    df.insert(0, "Rank", [f"#{i + 1}" for i in range(len(df))])
    cols = ["Rank", "Symbol", "Side", "Score Raw", "Action", "Unrealized P&L", "P&L %", "State", "Reason"]
    out = df[[c for c in cols if c in df.columns]].copy()
    if "Score Raw" in out.columns:
        out["Score"] = out["Score Raw"].map(lambda x: f"{safe_float(x):.0f}/100")
        out = out.drop(columns=["Score Raw"])
    order = ["Rank", "Symbol", "Side", "Score", "Action", "Unrealized P&L", "P&L %", "State", "Reason"]
    return out[[c for c in order if c in out.columns]]


def scanner_signal_for_row(scanner_row: Dict[str, Any]) -> str:
    return str(
        scanner_row.get("trade_recommendation")
        or scanner_row.get("signal")
        or scanner_row.get("recommendation")
        or scanner_row.get("bias")
        or "UNKNOWN"
    ).upper().strip()


def scanner_alignment_label(position_action: str, scanner_signal: str, side: str) -> Tuple[str, str]:
    action = str(position_action or "").upper().strip()
    signal = str(scanner_signal or "UNKNOWN").upper().strip()
    side = str(side or "LONG").upper().strip()

    if signal in {"", "UNKNOWN", "N/A"}:
        return "⚪ No Scanner Read", "neutral"
    if action == "EXIT":
        return "🚨 Position Risk", "risk"
    if side == "LONG" and signal in {"SELL", "SHORT", "BEARISH", "AVOID"}:
        return "🚨 Scanner Conflict", "risk"
    if side == "SHORT" and signal in {"BUY", "LONG", "BULLISH"}:
        return "🚨 Scanner Conflict", "risk"
    if signal in {"WATCH", "HOLD", "NEUTRAL"}:
        return "⚠️ Watch", "warning"
    return "✅ Aligned", "good"


def build_scanner_alignment(positions: Dict[str, Dict[str, Any]], market: Dict[str, Any]) -> pd.DataFrame:
    lookup = scanner_lookup()
    rows: List[Dict[str, Any]] = []
    for symbol, row in positions.items():
        health = score_position(row, market, lookup.get(symbol, {}))
        signal = scanner_signal_for_row(lookup.get(symbol, {}))
        alignment, _tone = scanner_alignment_label(health["action"], signal, row.get("side"))
        rows.append({
            "Symbol": symbol,
            "Side": row.get("side", ""),
            "Position Action": action_badge(health["action"]),
            "Scanner Signal": signal,
            "Alignment": alignment,
            "Health": health_badge(health["health_score"]),
            "Reason": " | ".join(health.get("reasons", [])),
        })
    if not rows:
        return pd.DataFrame()
    rank = {"🚨 Scanner Conflict": 0, "🚨 Position Risk": 1, "⚠️ Watch": 2, "⚪ No Scanner Read": 3, "✅ Aligned": 4}
    df = pd.DataFrame(rows)
    df["_Rank"] = df["Alignment"].map(rank).fillna(9)
    return df.sort_values(["_Rank", "Symbol"]).drop(columns=["_Rank"])


def build_commander_report(
    positions: Dict[str, Dict[str, Any]],
    pos_df: pd.DataFrame,
    exit_df: pd.DataFrame,
    heat: Dict[str, Any],
    market: Dict[str, Any],
    exposure: Dict[str, Any],
) -> Dict[str, Any]:
    action_source = "Action Raw" if not pos_df.empty and "Action Raw" in pos_df.columns else "Action"
    actions = pos_df[action_source].value_counts().to_dict() if not pos_df.empty and action_source in pos_df.columns else {}
    scores = [parse_health_score(x) for x in pos_df["Health"]] if not pos_df.empty and "Health" in pos_df.columns else []
    avg_health = sum(scores) / max(len(scores), 1) if scores else 0.0
    strong = sum(1 for score in scores if score >= 78)
    review = actions.get("EXIT", 0) + actions.get("TRIM", 0) + actions.get("TIGHTEN STOP", 0)

    if actions.get("EXIT", 0) > 0 or heat.get("tone") == "risk" or avg_health < 40:
        status, tone = "DEFENSIVE", "risk"
    elif review > 0 or heat.get("tone") == "warning" or avg_health < 65:
        status, tone = "SELECTIVE", "warning"
    elif len(positions) == 0:
        status, tone = "STANDBY", "info"
    else:
        status, tone = "HEALTHY", "good"

    exit_symbols: List[str] = []
    trim_symbols: List[str] = []
    protect_symbols: List[str] = []

    if pos_df is not None and not pos_df.empty and "Symbol" in pos_df.columns and action_source in pos_df.columns:
        action_map = {
            "EXIT": exit_symbols,
            "TRIM": trim_symbols,
            "TIGHTEN STOP": protect_symbols,
        }
        for _, position_row in pos_df.iterrows():
            action_value = str(position_row.get(action_source, "")).upper().strip()
            symbol_value = str(position_row.get("Symbol", "")).upper().strip()
            if symbol_value and action_value in action_map:
                action_map[action_value].append(symbol_value)

    action_lines: List[str] = []
    if exit_symbols:
        action_lines.append(f"🚨 EXIT CANDIDATES: {', '.join(exit_symbols[:6])}")
    if trim_symbols:
        action_lines.append(f"⚠️ TRIM CANDIDATES: {', '.join(trim_symbols[:6])}")
    if protect_symbols:
        action_lines.append(f"🛡 PROTECT: {', '.join(protect_symbols[:6])}")

    if action_lines:
        action_text = "<br>".join(action_lines)
    elif heat.get("tone") == "risk":
        action_text = "ACTION: Portfolio heat is high. Avoid adding exposure until risk normalizes."
    elif len(positions) == 0:
        action_text = "ACTION: No active positions detected. Stand by for qualified setups."
    else:
        action_text = "ACTION: No immediate risk actions required. Continue monitoring scanner alignment."

    review_symbols: List[str] = (exit_symbols + trim_symbols + protect_symbols)[:8]

    summary = (
        f"{len(positions)} positions open. {strong} strong. {review} requiring review. "
        f"Portfolio heat {safe_float(heat.get('heat')):.1f}%. "
        f"Largest position: {exposure.get('largest_symbol', '—')} "
        f"({safe_float(exposure.get('largest_pct')):.1f}%)."
    )
    return {
        "status": status,
        "tone": tone,
        "open_positions": len(positions),
        "strong": strong,
        "review": review,
        "exit_candidates": actions.get("EXIT", 0),
        "avg_health": avg_health,
        "summary": summary,
        "action_text": action_text,
        "exit_symbols": exit_symbols,
        "trim_symbols": trim_symbols,
        "protect_symbols": protect_symbols,
        "review_symbols": review_symbols,
    }


def render_commander_report(report: Dict[str, Any], market: Dict[str, Any], heat: Dict[str, Any], exposure: Dict[str, Any]) -> None:
    section_open("🎖 Commander Report", "Fast morning read before reviewing individual positions.")
    status = str(report.get("status", "STANDBY"))
    tone = str(report.get("tone", "info"))
    bg, border, color = tone_palette(tone)
    regime = html.escape(str(market.get("regime", "UNKNOWN")))
    stress = safe_int(market.get("stress_score"), 0)
    metrics = [
        ("Market Regime", regime),
        ("Stress", f"{stress}/100"),
        ("Open Positions", report.get("open_positions", 0)),
        ("Strong", report.get("strong", 0)),
        ("Review", report.get("review", 0)),
        ("Largest Position", exposure.get("largest_symbol", "—")),
        ("Portfolio Heat", f"{safe_float(heat.get('heat')):.1f}%"),
    ]
    action_text = str(report.get("action_text", "ACTION: Continue monitoring."))
    action_text = "<br>".join(html.escape(part) for part in action_text.split("<br>"))
    st.markdown(
        f"""
        <div class="pcc-hero" style="background:{bg};border-color:{border};">
            <div class="pcc-hero-kicker">Institutional Position Command</div>
            <div class="pcc-hero-title" style="color:{color};">🛡 PORTFOLIO STATUS: {html.escape(status)}</div>
            <div class="pcc-hero-text">Operational snapshot</div>
            <div class="pcc-hero-action">{action_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_hero_metrics(metrics)

    render_card_grid([
        {"title": "Portfolio Status", "value": status, "detail": "Institutional position-management state", "tone": tone},
        {"title": "Market Regime", "value": market.get("regime", "UNKNOWN"), "detail": f"Stress {safe_int(market.get('stress_score'), 0)}/100", "tone": "info"},
        {"title": "Strong Positions", "value": report.get("strong", 0), "detail": "Health score 78+", "tone": "good" if report.get("strong", 0) else "neutral"},
        {"title": "Review Required", "value": report.get("review", 0), "detail": "Exit / trim / tighten-stop candidates", "tone": "warning" if report.get("review", 0) else "good"},
        {"title": "Largest Position Risk", "value": exposure.get("largest_symbol", "—"), "detail": f"{safe_float(exposure.get('largest_pct')):.1f}% of guide equity", "tone": "risk" if safe_float(exposure.get("largest_pct")) >= 25 else "warning" if safe_float(exposure.get("largest_pct")) >= 20 else "info"},
        {"title": "Top 3 Concentration", "value": f"{safe_float(exposure.get('top3_pct')):.1f}%", "detail": "Red above 40%", "tone": "risk" if safe_float(exposure.get("top3_pct")) >= 40 else "good"},
        {"title": "Portfolio Heat", "value": f"{safe_float(heat.get('heat')):.1f}%", "detail": heat.get("label", "NORMAL"), "tone": heat.get("tone", "neutral")},
    ])
    section_close()


def render_mobile_position_cards(position_df: pd.DataFrame) -> None:
    st.markdown('<div class="pcc-mobile-only">', unsafe_allow_html=True)
    if position_df is None or position_df.empty:
        st.info("No mobile position cards available.")
    else:
        for _, row in position_df.iterrows():
            with st.expander(f"{row.get('Symbol', 'N/A')} · {row.get('Action', '—')} · {row.get('P&L %', '0.00%')}", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Health", row.get("Health", "N/A"))
                    st.metric("P&L", row.get("Unrealized P&L", "$0.00"))
                    st.metric("Stop", row.get("Stop", "$0.00"))
                with c2:
                    st.metric("Side", row.get("Side", "N/A"))
                    st.metric("Last", row.get("Last", "$0.00"))
                    st.metric("Target", row.get("Target", "$0.00"))
                st.caption(str(row.get("Reason", "")))
    st.markdown('</div>', unsafe_allow_html=True)


def prepare_position_ticket(row: Dict[str, Any], ticket_type: str, pct: float = 1.0) -> Dict[str, Any]:
    side = str(row.get("side") or "LONG").upper()
    close_action = "SELL" if side == "LONG" else "BUY"
    qty = safe_float(row.get("qty"), 0.0)
    pct = max(0.0, min(float(pct), 1.0))
    ticket_qty = qty * pct
    symbol = str(row.get("symbol") or "").upper().strip()
    execution_id = str(
        row.get("execution_id")
        or row.get("exec_id")
        or row.get("order_id")
        or (st.session_state.get("oms_execution_id_by_symbol", {}) or {}).get(symbol, "")
        or ""
    ).strip()

    position_action = {
        "TRIM_25": "TRIM_POSITION",
        "TRIM_50": "TRIM_POSITION",
        "FULL_EXIT": "CLOSE_LONG" if side == "LONG" else "CLOSE_SHORT",
        "STOP_BREAKEVEN": "MODIFY_STOP_TO_BREAKEVEN",
        "LOCK_PROFIT": "MODIFY_STOP_LOCK_PROFIT",
    }.get(ticket_type, "POSITION_MANAGEMENT")

    ticket = {
        "timestamp": now_iso(),
        "symbol": symbol,
        "execution_id": execution_id,
        "action": close_action if ticket_type in {"TRIM_25", "TRIM_50", "FULL_EXIT"} else "MODIFY_STOP",
        "qty": ticket_qty if ticket_type in {"TRIM_25", "TRIM_50", "FULL_EXIT"} else qty,
        "pct_of_position": pct if ticket_type in {"TRIM_25", "TRIM_50", "FULL_EXIT"} else None,
        "position_action": position_action,
        "side": side,
        "avg_price": safe_float(row.get("avg_price"), 0.0),
        "last_price": safe_float(row.get("last_price"), 0.0),
        "source": "Position_Command_Center_v2_7",
        "status": "PREPARED_NOT_ROUTED",
        "note": "Advisory position-management ticket. Confirm OMS, broker truth, liquidity, and risk before routing.",
    }
    st.session_state["pcc_prepared_exit_ticket"] = ticket
    st.session_state["oms_exit_ticket"] = ticket
    st.session_state["oms_order_symbol"] = symbol
    return ticket




def pnl_tone(value: Any) -> str:
    pnl = safe_float(value, 0.0)
    if pnl > 0:
        return "good"
    if pnl < 0:
        return "risk"
    return "neutral"


def position_summary_tone(action: str) -> str:
    action = str(action or "").upper().strip()
    if action == "EXIT":
        return "risk"
    if action in {"TRIM", "TIGHTEN STOP"}:
        return "warning"
    if action == "HOLD":
        return "good"
    return "neutral"


def render_position_summary(position_df: pd.DataFrame, max_cards: int = 6) -> None:
    """Render compact position summary cards using native Streamlit containers.

    This avoids raw HTML leakage in Streamlit while keeping the fast-read
    command-card behavior.
    """
    if position_df is None or position_df.empty:
        st.info("No open positions to summarize.")
        return

    display_df = position_df.copy()

    if "Action Raw" not in display_df.columns and "Action" in display_df.columns:
        display_df["Action Raw"] = (
            display_df["Action"]
            .astype(str)
            .str.replace("🟢", "", regex=False)
            .str.replace("🟡", "", regex=False)
            .str.replace("🟠", "", regex=False)
            .str.replace("🔴", "", regex=False)
            .str.strip()
        )

    action_rank = {"EXIT": 0, "TIGHTEN STOP": 1, "TRIM": 2, "HOLD": 3}
    display_df["_Summary Rank"] = display_df["Action Raw"].map(action_rank).fillna(9)
    display_df = (
        display_df
        .sort_values(["_Summary Rank", "Symbol"], ascending=[True, True])
        .head(max_cards)
    )

    rows = display_df.to_dict("records")

    for offset in range(0, len(rows), 3):
        cols = st.columns(3, gap="small")

        for idx, row in enumerate(rows[offset:offset + 3]):
            with cols[idx]:
                symbol = str(row.get("Symbol", "N/A"))
                state = str(row.get("State", "N/A"))
                action_raw = str(row.get("Action Raw", row.get("Action", ""))).upper().strip()
                action = action_badge(action_raw)
                pnl = str(row.get("Unrealized P&L", "$0.00"))
                pnl_pct = str(row.get("P&L %", "0.00%"))
                health = str(row.get("Health", "N/A"))
                tone = position_summary_tone(action_raw)

                with st.container(border=True):
                    if tone == "risk":
                        st.markdown(f"### 🔴 {symbol}")
                    elif tone == "warning":
                        st.markdown(f"### 🟡 {symbol}")
                    elif tone == "good":
                        st.markdown(f"### 🟢 {symbol}")
                    else:
                        st.markdown(f"### {symbol}")

                    st.markdown(f"**{state}**")
                    st.caption(f"P&L {pnl} · {pnl_pct}")
                    st.caption(f"Health {health}")
                    st.markdown(f"**{action}**")

def prepare_exit_ticket(row: Dict[str, Any]) -> Dict[str, Any]:
    return prepare_position_ticket(row, "FULL_EXIT", 1.0)


def send_position_review_to_journal(symbol: str, row: Dict[str, Any], health: Dict[str, Any]) -> Dict[str, Any]:
    symbol = str(symbol or "").upper().strip()
    execution_id = str(
        row.get("execution_id")
        or row.get("exec_id")
        or row.get("order_id")
        or (st.session_state.get("oms_execution_id_by_symbol", {}) or {}).get(symbol, "")
        or ""
    ).strip()

    note = {
        "timestamp": now_iso(),
        "symbol": symbol,
        "source": "Position_Command_Center_v2_7",
        "execution_id": execution_id,
        "setup_grade": "A" if health["health_score"] >= 75 else "B" if health["health_score"] >= 55 else "C" if health["health_score"] >= 35 else "D",
        "execution_grade": "Review",
        "tag": health["action"],
        "notes": " | ".join(health.get("reasons", [])),
        "position": {
            "side": row.get("side"),
            "qty": row.get("qty"),
            "avg_price": row.get("avg_price"),
            "last_price": row.get("last_price"),
            "unrealized_pnl": row.get("unrealized_pnl"),
            "health_score": health["health_score"],
            "recommended_action": health["action"],
        },
    }
    existing = st.session_state.get("pcc_journal_reviews", [])
    if not isinstance(existing, list):
        existing = []

    if execution_id:
        merged = [note]
        for item in existing:
            if not isinstance(item, dict):
                continue
            item_execution_id = str(item.get("execution_id") or "").strip()
            if item_execution_id == execution_id:
                merged[0] = {**item, **note}
                continue
            merged.append(item)
        st.session_state["pcc_journal_reviews"] = merged[:50]
    else:
        st.session_state["pcc_journal_reviews"] = [note] + existing[:49]

    st.session_state["journal_prefill_note"] = note
    return note


# =========================================================
# PAGE
# =========================================================

def run_page() -> None:
    inject_css()

    gateway, market_obj, oms, portfolio_engine = init_core()
    market = market_snapshot()
    risk = risk_snapshot()
    positions, position_source = pull_positions(gateway=gateway, portfolio_engine=portfolio_engine)
    ledger = pull_ledger(portfolio_engine)
    pos_df = build_position_rows(positions, market)
    exit_df = build_exit_watchlist(pos_df)
    ranking_df = build_position_ranking(pos_df)
    alignment_df = build_scanner_alignment(positions, market)
    heat = portfolio_heat(positions, risk)
    exposure = exposure_snapshot(positions, risk)
    report = build_commander_report(positions, pos_df, exit_df, heat, market, exposure)
    realized_pnl = total_realized_pnl(positions, ledger)
    winner_symbol, winner_pnl, loser_symbol, loser_pnl = largest_winner_loser(positions)
    sector_df = build_sector_exposure(positions)
    position_ledger_df = build_position_ledger_df(positions, pos_df)
    closed_archive_df = build_closed_trades_archive(ledger)
    risk_alerts = build_risk_alerts(report, heat, exposure, alignment_df)

    total_positions = len(positions)
    total_market_value = sum(abs(safe_float(row.get("position_value"), 0.0)) for row in positions.values())
    total_cost_basis = sum(abs(safe_float(row.get("cost_basis"), 0.0)) for row in positions.values())
    total_open_pnl = sum(safe_float(row.get("unrealized_pnl"), 0.0) for row in positions.values())
    total_daily_pnl = sum(safe_float(row.get("unrealized_pnl"), 0.0) for row in positions.values())
    winning_positions = sum(1 for row in positions.values() if safe_float(row.get("unrealized_pnl"), 0.0) > 0)
    losing_positions = sum(1 for row in positions.values() if safe_float(row.get("unrealized_pnl"), 0.0) < 0)
    largest_position = exposure.get("largest_symbol", "—")
    average_position = total_market_value / total_positions if total_positions else 0.0
    risk_score = safe_float(heat.get("heat"), 0.0)
    total_income = realized_pnl
    stop_distance = 0.0
    action_source = "Action Raw" if not pos_df.empty and "Action Raw" in pos_df.columns else "Action"
    actions = pos_df[action_source].value_counts().to_dict() if not pos_df.empty and action_source in pos_df.columns else {}
    health_values = [parse_health_score(x) for x in pos_df["Health"]] if not pos_df.empty and "Health" in pos_df.columns else []
    avg_health = sum(health_values) / max(len(health_values), 1) if health_values else 0
    winners = sum(1 for row in positions.values() if safe_float(row.get("unrealized_pnl"), 0.0) > 0) if positions else 0
    losers = sum(1 for row in positions.values() if safe_float(row.get("unrealized_pnl"), 0.0) < 0) if positions else 0
    winner_symbol, winner_pnl, loser_symbol, loser_pnl = largest_winner_loser(positions)

    st.title("🎯 Position Command Center")
    st.caption(
        "Institutional position management, exposure monitoring, scanner alignment, and OMS preparation. Advisory only."
    )

    st.markdown(
        """
        <div class="pcc-flow">
            <strong>Workflow:</strong><br>
            Opportunity Center → Scanner → Research Stock → Trade Command Center → OMS Execution → Position Command Center → Journal Review
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("ℹ️ How to use Position Command Center", expanded=False):
        st.markdown(
            """
            1. Read the Commander Report first. It tells you whether the book is healthy, selective, or defensive.
            2. Use the KPI strip for status, exposure, open P&L, realized P&L, risk utilization, and average health.
            3. Use Quick OMS Actions beside the intelligence layer when a position needs trim, stop adjustment, or exit preparation.
            4. Review Exposure Monitor for concentration and sector risk.
            5. Use the tabs to inspect open positions, risk alignment, ledger rows, and closed trades without long vertical scrolling.
            6. Send position reviews to Journal when a management decision is made.
            """
        )

    nav1, nav2, nav3, nav4 = st.columns(4)
    with nav1:
        if st.button("OMS Execution", width="stretch", key="pcc_nav_oms"):
            st.session_state["jfbp_main_navigation"] = "OMS Execution"
            st.rerun()
    with nav2:
        if st.button("Trade Command Center", width="stretch", key="pcc_nav_tcc"):
            st.session_state["jfbp_main_navigation"] = "Trade Command Center"
            st.rerun()
    with nav3:
        if st.button("Journal", width="stretch", key="pcc_nav_journal"):
            st.session_state["jfbp_main_navigation"] = "Journal"
            st.rerun()
    with nav4:
        if st.button("Refresh Position Center", width="stretch", key="pcc_refresh"):
            st.rerun()

    selected_symbol = st.selectbox("Select position", options=sorted(positions.keys()) if positions else ["No positions"], key="pcc_selected_symbol")
    selected_row = positions.get(selected_symbol, {}) if positions else {}
    selected_scanner = scanner_lookup().get(selected_symbol, {}) if selected_row else {}
    selected_health = score_position(selected_row, market, selected_scanner) if selected_row else {}

    last_price = safe_float(selected_row.get("last_price"), 0.0)
    stop_price = safe_float(selected_health.get("stop"), 0.0)
    target_price = safe_float(selected_health.get("target"), 0.0)
    selected_value = abs(safe_float(selected_row.get("position_value"), 0.0))
    gross_exposure = max(safe_float(exposure.get("gross_exposure"), 0.0), 1.0)
    portfolio_impact_pct = (selected_value / gross_exposure) * 100.0 if selected_value > 0 else 0.0

    if last_price:
        stop_distance = ((last_price - stop_price) / last_price) * 100.0
        reward_risk = ((target_price - last_price) / max(abs(last_price - stop_price), 1.0)) * 100.0
    else:
        stop_distance = 0.0
        reward_risk = 0.0

    def professional_text(value: Any, fallback: str = "Not Available") -> str:
        text = str(value or "").strip()
        if text.upper() in {"", "N/A", "NA", "NONE", "NULL", "UNKNOWN", "-", "—"}:
            return fallback
        return text

    score_value = safe_float(selected_health.get("health_score"), 0.0)
    if score_value >= 78:
        conviction_text = "High"
    elif score_value >= 55:
        conviction_text = "Medium"
    else:
        conviction_text = "Low"

    risk_level = professional_text(selected_health.get("health_label"), "Not Available")
    current_action = str(selected_health.get("action", "HOLD")).upper().strip()
    status_display_map = {
        "HOLD": "Hold",
        "TRIM": "Trim",
        "TIGHTEN STOP": "Tighten Stop",
        "EXIT": "Exit",
    }
    status_display = status_display_map.get(current_action, professional_text(current_action, "Pending"))

    if current_action == "EXIT":
        decision_summary = "Reduce / Exit"
        decision_style = "exit"
    elif current_action == "TRIM":
        decision_summary = "Reduce Risk"
        decision_style = "tighten"
    elif current_action == "TIGHTEN STOP":
        decision_summary = "Tighten Stop / Reduce Risk"
        decision_style = "tighten"
    elif score_value >= 85 and str(market.get("regime", "")).upper().strip() in {"RISK_ON", "RISK-ON"}:
        decision_summary = "Increase Position"
        decision_style = "add"
    else:
        decision_summary = "Hold Existing Position"
        decision_style = "hold"

    if decision_style == "hold":
        recommendation_color = "#15803d"
        recommendation_bg = "#ecfdf3"
        recommendation_border = "#86efac"
    elif decision_style == "add":
        recommendation_color = "#1d4ed8"
        recommendation_bg = "#eff6ff"
        recommendation_border = "#93c5fd"
    elif decision_style == "tighten":
        recommendation_color = "#b45309"
        recommendation_bg = "#fffbeb"
        recommendation_border = "#fcd34d"
    else:
        recommendation_color = "#b91c1c"
        recommendation_bg = "#fef2f2"
        recommendation_border = "#fca5a5"

    if decision_style in {"hold", "add"}:
        oms_bg = "#2563eb"
        oms_bg_hover = "#1d4ed8"
        oms_border = "#1e40af"
        oms_text = "#ffffff"
    elif decision_style == "tighten":
        oms_bg = "#f59e0b"
        oms_bg_hover = "#d97706"
        oms_border = "#b45309"
        oms_text = "#111827"
    else:
        oms_bg = "#dc2626"
        oms_bg_hover = "#b91c1c"
        oms_border = "#991b1b"
        oms_text = "#ffffff"

    trend_display = professional_text(selected_scanner.get("trend", market.get("regime")), "Awaiting Confirmation")
    rs_display = (
        f"{safe_float(selected_scanner.get('rs_score'), 0.0):.2f}"
        if selected_scanner and str(selected_scanner.get("rs_score", "")).strip() not in {"", "N/A", "UNKNOWN"}
        else "Pending"
    )
    technical_display = professional_text(selected_health.get("health_label"), "Not Available")

    why_items = [str(item).strip() for item in selected_health.get("reasons", []) if str(item).strip()][:3]
    if not why_items:
        why_items = [
            "Primary trend and posture remain within current risk tolerance.",
            "No critical distribution signal in the current model state.",
            "Position remains in monitored institutional health range.",
        ]

    sector_value = professional_text(selected_row.get("sector"), "Not Available")
    sector_pct = 0.0
    if not sector_df.empty and "Sector" in sector_df.columns and "Exposure %" in sector_df.columns:
        match = sector_df[sector_df["Sector"].astype(str) == sector_value]
        if not match.empty:
            sector_pct = safe_float(match.iloc[0].get("Exposure %"), 0.0)

    if sector_pct >= 35:
        correlation_risk = "High"
        correlation_detail = f"{sector_value} concentration {sector_pct:.1f}%"
        correlation_tone = "risk"
    elif sector_pct >= 20:
        correlation_risk = "Medium"
        correlation_detail = f"{sector_value} concentration {sector_pct:.1f}%"
        correlation_tone = "warning"
    else:
        correlation_risk = "Low"
        correlation_detail = f"{sector_value} concentration {sector_pct:.1f}%"
        correlation_tone = "good"

    if selected_row:
        section_open("1) Position Brief", "One-glance institutional read for today's position decision.")
        st.markdown(
            f"""
            <div class="pcc-hero" style="background:#f8fafc;border-color:#dbe3ef;">
                <div class="pcc-hero-kicker">Institutional Position Brief</div>
                <div class="pcc-hero-title">Position: {html.escape(selected_symbol)}</div>
                <div class="pcc-hero-badges">
                    <div class="pcc-pill pcc-pill-status"><span class="pcc-pill-label">Status</span><span class="pcc-pill-value">{html.escape(status_display)}</span></div>
                    <div class="pcc-pill pcc-pill-conviction"><span class="pcc-pill-label">Conviction</span><span class="pcc-pill-value">{html.escape(conviction_text)}</span></div>
                    <div class="pcc-pill pcc-pill-risk"><span class="pcc-pill-label">Risk</span><span class="pcc-pill-value">{html.escape(risk_level)}</span></div>
                </div>
                <div class="pcc-hero-action">Action: {html.escape(decision_summary)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        section_close()

        section_open("2) Position Health", "Decision cards replacing raw metric walls.")
        render_card_grid([
            {"title": "Trend", "value": trend_display, "detail": "Directional posture", "tone": "info"},
            {"title": "Momentum", "value": fmt_pct(selected_health.get("pnl_pct", 0.0)), "detail": "Open P&L momentum", "tone": pnl_tone(selected_health.get("pnl_pct", 0.0))},
            {"title": "Relative Strength", "value": rs_display, "detail": "Scanner relative strength", "tone": "info"},
            {"title": "Institutional Score", "value": health_badge(score_value), "detail": "Health engine output", "tone": position_summary_tone(current_action)},
            {"title": "Risk Level", "value": risk_level, "detail": "Current model risk posture", "tone": selected_health.get("tone", "warning")},
            {"title": "Technical Condition", "value": technical_display, "detail": f"Action bias: {status_display}", "tone": selected_health.get("tone", "info")},
        ], compact=True)
        section_close()

        section_open("3) Decision Summary")
        st.markdown(
            f"""
            <div style="text-align:center; padding:0.9rem 0.6rem; border:1px solid {recommendation_border}; border-radius:14px; background:{recommendation_bg};">
                <div class="pcc-label">Today's Recommendation</div>
                <div style="font-size:clamp(1.45rem, 2.8vw, 2.1rem); font-weight:900; color:{recommendation_color}; line-height:1.15;">
                    {html.escape(decision_summary)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        section_close()

        section_open("4) Why?", "Concise institutional rationale.")
        for item in why_items:
            st.markdown(f"- {item}")
        section_close()

        section_open("5) Risk Dashboard", "Executive risk report for position-level impact.")
        render_card_grid([
            {"title": "Position Size", "value": f"{safe_float(selected_row.get('qty'), 0.0):,.2f}", "detail": f"Market value {fmt_money(selected_value)}", "tone": "info"},
            {"title": "Portfolio Impact", "value": f"{portfolio_impact_pct:.1f}%", "detail": "Share of gross exposure", "tone": "warning" if portfolio_impact_pct >= 20 else "good"},
            {"title": "Stop Distance", "value": fmt_pct(stop_distance), "detail": f"Stop {fmt_money(stop_price)} from last {fmt_money(last_price)}", "tone": "warning"},
            {"title": "Drawdown Risk", "value": fmt_pct(min(0.0, selected_health.get('pnl_pct', 0.0))), "detail": "Current unrealized drawdown", "tone": "risk" if selected_health.get("pnl_pct", 0.0) < 0 else "good"},
            {"title": "Correlation Risk", "value": correlation_risk, "detail": correlation_detail, "tone": correlation_tone},
        ], compact=True)
        section_close()

        section_open("6) Execution Plan", "Action plan and OMS handoff tools.")
        if current_action == "HOLD":
            st.info("No action required. Continue monitoring. Review after next earnings.")
        elif current_action == "TRIM":
            st.warning(f"Reduce exposure in stages. Suggested trims: 25% then 50% if weakness persists. Modeled stop {fmt_money(stop_price)}.")
        elif current_action == "TIGHTEN STOP":
            st.warning(f"Hold position with tighter risk. Move stop toward breakeven. Current modeled stop {fmt_money(stop_price)}.")
        else:
            st.error(f"Reduce risk decisively. Full exit candidate if price loses stop area near {fmt_money(stop_price)}.")

        render_mini_grid([
            ("Entry Zone", fmt_money(selected_row.get("avg_price"))),
            ("Scaling Plan", "25% / 50% trims"),
            ("Stop", fmt_money(stop_price)),
            ("Target", fmt_money(target_price)),
        ])

        st.markdown(
            f"""
            <style>
            .st-key-pcc_open_oms button {{
                background:{oms_bg} !important;
                color:{oms_text} !important;
                border:1px solid {oms_border} !important;
            }}
            .st-key-pcc_open_oms button:hover {{
                background:{oms_bg_hover} !important;
                color:{oms_text} !important;
                border-color:{oms_border} !important;
            }}
            .st-key-pcc_prepare_exit button {{
                background:#b91c1c !important;
                color:#ffffff !important;
                border:1px solid #991b1b !important;
            }}
            .st-key-pcc_prepare_exit button:hover {{
                background:#991b1b !important;
                color:#ffffff !important;
                border-color:#7f1d1d !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        exec_left, exec_right = st.columns(2)
        with exec_left:
            if st.button("Open OMS With Prepared Ticket", width="stretch", disabled=not bool(selected_row), key="pcc_open_oms", type="primary"):
                if selected_row:
                    prepare_position_ticket(selected_row, "FULL_EXIT", 1.0)
                st.session_state["jfbp_main_navigation"] = "OMS Execution"
                st.rerun()
        with exec_right:
            if st.button("Send Review to Journal", width="stretch", disabled=not bool(selected_row), key="pcc_send_journal"):
                note = send_position_review_to_journal(selected_symbol, selected_row, selected_health)
                st.success(f"Position review note prepared for {selected_symbol}.")
                st.json(note)

        st.markdown("**Risk Reduction Actions**")
        rr1, rr2, rr3 = st.columns(3)
        with rr1:
            if st.button("🟡 Trim 25%", width="stretch", disabled=not bool(selected_row), key="pcc_trim_25"):
                ticket = prepare_position_ticket(selected_row, "TRIM_25", 0.25)
                st.success(f"Prepared 25% trim ticket for {ticket.get('symbol')}.")
        with rr2:
            if st.button("🟡 Trim 50%", width="stretch", disabled=not bool(selected_row), key="pcc_trim_50"):
                ticket = prepare_position_ticket(selected_row, "TRIM_50", 0.50)
                st.success(f"Prepared 50% trim ticket for {ticket.get('symbol')}.")
        with rr3:
            if st.button("🔴 Prepare Full Exit", width="stretch", disabled=not bool(selected_row), key="pcc_prepare_exit", type="primary"):
                ticket = prepare_position_ticket(selected_row, "FULL_EXIT", 1.0)
                st.success(f"Prepared full exit ticket for {ticket.get('symbol')}.")

        st.markdown("**Stop / Profit Management**")
        sp1, sp2, sp3 = st.columns(3)
        with sp1:
            if st.button("🟢 Move Stop to Breakeven", width="stretch", disabled=not bool(selected_row), key="pcc_stop_be"):
                ticket = prepare_position_ticket(selected_row, "STOP_BREAKEVEN", 1.0)
                st.success(f"Prepared breakeven stop ticket for {ticket.get('symbol')}.")
        with sp2:
            if st.button("🟢 Lock Profit", width="stretch", disabled=not bool(selected_row), key="pcc_lock_profit"):
                ticket = prepare_position_ticket(selected_row, "LOCK_PROFIT", 1.0)
                st.success(f"Prepared profit-lock stop ticket for {ticket.get('symbol')}.")
        with sp3:
            if st.button("🟢 Hold", width="stretch", disabled=not bool(selected_row), key="pcc_hold"):
                st.info("Hold selected position. No routing action was changed.")

        render_exit_rules_checklist(selected_health.get("reasons", ["No rule text available."]))
        section_close()
    else:
        st.info("No positions available for position-level workflow. Review commander diagnostics below.")

    st.subheader("7) Supporting Evidence")
    st.caption("Secondary analytics are collapsed for a cleaner morning decision flow.")

    with st.expander("▼ Trend Details", expanded=False):
        render_commander_report(report, market, heat, exposure)

    with st.expander("▼ Momentum Details", expanded=False):
        render_card_grid([
            {"title": "Open P&L", "value": fmt_money(total_open_pnl), "detail": "Current unrealized position P&L", "tone": pnl_tone(total_open_pnl)},
            {"title": "Realized P&L", "value": fmt_money(realized_pnl), "detail": "Engine/ledger realized", "tone": pnl_tone(realized_pnl)},
            {"title": "Avg Health", "value": health_badge(avg_health), "detail": "Book health momentum", "tone": "good" if avg_health >= 80 else "warning" if avg_health >= 40 else "risk"},
        ])

    with st.expander("▼ Volume", expanded=False):
        if pos_df.empty:
            st.info("No open positions detected.")
        else:
            display_pos_df = pos_df.drop(columns=["Action Raw"], errors="ignore")
            st.dataframe(display_pos_df, width="stretch", hide_index=True, height=360)
            render_mobile_position_cards(display_pos_df)

    with st.expander("▼ Relative Strength", expanded=False):
        if alignment_df.empty:
            st.info("No scanner alignment available. Run Scanner first to populate current signals.")
        else:
            conflicts = alignment_df[alignment_df["Alignment"].astype(str).str.contains("Conflict|Risk", case=False, regex=True)]
            if not conflicts.empty:
                conflict_symbols = ", ".join(conflicts["Symbol"].astype(str).head(5).tolist()) if "Symbol" in conflicts.columns else "review list"
                st.error(f"Scanner conflict / position risk detected: {conflict_symbols}.")
            st.dataframe(alignment_df, width="stretch", hide_index=True, height=320)

    with st.expander("▼ Institutional Signals", expanded=False):
        for title, detail in risk_alerts:
            if title.startswith("🔴"):
                st.error(f"**{title}**\n\n{detail}")
            elif title.startswith("🟡"):
                st.warning(f"**{title}**\n\n{detail}")
            else:
                st.success(f"**{title}**\n\n{detail}")

    with st.expander("▼ Statistics", expanded=False):
        stat_tab_ledger, stat_tab_archive, stat_tab_diag = st.tabs(["Ledger", "Trade Archive", "Diagnostics"])
        with stat_tab_ledger:
            if position_ledger_df.empty:
                st.info("No open position ledger rows available.")
            else:
                st.dataframe(position_ledger_df, width="stretch", hide_index=True, height=360)
        with stat_tab_archive:
            if closed_archive_df.empty:
                st.info("No closed-trade archive rows found in the current ledger yet.")
            else:
                st.dataframe(closed_archive_df, width="stretch", hide_index=True, height=360)
        with stat_tab_diag:
            st.write({
                "Version": "Frozen Build",
                "Updated": now_iso(),
                "Position Source": position_source,
                "Positions": positions,
                "Market Snapshot": market,
                "Risk Snapshot": risk,
                "Portfolio Heat": heat,
                "Exposure Snapshot": exposure,
                "Commander Report": report,
                "Scanner Alignment": alignment_df.to_dict("records") if not alignment_df.empty else [],
                "Position Ranking": ranking_df.to_dict("records") if not ranking_df.empty else [],
                "Prepared Exit Ticket": st.session_state.get("pcc_prepared_exit_ticket", {}),
                "Journal Prefill Note": st.session_state.get("journal_prefill_note", {}),
                "Realized PnL": realized_pnl,
                "Sector Exposure": sector_df.to_dict("records") if not sector_df.empty else [],
                "Risk Alerts": risk_alerts,
            })

def page() -> None:
    run_page()
