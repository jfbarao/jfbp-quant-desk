# 🚧 BUILD MARKER: TLP-0701-A
# =========================================================
# 🎯 OPPORTUNITY CENTER
# JFBP Quant Desk
# Morning Command Center for Stocks + Crypto + Forex + Gold + Oil
# Reads Market Pulse exports, Pulse Signal Bus, Scanner state,
# and Quant Executor / OMS session state.
# =========================================================

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

try:
    from options_engine.trade_lifecycle_packet import TradeLifecyclePacket, TradeStage
except Exception:
    TradeLifecyclePacket = None
    TradeStage = None

from core.responsive import inject_responsive_css
from core.ui_cards import inject_card_css

try:
    from pages.SaaS_Core import remember_active_page
except Exception:
    def remember_active_page(page_name: str):
        return None


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
    number = safe_float(value, None)
    if number is None:
        return "N/A"
    return f"{number:.1f}"


def fmt_multiplier(value: Any) -> str:
    return f"{safe_float(value, 1.0):.2f}x"


def grade_from_score(score: Any) -> str:
    s = safe_float(score, 0.0)
    if s >= 90:
        return "A"
    if s >= 80:
        return "B"
    if s >= 70:
        return "C"
    if s >= 60:
        return "D"
    return "F"


def short_time(value: Any) -> str:
    if not value:
        return "Not published"
    text = str(value)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return text[:19]


def minutes_old(value: Any) -> float | None:
    """Return age in minutes for ISO timestamps, or None when unavailable."""

    if not value:
        return None

    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 60.0)
    except Exception:
        return None


def freshness_label(value: Any, stale_after_minutes: int = 30) -> tuple[str, str]:
    age = minutes_old(value)

    if age is None:
        return "Not published", "neutral"

    if age <= stale_after_minutes:
        return f"Fresh · {int(age)} min old", "good"

    if age <= stale_after_minutes * 3:
        return f"Aging · {int(age)} min old", "warning"

    return f"Stale · {int(age)} min old", "risk"


def pulse_allowed_reason(row: Dict[str, Any]) -> str:
    regime = str(row.get("regime", "UNKNOWN")).upper().strip()
    stress = safe_float(row.get("stress_score"), 0.0)
    breadth = safe_float(row.get("breadth_score"), 50.0)
    allowed = bool(row.get("trade_allowed", True))

    if allowed:
        if regime in {"SELECTIVE", "CAUTIOUS"}:
            return "Allowed with selectivity"
        return "Allowed"

    if stress >= 70:
        return "Blocked due to elevated stress"
    if breadth < 30:
        return "Blocked due to weak breadth"
    if "BREAKDOWN" in regime or "RISK-OFF" in regime or regime == "RISK_OFF":
        return "Blocked by regime"
    return "Blocked"


def navigate_to(page_key: str) -> None:
    st.session_state["jfbp_main_navigation"] = page_key
    try:
        remember_active_page(page_key)
    except Exception:
        pass
    st.rerun()


def quick_action_buttons() -> None:
    st.caption("Quick actions")
    cols = st.columns(6)
    actions = [
        ("Market Pulse", "Market Pulse"),
        ("Scanner", "Scanner"),
        ("Crypto", "Crypto Pulse"),
        ("Forex", "Forex Pulse"),
        ("Gold", "Gold Pulse"),
        ("Oil", "Oil Pulse"),
    ]

    for col, (label, page_key) in zip(cols, actions):
        with col:
            if st.button(label, width="stretch", key=f"oc_go_{page_key}"):
                navigate_to(page_key)


def freshness_panel() -> None:
    bus = get_bus()
    stale_items = []
    missing_items = []

    for asset_key, label in [
        ("crypto", "Crypto"),
        ("forex", "Forex"),
        ("gold", "Gold"),
        ("oil", "Oil"),
    ]:
        row = bus.get(asset_key, {})
        if not isinstance(row, dict) or not row:
            missing_items.append(label)
            continue

        label_text, tone = freshness_label(row.get("timestamp"))
        if tone == "risk":
            stale_items.append(f"{label}: {label_text}")

    if stale_items:
        st.warning("Freshness warning: " + "; ".join(stale_items) + ". Refresh the related Pulse page before relying on the reading.")
    elif missing_items:
        st.info("Pulse context not loaded yet for: " + ", ".join(missing_items) + ". Open those Pulse pages only if you want that asset class included.")


def tone_for_regime(regime: Any) -> str:
    key = str(regime or "").upper().strip()

    if key in {
        "RISK_ON",
        "RISK-ON",
        "ALTCOIN RISK-ON",
        "CARRY RISK-ON",
        "GOLD BREAKOUT",
        "MINERS CONFIRMING",
        "ENERGY EXPANSION",
        "ENERGY CONFIRMATION",
        "SUPPLY SHOCK BID",
    }:
        return "good"

    if key in {
        "SELECTIVE",
        "CAUTIOUS",
        "NEUTRAL",
        "USD TREND",
        "MACRO MIXED",
    }:
        return "warning"

    if key in {
        "DEFENSIVE",
        "RISK_OFF",
        "RISK-OFF",
        "GOLD BREAKDOWN",
        "ENERGY BREAKDOWN",
        "CONTRACTION",
        "DEMAND SHOCK",
        "OIL CORRECTION",
    }:
        return "risk"

    return "neutral"


def tone_for_score(score: Any, inverse: bool = False) -> str:
    number = safe_float(score, 0.0)

    if inverse:
        if number >= 65:
            return "risk"
        if number >= 35:
            return "warning"
        return "good"

    if number >= 70:
        return "good"
    if number >= 40:
        return "warning"
    return "risk"


def tone_palette(tone: str) -> tuple[str, str, str]:
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
        "dark": ("#111827", "#334155", "#ffffff"),
    }
    return palette.get(str(tone), palette["neutral"])


def opportunity_grade(score: Any, rating: Any = "", signal: Any = "") -> tuple[str, str, str]:
    """Quality of the opportunity, independent from final execution readiness."""
    s = safe_float(score, 0.0)
    r = str(rating or "").upper().strip()
    sig = str(signal or "").upper().strip()

    if sig in {"AVOID", "STRONG SELL"}:
        return "🔴 AVOID", "risk", "Opportunity quality is weak or adverse."
    if s >= 85 or (s >= 75 and r in {"A+", "A", "A-"}):
        return "🟢 TRADEABLE", "good", "High-quality candidate worth considering."
    if s >= 60:
        return "🟡 PENDING CONFIRMATION", "warning", "Candidate is forming and requires further confirmation before execution."
    return "⚪ WATCHLIST", "neutral", "Watch only until the opportunity improves."


def institutional_grade(status: Any, score: Any = 0, executable: bool = False, blocked: bool = False) -> tuple[str, str, str]:
    """Execution readiness after institutional-style risk and process gates."""
    status_text = str(status or "").upper().strip()
    s = safe_float(score, 0.0)

    if blocked or "BLOCK" in status_text or "AVOID" in status_text:
        return "🔴 BLOCKED", "risk", "Risk controls do not allow execution."
    if executable or "EXECUTABLE" in status_text or "ALLOWED" in status_text or s >= 80:
        return "🔵 READY", "good", "Execution criteria are sufficiently aligned."
    if s >= 60 or "BUY" in status_text or "WATCH" in status_text or "PENDING CONFIRMATION" in status_text or "INFERRED" in status_text:
        return "🟡 PENDING CONFIRMATION", "warning", "Opportunity exists, but full institutional confirmation is not complete."
    return "⚪ STAND BY", "neutral", "Insufficient confirmation for deployment."


def grade_explainer() -> str:
    return (
        "**JFBP Quant Desk protects capital first and pursues opportunity second.** "
        "A symbol can be a strong opportunity while still not meeting full institutional execution standards. "
        "**Opportunity Grade** answers: *Is this worth considering?* "
        "**Institutional Grade** answers: *Is it ready for capital deployment?*"
    )


