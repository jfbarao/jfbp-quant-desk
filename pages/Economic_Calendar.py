# =========================================================
# ECONOMIC CALENDAR PAGE — v2.1
# JFBP Quant Desk
# Institutional Risk Panel + Market Stress Integration
# Responsive iPad/mobile layout pass + HTML card rendering fix
# =========================================================

from __future__ import annotations

import html
from typing import Any, Dict, Iterable, List

import pandas as pd
import streamlit as st

from engines.economic_calendar import (
    analyze_economic_calendar,
    sample_events,
)


# =========================================================
# RESPONSIVE UI HELPERS
# =========================================================

def inject_economic_calendar_css() -> None:
    """Visual-only responsive layer for Economic Calendar."""

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.4rem !important;
                padding-bottom: 2.5rem !important;
                max-width: 1450px !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            h1 {
                font-size: clamp(1.85rem, 3.6vw, 2.45rem) !important;
                font-weight: 850 !important;
                line-height: 1.12 !important;
                color: #1f2937 !important;
            }

            h2, h3 {
                font-size: clamp(1.10rem, 2.3vw, 1.45rem) !important;
                font-weight: 850 !important;
                line-height: 1.18 !important;
                color: #1f2937 !important;
            }

            div[data-testid="stDataFrame"] {
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
                border-radius: 12px !important;
            }

            div[data-testid="stAlert"] {
                overflow-wrap: break-word !important;
                word-break: normal !important;
            }

            .econ-card-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.85rem;
                margin: 0.75rem 0 1.0rem 0;
            }

            .econ-card-grid-3 {
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }

            .econ-card-grid-2 {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .econ-metric-card {
                border-radius: 14px;
                padding: 0.78rem 0.9rem;
                min-height: 106px;
                border: 1px solid #dbe3ef;
                background: #f8fafc;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
                overflow: hidden;
            }

            .econ-metric-label {
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #64748b;
                font-weight: 850;
                line-height: 1.15;
                margin-bottom: 0.35rem;
                white-space: normal;
                overflow-wrap: break-word;
                word-break: normal;
            }

            .econ-metric-value {
                font-size: clamp(1.02rem, 2.3vw, 1.30rem);
                line-height: 1.18;
                font-weight: 900;
                color: #111827;
                white-space: normal;
                overflow-wrap: break-word;
                word-break: normal;
            }

            .econ-metric-detail {
                font-size: 0.78rem;
                line-height: 1.35;
                color: #64748b;
                margin-top: 0.38rem;
                white-space: normal;
                overflow-wrap: break-word;
                word-break: normal;
            }

            .econ-flow {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 14px;
                padding: 0.95rem 1rem;
                margin: 0.8rem 0 1rem 0;
                overflow-wrap: break-word;
                word-break: normal;
            }

            .econ-section-card {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 1rem;
                margin: 0.5rem 0 1rem 0;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.035);
                overflow: hidden;
            }

            @media (max-width: 1180px) {
                .block-container {
                    padding-left: 1.25rem !important;
                    padding-right: 1.25rem !important;
                    max-width: 100% !important;
                }

                .econ-card-grid,
                .econ-card-grid-3,
                .econ-card-grid-2 {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem !important;
                    padding-right: 0.9rem !important;
                }

                .econ-card-grid,
                .econ-card-grid-3,
                .econ-card-grid-2 {
                    grid-template-columns: 1fr;
                    gap: 0.65rem;
                }

                .econ-metric-card {
                    min-height: 92px;
                    padding: 0.72rem 0.82rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _tone_palette(tone: str) -> tuple[str, str, str]:
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
    }

    return palette.get(tone, palette["neutral"])


def economic_tone(score: int, is_demo_mode: bool = False) -> str:
    if is_demo_mode:
        return "warning"
    if score >= 80:
        return "risk"
    if score >= 60:
        return "risk"
    if score >= 35:
        return "warning"
    return "good"


def economic_metric_card(
    label: str,
    value: Any,
    detail: str = "",
    tone: str = "neutral",
) -> str:
    """Return one compact HTML card as a single-line-safe string.

    Streamlit/Markdown can misread deeply indented multi-line raw HTML as
    a code block on some pages. Keeping the card HTML left-aligned and
    compact prevents the raw <div> text from appearing on screen.
    """
    background, border, value_color = _tone_palette(tone)

    label_text = html.escape(str(label))
    value_text = html.escape(str(value))
    detail_text = html.escape(str(detail))

    detail_html = (
        f'<div class="econ-metric-detail">{detail_text}</div>'
        if detail_text
        else ""
    )

    return (
        f'<div class="econ-metric-card" '
        f'style="background:{background};border-color:{border};">'
        f'<div class="econ-metric-label">{label_text}</div>'
        f'<div class="econ-metric-value" style="color:{value_color};">'
        f'{value_text}</div>'
        f'{detail_html}'
        f'</div>'
    )


def economic_metric_grid(cards: Iterable[Dict[str, Any]], columns: int = 4) -> None:
    cards = list(cards)

    grid_class = "econ-card-grid"
    if columns == 3:
        grid_class += " econ-card-grid-3"
    elif columns == 2:
        grid_class += " econ-card-grid-2"

    html_cards = "".join(
        economic_metric_card(
            label=card.get("label", ""),
            value=card.get("value", ""),
            detail=card.get("detail", ""),
            tone=card.get("tone", "neutral"),
        )
        for card in cards
    )

    st.markdown(
        f'<div class="{grid_class}">{html_cards}</div>',
        unsafe_allow_html=True,
    )


def help_text(text: str) -> None:
    st.caption(f"💡 {text}")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def event_time_label(event: Dict[str, Any]) -> str:
    hours_until = event.get("hours_until")

    if hours_until is None:
        return "Timing unavailable"

    try:
        hours = float(hours_until)
    except Exception:
        return "Timing unavailable"

    if hours < 0:
        return "Already released"

    if hours < 1:
        return "Within 1 hour"

    if hours < 24:
        return f"In {hours:.1f} hours"

    return f"In {hours / 24:.1f} days"


def build_event_view(events: List[Dict[str, Any]]) -> pd.DataFrame:
    if not events:
        return pd.DataFrame()

    event_df = pd.DataFrame(events)

    display_cols = [
        "name",
        "country",
        "category",
        "importance",
        "hours_until",
        "risk_label",
        "risk_score",
        "market_relevant",
        "source",
    ]

    display_cols = [
        col for col in display_cols
        if col in event_df.columns
    ]

    if display_cols:
        return event_df[display_cols]

    return event_df


# =========================================================
# PAGE
# =========================================================

def run_page() -> None:

    inject_economic_calendar_css()

    st.title("📅 Economic Calendar Risk")
    st.caption(
        "Macro-event risk panel for CPI, PPI, FOMC, NFP, GDP, and other events "
        "that can change Market Pulse, Scanner aggressiveness, and position sizing."
    )

    st.markdown(
        """
        <div class="econ-flow">
            <strong>Workflow:</strong><br>
            Economic Calendar → Market Pulse Stress Model → Scanner Risk Controls → OMS Execution
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📘 How to use this page", expanded=False):
        st.markdown(
            """
            1. Review the headline economic risk score.
            2. Check the highest-risk event and timing.
            3. Confirm whether the calendar is live or demo/sample data.
            4. Open Market Pulse to see the combined stress model.
            5. Use reduced position sizing or tighter filters when risk is elevated.

            **Important:** Demo mode means the page is using sample events only. Scanner enforcement should remain OFF until live calendar data is connected.
            """
        )

    try:
        economic_calendar_result = analyze_economic_calendar(
            sample_events()
        )

        economic_score = safe_int(
            economic_calendar_result.get(
                "economic_risk_score",
                0,
            )
        )

        economic_label = str(
            economic_calendar_result.get(
                "economic_risk_label",
                "NONE",
            )
        )

        # =====================================================
        # SCANNER / MARKET STRESS EXPORT
        # =====================================================

        st.session_state["economic_risk_score"] = int(
            economic_score
        )

        st.session_state["economic_risk_label"] = str(
            economic_label
        )

        highest_event = economic_calendar_result.get(
            "highest_risk_event",
        )

        calendar_source = (
            economic_calendar_result.get("calendar_source")
            or economic_calendar_result.get("source")
            or "UNKNOWN"
        )

        is_demo_mode = bool(
            economic_calendar_result.get(
                "is_demo_mode",
                False,
            )
        )

        events = economic_calendar_result.get(
            "events",
            [],
        )

        risk_tone = economic_tone(
            economic_score,
            is_demo_mode=is_demo_mode,
        )

        highest_event_name = "None"
        highest_event_detail = "No major event detected."

        if isinstance(highest_event, dict) and highest_event:
            highest_event_name = str(
                highest_event.get("name", "N/A")
            )
            highest_event_detail = event_time_label(highest_event)

        source_detail = (
            "Sample events only"
            if is_demo_mode
            else "Calendar source used by risk model"
        )

        st.subheader("🧠 Economic Risk Brief")
        st.caption(
            "What it means: This is the macro-risk input that Market Pulse uses "
            "inside the weighted stress model."
        )

        economic_metric_grid(
            [
                {
                    "label": "Economic Risk",
                    "value": economic_label,
                    "detail": "Current macro-event state.",
                    "tone": risk_tone,
                },
                {
                    "label": "Risk Score",
                    "value": f"{economic_score}/100",
                    "detail": "Stress contribution input.",
                    "tone": risk_tone,
                },
                {
                    "label": "Highest Risk Event",
                    "value": highest_event_name,
                    "detail": highest_event_detail,
                    "tone": risk_tone if highest_event_name != "None" else "neutral",
                },
                {
                    "label": "Source",
                    "value": calendar_source,
                    "detail": source_detail,
                    "tone": "warning" if is_demo_mode else "info",
                },
            ],
            columns=4,
        )

        if is_demo_mode:
            st.warning(
                "DEMO mode only. These are sample events. No live economic-event risk is being enforced."
            )

        elif economic_score >= 80:
            st.error(
                "EXTREME economic event risk. New trades should be reduced or avoided."
            )

        elif economic_score >= 60:
            st.warning(
                "HIGH economic event risk. Scanner should tighten BUY conditions."
            )

        elif economic_score >= 35:
            st.info(
                "MEDIUM economic event risk. Use reduced position sizing."
            )

        else:
            st.success(
                "Economic event risk is low. Normal scanner operation is allowed, subject to Market Pulse confirmation."
            )

        help_text(
            "Economic Calendar contributes 15% of the Market Pulse stress model. "
            "Major macro events can reduce scanner aggressiveness even when charts look constructive."
        )

        st.divider()

        # =====================================================
        # EVENT TABLE
        # =====================================================

        st.subheader("📋 Upcoming Economic Events")
        st.caption(
            "What it means: Event-level view used to identify macro catalysts "
            "that may affect volatility, gap risk, and execution sizing."
        )

        event_view_df = build_event_view(events)

        if event_view_df.empty:
            st.info("No economic calendar events returned.")
        else:
            st.dataframe(
                event_view_df,
                use_container_width=True,
                hide_index=True,
            )

        st.divider()

        # =====================================================
        # SCANNER IMPACT
        # =====================================================

        st.subheader("🎯 Scanner Impact")
        st.caption(
            "What it means: Practical trading impact of the current macro-event risk."
        )

        if is_demo_mode:
            scanner_action = "Do not enforce"
            position_guidance = "Demo only"
            trade_filter = "Keep scanner enforcement OFF"
            impact_tone = "warning"

        elif economic_score >= 80:
            scanner_action = "Avoid new trades"
            position_guidance = "Very small / pause"
            trade_filter = "Only exceptional A+ setups"
            impact_tone = "risk"

        elif economic_score >= 60:
            scanner_action = "Tighten filters"
            position_guidance = "Reduced size"
            trade_filter = "Prefer liquid leaders only"
            impact_tone = "risk"

        elif economic_score >= 35:
            scanner_action = "Trade selectively"
            position_guidance = "Moderate reduction"
            trade_filter = "Confirm Market Pulse first"
            impact_tone = "warning"

        else:
            scanner_action = "Normal operation"
            position_guidance = "Standard sizing"
            trade_filter = "Use normal scanner rules"
            impact_tone = "good"

        economic_metric_grid(
            [
                {
                    "label": "Scanner Action",
                    "value": scanner_action,
                    "detail": "Recommended scanner posture.",
                    "tone": impact_tone,
                },
                {
                    "label": "Position Guidance",
                    "value": position_guidance,
                    "detail": "Suggested sizing behavior.",
                    "tone": impact_tone,
                },
                {
                    "label": "Trade Filter",
                    "value": trade_filter,
                    "detail": "How strict entries should be.",
                    "tone": impact_tone,
                },
            ],
            columns=3,
        )

        with st.expander("🔎 Raw Economic Calendar Result", expanded=False):
            st.caption(
                "Diagnostic view of the data returned by the economic calendar engine."
            )
            st.json(economic_calendar_result)

    except Exception as exc:
        st.error(
            f"Economic Calendar Risk panel failed: {exc}"
        )


def page() -> None:
    run_page()
