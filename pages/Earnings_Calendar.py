# =========================================================
# 🗓️ EARNINGS CALENDAR PAGE — v2.1
# JFBP Quant Desk
# Institutional Earnings Risk Panel
# Market Pulse + Scanner Risk Integration
# Responsive iPad / mobile layout + HTML card render fix
# =========================================================

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from engines.earnings_risk import (
    analyze_earnings_risk,
    sample_symbols,
)

try:
    from universe.jfbp_universe import JFBP_UNIVERSE
except Exception:
    JFBP_UNIVERSE = {}

try:
    from universe.ost_universe import OST_UNIVERSE
except Exception:
    OST_UNIVERSE = {}


# =========================================================
# RESPONSIVE UI HELPERS
# =========================================================

def inject_earnings_calendar_css() -> None:
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
                font-size: clamp(1.85rem, 4vw, 2.55rem) !important;
                font-weight: 850 !important;
                line-height: 1.12 !important;
                color: #1f2937 !important;
            }

            h2, h3 {
                font-size: clamp(1.12rem, 2.35vw, 1.55rem) !important;
                font-weight: 850 !important;
                line-height: 1.2 !important;
                color: #1f2937 !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.85rem !important;
                align-items: stretch !important;
            }

            div[data-testid="stHorizontalBlock"] > div,
            div[data-testid="column"] {
                min-width: 0 !important;
            }

            div[data-testid="stDataFrame"] {
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
            }

            div[data-testid="stDataFrame"] iframe,
            div[data-testid="stDataFrame"] > div {
                max-width: 100% !important;
            }

            div[data-testid="stAlert"] {
                overflow-wrap: anywhere !important;
                word-break: normal !important;
            }

            .earnings-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 0.85rem;
                margin: 0.65rem 0 1rem 0;
                width: 100%;
            }

            .earnings-card {
                border-radius: 14px;
                padding: 0.85rem 0.95rem;
                min-height: 104px;
                border: 1px solid #dbe3ef;
                background: #f8fafc;
                overflow: hidden;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }

            .earnings-card-label {
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.045em;
                color: #64748b;
                font-weight: 850;
                margin-bottom: 0.35rem;
                line-height: 1.25;
            }

            .earnings-card-value {
                font-size: clamp(1.20rem, 2.2vw, 1.55rem);
                line-height: 1.16;
                font-weight: 900;
                color: #111827;
                overflow-wrap: normal;
                word-break: normal;
            }

            .earnings-card-detail {
                font-size: 0.78rem;
                line-height: 1.35;
                color: #64748b;
                margin-top: 0.35rem;
                overflow-wrap: normal;
                word-break: normal;
            }

            .earnings-flow {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 14px;
                padding: 1rem;
                margin: 0.8rem 0 0.8rem 0;
                overflow-wrap: anywhere;
            }

            .earnings-safety {
                background: #fffbeb;
                border: 1px solid #fde68a;
                border-radius: 14px;
                padding: 1rem;
                margin: 0.8rem 0 0.8rem 0;
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

                .earnings-grid {
                    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                }
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem !important;
                    padding-right: 0.9rem !important;
                }

                .earnings-grid {
                    grid-template-columns: 1fr;
                }

                .earnings-card {
                    min-height: 92px;
                    padding: 0.78rem 0.86rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def responsive_columns(spec, gap: str = "small"):
    return st.columns(spec, gap=gap)


def _symbols_from_universe(universe) -> list:
    if isinstance(universe, dict) and universe:
        return sorted([
            str(symbol).upper().strip()
            for symbol in universe.keys()
            if str(symbol or "").strip()
        ])

    return sample_symbols()


def risk_tone(score: int) -> str:
    if score >= 80:
        return "risk"
    if score >= 60:
        return "risk"
    if score >= 35:
        return "warning"
    return "good"


def scanner_action_from_score(score: int, label: str) -> tuple[str, str, str]:
    label_text = str(label or "NONE").upper().strip()

    if score >= 80:
        return (
            "Avoid new entries",
            "Extreme earnings-event risk.",
            "risk",
        )

    if score >= 60:
        return (
            "Reduce size",
            "High earnings risk near the scanned universe.",
            "risk",
        )

    if score >= 35:
        return (
            "Trade selectively",
            "Medium earnings risk. Confirm dates before entry.",
            "warning",
        )

    if label_text in {"NONE", "LOW"}:
        return (
            "Normal posture",
            "No major earnings restriction from scanned symbols.",
            "good",
        )

    return (
        "Review risk",
        "Earnings risk requires manual review.",
        "warning",
    )


def earnings_metric_card(
    label: str,
    value: Any,
    detail: str = "",
    tone: str = "neutral",
) -> str:
    """Return one compact HTML card.

    Important: keep this string left-aligned/compact. Streamlit markdown can
    display indented multiline HTML as a code block on some browsers.
    """
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
    }

    background, border, value_color = palette.get(tone, palette["neutral"])

    label_text = html.escape(str(label))
    value_text = html.escape(str(value))
    detail_text = html.escape(str(detail))

    detail_html = (
        f'<div class="earnings-card-detail">{detail_text}</div>'
        if detail_text
        else ""
    )

    return (
        f'<div class="earnings-card" '
        f'style="background:{background};border-color:{border};">'
        f'<div class="earnings-card-label">{label_text}</div>'
        f'<div class="earnings-card-value" style="color:{value_color};">'
        f'{value_text}</div>'
        f'{detail_html}'
        f'</div>'
    )