def inject_css() -> None:
    inject_responsive_css(max_width=1500)
    inject_card_css()
    st.markdown(
        """
        <style>
            div[data-testid="stDataFrame"] {
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.85rem;
                align-items: stretch;
            }

            div[data-testid="stHorizontalBlock"] > div {
                min-width: 0 !important;
            }

            .oc-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
                gap: 0.65rem;
                margin: 0.35rem 0 0.65rem 0;
                width: 100%;
            }

            .oc-card {
                border: 1px solid;
                border-radius: 14px;
                padding: 0.72rem 0.82rem;
                min-width: 0;
                min-height: 124px;
                box-sizing: border-box;
                overflow: hidden;
                background: #ffffff;
                box-shadow: none;
            }

            .oc-card-title {
                font-size: var(--jfbp-type-card-label);
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #64748b;
                margin-bottom: 0.28rem;
                line-height: 1.25;
            }

            .oc-card-value {
                font-size: var(--jfbp-type-card-value);
                font-weight: 850;
                line-height: 1.15;
                margin-bottom: 0.30rem;
                overflow-wrap: normal;
                word-break: normal;
                white-space: normal;
            }

            .oc-card-detail {
                color: #64748b;
                font-size: var(--jfbp-type-caption);
                margin-top: 0.35rem;
                line-height: 1.35;
                overflow-wrap: normal;
                word-break: normal;
                white-space: normal;
            }

            .oc-mini-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr));
                gap: 0.65rem;
                margin: 0.35rem 0 0.65rem 0;
            }

            .oc-mini {
                background: #f8fafc;
                border: 1px solid #dbe3ef;
                border-radius: 14px;
                padding: 0.72rem 0.82rem;
            }

            .oc-mini-label {
                font-size: var(--jfbp-type-card-label);
                font-weight: 800;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                margin-bottom: 0.28rem;
                line-height: 1.25;
            }

            .oc-mini-value {
                font-size: var(--jfbp-type-card-value);
                font-weight: 850;
                color: #111827;
                overflow-wrap: normal;
                word-break: normal;
            }

            .oc-table-wrap {
                width: 100%;
                max-width: 100%;
                max-height: 390px;
                overflow: auto;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                background: #ffffff;
                margin: 0.35rem 0 1.4rem 0;
                position: relative;
                z-index: 1;
                box-sizing: border-box;
            }

            .oc-rank-table {
                width: 100%;
                min-width: 1120px;
                border-collapse: collapse;
                table-layout: fixed;
                font-size: 0.92rem;
            }

            .oc-rank-table th {
                position: sticky;
                top: 0;
                z-index: 2;
                background: #f8fafc;
                color: #64748b;
                font-weight: 850;
                text-align: left;
                border-bottom: 1px solid #e5e7eb;
                padding: 0.72rem 0.70rem;
                white-space: nowrap;
            }

            .oc-rank-table td {
                border-bottom: 1px solid #eef2f7;
                color: #1f2937;
                padding: 0.62rem 0.70rem;
                vertical-align: middle;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .oc-rank-table tr:last-child td {
                border-bottom: none;
            }

            .oc-rank-col-rank { width: 58px; }
            .oc-rank-col-asset { width: 105px; }
            .oc-rank-col-opportunity { width: 190px; }
            .oc-rank-col-setup { width: 175px; }
            .oc-rank-col-score { width: 70px; text-align: right; }
            .oc-rank-col-status { width: 130px; }
            .oc-rank-col-opportunity-grade { width: 150px; }
            .oc-rank-col-institutional-grade { width: 165px; }
            .oc-rank-col-reason { width: 300px; }
            .oc-rank-col-size { width: 80px; text-align: right; }
            .oc-rank-col-handoff { width: 135px; }

            @media (max-width: 760px) {
                .oc-rank-table {
                    min-width: 860px;
                    font-size: 0.86rem;
                }
            }


            .oc-hero {
                border: 1px solid;
                border-radius: 18px;
                padding: 0.88rem 0.92rem;
                margin: 0.60rem 0 0.82rem 0;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
            }

            .oc-hero-kicker {
                font-size: var(--jfbp-type-card-label);
                font-weight: 850;
                letter-spacing: 0.055em;
                text-transform: uppercase;
                color: #64748b;
                margin-bottom: 0.24rem;
            }

            .oc-hero-title {
                font-size: clamp(1.22rem, 2.35vw, 1.62rem);
                font-weight: 880;
                line-height: 1.14;
                margin: 0 0 0.30rem 0;
                overflow-wrap: normal;
                word-break: normal;
            }

            .oc-hero-text {
                font-size: var(--jfbp-type-body);
                font-weight: 700;
                color: #334155;
                line-height: 1.38;
                margin-bottom: 0.36rem;
                overflow-wrap: normal;
                word-break: normal;
            }

            .oc-hero-action {
                border-radius: 12px;
                padding: 0.60rem 0.78rem;
                background: rgba(255,255,255,0.76);
                border: 1px solid rgba(148,163,184,0.35);
                font-size: var(--jfbp-type-body);
                font-weight: 820;
                color: #111827;
                overflow-wrap: normal;
                word-break: normal;
            }

            @media (max-width: 1180px) {
                .block-container {
                    max-width: 100% !important;
                    padding-left: 1.35rem !important;
                    padding-right: 1.35rem !important;
                }

                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                }

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

                .oc-grid,
                .oc-mini-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def card_html(title: str, value: Any, detail: str = "", tone: str = "neutral") -> str:
    """Return a compact HTML card.

    Important: keep HTML left-aligned with no leading indentation.
    Streamlit/Markdown can treat indented HTML as a code block and print it
    instead of rendering it.
    """
    bg, border, color = tone_palette(tone)
    title_text = html.escape(str(title))
    value_text = html.escape(str(value))
    detail_text = html.escape(str(detail))
    return (
        f'<div class="oc-card" style="background:{bg};border-color:{border};">'
        f'<div class="oc-card-title">{title_text}</div>'
        f'<div class="oc-card-value" style="color:{color};">{value_text}</div>'
        f'<div class="oc-card-detail">{detail_text}</div>'
        f'</div>'
    )


def render_card_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="oc-grid">']
    for card in cards:
        pieces.append(
            card_html(
                card.get("title", ""),
                card.get("value", ""),
                card.get("detail", ""),
                card.get("tone", "neutral"),
            )
        )
    pieces.append("</div>")
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_mini_grid(items: List[tuple[str, Any]]) -> None:
    pieces = ['<div class="oc-mini-grid">']
    for label, value in items:
        label_text = html.escape(str(label))
        value_text = html.escape(str(value))
        pieces.append(
            f'<div class="oc-mini">'
            f'<div class="oc-mini-label">{label_text}</div>'
            f'<div class="oc-mini-value">{value_text}</div>'
            f'</div>'
        )
    pieces.append("</div>")
    st.markdown("".join(pieces), unsafe_allow_html=True)


def get_bus() -> Dict[str, Dict[str, Any]]:
    bus = st.session_state.get("multi_asset_signal_bus", {})
    return bus if isinstance(bus, dict) else {}


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
        "event": st.session_state.get("market_reaction_event", "N/A"),
    }


def scanner_snapshot() -> Dict[str, Any]:
    rows = st.session_state.get("scanner_last_raw_signals", [])
    plan = st.session_state.get("scanner_last_risk_plan", [])
    holds = st.session_state.get("scanner_last_hold_rows", [])

    rows = [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    plan = [r for r in plan if isinstance(r, dict)] if isinstance(plan, list) else []
    holds = [r for r in holds if isinstance(r, dict)] if isinstance(holds, list) else []

    best = {}
    if rows:
        best = sorted(
            rows,
            key=lambda r: (
                safe_float(r.get("opportunity_score_pct"), 0.0),
                safe_float(r.get("model_score"), 0.0),
                safe_float(r.get("rs_score"), 0.0),
            ),
            reverse=True,
        )[0]

    executable = len([r for r in plan if bool(r.get("executable"))])
    blocked_shorts = len([r for r in holds if r.get("position_action") == "BLOCKED_OPEN_SHORT"])

    return {
        "status": st.session_state.get("scanner_last_status", "READY"),
        "best_symbol": best.get("display_symbol") or best.get("symbol") or "Run Scanner",
        "best_score": best.get("opportunity_score_pct", "N/A"),
        "best_rating": best.get("overall_rating", "N/A"),
        "best_recommendation": best.get("trade_recommendation", "N/A"),
        "best_sector": best.get("sector", "N/A"),
        "executable": executable,
        "blocked_shorts": blocked_shorts,
        "rows": len(rows),
    }


def executor_snapshot() -> Dict[str, Any]:
    mode = str(st.session_state.get("mode", "SIM")).upper().strip()
    pipeline = st.session_state.get("pipeline")
    risk_engine = st.session_state.get("risk_engine")
    kill = bool(st.session_state.get("risk_kill_switch", False))

    armed_keys = [
        "quant_executor_enabled",
        "automation_executor_enabled",
        "signal_watcher_enabled",
        "live_trading_armed",
        "oms_live_armed",
    ]

    armed = any(bool(st.session_state.get(k, False)) for k in armed_keys)

    risk_state = "UNKNOWN"
    gross_exposure = 0.0
    open_positions = 0
    try:
        if risk_engine and hasattr(risk_engine, "snapshot"):
            snap = risk_engine.snapshot()
            if isinstance(snap, dict):
                risk_state = str(snap.get("risk_state", "UNKNOWN"))
                gross_exposure = safe_float(snap.get("gross_exposure"), 0.0)
                open_positions = safe_int(snap.get("open_positions"), 0)
    except Exception:
        pass

    return {
        "mode": mode,
        "pipeline": "READY" if pipeline else "MISSING",
        "armed": armed,
        "kill_switch": kill,
        "risk_state": risk_state,
        "gross_exposure": gross_exposure,
        "open_positions": open_positions,
    }


def pulse_card(asset_key: str, label: str, icon: str) -> Dict[str, Any]:
    row = get_bus().get(asset_key, {})
    if not isinstance(row, dict) or not row:
        return {
            "title": f"{icon} {label}",
            "value": "Not Loaded",
            "detail": "Open the Pulse page once to publish this asset context.",
            "tone": "neutral",
        }

    best_symbol = row.get("best_symbol") or "N/A"
    best_name = row.get("best_name") or ""
    score = row.get("best_score", "N/A")
    regime = row.get("regime", "UNKNOWN")
    multiplier = fmt_multiplier(row.get("execution_multiplier", 1.0))
    allowed = "Allowed" if bool(row.get("trade_allowed", True)) else "Blocked"
    reason = pulse_allowed_reason(row)
    fresh, fresh_tone = freshness_label(row.get("timestamp"))

    # Determine opportunity quality and final card tone
    score_num = safe_float(score, 0.0)
    opp_label, opp_tone, opp_reason = opportunity_grade(score_num, "", row.get("regime"))

    # Default card tone based on regime, but only promote to 'good' when opportunity is qualified
    if not allowed:
        card_tone = "risk"
    else:
        # If opportunity grade is good (tradeable), show good; if pending, show warning; otherwise neutral
        if opp_tone == "good":
            card_tone = "good"
        elif opp_tone == "warning":
            card_tone = "warning"
        else:
            # Regime may be risk-on but scanner doesn't have a qualified opportunity
            card_tone = "neutral"
    # If freshness is bad, escalate tone to warning when appropriate
    if fresh_tone == "risk" and card_tone != "risk":
        card_tone = "warning"

    # If allowed by regime but not qualified, add concise summary wording
    if allowed and opp_tone != "good":
        extra_detail = "No qualified setup available."
    else:
        extra_detail = ""

    return {
        "title": f"{icon} {label}",
        "value": best_symbol,
        "detail": (
            f"{best_name} | Regime: {regime} | Score: {fmt_score(score_num)} | "
            f"Execution: {allowed} | {reason} | Size: {multiplier} | {fresh} {(' | ' + extra_detail) if extra_detail else ''}"
        ),
        "tone": card_tone,
    }


def pulse_table() -> pd.DataFrame:
    rows = []
    bus = get_bus()

    for asset_key, label in [
        ("crypto", "Crypto"),
        ("forex", "Forex"),
        ("gold", "Gold"),
        ("oil", "Oil"),
    ]:
        row = bus.get(asset_key, {})
        if not isinstance(row, dict) or not row:
            rows.append(
                {
                    "Asset": label,
                    "Regime": "Not loaded",
                    "Stress": "",
                    "Breadth": "",
                    "Best": "",
                    "Score": "",
                    "Execution": "",
                    "Reason": "",
                    "Size": "",
                    "Freshness": "",
                    "Updated": "",
                }
            )
            continue

        rows.append(
            {
                "Asset": label,
                "Regime": row.get("regime", "UNKNOWN"),
                "Stress": row.get("stress_score", ""),
                "Breadth": row.get("breadth_score", ""),
                "Best": row.get("best_symbol", ""),
                "Score": row.get("best_score", ""),
                "Execution": "Allowed" if row.get("trade_allowed", True) else "Blocked",
                "Reason": pulse_allowed_reason(row),
                "Size": fmt_multiplier(row.get("execution_multiplier", 1.0)),
                "Freshness": freshness_label(row.get("timestamp", ""))[0],
                "Updated": short_time(row.get("timestamp", "")),
            }
        )

    return pd.DataFrame(rows)



def options_opportunity_snapshot(scanner: Dict[str, Any]) -> Dict[str, Any]:
    """Return the best options opportunity published by Options Center or infer one from Scanner.

    Options Center v2 can publish a compact session object. If that object does
    not exist yet, this function builds a safe fallback from the current Scanner
    leader so Opportunity Center still has a useful options row.
    """

    published = st.session_state.get("options_best_opportunity", {})

    if isinstance(published, dict) and published:
        symbol = str(
            published.get("symbol")
            or published.get("underlying")
            or published.get("display_symbol")
            or "Options"
        ).upper().strip()

        strategy = str(
            published.get("strategy")
            or published.get("recommended_structure")
            or published.get("structure")
            or "Options Strategy"
        ).strip()

        score = safe_float(
            published.get("score")
            or published.get("options_score")
            or published.get("opportunity_score")
            or 0,
            0.0,
        )

        allowed = bool(published.get("allowed", published.get("trade_allowed", True)))
        reason = str(published.get("reason") or published.get("detail") or "Published by Options Center.")
        timestamp = published.get("timestamp") or published.get("updated")

        return {
            "loaded": True,
            "symbol": symbol,
            "strategy": strategy,
            "display": f"{symbol} {strategy}",
            "score": score,
            "allowed": allowed,
            "status": "Allowed" if allowed else "Blocked",
            "reason": reason,
            "freshness": freshness_label(timestamp)[0] if timestamp else "Session current",
            "tone": "good" if allowed and score >= 70 else "warning" if allowed else "risk",
        }

    best_symbol = str(scanner.get("best_symbol") or "Run Scanner").upper().strip()
    best_score = safe_float(scanner.get("best_score"), 0.0)
    recommendation = str(scanner.get("best_recommendation") or "N/A").upper().strip()
    rating = str(scanner.get("best_rating") or "N/A").upper().strip()

    if not best_symbol or best_symbol == "RUN SCANNER" or best_score <= 0:
        return {
            "loaded": False,
            "symbol": "Not Loaded",
            "strategy": "Open Options Center",
            "display": "Not Loaded",
            "score": 0.0,
            "allowed": False,
            "status": "Not Loaded",
            "reason": "Open Scanner and Options Center to publish the best options setup.",
            "freshness": "Not published",
            "tone": "neutral",
        }

    if recommendation in {"BUY", "STRONG BUY"}:
        strategy = "Bull Call Spread"
    elif recommendation in {"SELL", "STRONG SELL"}:
        strategy = "Bear Put Spread"
    elif best_score >= 65:
        strategy = "Cash-Secured Put"
    else:
        strategy = "No Options Trade"

    options_score = min(100.0, max(0.0, best_score + (8 if rating in {"A+", "A", "A-"} else 0)))
    allowed = strategy != "No Options Trade" and options_score >= 60

    return {
        "loaded": False,
        "symbol": best_symbol,
        "strategy": strategy,
        "display": f"{best_symbol} {strategy}",
        "score": options_score,
        "allowed": allowed,
        "status": "Inferred" if allowed else "PENDING CONFIRMATION",
        "reason": "Inferred from Scanner leader. Open Options Center to confirm structure, strike, volatility, and liquidity.",
        "freshness": "Inferred now",
        "tone": "good" if allowed and options_score >= 80 else "warning" if allowed else "neutral",
    }


def options_card(scanner: Dict[str, Any]) -> Dict[str, Any]:
    row = options_opportunity_snapshot(scanner)

    return {
        "title": "🧩 Options",
        "value": row.get("display", "Not Loaded"),
        "detail": (
            f"Score: {fmt_score(row.get('score'))} | "
            f"Status: {row.get('status')} | "
            f"{row.get('reason')} | {row.get('freshness')}"
        ),
        "tone": row.get("tone", "neutral"),
    }


def scanner_rows() -> List[Dict[str, Any]]:
    rows = st.session_state.get("scanner_last_raw_signals", [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def risk_plan_rows() -> List[Dict[str, Any]]:
    rows = st.session_state.get("scanner_last_risk_plan", [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def row_symbol(row: Dict[str, Any]) -> str:
    return str(row.get("display_symbol") or row.get("symbol") or row.get("underlying") or "").upper().strip()


def normalize_action(value: Any) -> str:
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


def optionable_symbol(symbol: str) -> bool:
    s = str(symbol or "").upper().strip()
    if not s or s in {"RUN SCANNER", "N/A"}:
        return False
    if s.endswith("=X") or s.endswith("=F") or s.endswith("-USD"):
        return False
    if ".TO" in s:
        return False
    return True


def plan_lookup() -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for row in risk_plan_rows():
        symbol = row_symbol(row) or str(row.get("symbol") or "").upper().strip()
        if symbol:
            lookup[symbol] = row
    return lookup


def option_strategy_for_row(row: Dict[str, Any], market: Dict[str, Any]) -> tuple[str, str, bool, str]:
    symbol = row_symbol(row)
    signal = normalize_action(row.get("trade_recommendation") or row.get("scanner_action") or row.get("signal"))
    score = safe_float(row.get("opportunity_score_pct") or row.get("model_score"), 0.0)
    stress = safe_float(market.get("stress_score"), 0.0)
    buy_allowed = bool(market.get("buy_allowed", True))
    regime = str(market.get("regime") or "UNKNOWN").upper().strip()

    if not optionable_symbol(symbol):
        return "No Options", "Not optionable in this options workflow.", False, "neutral"
    if stress >= 70 or not buy_allowed or regime in {"RISK_OFF", "RISK-OFF", "DEFENSIVE"}:
        return "No New Long Premium", "Market filter is defensive.", False, "risk"
    if signal in {"BUY", "STRONG BUY"}:
        return "Bull Call Spread", "Defined-risk bullish options expression.", score >= 60, "good"
    if signal in {"SELL", "STRONG SELL"}:
        return "Bear Put Spread", "Defined-risk bearish options expression.", score >= 60, "risk"
    if signal == "WATCH" and score >= 65:
        return "Cash-Secured Put", "Watchlist income/entry structure; confirm willingness to own shares.", True, "warning"
    return "No Options Trade", "PENDING CONFIRMATION — wait for stronger scanner confirmation.", False, "neutral"
    


def build_global_opportunity_rows(scanner: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build Global Opportunity Ranking rows across stocks, options, crypto, forex, gold, and oil.

    v3.0 uses all available Scanner rows, not just the single Scanner leader.
    It also publishes the ranking to session_state so Trade Command Center,
    Options Center, and OMS handoff can use the same chosen opportunity.
    """

    rows: List[Dict[str, Any]] = []
    market = market_snapshot()
    plans = plan_lookup()

    for source_row in scanner_rows()[:50]:
        symbol = row_symbol(source_row)
        if not symbol:
            continue

        score = safe_float(source_row.get("opportunity_score_pct") or source_row.get("model_score"), 0.0)
        if score <= 0:
            continue

        recommendation = str(source_row.get("trade_recommendation") or source_row.get("scanner_action") or source_row.get("signal") or "WATCH").upper().strip()
        plan = plans.get(symbol, {})
        executable = bool(plan.get("executable")) or str(plan.get("position_action") or "").upper().startswith("OPEN")
        event_label = str(source_row.get("combined_event_risk_label") or source_row.get("earnings_risk_label") or "NONE").upper().strip()
        pulse_asset = str(source_row.get("pulse_asset_class") or "stocks").title()
        rating = source_row.get("overall_rating", "N/A")
        sector = source_row.get("sector", "N/A")

        status = "🟢 Executable" if executable else f"🟡 {recommendation}"
        if recommendation in {"AVOID", "SELL"} and not executable:
            status = f"🔴 {recommendation}" if recommendation == "AVOID" else f"🟡 {recommendation}"
        opp_label, _, _ = opportunity_grade(score, rating, recommendation)
        inst_label, _, _ = institutional_grade(status, score, executable=executable, blocked="🔴" in status)

        rows.append(
            {
                "Asset Class": "Stocks",
                "Symbol": symbol,
                "Opportunity": symbol,
                "Setup": recommendation,
                "Score": round(score, 1),
                "Status": status,
                "Opportunity Grade": opp_label,
                "Institutional Grade": inst_label,
                "Reason": f"{sector} | Rating {rating} | Event risk {event_label}",
                "Size": fmt_multiplier(market.get("execution_multiplier", 1.0)),
                "Handoff": "Trade Command",
                "_symbol": symbol,
                "_page": "Trade Command Center",
            }
        )

        strategy, detail, allowed, tone = option_strategy_for_row(source_row, market)
        if strategy not in {"No Options", "No Options Trade"}:
            option_score = min(100.0, max(0.0, score + (8 if str(rating).upper() in {"A+", "A", "A-"} else 0)))
            opp_label, _, _ = opportunity_grade(option_score, rating, recommendation)
            inst_label, _, _ = institutional_grade("Allowed" if allowed else "Blocked", option_score, executable=allowed, blocked=not allowed)
            rows.append(
                {
                    "Asset Class": "Options",
                    "Symbol": symbol,
                    "Opportunity": f"{symbol} {strategy}",
                    "Setup": strategy,
                    "Score": round(option_score, 1),
                    "Status": "🟢 Allowed" if allowed else "🔴 Blocked",
                    "Opportunity Grade": opp_label,
                    "Institutional Grade": inst_label,
                    "Reason": detail,
                    "Size": fmt_multiplier(1.0),
                    "Handoff": "Options Center",
                    "_symbol": symbol,
                    "_page": "Options Center",
                }
            )

    # Preserve Options Center's explicitly published best setup when available.
    opt = options_opportunity_snapshot(scanner)
    opt_symbol = str(opt.get("symbol") or "").upper().strip()
    if opt.get("display") != "Not Loaded" and safe_float(opt.get("score"), 0.0) > 0:
        opp_label, _, _ = opportunity_grade(opt.get("score"), "", opt.get("strategy"))
        inst_label, _, _ = institutional_grade("Allowed" if opt.get("allowed") else opt.get("status"), opt.get("score"), executable=bool(opt.get("allowed")), blocked=False)
        rows.append(
            {
                "Asset Class": "Options",
                "Symbol": opt_symbol,
                "Opportunity": opt.get("display"),
                "Setup": opt.get("strategy"),
                "Score": round(safe_float(opt.get("score"), 0.0), 1),
                "Status": "🟢 Allowed" if opt.get("allowed") else f"🟡 {opt.get('status')}",
                "Opportunity Grade": opp_label,
                "Institutional Grade": inst_label,
                "Reason": opt.get("reason"),
                "Size": fmt_multiplier(1.0),
                "Handoff": "Options Center",
                "_symbol": opt_symbol,
                "_page": "Options Center",
            }
        )

    for asset_key, label in [
        ("crypto", "Crypto"),
        ("forex", "Forex"),
        ("gold", "Gold"),
        ("oil", "Oil"),
    ]:
        row = get_bus().get(asset_key, {})
        if not isinstance(row, dict) or not row:
            continue

        symbol = str(row.get("best_symbol") or "N/A").upper().strip()
        score = safe_float(row.get("best_score"), 0.0)
        allowed = bool(row.get("trade_allowed", True))
        freshness, fresh_tone = freshness_label(row.get("timestamp"))

        adjusted_score = score
        if not allowed:
            adjusted_score = min(adjusted_score, 49.0)
        elif fresh_tone == "risk":
            adjusted_score = min(adjusted_score, 59.0)

        opp_label, _, _ = opportunity_grade(adjusted_score, "", row.get("regime"))
        inst_label, _, _ = institutional_grade("Allowed" if allowed else "Blocked", adjusted_score, executable=allowed, blocked=not allowed)

        # Only mark Allowed as green when the opportunity grade is actually TRADEABLE
        if allowed:
            if "TRADEABLE" in str(opp_label).upper() or "🟢" in str(opp_label):
                status_text = "🟢 Allowed"
            else:
                status_text = "🟡 Allowed"
        else:
            status_text = "🔴 Blocked"

        rows.append(
            {
                "Asset Class": label,
                "Symbol": symbol,
                "Opportunity": symbol,
                "Setup": row.get("regime", "UNKNOWN"),
                "Score": round(adjusted_score, 1),
                "Status": status_text,
                "Opportunity Grade": opp_label,
                "Institutional Grade": inst_label,
                "Reason": f"{pulse_allowed_reason(row)} | {freshness}",
                "Size": fmt_multiplier(row.get("execution_multiplier", 1.0)),
                "Handoff": f"{label} Pulse",
                "_symbol": symbol,
                "_page": f"{label} Pulse",
            }
        )

    # De-duplicate exact same asset/symbol/setup rows, keeping highest score.
    deduped: Dict[tuple, Dict[str, Any]] = {}
    for row in rows:
        key = (row.get("Asset Class"), row.get("Symbol"), row.get("Setup"))
        if key not in deduped or safe_float(row.get("Score"), 0.0) > safe_float(deduped[key].get("Score"), 0.0):
            deduped[key] = row

    ranked = sorted(
        deduped.values(),
        key=lambda r: (safe_float(r.get("Score"), 0.0), "🟢" in str(r.get("Status", ""))),
        reverse=True,
    )

    for idx, row in enumerate(ranked, start=1):
        row["Rank"] = f"#{idx}"

    st.session_state["opportunity_center_global_ranking"] = ranked
    st.session_state["opportunity_center_best"] = ranked[0] if ranked else {}

    return ranked


def opportunity_ranking_table(scanner: Dict[str, Any]) -> pd.DataFrame:
    rows = build_global_opportunity_rows(scanner)

    if not rows:
        return pd.DataFrame(
            [
                {
                    "Rank": "—",
                    "Asset Class": "None",
                    "Opportunity": "Run Market Pulse, Pulse pages, Scanner, and Options Center",
                    "Setup": "PENDING CONFIRMATION",
                    "Score": "",
                    "Status": "Waiting for data",
                    "Opportunity Grade": "—",
                    "Institutional Grade": "—",
                    "Reason": "No published opportunities yet.",
                    "Size": "",
                    "Handoff": "",
                }
            ]
        )

    cols = ["Rank", "Asset Class", "Opportunity", "Setup", "Score", "Status", "Opportunity Grade", "Institutional Grade", "Reason", "Size", "Handoff"]
    return pd.DataFrame(rows)[cols]


def best_overall_opportunity(scanner: Dict[str, Any]) -> Dict[str, Any]:
    rows = build_global_opportunity_rows(scanner)

    if not rows:
        return {
            "title": "🏆 Best Opportunity Right Now",
            "value": "Waiting for data",
            "detail": "Run the workflow to populate the ranking engine.",
            "tone": "neutral",
        }

    top = rows[0]
    status = str(top.get("Status", ""))
    tone = "good" if "🟢" in status else "risk" if "🔴" in status else "warning"

    return {
        "title": "🏆 Best Opportunity Right Now",
        "value": top.get("Opportunity", "N/A"),
        "detail": (
            f"Asset: {top.get('Asset Class')} | Score: {top.get('Score')} | "
            f"Status: {top.get('Status')} | Handoff: {top.get('Handoff')}"
        ),
        "tone": tone,
    }




def build_decision_packet_from_opportunity(row: Dict[str, Any], destination: str = "Options Decision Center") -> Dict[str, Any]:
    """Create the universal Decision Packet consumed by Options Decision Center."""
    symbol = str(row.get("_symbol") or row.get("Symbol") or row.get("Opportunity") or "").upper().strip()
    symbol = symbol.split(" ")[0].strip()
    setup = str(row.get("Setup") or "").strip()
    asset_class = str(row.get("Asset Class") or "").strip()

    if asset_class == "Options":
        mission = "Generate Income" if setup in {"Cash-Secured Put", "Covered Call"} else "Bullish Directional Trade" if setup == "Bull Call Spread" else "Evaluate Options Opportunity"
    else:
        mission = "Evaluate Opportunity"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Opportunity Center",
        "destination": destination,
        "symbol": symbol,
        "asset_class": asset_class,
        "mission": mission,
        "recommended_strategy": setup,
        "strategy": setup,
        "market_bias": str(row.get("Status") or ""),
        "stock_price": 0.0,
        "score": safe_float(row.get("Score"), 0.0),
        "institutional_grade": str(row.get("Institutional Grade") or ""),
        "opportunity_grade": str(row.get("Opportunity Grade") or ""),
        "confidence": safe_float(row.get("Score"), 0.0),
        "next_action": "Validate, construct, approve, and prepare the options trade.",
        "reason": str(row.get("Reason") or "Published by Opportunity Center."),
        "rank": str(row.get("Rank") or ""),
        "opportunity": str(row.get("Opportunity") or ""),
    }


def publish_trade_lifecycle_from_opportunity(row: Dict[str, Any], destination: str = "Options Center") -> Dict[str, Any]:
    """Create/enrich the canonical TradeLifecyclePacket from an Opportunity Center row.

    This is intentionally non-destructive: Opportunity Center owns opportunity
    analysis fields and must not erase construction/execution data already added
    by downstream modules. Legacy flat keys are mirrored by save_to_session().
    """
    symbol = str(row.get("_symbol") or row.get("Symbol") or row.get("Opportunity") or "").upper().strip()
    symbol = symbol.split(" ")[0].strip()
    if not symbol or TradeLifecyclePacket is None:
        return build_decision_packet_from_opportunity(row, destination)

    setup = str(row.get("Setup") or "").strip()
    score = safe_float(row.get("Score"), 0.0)
    packet = TradeLifecyclePacket.from_session(st.session_state)

    # Start a new packet only when the selected symbol changes. Otherwise enrich.
    if packet.identity.symbol and packet.identity.symbol != symbol:
        packet = TradeLifecyclePacket.create(symbol=symbol, source="Opportunity Center", asset_class=row.get("Asset Class"), strategy=setup)

    packet.merge_update(
        {
            "identity": {
                "symbol": symbol,
                "asset_class": row.get("Asset Class"),
                "strategy": setup,
                "source": "Opportunity Center",
            },
            "opportunity": {
                "institutional_score": score,
                "approval": str(row.get("Institutional Grade") or row.get("Opportunity Grade") or ""),
                "confidence": score,
                "summary": str(row.get("Reason") or "Published by Opportunity Center."),
            },
        },
        source="Opportunity Center",
        overwrite=False,
    )
    if TradeStage is not None:
        packet.mark_stage_complete(TradeStage.OPPORTUNITY_ANALYSIS, source="Opportunity Center")
        packet.advance_stage(TradeStage.OPPORTUNITY_ANALYSIS, source="Opportunity Center")
    packet.save_to_session(st.session_state)

    # Legacy mirror used while Options Decision Center migration completes.
    legacy = build_decision_packet_from_opportunity(row, destination)
    legacy.update(
        {
            "trade_lifecycle_packet": packet.to_dict(),
            "institutional_score": packet.opportunity.institutional_score,
            "opportunity_score": packet.opportunity.institutional_score,
            "options_quality": packet.construction.options_quality,
            "options_quality_score": packet.construction.options_quality,
            "execution_confidence": packet.execution.execution_confidence,
        }
    )
    st.session_state["decision_packet"] = legacy
    st.session_state["opportunity_packet"] = legacy
    return legacy