def earnings_metric_grid(cards: list[dict]) -> None:
    """Render a responsive card grid without exposing raw HTML."""
    card_html = "".join(
        earnings_metric_card(
            card.get("label", ""),
            card.get("value", ""),
            card.get("detail", ""),
            card.get("tone", "neutral"),
        )
        for card in cards
    )

    st.markdown(
        f'<div class="earnings-grid">{card_html}</div>',
        unsafe_allow_html=True,
    )


def help_text(text: str) -> None:
    st.caption(f"💡 {text}")


# =========================================================
# PAGE
# =========================================================

def run_page() -> None:

    inject_earnings_calendar_css()

    st.title("🗓️ Earnings Calendar Risk")

    st.caption(
        "Stock-specific earnings-event risk layer. This page checks upcoming "
        "earnings dates and exports risk context into Market Pulse and Scanner controls."
    )

    st.markdown(
        """
        <div class="earnings-flow">
            <strong>Workflow:</strong><br>
            Earnings Calendar → Market Pulse Stress Model → Scanner Risk Controls → Research Stock → OMS Execution
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📘 How to use this page", expanded=False):
        st.markdown(
            """
            1. Select the universe you want to scan.
            2. Choose how many symbols to check.
            3. Refresh Earnings Risk.
            4. Review the highest-risk symbol and upcoming event table.
            5. Use the Scanner Impact section to decide whether to reduce size or avoid new entries.
            6. Always verify earnings dates before placing live orders.

            **Important:** this page uses free-source earnings data. Treat it as a risk-awareness layer, not an official exchange calendar.
            """
        )

    universe_options = [
        "JFBP",
        "CUSTOM",
        "SAMPLE",
    ]

    st.subheader("⚙️ Earnings Scan Controls")
    st.caption(
        "What it means: Selects which symbols are checked for upcoming earnings risk."
    )

    control_left, control_right = responsive_columns([1, 2])

    with control_left:
        universe_mode = st.selectbox(
            "Universe",
            universe_options,
            index=0,
            key="earnings_risk_universe_mode",
        )

    custom_symbols_raw = ""

    if universe_mode == "CUSTOM":
        with control_right:
            custom_symbols_raw = st.text_input(
                "Custom symbols, comma-separated",
                value="AAPL, MSFT, NVDA, AMZN, TSLA",
                key="earnings_risk_custom_symbols",
            )
    else:
        with control_right:
            st.info(
                f"Universe mode selected: {universe_mode}. Use CUSTOM to scan your own comma-separated symbols."
            )

    if universe_mode == "OST":
        symbols = _symbols_from_universe(OST_UNIVERSE)

    elif universe_mode == "CUSTOM":
        symbols = [
            item.upper().strip()
            for item in custom_symbols_raw.split(",")
            if item.strip()
        ]

    elif universe_mode == "SAMPLE":
        symbols = sample_symbols()

    else:
        symbols = _symbols_from_universe(JFBP_UNIVERSE)

    max_symbols = st.slider(
        "Max symbols to scan",
        min_value=1,
        max_value=max(1, min(100, len(symbols))),
        value=max(1, min(25, len(symbols))),
        step=1,
        key="earnings_risk_max_symbols",
    )

    selected_symbols = symbols[:max_symbols]

    refresh_btn = st.button(
        "Refresh Earnings Risk",
        use_container_width=True,
        key="earnings_risk_refresh_button",
    )

    if refresh_btn:
        st.cache_data.clear()

    try:
        with st.spinner("Checking earnings dates..."):
            result = _cached_analyze_earnings_risk(tuple(selected_symbols))

        score = int(result.get("earnings_risk_score", 0) or 0)
        label = str(result.get("earnings_risk_label", "NONE") or "NONE")

        # =====================================================
        # SCANNER / MARKET STRESS EXPORT
        # =====================================================

        st.session_state["earnings_risk_score"] = int(score)
        st.session_state["earnings_risk_label"] = str(label)

        highest_event = result.get("highest_risk_event")
        symbol_count = int(result.get("symbol_count", len(selected_symbols)) or 0)
        highest_symbol = "None"
        highest_days = "N/A"
        highest_status = "N/A"

        if highest_event:
            highest_symbol = str(highest_event.get("symbol", "N/A") or "N/A")
            highest_days = str(highest_event.get("days_until", "N/A") or "N/A")
            highest_status = str(highest_event.get("status", "N/A") or "N/A")

        action_text, action_detail, action_tone = scanner_action_from_score(
            score,
            label,
        )

        st.divider()
        st.subheader("🧠 Earnings Risk Brief")
        st.caption(
            "What it means: This is the stock-specific catalyst-risk input used by Market Pulse and Scanner risk controls."
        )

        earnings_metric_grid(
            [
                {
                    "label": "Earnings Risk",
                    "value": label,
                    "detail": "Current earnings-event state.",
                    "tone": risk_tone(score),
                },
                {
                    "label": "Risk Score",
                    "value": f"{score}/100",
                    "detail": "Contribution to event-risk model.",
                    "tone": risk_tone(score),
                },
                {
                    "label": "Symbols Checked",
                    "value": symbol_count,
                    "detail": f"Universe: {universe_mode}",
                    "tone": "info",
                },
                {
                    "label": "Highest Risk Symbol",
                    "value": highest_symbol,
                    "detail": f"Status: {highest_status}",
                    "tone": risk_tone(score),
                },
            ]
        )

        if score >= 80:
            st.error(
                "EXTREME earnings risk. Avoid new entries near earnings unless intentionally trading the event."
            )

        elif score >= 60:
            st.warning(
                "HIGH earnings risk. Position sizing should be reduced before earnings."
            )

        elif score >= 35:
            st.info(
                "MEDIUM earnings risk. Watch upcoming earnings dates and confirm symbols before entry."
            )

        else:
            st.success(
                "Earnings risk is low for the scanned symbols."
            )

        help_text(
            "Earnings Calendar contributes 15% of the Market Pulse stress model. "
            "Upcoming earnings can reduce scanner aggressiveness even when technical conditions look constructive."
        )

        events = result.get("events", [])

        st.divider()
        st.subheader("📋 Upcoming Earnings Events")
        st.caption(
            "What it means: Symbol-level earnings-event table used to identify catalyst risk before entering trades."
        )

        if events:
            event_df = pd.DataFrame(events)

            display_cols = [
                "symbol",
                "earnings_date",
                "days_until",
                "risk_label",
                "risk_score",
                "status",
                "source",
                "reason",
            ]

            display_cols = [
                col
                for col in display_cols
                if col in event_df.columns
            ]

            st.dataframe(
                event_df[display_cols],
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No earnings events returned for the selected symbols.")

        st.divider()
        st.subheader("🎯 Scanner Impact")
        st.caption(
            "What it means: Practical scanner and position-sizing guidance based on the current earnings-event risk."
        )

        earnings_metric_grid(
            [
                {
                    "label": "Scanner Action",
                    "value": action_text,
                    "detail": action_detail,
                    "tone": action_tone,
                },
                {
                    "label": "Position Sizing",
                    "value": (
                        "Reduce"
                        if score >= 35
                        else "Normal"
                    ),
                    "detail": "Suggested posture for new entries.",
                    "tone": action_tone,
                },
                {
                    "label": "Trade Filter",
                    "value": (
                        "Tighten"
                        if score >= 35
                        else "Normal"
                    ),
                    "detail": "How strict Scanner should be.",
                    "tone": action_tone,
                },
                {
                    "label": "Days to Highest Risk",
                    "value": highest_days,
                    "detail": f"Symbol: {highest_symbol}",
                    "tone": risk_tone(score),
                },
            ]
        )

        st.markdown(
            """
            <div class="earnings-safety">
                <strong>Safety reminder:</strong> Do not place new live trades near earnings unless the event risk is intentional. Confirm the date, symbol, side, quantity, and OMS mode before execution.
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("📊 Raw Earnings Risk Result", expanded=False):
            st.json(result)

    except Exception as exc:
        st.error(f"Earnings Risk page failed: {exc}")


@st.cache_data(
    ttl=900,
    show_spinner=False,
)
def _cached_analyze_earnings_risk(
    symbols: tuple,
) -> dict:

    return analyze_earnings_risk(list(symbols))