def publish_handoff(row: Dict[str, Any], destination: str | None = None) -> None:
    symbol = str(row.get("_symbol") or row.get("Symbol") or row.get("Opportunity") or "").upper().strip()
    symbol = symbol.split(" ")[0].strip()
    if not symbol or symbol in {"N/A", "NONE"}:
        return

    destination = destination or str(row.get("_page") or row.get("Handoff") or "Trade Command Center")

    handoff_ticket = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Opportunity_Center",
        "destination": destination,
        "symbol": symbol,
        "asset_class": row.get("Asset Class"),
        "opportunity": row.get("Opportunity"),
        "setup": row.get("Setup"),
        "score": row.get("Score"),
        "status": row.get("Status"),
        "opportunity_grade": row.get("Opportunity Grade"),
        "institutional_grade": row.get("Institutional Grade"),
        "reason": row.get("Reason"),
        "size": row.get("Size"),
        "rank": row.get("Rank"),
    }

    publish_trade_lifecycle_from_opportunity(row, destination)

    # Publish the exact selected row everywhere downstream pages look for it.
    # This prevents handoff buttons from falling back to the #1 opportunity.
    st.session_state["opportunity_center_selected"] = row
    st.session_state["opportunity_center_handoff_ticket"] = handoff_ticket
    st.session_state["trade_command_symbol"] = symbol
    st.session_state["options_manual_symbol"] = symbol
    st.session_state["research_symbol"] = symbol
    st.session_state["research_ticker"] = symbol
    st.session_state["selected_symbol"] = symbol
    st.session_state["oms_order_symbol"] = symbol
    st.session_state["oms_prepared_ticket"] = handoff_ticket

    if destination == "Options Decision Center":
        packet = st.session_state.get("decision_packet") or build_decision_packet_from_opportunity(row, destination)
        st.session_state["decision_packet"] = packet
        st.session_state["opportunity_packet"] = packet
        st.session_state["options_decision_packet"] = packet
        st.session_state["options_handoff_ticket"] = handoff_ticket
        st.session_state["options_handoff_symbol"] = symbol
        st.session_state["options_selected_symbol"] = symbol
        st.session_state["options_symbol"] = symbol
        st.session_state["options_underlying"] = symbol
        st.session_state["selected_options_symbol"] = symbol
        st.session_state["manual_options_symbol"] = symbol
        st.session_state["options_manual_symbol"] = symbol
    elif destination == "Options Center":
        # Options Center builds its own strategy rows. Keep this handoff simple:
        # publish the selected UNDERLYING symbol through every known symbol key,
        # but do not overwrite Options Center's internal best-opportunity object.
        st.session_state["options_handoff_ticket"] = handoff_ticket
        st.session_state["options_handoff_symbol"] = symbol
        st.session_state["options_selected_symbol"] = symbol
        st.session_state["options_symbol"] = symbol
        st.session_state["options_underlying"] = symbol
        st.session_state["selected_options_symbol"] = symbol
        st.session_state["manual_options_symbol"] = symbol
        st.session_state["options_manual_symbol"] = symbol
    elif destination == "Trade Command Center":
        st.session_state["trade_command_handoff_ticket"] = handoff_ticket
    elif destination == "Research Stock":
        st.session_state["research_handoff_ticket"] = handoff_ticket
    elif destination == "OMS Execution":
        st.session_state["tcc_prepared_oms_ticket"] = handoff_ticket

    if destination in {"Trade Command Center", "Options Center", "Research Stock", "OMS Execution", "Market Pulse", "Crypto Pulse", "Forex Pulse", "Gold Pulse", "Oil Pulse"}:
        st.session_state["jfbp_main_navigation"] = destination

    st.rerun()


def render_global_handoff_controls(scanner: Dict[str, Any]) -> None:
    rows = build_global_opportunity_rows(scanner)[:25]
    if not rows:
        return

    labels = [
        f"{row.get('Rank')} · {row.get('Asset Class')} · {row.get('Opportunity')} · {row.get('Score')}"
        for row in rows
    ]

    selected_index = st.selectbox(
        "Select opportunity for handoff",
        options=list(range(len(rows))),
        index=0,
        format_func=lambda idx: labels[int(idx)],
        key="opportunity_center_handoff_index_v2",
    )

    try:
        selected_index = int(selected_index)
    except Exception:
        selected_index = 0

    if selected_index < 0 or selected_index >= len(rows):
        selected_index = 0

    selected = rows[selected_index]

    top_1, top_2 = st.columns(2, gap="small")
    with top_1:
        if st.button("Trade Command", width="stretch", key="oc_open_trade_command_selected_v2"):
            publish_handoff(selected, "Trade Command Center")
    with top_2:
        if st.button("Options Center", width="stretch", key="oc_open_options_selected_v2"):
            publish_handoff(selected, "Options Center")

    bottom_1, bottom_2 = st.columns(2, gap="small")
    with bottom_1:
        if st.button("Research", width="stretch", key="oc_open_research_selected_v2"):
            publish_handoff(selected, "Research Stock")
    with bottom_2:
        if st.button("OMS", width="stretch", key="oc_send_oms_selected_v2"):
            publish_handoff(selected, "OMS Execution")


def render_commander_opportunity(best_row: Dict[str, Any]) -> None:
    """Render the top-ranked opportunity as a large commander hero."""
    if not best_row:
        title = "PENDING CONFIRMATION"
        asset = "Run Market Pulse, Pulse pages, Scanner, and Options Center."
        score = "N/A"
        status = "PENDING CONFIRMATION"
        size = "N/A"
        handoff = "Workflow"
        tone = "neutral"
        reason = "No published opportunity yet."
        opportunity_grade_text = "—"
        institutional_grade_text = "—"
    else:
        title = str(best_row.get("Opportunity", "N/A"))
        asset = str(best_row.get("Asset Class", "N/A"))
        score = str(best_row.get("Score", "N/A"))
        status = str(best_row.get("Status", "PENDING CONFIRMATION"))
        size = str(best_row.get("Size", "N/A"))
        handoff = str(best_row.get("Handoff", "Workflow"))
        reason = str(best_row.get("Reason", ""))
        opportunity_grade_text = str(best_row.get("Opportunity Grade", "—"))
        institutional_grade_text = str(best_row.get("Institutional Grade", "—"))
        tone = "good" if "🟢" in opportunity_grade_text or "🔵" in institutional_grade_text else "risk" if "🔴" in status else "warning"

    bg, border, color = tone_palette(tone)
    st.subheader("🏆 Commander Opportunity")
    st.markdown(
        f"""
<div class="oc-hero" style="background:{bg};border-color:{border};">
    <div class="oc-hero-kicker">Best Opportunity Right Now</div>
    <div class="oc-hero-title" style="color:{color};">{html.escape(title)}</div>
    <div class="oc-hero-text">
        <strong>Asset:</strong> {html.escape(asset)} ·
        <strong>Score:</strong> {html.escape(score)} ·
        <strong>Status:</strong> {html.escape(status)} ·
        <strong>Opportunity Grade:</strong> {html.escape(opportunity_grade_text)} ·
        <strong>Institutional Grade:</strong> {html.escape(institutional_grade_text)} ·
        <strong>Size:</strong> {html.escape(size)}
    </div>
    <div class="oc-hero-action">Next action: {html.escape(handoff)} — {html.escape(reason)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_elite_candidates(ranking_rows: List[Dict[str, Any]], max_items: int = 3) -> None:
    """Render the top three opportunity rows as an action strip."""
    st.subheader("⭐ Additional Elite Candidates")
    if not ranking_rows or len(ranking_rows) <= 1:
        st.info("No additional elite candidates yet. Run the workflow to populate the opportunity ranking.")
        return

    cards = []
    for idx, row in enumerate(ranking_rows[1:1 + max_items], start=2):
        status = str(row.get("Status", ""))
        tone = "good" if "🟢" in status else "risk" if "🔴" in status else "warning"
        cards.append(
            {
                "title": f"#{idx} · {row.get('Asset Class', 'N/A')}",
                "value": row.get("Opportunity", "N/A"),
                "detail": f"Score {row.get('Score', 'N/A')} | Opportunity {row.get('Opportunity Grade', '—')} | Institutional {row.get('Institutional Grade', '—')} | Next: {row.get('Handoff', '')}",
                "tone": tone,
            }
        )
    render_card_grid(cards)


def render_pulse_status_cards() -> None:
    """Compact right-rail Pulse status mini-cards."""
    st.subheader("📡 Pulse Status")
    pulse_df = pulse_table()

    if pulse_df.empty:
        st.info("No Pulse status published yet.")
        return

    items = []
    for _, row in pulse_df.iterrows():
        asset = str(row.get("Asset", "Pulse"))
        execution_state = str(row.get("Execution", ""))
        freshness = str(row.get("Freshness", "Not published"))
        best = str(row.get("Best", "") or "N/A")
        score = str(row.get("Score", "") or "N/A")

        if freshness.startswith("Fresh"):
            freshness_short = "🟢 Fresh"
        elif freshness.startswith("Aging"):
            freshness_short = "🟡 Aging"
        elif freshness.startswith("Stale"):
            freshness_short = "🔴 Stale"
        else:
            freshness_short = "⚪ Not Loaded"

        execution_short = execution_state if execution_state in {"Allowed", "Blocked", "Pending Confirmation"} else "N/A"
        items.append(
            (
                asset,
                f"{freshness_short} · Execution {execution_short} · {best} · {score}",
            )
        )

    render_mini_grid(items)


def render_global_ranking_table(df: pd.DataFrame, height: int = 390) -> None:
    """Render the Global Opportunity table in a clipped HTML scroll box.

    This avoids Streamlit dataframe canvas overflow where the table can visually
    extend underneath the next card section on some browser/zoom combinations.
    """
    if df is None or df.empty:
        st.info("No published opportunities yet.")
        return

    cols = list(df.columns)
    class_map = {
        "Rank": "oc-rank-col-rank",
        "Asset Class": "oc-rank-col-asset",
        "Opportunity": "oc-rank-col-opportunity",
        "Setup": "oc-rank-col-setup",
        "Score": "oc-rank-col-score",
        "Status": "oc-rank-col-status",
        "Opportunity Grade": "oc-rank-col-opportunity-grade",
        "Institutional Grade": "oc-rank-col-institutional-grade",
        "Reason": "oc-rank-col-reason",
        "Size": "oc-rank-col-size",
        "Handoff": "oc-rank-col-handoff",
    }

    html_parts = [f'<div class="oc-table-wrap" style="max-height:{int(height)}px;">']
    html_parts.append('<table class="oc-rank-table"><thead><tr>')
    for col in cols:
        cls = class_map.get(str(col), "")
        html_parts.append(f'<th class="{cls}">{html.escape(str(col))}</th>')
    html_parts.append('</tr></thead><tbody>')

    for _, row in df.iterrows():
        html_parts.append('<tr>')
        for col in cols:
            cls = class_map.get(str(col), "")
            value = html.escape(str(row.get(col, "")))
            html_parts.append(f'<td class="{cls}" title="{value}">{value}</td>')
        html_parts.append('</tr>')

    html_parts.append('</tbody></table></div>')
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def opportunity_brief(market: Dict[str, Any], scanner: Dict[str, Any], executor: Dict[str, Any]) -> tuple[str, str]:
    regime = str(market.get("regime", "UNKNOWN")).upper()
    stress = safe_float(market.get("stress_score"), 0.0)
    executable = safe_int(scanner.get("executable"), 0)

    if executor.get("kill_switch"):
        return (
            "🛑 KILL SWITCH ACTIVE",
            "Trading should remain blocked until the kill switch is cleared.",
        )

    if regime in ("RISK_OFF", "RISK-OFF", "DEFENSIVE") or stress >= 70:
        return (
            "🔴 Defensive Command",
            "Capital preservation comes first. Use smaller size and avoid forcing new long exposure.",
        )

    if executable > 0 and regime in ("RISK_ON", "RISK-ON"):
        return (
            "🟢 Risk-On Opportunity",
            "Market conditions and Scanner approval are aligned. Focus only on approved executable rows.",
        )

    if executable > 0:
        return (
            "🟡 Selective Opportunity",
            "Some trades are approved, but the market still requires selectivity and normal risk checks.",
        )

    return (
        "🟡 Watchlist Mode",
        "No executable trades are currently approved. Use the center to identify where leadership may be forming.",
    )


# =========================================================
# PAGE
# =========================================================

def run_page() -> None:
    inject_css()

    st.title("🎯 Opportunity Center")
    st.caption("Institutional opportunity command center and workflow launcher.")

    market = market_snapshot()
    scanner = scanner_snapshot()
    executor = executor_snapshot()
    brief_title, brief_text = opportunity_brief(market, scanner, executor)
    ranking_rows = build_global_opportunity_rows(scanner)
    best_row = ranking_rows[0] if ranking_rows else {}

    with st.expander("ℹ️ How to use Opportunity Center", expanded=False):
        st.markdown(
            """
            **Morning workflow**

            1. Open **Market Pulse** to publish the broad market regime.
            2. Open **Crypto Pulse**, **Forex Pulse**, **Gold Pulse**, and **Oil Pulse** only if you want cross-asset context.
            3. Open **Scanner**, choose the universe, and run the scan.
            4. Return here to rank all available opportunities in one command-desk list.
            5. Send the selected opportunity to **Trade Command**, **Options**, **Research**, or **OMS**.
            6. Check **TRADEABLE**, **PENDING CONFIRMATION**, or **WATCHLIST** status, freshness, risk plan status, and executor readiness before acting.

            Terminology:
            - **TRADEABLE**: Actionable now (meets institutional and Pulse criteria).
            - **PENDING CONFIRMATION**: Promising but requires additional confirmation or review.
            - **WATCHLIST**: Monitor only; not currently actionable.

            Opportunity Center ranks and routes ideas; final execution is handled by **OMS / Trade Command** after confirmation.
            """
        )

    # =====================================================
    # COMMAND ROW
    # =====================================================
    with st.container(border=True):
        nav_cols = st.columns([1, 1, 1, 1, 1, 1, 1], gap="small")
        nav_actions = [
            ("Market Pulse", "Market Pulse"),
            ("Scanner", "Scanner"),
            ("Research", "Research Stock"),
            ("Trade Command", "Trade Command Center"),
            ("Options", "Options Center"),
            ("OMS", "OMS Execution"),
        ]
        for col, (label, page_key) in zip(nav_cols[:-1], nav_actions):
            with col:
                if st.button(label, width="stretch", key=f"oc_nav_{page_key}"):
                    navigate_to(page_key)
        with nav_cols[-1]:
            if st.button("Refresh", width="stretch", key="oc_refresh_main"):
                st.rerun()

    freshness_panel()
    st.info(grade_explainer())

    # =====================================================
    # EXECUTIVE OPPORTUNITY DASHBOARD (v6.0)
    # =====================================================
    # Compute executive metrics without changing underlying logic
    tradeable_count = sum(1 for r in ranking_rows if "TRADEABLE" in str(r.get("Opportunity Grade", "")).upper())
    pending_count = sum(1 for r in ranking_rows if "PENDING" in str(r.get("Institutional Grade", "")).upper() or "PENDING" in str(r.get("Opportunity Grade", "")).upper())
    watchlist_count = sum(1 for r in ranking_rows if "WATCHLIST" in str(r.get("Opportunity Grade", "")).upper())
    highest_confidence = max((safe_float(r.get("Score"), 0.0) for r in ranking_rows), default=0.0)
    best_opportunity = best_row.get("Opportunity") if best_row else "N/A"
    market_regime = market.get("regime", "UNKNOWN")
    market_tone = tone_for_regime(market_regime)

    overall_grade = grade_from_score(sum((safe_float(r.get("Score"), 0.0) for r in ranking_rows[:5])) / (min(len(ranking_rows), 5) or 1))
    regime_context = {
        "SELECTIVE": "Moderate risk environment. Trade only high-quality opportunities.",
        "CAUTIOUS": "Reduced deployment advised. Confirm before committing capital.",
        "NEUTRAL": "Market is balanced. Focus on clearly superior ideas.",
        "DEFENSIVE": "Risk-off environment. Avoid aggressive entries.",
        "RISK-ON": "Broad participation expected. Use selective execution.",
        "RISK_OFF": "Capital preservation mode. Only the best ideas are viable.",
    }
    market_status_detail = regime_context.get(str(market_regime).upper().strip(), "Review market condition and risk before acting.")

    # Institutional Market Brief — single coherent briefing for the desk
    regime_context = {
        "SELECTIVE": "Moderate risk environment. Trade only high-quality opportunities.",
        "CAUTIOUS": "Reduced deployment advised. Confirm before committing capital.",
        "NEUTRAL": "Market is balanced. Focus on clearly superior ideas.",
        "DEFENSIVE": "Risk-off environment. Avoid aggressive entries.",
        "RISK-ON": "Broad participation expected. Use selective execution.",
        "RISK_OFF": "Capital preservation mode. Only the best ideas are viable.",
    }
    market_status_detail = regime_context.get(str(market_regime).upper().strip(), "Review market condition and risk before acting.")

    # Research summary — reuse scanner best recommendation where available
    research_conclusion = scanner.get("best_recommendation") or (best_row.get("trade_recommendation") if best_row else "N/A")

    # Leadership summary for the briefing page; do not repeat the specific trade
    lead_asset_class = str(best_row.get("Asset Class", "N/A")).upper().strip() if best_row else "N/A"
    leadership_summary = f"{lead_asset_class} Leading" if lead_asset_class and lead_asset_class != "N/A" else "Leadership unavailable"

    # Institutional grade for top opportunity
    institutional_grade = best_row.get("Institutional Grade") if best_row else "N/A"

    # Execution decision (UI-only mapping, preserving underlying logic)
    if executor.get("kill_switch"):
        execution_decision = "DO NOT TRADE"
    elif tradeable_count > 0:
        execution_decision = "EXECUTE"
    elif pending_count > 0:
        execution_decision = "WAIT"
    else:
        execution_decision = "WAIT"

    # Determine tone for best opportunity based on its opportunity/institutional grade
    best_tone = "neutral"
    try:
        best_opp_label = str(best_row.get("Opportunity Grade", "")).upper()
        best_inst_label = str(best_row.get("Institutional Grade", "")).upper()
        if "TRADEABLE" in best_opp_label or "🟢" in best_opp_label:
            best_tone = "good"
        elif "PENDING" in best_opp_label or "PENDING" in best_inst_label:
            best_tone = "warning"
        else:
            best_tone = "neutral"
    except Exception:
        best_tone = "neutral"

    with st.container():
        st.subheader("INSTITUTIONAL MARKET BRIEF")
        st.caption("One coherent briefing: market, trend, asset leadership, research, grade, and execution.")
        render_card_grid([
            {"title": "Macro Environment", "value": market_regime, "detail": market_status_detail, "tone": market_tone},
            {"title": "Trend", "value": market.get("playbook", "N/A"), "detail": "Research-derived trend context.", "tone": "neutral"},
            {"title": "Opportunity Leadership", "value": leadership_summary, "detail": "Market-level summary of the leading asset class, not the specific trade.", "tone": best_tone},
            {"title": "Research", "value": research_conclusion, "detail": brief_title or "Research summary for the desk.", "tone": "info"},
            {"title": "Institutional Grade", "value": institutional_grade, "detail": "Readiness for capital deployment.", "tone": "good" if "READY" in str(institutional_grade).upper() else ("warning" if "PENDING" in str(institutional_grade).upper() else "risk")},
            {"title": "Execution", "value": execution_decision, "detail": "Immediate action for the desk.", "tone": "good" if execution_decision=="EXECUTE" else ("warning" if execution_decision=="WAIT" else "risk")},
        ])

    # Commander Assessment card
    top_strength = "Top-ranked opportunities meet pulse and scanner alignment." if tradeable_count > 0 else "No immediate tradeable leaders; monitoring leadership formation."
    top_risk = "Execution confirmation required before deployment." if pending_count > 0 else "Market regime or data freshness may be limiting execution."
    recommended_next = brief_text or "Review elite candidates and confirm in Scanner / Options Center."

    with st.container():
        st.subheader("Commander Assessment")
        st.caption("Why the briefing looks this way: strengths, risks, and recommendation.")
        # Keep the four executive cards, avoid duplicating execution state
        render_card_grid([
            {"title": "Overall Grade", "value": overall_grade, "detail": "Aggregate grade from top opportunities.", "tone": "good"},
            {"title": "Top Strength", "value": top_strength, "detail": "Primary factor supporting current opportunities.", "tone": "good"},
            {"title": "Primary Risk", "value": top_risk, "detail": "Key risk to monitor before deployment.", "tone": "risk" if pending_count > 0 else "warning"},
            {"title": "Recommendation", "value": recommended_next, "detail": "Actionable guidance for the desk.", "tone": "info"},
        ])

    # Business Intelligence (counts and runtime metrics)
    with st.expander("📈 Business Intelligence", expanded=False):
        st.subheader("Business Intelligence")
        st.caption("Record counts, growth signals, recovery and runtime metrics for monitoring.")
        render_card_grid([
            {"title": "🔢 Scanner Rows", "value": scanner.get("rows", 0), "detail": "Raw scanner rows", "tone": "info"},
            {"title": "📋 Ranked Opportunities", "value": len(ranking_rows), "detail": "Global ranking rows", "tone": "info"},
            {"title": "🧩 Options Setups", "value": len([r for r in ranking_rows if r.get('Asset Class')=='Options']), "detail": "Options rows in ranking", "tone": "info"},
            {"title": "📡 Pulse Sources", "value": len([k for k,v in get_bus().items() if v]), "detail": "Loaded Pulse asset classes", "tone": "info"},
            {"title": "⚖️ Open Positions", "value": executor.get("open_positions", 0), "detail": "Executor open positions", "tone": "info"},
            {"title": "⛔ Kill Switch", "value": "ON" if executor.get("kill_switch") else "OFF", "detail": "Executor kill switch", "tone": "risk" if executor.get("kill_switch") else "good"},
        ])

    # =====================================================
    # COMMANDER OPPORTUNITY HERO
    # =====================================================
    render_commander_opportunity(best_row)
    render_elite_candidates(ranking_rows)

    # =====================================================
    # 70/30 COMMAND LAYOUT
    # =====================================================
    left, right = st.columns([0.70, 0.30], gap="large")

    with left:
        st.subheader("🏆 Global Opportunity Ranking Engine")
        st.caption(
            "Ranks Scanner rows, options setups, crypto, forex, gold, and oil into one command-desk list."
        )
        ranking_df = opportunity_ranking_table(scanner)
        render_global_ranking_table(ranking_df, height=390)

        st.subheader("🌍 Best Opportunities by Asset Class")
        render_card_grid(
            [
                {
                    "title": "📈 Stocks / Scanner",
                    "value": scanner.get("best_symbol", "Run Scanner"),
                    "detail": (
                        f"{scanner.get('best_sector')} | Recommendation: {scanner.get('best_recommendation')} | "
                        f"Opportunity: {opportunity_grade(scanner.get('best_score'), scanner.get('best_rating'), scanner.get('best_recommendation'))[0]} | "
                        f"Institutional: {'🔵 READY' if safe_int(scanner.get('executable')) > 0 else '🟡 PENDING CONFIRMATION'} | Blocked Shorts: {scanner.get('blocked_shorts')}"
                    ),
                    "tone": "good" if safe_int(scanner.get("executable")) > 0 else "warning",
                },
                options_card(scanner),
                pulse_card("forex", "Forex", "💱"),
                pulse_card("gold", "Gold", "🥇"),
                pulse_card("oil", "Oil", "🛢"),
                pulse_card("crypto", "Crypto", "₿"),
            ]
        )

        st.subheader("🌍 Cross-Asset Regime Table")
        st.caption(
            "Context table showing execution eligibility and whether the Pulse reading is fresh."
        )
        st.dataframe(
            pulse_table(),
            width="stretch",
            hide_index=True,
            height=240,
        )

    with right:
        st.subheader("🚀 Execution Console")
        st.caption("Select one opportunity and continue the workflow without retyping symbols.")
        render_global_handoff_controls(scanner)

        st.subheader("⚙️ Execution Readiness")
        render_mini_grid(
            [
                ("Market Buy Execution", "Allowed" if bool(market.get("buy_allowed", True)) else "Blocked"),
                ("Market Size", fmt_multiplier(market.get("execution_multiplier", 1.0))),
                ("Scanner Rows", scanner.get("rows", 0)),
                ("Executable Trades", scanner.get("executable", 0)),
                ("Executor Mode", executor.get("mode", "SIM")),
                ("Open Positions", executor.get("open_positions", 0)),
                ("Pipeline", executor.get("pipeline", "MISSING")),
                ("Kill Switch", "ON" if executor.get("kill_switch") else "OFF"),
            ]
        )

        render_pulse_status_cards()

    # =====================================================
    # DECISION SUMMARY
    # =====================================================
    with st.container():
        st.subheader("📌 Decision Summary")
        st.caption("Concise guidance for the trader: what to do, avoid, and monitor next.")
        do_text = "Focus on TRADEABLE elite candidates and confirm execution details in Trade Command / Options Center." if tradeable_count > 0 else "No immediate TRADEABLE candidates; prioritize monitoring and confirm signals in Scanner."
        avoid_text = "Avoid deploying large size when Institutional Grade is PENDING CONFIRMATION or market regime is defensive." if pending_count > 0 else "Avoid forcing trades outside allowed Pulse regimes."
        monitor_text = "Monitor elite candidates, pulse freshness, and execution confirmation; refresh Pulse pages when stale."
        render_card_grid([
            {"title": "🟢 Execute", "value": do_text, "detail": "Immediate focus for the desk.", "tone": "good"},
            {"title": "🟠 Avoid", "value": avoid_text, "detail": "What to hold off on now.", "tone": "warning"},
            {"title": "🔵 Monitor", "value": monitor_text, "detail": "Keep these signals on watch.", "tone": "info"},
        ])

    # =====================================================
    # LOWER DETAILS
    # =====================================================
    with st.expander("🧭 Opportunity Workflow", expanded=False):
        st.subheader("Opportunity Workflow")
        st.markdown(
            """
            **Recommended route:**

            1. **Market Pulse** confirms the broad regime.
            2. **Scanner** identifies stock leadership and executable rows.
            3. **Opportunity Center** ranks all ideas across asset classes.
            4. **Research Stock** validates the thesis and chart.
            5. **Trade Command Center** prepares the trade decision.
            6. **OMS Execution** routes only approved orders.
            7. **Position Command Center** manages open risk.
            8. **Journal** records the decision.
            """
        )

    with st.expander("🛠 Diagnostics", expanded=False):
        st.write(
            {
                "Market Snapshot": market,
                "Scanner Snapshot": scanner,
                "Executor Snapshot": executor,
                "Multi-Asset Signal Bus": get_bus(),
                "Global Ranking": ranking_rows,
                "Updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )

def page():
    run_page()
