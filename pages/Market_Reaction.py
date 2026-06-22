# =========================================================
# 🌎 MARKET PULSE PAGE — v88 iPad Card Grid Fix
# JFBP Quant Desk
# Public Dashboard + Event History
# Market Playbook + Regime Dashboard + Similar Events
# AI Market Brief + Education Layer v2 + Decision-First Right Rail
# Responsive Layout Pass v89 — iPad card grid standardization
# =========================================================

from __future__ import annotations

import math
import html

import pandas as pd
import streamlit as st

from core.responsive import inject_responsive_css, columns as jfbp_columns
from core.ui_cards import inject_card_css

from analytics.market_reaction import generate_market_reaction_report
from analytics.market_event_history import (
    save_market_event,
    load_recent_market_events,
)


# =========================================================
# HELPERS
# =========================================================

def help_text(text: str) -> None:
    st.caption(f"💡 {text}")



def inject_market_pulse_responsive_css() -> None:
    """Responsive layout guardrails for Market Pulse.

    Visual-only CSS. Does not change any calculations, signals, or exports.
    Keeps cards/tables usable on laptop, Safari, Opera, and narrow screens.
    """

    st.markdown(
        """
        <style>
            /* Page rhythm */
            .block-container {
                padding-top: 1.4rem;
                padding-bottom: 2.5rem;
                max-width: 1500px;
            }

            /* Let Streamlit tables shrink/scroll instead of forcing columns wide. */
            div[data-testid="stDataFrame"] {
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
            }

            div[data-testid="stDataFrame"] iframe,
            div[data-testid="stDataFrame"] > div {
                max-width: 100% !important;
            }

            /* Card text wrapping for Safari/Opera.
               Do NOT use overflow-wrap:anywhere here; it causes iPad cards
               to split words vertically (RISK_ON, Constructive, Calm Market). */
            div[data-testid="stMarkdownContainer"] div {
                overflow-wrap: break-word;
                word-break: normal;
            }

            /* Prevent metric/card rows from creating horizontal overflow. */
            div[data-testid="column"] {
                min-width: 0 !important;
            }

            div[data-testid="column"] .stMetric,
            div[data-testid="column"] [data-testid="stMetric"] {
                min-width: 0 !important;
            }

            /* Make alert boxes behave like responsive cards. */
            div[data-testid="stAlert"] {
                overflow-wrap: anywhere;
                word-break: normal;
            }

            /* iPad / tablet: stack Streamlit columns instead of squeezing cards.
               Market Pulse uses CSS grids for card rows, so stacked sections are cleaner. */
            @media (max-width: 1180px) {
                .block-container {
                    padding-left: 1.25rem;
                    padding-right: 1.25rem;
                }

                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                    gap: 0.85rem !important;
                }

                div[data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }
            }

            /* Mobile / narrow browser: one clean column, no empty right rail. */
            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem;
                    padding-right: 0.9rem;
                }

                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                    gap: 0.65rem !important;
                }

                div[data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }

                h1 {
                    font-size: 1.65rem !important;
                }

                h2, h3 {
                    line-height: 1.2 !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def responsive_columns(spec, gap: str = "small"):
    """Shared JFBP responsive column wrapper."""

    return jfbp_columns(spec, gap=gap)


def get_move(df, symbol: str):
    row = df[df["Symbol"] == symbol]

    if row.empty:
        return None

    try:
        return float(row.iloc[0]["Daily %"])
    except Exception:
        return None


def format_pct(value):
    if value is None:
        return "N/A"

    return f"{value:.2f}%"



def safe_float(value, default: float = 0.0) -> float:
    """Convert values from market data/session state into a safe finite float."""
    try:
        number = float(value)
    except Exception:
        return default

    if not math.isfinite(number):
        return default

    return number


def style_pct(val):
    try:
        val = float(val)
    except Exception:
        return ""

    if val > 0:
        return "color: green; font-weight: bold;"

    if val < 0:
        return "color: red; font-weight: bold;"

    return ""


def display_table(title: str, df):
    st.subheader(title)

    if df is None or df.empty:
        st.warning("No data available.")
        return

    styled = df.style.map(
        style_pct,
        subset=["Daily %"],
    )

    st.dataframe(
        styled,
        width="stretch",
        hide_index=True,
    )


def display_compact_market_table(title: str, df, max_rows: int | None = None) -> None:
    st.markdown(f"#### {title}")

    if df is None or df.empty:
        st.info("No data available.")
        return

    view_df = df.copy()

    if max_rows is not None:
        view_df = view_df.head(max_rows)

    if "Daily %" in view_df.columns:
        styled = view_df.style.map(
            style_pct,
            subset=["Daily %"],
        )
    else:
        styled = view_df

    st.dataframe(
        styled,
        width="stretch",
        hide_index=True,
        height=260,
    )


def pulse_metric_card(
    label: str,
    value,
    detail: str = "",
    tone: str = "neutral",
) -> None:
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
    }

    background, border, value_color = palette.get(
        tone,
        palette["neutral"],
    )

    label_text = html.escape(str(label))
    value_text = html.escape(str(value))
    detail_text = html.escape(str(detail))

    detail_html = (
        f'<div style="font-size:0.78rem;color:#64748b;margin-top:0.35rem;">{detail_text}</div>'
        if detail_text
        else ""
    )

    card_html = f"""
        <div style="
            background:{background};
            border:1px solid {border};
            border-radius:12px;
            padding:0.72rem 0.82rem;
            margin-bottom:0.55rem;
        ">
            <div style="
                font-size:0.72rem;
                text-transform:uppercase;
                letter-spacing:0.04em;
                color:#64748b;
                font-weight:700;
                margin-bottom:0.25rem;
            ">{label_text}</div>
            <div style="
                font-size:clamp(1.05rem, 2.2vw, 1.35rem);
                line-height:1.18;
                font-weight:800;
                color:{value_color};
                overflow-wrap:normal;
                word-break:normal;
                white-space:normal;
            ">{value_text}</div>
            {detail_html}
        </div>
    """

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )




def pulse_metric_card_html(
    label: str,
    value,
    detail: str = "",
    tone: str = "neutral",
) -> str:
    """Return the same pulse card as HTML so several cards can live in a CSS grid."""

    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
    }

    background, border, value_color = palette.get(
        tone,
        palette["neutral"],
    )

    label_text = html.escape(str(label))
    value_text = html.escape(str(value))
    detail_text = html.escape(str(detail))

    detail_html = (
        f'<div class="pulse-grid-card-detail">{detail_text}</div>'
        if detail_text
        else ""
    )

    return f'''
        <div class="pulse-grid-card" style="background:{background};border-color:{border};">
            <div class="pulse-grid-card-label">{label_text}</div>
            <div class="pulse-grid-card-value" style="color:{value_color};">{value_text}</div>
            {detail_html}
        </div>
    '''


def pulse_metric_grid(
    cards: list[dict],
    min_width: int = 220,
) -> None:
    """Responsive metric grid for Market Pulse."""

    card_html = "".join(
        pulse_metric_card_html(
            card.get("label", ""),
            card.get("value", ""),
            card.get("detail", ""),
            card.get("tone", "neutral"),
        )
        for card in cards
    )

    grid_html = f'''
        <style>
            .pulse-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, {min_width}px), 1fr));
                gap: 0.65rem;
                margin: 0.35rem 0 0.65rem 0;
                width: 100%;
                min-width: 0;
            }}

            .pulse-grid-card {{
                border: 1px solid;
                border-radius: 14px;
                padding: 0.72rem 0.82rem;
                min-width: 0;
                width: 100%;
                box-sizing: border-box;
                overflow: hidden;
            }}

            .pulse-grid-card-label {{
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #64748b;
                font-weight: 800;
                margin-bottom: 0.28rem;
                line-height: 1.25;
                overflow-wrap: normal;
                word-break: normal;
            }}

            .pulse-grid-card-value {{
                font-size: clamp(1.05rem, 2.2vw, 1.45rem);
                line-height: 1.15;
                font-weight: 850;
                overflow-wrap: normal;
                word-break: normal;
                white-space: normal;
            }}

            .pulse-grid-card-detail {{
                font-size: 0.78rem;
                color: #64748b;
                margin-top: 0.35rem;
                line-height: 1.35;
                overflow-wrap: normal;
                word-break: normal;
            }}

            @media (max-width: 760px) {{
                .pulse-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>

        <div class="pulse-grid">
            {card_html}
        </div>
    '''

    st.markdown(
        grid_html,
        unsafe_allow_html=True,
    )


def pulse_list_card_html(
    title: str,
    rows: list[tuple[str, str]],
    tone: str = "neutral",
) -> str:
    """Return a responsive list-card HTML block."""

    palette = {
        "neutral": ("#f8fafc", "#dbe3ef"),
        "good": ("#ecfdf5", "#bbf7d0"),
        "warning": ("#fffbeb", "#fde68a"),
        "risk": ("#fef2f2", "#fecaca"),
        "info": ("#eff6ff", "#bfdbfe"),
    }

    background, border = palette.get(
        tone,
        palette["neutral"],
    )

    title_text = html.escape(str(title))
    row_html = ""

    for label, value in rows:
        row_html += (
            '<div class="pulse-list-row">'
            f'<div class="pulse-list-label">{html.escape(str(label))}</div>'
            f'<div class="pulse-list-value">{html.escape(str(value))}</div>'
            '</div>'
        )

    return (
        f'<div class="pulse-list-card" '
        f'style="background:{background};border-color:{border};">'
        f'<div class="pulse-list-title">{title_text}</div>'
        f'{row_html}'
        f'</div>'
    )


def pulse_list_grid(
    cards: list[dict],
    min_width: int = 280,
) -> None:
    """Responsive list-card grid for guidance sections."""

    cards_html = "".join(
        pulse_list_card_html(
            card.get("title", ""),
            card.get("rows", []),
            card.get("tone", "neutral"),
        )
        for card in cards
    )

    grid_html = f'''
        <style>
            .pulse-list-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, {min_width}px), 1fr));
                gap: 0.75rem;
                margin: 0.45rem 0 0.75rem 0;
                width: 100%;
                min-width: 0;
            }}

            .pulse-list-card {{
                border: 1px solid;
                border-radius: 16px;
                padding: 0.85rem 0.95rem;
                min-width: 0;
                width: 100%;
                box-sizing: border-box;
                overflow: hidden;
            }}

            .pulse-list-title {{
                font-size: 1.02rem;
                font-weight: 850;
                color: #1f2937;
                margin-bottom: 0.62rem;
                line-height: 1.2;
                overflow-wrap: normal;
                word-break: normal;
            }}

            .pulse-list-row {{
                display: grid;
                grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.35fr);
                gap: 0.65rem;
                align-items: start;
                border-bottom: 1px solid rgba(148, 163, 184, 0.28);
                padding: 0.38rem 0;
                min-width: 0;
            }}

            .pulse-list-row:last-child {{
                border-bottom: none;
            }}

            .pulse-list-label {{
                color: #64748b;
                font-weight: 750;
                line-height: 1.28;
                min-width: 0;
                overflow-wrap: normal;
                word-break: normal;
            }}

            .pulse-list-value {{
                color: #1f2937;
                font-weight: 850;
                line-height: 1.28;
                min-width: 0;
                overflow-wrap: normal;
                word-break: normal;
            }}

            @media (max-width: 1180px) {{
                .pulse-list-grid {{
                    grid-template-columns: 1fr;
                }}

                .pulse-list-row {{
                    grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.45fr);
                }}
            }}

            @media (max-width: 760px) {{
                .pulse-list-row {{
                    grid-template-columns: 1fr;
                    gap: 0.16rem;
                }}
            }}
        </style>

        <div class="pulse-list-grid">
            {cards_html}
        </div>
    '''

    st.markdown(
        grid_html,
        unsafe_allow_html=True,
    )


def pulse_list_card(
    title: str,
    rows: list[tuple[str, str]],
    tone: str = "neutral",
) -> None:
    """Single responsive list card."""

    pulse_list_grid(
        [
            {
                "title": title,
                "rows": rows,
                "tone": tone,
            }
        ],
        min_width=280,
    )

def stress_tone(score: int) -> str:
    if score > 65:
        return "risk"
    if score >= 35:
        return "warning"
    return "good"


def breadth_tone(score: float) -> str:
    if score < 40:
        return "risk"
    if score <= 60:
        return "warning"
    return "good"


def regime_tone(regime: str) -> str:
    regime_key = str(regime or "").upper().strip()

    if regime_key in ("DEFENSIVE", "RISK_OFF", "RISK-OFF"):
        return "risk"

    if regime_key in ("CAUTIOUS", "SELECTIVE"):
        return "warning"

    if regime_key in ("RISK_ON", "RISK-ON"):
        return "good"

    return "neutral"


def regime_icon(regime: str) -> str:
    tone = regime_tone(regime)

    if tone == "good":
        return "🟢"

    if tone == "warning":
        return "🟡"

    if tone == "risk":
        return "🔴"

    return "⚪"


def command_status_pill(regime: str, stress_score: int, breadth_score: float) -> None:
    tone = regime_tone(regime)

    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#334155"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
    }

    background, border, text_color = palette.get(
        tone,
        palette["neutral"],
    )

    regime_text = html.escape(str(regime or "N/A"))
    icon = regime_icon(regime)

    pill_html = f"""
        <div style="
            display:inline-flex;
            align-items:center;
            gap:0.55rem;
            background:{background};
            border:1px solid {border};
            color:{text_color};
            border-radius:999px;
            padding:0.35rem 0.75rem;
            font-weight:800;
            margin:0.25rem 0 0.75rem 0;
        ">
            <span>{icon}</span>
            <span>Command Status: {regime_text}</span>
            <span style="color:#64748b;font-weight:650;">Stress {stress_score}/100</span>
            <span style="color:#64748b;font-weight:650;">Breadth {breadth_score:.1f}/100</span>
        </div>
    """

    st.markdown(
        pill_html,
        unsafe_allow_html=True,
    )


def calculate_market_stress(indexes, sectors) -> tuple[int, str]:

    qqq = get_move(indexes, "QQQ")
    spy = get_move(indexes, "SPY")
    iwm = get_move(indexes, "IWM")
    vixy = get_move(indexes, "VIXY")
    xlk = get_move(sectors, "XLK")

    score = 0

    if qqq is not None:
        score += min(abs(min(qqq, 0)) * 10, 30)

    if spy is not None:
        score += min(abs(min(spy, 0)) * 8, 25)

    if iwm is not None:
        score += min(abs(min(iwm, 0)) * 5, 15)

    if xlk is not None:
        score += min(abs(min(xlk, 0)) * 5, 15)

    if vixy is not None and vixy > 0:
        score += min(vixy * 2, 15)

    score = safe_float(score, default=0.0)
    score = int(max(0, min(score, 100)))

    if score >= 80:
        label = "Severe Stress"
    elif score >= 60:
        label = "High Stress"
    elif score >= 40:
        label = "Moderate Stress"
    elif score >= 20:
        label = "Low Stress"
    else:
        label = "Calm Market"

    return score, label


def calculate_market_breadth(
    indexes: pd.DataFrame,
    sectors: pd.DataFrame,
    megacaps: pd.DataFrame,
) -> dict:

    market_etfs = pd.DataFrame(
        [
            {"Symbol": "QQQ", "Daily %": get_move(indexes, "QQQ")},
            {"Symbol": "SPY", "Daily %": get_move(indexes, "SPY")},
            {"Symbol": "IWM", "Daily %": get_move(indexes, "IWM")},
            {"Symbol": "SOXX", "Daily %": get_move(indexes, "SOXX")},
            {"Symbol": "VIXY", "Daily %": get_move(indexes, "VIXY")},
            {"Symbol": "DIA", "Daily %": get_move(indexes, "DIA")},
            {"Symbol": "TLT", "Daily %": get_move(indexes, "TLT")},
            {"Symbol": "GLD", "Daily %": get_move(indexes, "GLD")},
            {"Symbol": "UUP", "Daily %": get_move(indexes, "UUP")},
            {"Symbol": "HYG", "Daily %": get_move(indexes, "HYG")},
        ]
    )

    breadth_groups = [
        {
            "Group": "Market ETFs",
            "Data": market_etfs,
        },
        {
            "Group": "Sectors",
            "Data": sectors,
        },
        {
            "Group": "Megacaps",
            "Data": megacaps,
        },
    ]

    breadth_rows = []

    for breadth_group in breadth_groups:

        group_name = breadth_group.get("Group")
        group_df = breadth_group.get("Data")

        if group_df is None or group_df.empty:
            continue

        if "Daily %" not in group_df.columns:
            continue

        clean_group_df = group_df.copy()

        clean_group_df["Daily %"] = pd.to_numeric(
            clean_group_df["Daily %"],
            errors="coerce",
        )

        valid_rows = clean_group_df.dropna(
            subset=["Daily %"],
        )

        if valid_rows.empty:
            continue

        total_count = len(valid_rows)
        advancing_count = int((valid_rows["Daily %"] > 0).sum())
        declining_count = int((valid_rows["Daily %"] < 0).sum())
        flat_count = int((valid_rows["Daily %"] == 0).sum())

        average_move = float(valid_rows["Daily %"].mean())
        median_move = float(valid_rows["Daily %"].median())

        advance_pct = (
            advancing_count / total_count
        ) * 100

        decline_pct = (
            declining_count / total_count
        ) * 100

        breadth_rows.append(
            {
                "Group": group_name,
                "Total": total_count,
                "Advancing": advancing_count,
                "Declining": declining_count,
                "Flat": flat_count,
                "Advance %": round(advance_pct, 1),
                "Decline %": round(decline_pct, 1),
                "Average Move %": round(average_move, 2),
                "Median Move %": round(median_move, 2),
            }
        )

    breadth_df = pd.DataFrame(breadth_rows)

    if breadth_df.empty:
        return {
            "df": breadth_df,
            "score": 50.0,
            "state": "Unknown",
            "total_names": 0,
            "total_advancing": 0,
            "total_declining": 0,
            "market_advance_pct": 0.0,
            "market_decline_pct": 0.0,
            "average_group_move": 0.0,
        }

    total_names = int(breadth_df["Total"].sum())
    total_advancing = int(breadth_df["Advancing"].sum())
    total_declining = int(breadth_df["Declining"].sum())

    market_advance_pct = (
        total_advancing / total_names
    ) * 100 if total_names else 0.0

    market_decline_pct = (
        total_declining / total_names
    ) * 100 if total_names else 0.0

    average_group_move = float(
        breadth_df["Average Move %"].mean()
    )

    breadth_score = round(
        (
            market_advance_pct * 0.70
            + max(0.0, average_group_move + 2.0) / 4.0 * 30.0
        ),
        1,
    )

    breadth_score = max(
        0.0,
        min(
            100.0,
            breadth_score,
        ),
    )

    if breadth_score >= 70:
        breadth_state = "Bullish Participation"
    elif breadth_score >= 55:
        breadth_state = "Constructive"
    elif breadth_score >= 40:
        breadth_state = "Mixed / Selective"
    elif breadth_score >= 25:
        breadth_state = "Weak Breadth"
    else:
        breadth_state = "Broad Damage"

    return {
        "df": breadth_df,
        "score": breadth_score,
        "state": breadth_state,
        "total_names": total_names,
        "total_advancing": total_advancing,
        "total_declining": total_declining,
        "market_advance_pct": market_advance_pct,
        "market_decline_pct": market_decline_pct,
        "average_group_move": average_group_move,
    }


def calculate_impact_label(portfolio_move: float) -> str:
    abs_move = abs(portfolio_move)

    if abs_move >= 2.0:
        return "HIGH"

    if abs_move >= 1.0:
        return "MODERATE"

    return "LOW"


def calculate_buy_the_dip_score(
    indexes,
    sectors,
    stress_score: int,
) -> tuple[int, str]:

    qqq = get_move(indexes, "QQQ")
    spy = get_move(indexes, "SPY")
    soxx = get_move(indexes, "SOXX")
    vixy = get_move(indexes, "VIXY")
    xlk = get_move(sectors, "XLK")

    score = 0

    if qqq is not None:
        score += min(abs(min(qqq, 0)) * 8, 30)

    if spy is not None:
        score += min(abs(min(spy, 0)) * 5, 20)

    if soxx is not None:
        score += min(abs(min(soxx, 0)) * 6, 25)

    if xlk is not None:
        score += min(abs(min(xlk, 0)) * 4, 15)

    if vixy is not None and vixy > 0:
        score += min(vixy, 15)

    score += min(stress_score // 5, 10)

    score = safe_float(score, default=0.0)
    score = int(max(0, min(score, 100)))

    if score >= 80:
        label = "Exceptional"
    elif score >= 60:
        label = "Attractive"
    elif score >= 40:
        label = "Watchlist"
    elif score >= 20:
        label = "Neutral"
    else:
        label = "Overheated"

    return score, label


def build_market_playbook(
    event_label: str,
    dip_score: int,
) -> tuple[str, str, str, str]:

    if "Semiconductor" in event_label:

        duration = "1–5 Trading Days"
        risk = "Medium"

        if dip_score >= 80:
            opportunity = "9/10"
            action = (
                "Accumulation is favored for quality tech, broad-market ETFs, "
                "and dividend-growth positions. Avoid leverage until market "
                "stress falls below 70."
            )
        elif dip_score >= 60:
            opportunity = "7/10"
            action = (
                "Scale in slowly. Favor quality and avoid chasing weak rebounds."
            )
        else:
            opportunity = "5/10"
            action = (
                "Watch for stabilization before adding risk."
            )

    elif "Risk-Off" in event_label:

        duration = "1–3 Weeks"
        risk = "High"

        if dip_score >= 70:
            opportunity = "7/10"
            action = (
                "Selective buying is reasonable, but keep cash available. "
                "Wait for broad stabilization before aggressive adds."
            )
        else:
            opportunity = "5/10"
            action = (
                "Remain defensive. Avoid forced buying until volatility cools."
            )

    elif "Defensive" in event_label:

        duration = "Several Sessions"
        risk = "Medium"
        opportunity = "6/10"
        action = (
            "Market is rotating away from growth. Favor quality, dividends, "
            "and defensive sectors until leadership improves."
        )

    elif "Energy" in event_label:

        duration = "Several Sessions"
        risk = "Medium"
        opportunity = "6/10"
        action = (
            "Rotation favors energy. Avoid assuming broad market strength "
            "unless SPY and QQQ confirm."
        )

    elif "Volatility" in event_label:

        duration = "1–10 Trading Days"
        risk = "High"
        opportunity = "6/10"
        action = (
            "Volatility is elevated. Scale entries, avoid leverage, and wait "
            "for confirmation before increasing exposure."
        )

    else:

        duration = "Unknown"
        risk = "Low"
        opportunity = "5/10"
        action = (
            "No major shock detected. Monitor conditions without forcing trades."
        )

    return duration, risk, opportunity, action


def build_playbook_df(
    event,
    dip_score: int,
    dip_label: str,
) -> pd.DataFrame:

    duration, risk, opportunity, action = build_market_playbook(
        event.label,
        dip_score,
    )

    return pd.DataFrame(
        [
            {"Metric": "Event", "Reading": event.label},
            {"Metric": "Buy-The-Dip Score", "Reading": f"{dip_score}/100"},
            {"Metric": "Opportunity", "Reading": dip_label},
            {"Metric": "Typical Duration", "Reading": duration},
            {"Metric": "Risk Level", "Reading": risk},
            {"Metric": "Opportunity Rating", "Reading": opportunity},
            {"Metric": "Suggested Action", "Reading": action},
        ]
    )


def all_values_negative(df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False

    values = pd.to_numeric(df["Daily %"], errors="coerce").dropna()

    if values.empty:
        return False

    return bool((values < 0).all())


def get_top_name(df: pd.DataFrame, strongest: bool = True) -> str:
    if df is None or df.empty:
        return "N/A"

    sorted_df = df.sort_values(
        "Daily %",
        ascending=not strongest,
        na_position="last",
    )

    row = sorted_df.iloc[0]

    return f"{row['Name']} ({format_pct(row['Daily %'])})"


def get_market_regime(
    indexes,
    sectors,
    stress_score: int,
) -> dict:

    qqq = get_move(indexes, "QQQ")
    spy = get_move(indexes, "SPY")
    iwm = get_move(indexes, "IWM")
    soxx = get_move(indexes, "SOXX")
    vixy = get_move(indexes, "VIXY")

    tlt = get_move(indexes, "TLT")
    gld = get_move(indexes, "GLD")
    uup = get_move(indexes, "UUP")
    hyg = get_move(indexes, "HYG")

    xlk = get_move(sectors, "XLK")
    xlp = get_move(sectors, "XLP")
    xlu = get_move(sectors, "XLU")
    xlv = get_move(sectors, "XLV")

    defensive_avg = pd.Series(
        [
            x for x in [xlp, xlu, xlv]
            if x is not None
        ]
    )

    defensive_score = (
        float(defensive_avg.mean())
        if not defensive_avg.empty
        else None
    )

    if stress_score >= 80:
        breadth_damage = "Severe"
    elif stress_score >= 60:
        breadth_damage = "High"
    elif stress_score >= 40:
        breadth_damage = "Moderate"
    else:
        breadth_damage = "Contained"

    if vixy is not None and vixy >= 5:
        volatility_regime = "Elevated"
    elif vixy is not None and vixy >= 2:
        volatility_regime = "Rising"
    else:
        volatility_regime = "Normal"

    if qqq is not None and spy is not None and qqq < spy:
        growth_vs_value = "Growth Underperforming"
    elif qqq is not None and spy is not None and qqq > spy:
        growth_vs_value = "Growth Leading"
    else:
        growth_vs_value = "Neutral"

    if defensive_score is not None and xlk is not None and defensive_score > xlk:
        rotation = "Defensive Rotation"
    else:
        rotation = "No Clear Defensive Rotation"

    if iwm is not None and spy is not None and iwm < spy:
        small_caps = "Small Caps Weak"
    elif iwm is not None and spy is not None and iwm > spy:
        small_caps = "Small Caps Leading"
    else:
        small_caps = "Neutral"

    if soxx is not None and soxx <= -2:
        semis = "Semiconductors Risk-Off"
    elif soxx is not None and soxx > 0:
        semis = "Semiconductors Risk-On"
    else:
        semis = "Neutral"

    if hyg is not None and hyg < 0:
        credit = "Credit Weak"
    elif hyg is not None and hyg > 0:
        credit = "Credit Stable"
    else:
        credit = "N/A"

    if tlt is not None and tlt > 0:
        bonds = "Bonds Bid"
    elif tlt is not None and tlt < 0:
        bonds = "Bonds Weak"
    else:
        bonds = "N/A"

    if gld is not None and gld > 0:
        gold = "Gold Bid"
    elif gld is not None and gld < 0:
        gold = "Gold Weak"
    else:
        gold = "N/A"

    if uup is not None and uup > 0:
        dollar = "Dollar Strong"
    elif uup is not None and uup < 0:
        dollar = "Dollar Weak"
    else:
        dollar = "N/A"

    if (
        stress_score >= 70
        and qqq is not None and qqq < 0
        and spy is not None and spy < 0
    ):
        overall = "Risk-Off / Defensive"
    elif qqq is not None and qqq > 0 and spy is not None and spy > 0:
        overall = "Risk-On"
    else:
        overall = "Mixed"

    return {
        "Overall Regime": overall,
        "Breadth Damage": breadth_damage,
        "Volatility Regime": volatility_regime,
        "Growth vs Value": growth_vs_value,
        "Rotation": rotation,
        "Small Caps": small_caps,
        "Semiconductors": semis,
        "Credit": credit,
        "Bonds": bonds,
        "Gold": gold,
        "Dollar": dollar,
    }


def build_event_scorecard(
    event,
    indexes,
    sectors,
    stress_score: int,
    stress_label: str,
) -> pd.DataFrame:

    regime = get_market_regime(
        indexes=indexes,
        sectors=sectors,
        stress_score=stress_score,
    )

    leadership = get_top_name(
        sectors,
        strongest=True,
    )

    weakest_group = get_top_name(
        sectors,
        strongest=False,
    )

    rows = [
        {"Metric": "Event Type", "Reading": event.label},
        {"Metric": "Market Stress", "Reading": f"{stress_score}/100 — {stress_label}"},
        {"Metric": "Leadership", "Reading": leadership},
        {"Metric": "Weakest Group", "Reading": weakest_group},
        {"Metric": "Overall Regime", "Reading": regime["Overall Regime"]},
        {"Metric": "Breadth Damage", "Reading": regime["Breadth Damage"]},
        {"Metric": "Volatility Regime", "Reading": regime["Volatility Regime"]},
        {"Metric": "Growth vs Value", "Reading": regime["Growth vs Value"]},
        {"Metric": "Rotation", "Reading": regime["Rotation"]},
        {"Metric": "Small Caps", "Reading": regime["Small Caps"]},
        {"Metric": "Semiconductors", "Reading": regime["Semiconductors"]},
    ]

    return pd.DataFrame(rows)


def build_regime_dashboard_df(
    indexes,
    sectors,
    stress_score: int,
) -> pd.DataFrame:

    regime = get_market_regime(
        indexes=indexes,
        sectors=sectors,
        stress_score=stress_score,
    )

    rows = [
        {"Regime Component": "Overall Market", "Reading": regime["Overall Regime"]},
        {"Regime Component": "Technology / Growth", "Reading": regime["Growth vs Value"]},
        {"Regime Component": "Semiconductors", "Reading": regime["Semiconductors"]},
        {"Regime Component": "Small Caps", "Reading": regime["Small Caps"]},
        {"Regime Component": "Defensives", "Reading": regime["Rotation"]},
        {"Regime Component": "Volatility", "Reading": regime["Volatility Regime"]},
        {"Regime Component": "Credit", "Reading": regime["Credit"]},
        {"Regime Component": "Bonds", "Reading": regime["Bonds"]},
        {"Regime Component": "Gold", "Reading": regime["Gold"]},
        {"Regime Component": "Dollar", "Reading": regime["Dollar"]},
    ]

    return pd.DataFrame(rows)


def build_market_decision_support(
    event,
    stress_score: int,
    stress_label: str,
    breadth_score: float,
    breadth_state: str,
    dip_score: int,
    dip_label: str,
    scanner_regime: str,
    scanner_execution_multiplier: float,
    scanner_buy_allowed: bool,
) -> dict:

    regime_key = str(scanner_regime or "").upper().strip()

    if regime_key == "DEFENSIVE":
        current_regime = "Institutional Risk-Off / Defensive"
        recommended_exposure = "25–50%"
        recommended_position_size = f"{scanner_execution_multiplier:.2f}x"
        expected_duration = "1–3 Weeks"
        primary_action = "Protect capital and reduce new long exposure."
        action_items = [
            "Reduce or pause new long entries",
            "Favor defensive sectors and high-quality holdings",
            "Keep cash available for better breadth confirmation",
            "Avoid leverage and oversized position adds",
            "Wait for breadth to improve before restoring normal exposure",
        ]

    elif regime_key == "CAUTIOUS":
        current_regime = "Weak Breadth / Cautious"
        recommended_exposure = "40–65%"
        recommended_position_size = f"{scanner_execution_multiplier:.2f}x"
        expected_duration = "Several Sessions to 2 Weeks"
        primary_action = "Trade selectively and keep position size reduced."
        action_items = [
            "Take only the highest-quality setups",
            "Avoid chasing weak rebounds",
            "Keep stops and risk limits tight",
            "Prefer liquid leaders over laggards",
            "Increase exposure only if breadth improves",
        ]

    elif regime_key == "SELECTIVE":
        current_regime = "Mixed / Selective"
        recommended_exposure = "50–75%"
        recommended_position_size = f"{scanner_execution_multiplier:.2f}x"
        expected_duration = "Several Sessions"
        primary_action = "Let sector leadership drive trade selection."
        action_items = [
            "Focus on relative-strength sectors",
            "Avoid broad-market assumptions",
            "Use normal screening but reduced conviction",
            "Let winners confirm before adding",
            "Watch breadth for confirmation or deterioration",
        ]

    elif regime_key in {"RISK_ON", "RISK-ON"}:
        current_regime = "Risk-On"
        recommended_exposure = "80–100%"
        recommended_position_size = f"{scanner_execution_multiplier:.2f}x"
        expected_duration = "Trend Dependent"
        primary_action = "Normal scanner exposure is allowed."
        action_items = [
            "Allow normal qualified long setups",
            "Favor leaders with strong relative strength",
            "Let winners compound while risk remains contained",
            "Avoid overtrading extended names",
            "Monitor stress and breadth for deterioration",
        ]

    elif regime_key == "RISK_OFF":
        current_regime = "Institutional Risk-Off"
        recommended_exposure = "25–50%"
        recommended_position_size = f"{scanner_execution_multiplier:.2f}x"
        expected_duration = "1–3 Weeks"
        primary_action = "Stay defensive until market stress cools."
        action_items = [
            "Reduce new longs",
            "Favor cash and defensive exposure",
            "Do not average down weak names aggressively",
            "Use smaller position sizes",
            "Wait for volatility and breadth stabilization",
        ]

    else:
        current_regime = "Neutral / Mixed"
        recommended_exposure = "65–85%"
        recommended_position_size = f"{scanner_execution_multiplier:.2f}x"
        expected_duration = "Unclear"
        primary_action = "Trade normally but avoid forcing setups."
        action_items = [
            "Use standard scanner filters",
            "Avoid forcing trades without confirmation",
            "Watch breadth and stress for directional clues",
            "Keep normal risk controls active",
            "Let price action confirm leadership",
        ]

    decision_rows = [
        {"Decision Component": "Current Regime", "Reading": current_regime},
        {"Decision Component": "Event Type", "Reading": str(getattr(event, "label", "") or "N/A")},
        {"Decision Component": "Event Confidence", "Reading": f"{getattr(event, 'confidence', 0) or 0}%"},
        {"Decision Component": "Market Stress", "Reading": f"{stress_score}/100 — {stress_label}"},
        {"Decision Component": "Breadth", "Reading": f"{breadth_score:.1f}/100 — {breadth_state}"},
        {"Decision Component": "Buy-The-Dip", "Reading": f"{dip_score}/100 — {dip_label}"},
        {"Decision Component": "Recommended Exposure", "Reading": recommended_exposure},
        {"Decision Component": "Recommended Position Size", "Reading": recommended_position_size},
        {"Decision Component": "Expected Duration", "Reading": expected_duration},
        {"Decision Component": "Primary Action", "Reading": primary_action},
    ]

    action_rows = [
        {"Priority": index + 1, "Recommended Action": action}
        for index, action in enumerate(action_items)
    ]

    return {
        "current_regime": current_regime,
        "recommended_exposure": recommended_exposure,
        "recommended_position_size": recommended_position_size,
        "expected_duration": expected_duration,
        "primary_action": primary_action,
        "buy_allowed_text": "Yes" if scanner_buy_allowed else "No",
        "decision_df": pd.DataFrame(decision_rows),
        "actions_df": pd.DataFrame(action_rows),
    }


def build_market_summary(
    event,
    indexes,
    sectors,
    megacaps,
    stress_score: int,
    stress_label: str,
) -> str:

    qqq = get_move(indexes, "QQQ")
    spy = get_move(indexes, "SPY")
    vixy = get_move(indexes, "VIXY")
    soxx = get_move(indexes, "SOXX")

    weakest_megacaps = megacaps.sort_values(
        "Daily %",
        ascending=True,
        na_position="last",
    ).head(3)

    strongest_sectors = sectors.sort_values(
        "Daily %",
        ascending=False,
        na_position="last",
    ).head(3)

    weak_names = [
        f"{row['Symbol']} {format_pct(row['Daily %'])}"
        for _, row in weakest_megacaps.iterrows()
    ]

    strong_names = [
        f"{row['Name']} {format_pct(row['Daily %'])}"
        for _, row in strongest_sectors.iterrows()
    ]

    soxx_text = (
        f", SOXX is {format_pct(soxx)}"
        if soxx is not None
        else ""
    )

    return (
        f"{event.label} detected. "
        f"QQQ is {format_pct(qqq)}, SPY is {format_pct(spy)}"
        f"{soxx_text}, and VIXY is {format_pct(vixy)}. "
        f"The weakest megacaps are {', '.join(weak_names)}. "
        f"The strongest sectors are {', '.join(strong_names)}. "
        f"Market stress is {stress_score}/100 — {stress_label}."
    )




# =========================================================
# AI MARKET BRIEF
# =========================================================

def build_ai_market_brief(
    event,
    stress_score: int,
    stress_label: str,
    breadth_score: float,
    breadth_state: str,
    scanner_regime: str,
    scanner_execution_multiplier: float,
    dip_score: int,
    dip_label: str,
    best_sector: str,
    best_sector_move: str,
    best_mega: str,
    best_mega_move: str,
) -> dict:

    regime_key = str(scanner_regime or "").upper().strip()

    if regime_key in ("RISK_ON", "RISK-ON"):
        bias = "Constructive / Risk-On"
        tone = "good"
        setup = "breakouts, relative-strength leaders, and trend continuation"
        avoid = "bottom fishing weak names or chasing extended laggards"
        conclusion = (
            "The market structure remains healthy enough for normal long exposure."
        )

    elif regime_key in ("CAUTIOUS", "SELECTIVE"):
        bias = "Selective / Cautious"
        tone = "warning"
        setup = "only the strongest relative-strength setups"
        avoid = "weak sectors, low-quality rebounds, and oversized positions"
        conclusion = (
            "The market is tradable, but selectivity matters more than aggression."
        )

    elif regime_key in ("DEFENSIVE", "RISK_OFF", "RISK-OFF"):
        bias = "Defensive / Risk-Off"
        tone = "risk"
        setup = "capital protection, smaller size, and only exceptional A+ setups"
        avoid = "new broad long exposure and averaging down weak stocks"
        conclusion = (
            "Risk control should take priority until stress cools and breadth improves."
        )

    else:
        bias = "Neutral / Mixed"
        tone = "info"
        setup = "confirmed setups with clear leadership"
        avoid = "forcing trades without confirmation"
        conclusion = (
            "Conditions are mixed, so price confirmation should lead decision-making."
        )

    event_label = str(
        getattr(
            event,
            "label",
            "N/A",
        )
        or "N/A"
    )

    event_confidence = getattr(
        event,
        "confidence",
        0,
    ) or 0

    brief = (
        f"Market Pulse is currently reading **{bias}**. "
        f"The active regime is **{scanner_regime}**, market stress is "
        f"**{stress_score}/100 ({stress_label})**, and breadth is "
        f"**{breadth_score:.1f}/100 ({breadth_state})**. "
        f"The main event read is **{event_label}** with "
        f"**{event_confidence}% confidence**. "
        f"Leadership is currently strongest in **{best_sector}** "
        f"({best_sector_move}) with **{best_mega}** leading megacaps "
        f"({best_mega_move}). "
        f"Current conditions favor **{setup}**. Avoid **{avoid}**. "
        f"Suggested position size is **{scanner_execution_multiplier:.2f}x**. "
        f"Buy-the-dip score is **{dip_score}/100 ({dip_label})**. "
        f"{conclusion}"
    )

    playbook = (
        f"Scope of the day: {bias}. "
        f"Focus on {best_sector} leadership and {best_mega} among megacaps. "
        f"Use {scanner_execution_multiplier:.2f}x sizing unless stress or breadth deteriorates."
    )

    return {
        "bias": bias,
        "tone": tone,
        "brief": brief,
        "playbook": playbook,
    }

def safe_save_market_event(
    event,
    stress_score: int,
    stress_label: str,
    scanner_regime: str,
    breadth_state: str,
    breadth_score: float,
    execution_multiplier: float,
    qqq,
    spy,
    dia,
    iwm,
    vixy,
    portfolio_move,
) -> None:

    try:
        save_market_event(
            event_label=event.label,
            confidence=event.confidence,
            stress_score=stress_score,
            stress_label=stress_label,
            scanner_regime=scanner_regime,
            breadth_state=breadth_state,
            breadth_score=breadth_score,
            execution_multiplier=execution_multiplier,
            qqq=qqq,
            spy=spy,
            dia=dia,
            iwm=iwm,
            vixy=vixy,
            portfolio_move=portfolio_move,
        )
    except Exception as exc:
        st.caption(f"Market event history not saved: {exc}")

def calculate_similarity_score(
    current: dict,
    historical_row: pd.Series,
) -> float:

    columns = [
        ("qqq", "QQQ"),
        ("spy", "SPY"),
        ("dia", "DIA"),
        ("iwm", "IWM"),
        ("vixy", "VIXY"),
    ]

    differences = []

    for current_key, history_key in columns:
        current_value = current.get(current_key)

        if current_value is None:
            continue

        if history_key not in historical_row:
            continue

        history_value = historical_row[history_key]

        if pd.isna(history_value):
            continue

        differences.append(abs(float(current_value) - float(history_value)))

    if not differences:
        return 0.0

    avg_difference = sum(differences) / len(differences)

    similarity = max(0.0, 100.0 - (avg_difference * 15.0))

    return round(similarity, 1)


def build_similar_events_df(
    history_df: pd.DataFrame,
    current_event_label: str,
    qqq,
    spy,
    dia,
    iwm,
    vixy,
) -> pd.DataFrame:

    if history_df is None or history_df.empty:
        return pd.DataFrame()

    current = {
        "qqq": qqq,
        "spy": spy,
        "dia": dia,
        "iwm": iwm,
        "vixy": vixy,
    }

    rows = []

    for _, row in history_df.iterrows():

        if row.get("Event") != current_event_label:
            continue

        similarity = calculate_similarity_score(
            current=current,
            historical_row=row,
        )

        rows.append(
            {
                "Date": row.get("Date"),
                "Event": row.get("Event"),
                "Similarity %": similarity,
                "QQQ": row.get("QQQ"),
                "SPY": row.get("SPY"),
                "IWM": row.get("IWM"),
                "VIXY": row.get("VIXY"),
                "Stress Score": row.get("Stress Score"),
            }
        )

    similar_df = pd.DataFrame(rows)

    if similar_df.empty:
        return similar_df

    similar_df = similar_df.sort_values(
        "Similarity %",
        ascending=False,
    ).head(5)

    return similar_df


# =========================================================
# PAGE
# =========================================================

def run_page() -> None:

    inject_responsive_css()
    inject_card_css()
    inject_market_pulse_responsive_css()

    st.title("🌎 Market Pulse")

    st.caption(
        "Live read of market stress, breadth, rotation, execution risk, "
        "sector pressure, and megacap reaction."
    )

    refresh = st.button(
        "Refresh Market Pulse Data",
        width="stretch",
    )

    if refresh:
        st.rerun()

    with st.spinner("Loading market reaction data..."):
        report = generate_market_reaction_report()

    event = report["event"]
    indexes = report["indexes"]
    sectors = report["sectors"]
    megacaps = report["megacaps"]

    portfolio = report.get("portfolio")
    portfolio_move = None
    portfolio_df = None
    portfolio_impact = None

    if portfolio is not None:
        portfolio_move = portfolio.get("portfolio_move")
        portfolio_df = portfolio.get("portfolio_df")

        if portfolio_move is not None:
            portfolio_impact = calculate_impact_label(
                float(portfolio_move)
            )

    qqq = get_move(indexes, "QQQ")
    spy = get_move(indexes, "SPY")
    dia = get_move(indexes, "DIA")
    iwm = get_move(indexes, "IWM")
    soxx = get_move(indexes, "SOXX")
    tlt = get_move(indexes, "TLT")
    gld = get_move(indexes, "GLD")
    uup = get_move(indexes, "UUP")
    hyg = get_move(indexes, "HYG")
    vixy = get_move(indexes, "VIXY")

    # =====================================================
    # MARKET STRESS v3
    # Weighted Stress Model
    # Technical Stress 70%
    # Economic Calendar Risk 15%
    # Earnings Risk 15%
    # Market Breadth Overlay
    # =====================================================

    economic_score = int(safe_float(
        st.session_state.get(
            "economic_risk_score",
            0,
        ),
        default=0.0,
    ))

    economic_label = str(
        st.session_state.get(
            "economic_risk_label",
            "NONE",
        )
    )

    earnings_score = int(safe_float(
        st.session_state.get(
            "earnings_risk_score",
            0,
        ),
        default=0.0,
    ))

    earnings_label = str(
        st.session_state.get(
            "earnings_risk_label",
            "NONE",
        )
    )

    technical_stress_score, technical_stress_label = (
        calculate_market_stress(
            indexes,
            sectors,
        )
    )

    # =====================================================
    # MARKET BREADTH CALCULATION
    # Single source of truth for stress, scanner, and display.
    # =====================================================

    breadth_result = calculate_market_breadth(
        indexes=indexes,
        sectors=sectors,
        megacaps=megacaps,
    )

    breadth_df = breadth_result["df"]
    breadth_score = float(breadth_result["score"])
    breadth_state = str(breadth_result["state"])
    total_names = int(breadth_result["total_names"])
    total_advancing = int(breadth_result["total_advancing"])
    total_declining = int(breadth_result["total_declining"])
    market_advance_pct = float(breadth_result["market_advance_pct"])
    market_decline_pct = float(breadth_result["market_decline_pct"])

    # =====================================================
    # CORE STRESS SCORE
    # =====================================================

    technical_component = technical_stress_score * 0.70
    economic_component = economic_score * 0.15
    earnings_component = earnings_score * 0.15

    stress_score = int(
        round(
            technical_component
            + economic_component
            + earnings_component
        )
    )

    stress_score = max(
        0,
        min(
            stress_score,
            100,
        ),
    )

    # =====================================================
    # BREADTH-ADJUSTED STRESS SCORE
    # =====================================================

    if breadth_score < 25:
        stress_score = max(
            stress_score,
            75,
        )

    elif breadth_score < 40:
        stress_score = max(
            stress_score,
            65,
        )

    elif breadth_score < 55:
        stress_score = max(
            stress_score,
            55,
        )

    if stress_score >= 80:
        stress_label = "Severe Stress"
    elif stress_score >= 60:
        stress_label = "High Stress"
    elif stress_score >= 40:
        stress_label = "Moderate Stress"
    elif stress_score >= 20:
        stress_label = "Low Stress"
    else:
        stress_label = "Calm Market"

    dip_score, dip_label = calculate_buy_the_dip_score(
        indexes,
        sectors,
        stress_score,
    )

    playbook_df = build_playbook_df(
        event,
        dip_score,
        dip_label,
    )

    regime = get_market_regime(
        indexes=indexes,
        sectors=sectors,
        stress_score=stress_score,
    )

    overall_regime = regime.get(
        "Overall Regime",
        "Mixed",
    )

    if breadth_score < 25:

        scanner_playbook = "BREADTH DAMAGE"
        scanner_regime = "DEFENSIVE"
        scanner_buy_allowed = False
        scanner_sell_allowed = True
        scanner_execution_multiplier = 0.50

    elif breadth_score < 40:

        scanner_playbook = "WEAK BREADTH"
        scanner_regime = "CAUTIOUS"
        scanner_buy_allowed = True
        scanner_sell_allowed = True
        scanner_execution_multiplier = 0.65

    elif breadth_score < 55:

        scanner_playbook = "SELECTIVE MARKET"
        scanner_regime = "SELECTIVE"
        scanner_buy_allowed = True
        scanner_sell_allowed = True
        scanner_execution_multiplier = 0.75

    elif stress_score >= 70:

        scanner_playbook = "INSTITUTIONAL RISK OFF"
        scanner_regime = "RISK_OFF"
        scanner_buy_allowed = False
        scanner_sell_allowed = True
        scanner_execution_multiplier = 0.50

    elif stress_score >= 40:

        scanner_playbook = "CAUTION"
        scanner_regime = "NEUTRAL"
        scanner_buy_allowed = True
        scanner_sell_allowed = True
        scanner_execution_multiplier = 0.75

    elif overall_regime == "Risk-On":

        scanner_playbook = "RISK ON"
        scanner_regime = "RISK_ON"
        scanner_buy_allowed = True
        scanner_sell_allowed = True
        scanner_execution_multiplier = 1.00

    else:

        scanner_playbook = "NEUTRAL"
        scanner_regime = "NEUTRAL"
        scanner_buy_allowed = True
        scanner_sell_allowed = True
        scanner_execution_multiplier = 1.00

    # =====================================================
    # MARKET DECISION SUPPORT v42
    # =====================================================

    decision_support = build_market_decision_support(
        event=event,
        stress_score=stress_score,
        stress_label=stress_label,
        breadth_score=breadth_score,
        breadth_state=breadth_state,
        dip_score=dip_score,
        dip_label=dip_label,
        scanner_regime=scanner_regime,
        scanner_execution_multiplier=scanner_execution_multiplier,
        scanner_buy_allowed=scanner_buy_allowed,
    )

    # =====================================================
    # SCANNER / RISK ENGINE SESSION EXPORT
    # =====================================================
    # This is the bridge used by Scanner_page.py.
    # Scanner reads these keys inside market_reaction_context().

    st.session_state["market_reaction_score"] = int(stress_score)
    st.session_state["market_reaction_confidence"] = float(
        getattr(event, "confidence", 0) or 0
    )
    st.session_state["market_reaction_event"] = str(
        getattr(event, "label", "") or ""
    )
    st.session_state["market_reaction_playbook"] = scanner_playbook
    st.session_state["market_reaction_regime"] = scanner_regime
    st.session_state["market_reaction_overall_regime"] = overall_regime
    st.session_state["market_reaction_stress_label"] = stress_label
    st.session_state["market_reaction_dip_score"] = int(dip_score)
    st.session_state["market_reaction_dip_label"] = dip_label
    st.session_state["market_reaction_buy_allowed"] = scanner_buy_allowed
    st.session_state["market_reaction_sell_allowed"] = scanner_sell_allowed
    st.session_state["market_reaction_execution_multiplier"] = (
        scanner_execution_multiplier
    )
    st.session_state["market_reaction_breadth_score"] = float(
        breadth_score
    )
    st.session_state["market_reaction_breadth_state"] = breadth_state

    summary = build_market_summary(
        event,
        indexes,
        sectors,
        megacaps,
        stress_score,
        stress_label,
    )

    scorecard_df = build_event_scorecard(
        event=event,
        indexes=indexes,
        sectors=sectors,
        stress_score=stress_score,
        stress_label=stress_label,
    )

    regime_df = build_regime_dashboard_df(
        indexes=indexes,
        sectors=sectors,
        stress_score=stress_score,
    )

    safe_save_market_event(
        event=event,
        stress_score=stress_score,
        stress_label=stress_label,
        scanner_regime=scanner_regime,
        breadth_state=breadth_state,
        breadth_score=breadth_score,
        execution_multiplier=(
            scanner_execution_multiplier
        ),
        qqq=qqq,
        spy=spy,
        dia=dia,
        iwm=iwm,
        vixy=vixy,
        portfolio_move=portfolio_move,
    )

    try:
        history_df = load_recent_market_events(50)
    except Exception:
        history_df = pd.DataFrame()

    similar_events_df = build_similar_events_df(
        history_df=history_df,
        current_event_label=event.label,
        qqq=qqq,
        spy=spy,
        dia=dia,
        iwm=iwm,
        vixy=vixy,
    )

    # =====================================================
    # MARKET PULSE v82 TRADE BIAS + OPPORTUNITY PANEL
    # =====================================================

    command_status_pill(
        scanner_regime,
        stress_score,
        breadth_score,
    )

    # =====================================================
    # AI MARKET BRIEF
    # Gives traders the scope of the day before reading the full dashboard.
    # =====================================================

    if sectors is not None and not sectors.empty:
        ai_best_sector_row = sectors.sort_values(
            "Daily %",
            ascending=False,
            na_position="last",
        ).iloc[0]

        ai_best_sector = (
            f"{ai_best_sector_row.get('Name', 'N/A')} "
            f"({ai_best_sector_row.get('Symbol', 'N/A')})"
        )

        ai_best_sector_move = format_pct(
            ai_best_sector_row.get("Daily %")
        )

    else:
        ai_best_sector = "N/A"
        ai_best_sector_move = "N/A"

    if megacaps is not None and not megacaps.empty:
        ai_best_mega_row = megacaps.sort_values(
            "Daily %",
            ascending=False,
            na_position="last",
        ).iloc[0]

        ai_best_mega = (
            f"{ai_best_mega_row.get('Name', 'N/A')} "
            f"({ai_best_mega_row.get('Symbol', 'N/A')})"
        )

        ai_best_mega_move = format_pct(
            ai_best_mega_row.get("Daily %")
        )

    else:
        ai_best_mega = "N/A"
        ai_best_mega_move = "N/A"

    ai_market_brief = build_ai_market_brief(
        event=event,
        stress_score=stress_score,
        stress_label=stress_label,
        breadth_score=breadth_score,
        breadth_state=breadth_state,
        scanner_regime=scanner_regime,
        scanner_execution_multiplier=scanner_execution_multiplier,
        dip_score=dip_score,
        dip_label=dip_label,
        best_sector=ai_best_sector,
        best_sector_move=ai_best_sector_move,
        best_mega=ai_best_mega,
        best_mega_move=ai_best_mega_move,
    )

    st.subheader("🤖 AI Market Brief")

    st.caption(
        "What it means: Executive summary of today's market conditions. "
        "Read this first for the 30-second overview."
    )

    if ai_market_brief["tone"] == "good":
        st.success(ai_market_brief["brief"])

    elif ai_market_brief["tone"] == "warning":
        st.warning(ai_market_brief["brief"])

    elif ai_market_brief["tone"] == "risk":
        st.error(ai_market_brief["brief"])

    else:
        st.info(ai_market_brief["brief"])

    st.caption(ai_market_brief["playbook"])

    help_text(
        "Start here. The AI Market Brief summarizes the entire dashboard "
        "in under 30 seconds."
    )

    left_col, right_col = responsive_columns([1, 1])

    with left_col:
        
        # =====================================================
        # MARKET STRESS DASHBOARD
        # Institutional compact-card layout
        # Replaces cramped st.metric-style cards on iPad.
        # =====================================================

        st.divider()

        st.subheader("🚦 Market Stress Dashboard")

        st.caption(
            "What it means: Measures overall market risk and determines "
            "how aggressive your trading should be."
        )

        pulse_metric_grid(
            [
                {
                    "label": "Stress Score",
                    "value": f"{stress_score}/100",
                    "detail": "Overall market risk.",
                    "tone": stress_tone(stress_score),
                },
                {
                    "label": "Stress State",
                    "value": stress_label,
                    "detail": "Current risk condition.",
                    "tone": stress_tone(stress_score),
                },
                {
                    "label": "Scanner Regime",
                    "value": f"{regime_icon(scanner_regime)} {scanner_regime}",
                    "detail": "Scanner behavior mode.",
                    "tone": regime_tone(scanner_regime),
                },
                {
                    "label": "Execution Multiplier",
                    "value": f"{scanner_execution_multiplier:.2f}x",
                    "detail": "Position-size adjustment.",
                    "tone": "info",
                },
            ],
            min_width=220,
        )
        # =====================================================
        # STRESS INTERPRETATION
        # =====================================================

        if stress_score >= 80:
            stress_interpretation = "SEVERE RISK OFF"

        elif stress_score >= 60:
            stress_interpretation = "DEFENSIVE"

        elif stress_score >= 40:
            stress_interpretation = "CAUTION"

        elif stress_score >= 20:
            stress_interpretation = "NEUTRAL"

        else:
            stress_interpretation = "RISK ON"

        st.info(
            f"Market Stress Interpretation: {stress_interpretation}"
        )

        help_text(
            "Stress Score combines technical stress, economic risk, "
            "earnings risk, and breadth deterioration. Higher scores "
            "require more caution."
        )

        breadth_overlay_component = max(
            0,
            stress_score - int(
                round(
                    technical_component
                    + economic_component
                    + earnings_component
                )
            ),
        )

        stress_df = pd.DataFrame(
            [
                {
                    "Component": "Technical Stress",
                    "Raw Score": technical_stress_score,
                    "Weight": "70%",
                    "Weighted Contribution": round(
                        technical_component,
                        2,
                    ),
                },
                {
                    "Component": f"Economic Risk ({economic_label})",
                    "Raw Score": economic_score,
                    "Weight": "15%",
                    "Weighted Contribution": round(
                        economic_component,
                        2,
                    ),
                },
                {
                    "Component": f"Earnings Risk ({earnings_label})",
                    "Raw Score": earnings_score,
                    "Weight": "15%",
                    "Weighted Contribution": round(
                        earnings_component,
                        2,
                    ),
                },
                {
                    "Component": "Market Breadth Overlay",
                    "Raw Score": round(
                        breadth_score,
                        1,
                    ),
                    "Weight": "Overlay",
                    "Weighted Contribution": breadth_overlay_component,
                },
                {
                    "Component": "Final Market Stress",
                    "Raw Score": stress_score,
                    "Weight": "100%",
                    "Weighted Contribution": stress_score,
                },
            ]
        )

        st.dataframe(
            stress_df,
            width="stretch",
            hide_index=True,
        )
        
        # =====================================================
        # EVENT BANNER
        # Compact responsive event summary.
        # =====================================================

        st.divider()

        event_tone = (
            "good"
            if event.label == "No Major Shock Detected"
            else "warning"
        )

        event_icon = (
            "✅"
            if event.label == "No Major Shock Detected"
            else "⚠️"
        )

        pulse_metric_card(
            "Market Event",
            f"{event_icon} {event.label}",
            event.explanation,
            tone=event_tone,
        )

        pulse_metric_grid(
            [
                {"label": "Event Confidence", "value": f"{event.confidence}%", "tone": "info"},
                {"label": "Market Stress", "value": f"{stress_score}/100", "detail": stress_label, "tone": stress_tone(stress_score)},
                {
                    "label": "Buy-The-Dip",
                    "value": f"{dip_score}/100",
                    "detail": dip_label,
                    "tone": (
                        "good"
                        if dip_score >= 60
                        else "warning"
                        if dip_score >= 30
                        else "neutral"
                    ),
                },
            ],
            min_width=220,
        )

        # =====================================================
        # MARKET SUMMARY
        # =====================================================

        st.divider()

        st.subheader("What Happened Today?")

        st.caption(
            "What it means: Plain-English explanation of the main market move, "
            "leadership, weakness, and stress reading."
        )

        st.info(summary)

        # =====================================================
        # MARKET BREADTH ENGINE
        # Compact responsive participation dashboard.
        # =====================================================

        st.divider()

        st.subheader("📊 Market Breadth Engine")

        st.caption(
            "What it means: Measures how many stocks, sectors, and indexes "
            "are participating in the current move."
        )

        if breadth_df.empty:

            st.warning("Breadth data unavailable.")

        else:

            pulse_metric_grid(
                [
                    {
                        "label": "Breadth Score",
                        "value": f"{breadth_score:.1f}/100",
                        "detail": "Participation strength.",
                        "tone": breadth_tone(breadth_score),
                    },
                    {
                        "label": "Breadth State",
                        "value": breadth_state,
                        "detail": "Market participation.",
                        "tone": breadth_tone(breadth_score),
                    },
                    {
                        "label": "Advancers",
                        "value": f"{total_advancing}/{total_names}",
                        "detail": "Names moving higher.",
                        "tone": "info",
                    },
                    {
                        "label": "Advance %",
                        "value": f"{market_advance_pct:.0f}%",
                        "detail": "Positive participation.",
                        "tone": (
                            "good"
                            if market_advance_pct >= 60
                            else "warning"
                            if market_advance_pct >= 40
                            else "risk"
                        ),
                    },
                    {
                        "label": "Decline %",
                        "value": f"{market_decline_pct:.0f}%",
                        "detail": "Negative participation.",
                        "tone": (
                            "risk"
                            if market_decline_pct >= 60
                            else "warning"
                            if market_decline_pct >= 40
                            else "good"
                        ),
                    },
                ],
                min_width=220,
            )

            if breadth_state == "Broad Damage":

                st.error(
                    "Market Breadth Interpretation: Broad market damage detected. "
                    "Scanner regime automatically shifted to DEFENSIVE "
                    f"({scanner_execution_multiplier:.2f}x). "
                    "New long exposure should be reduced."
                )

            elif breadth_state == "Weak Breadth":

                st.warning(
                    "Market Breadth Interpretation: Weak participation detected. "
                    "Scanner regime should remain cautious. "
                    f"Current execution multiplier: {scanner_execution_multiplier:.2f}x."
                )

            elif breadth_state == "Mixed / Selective":

                st.info(
                    "Market Breadth Interpretation: Mixed participation. "
                    "Scanner should prioritize selective setups over broad-market exposure. "
                    f"Current execution multiplier: {scanner_execution_multiplier:.2f}x."
                )

            else:

                st.success(
                    "Market Breadth Interpretation: Healthy participation. "
                    "Market support is broad enough for normal scanner exposure. "
                    f"Current execution multiplier: {scanner_execution_multiplier:.2f}x."
                )

            help_text(
                "Breadth measures participation across indexes, sectors, "
                "and megacaps. Healthy rallies require broad participation."
            )

            with st.expander(
                "Breadth Details",
                expanded=False,
            ):
                st.dataframe(
                    breadth_df,
                    width="stretch",
                    hide_index=True,
                )
        # =====================================================
        # MARKET PLAYBOOK
        # =====================================================

        st.divider()

        st.subheader("🎯 Market Playbook")

        st.caption(
            "What it means: Converts market conditions into practical trading "
            "guidance and risk management."
        )

        playbook_lookup = dict(
            zip(
                playbook_df["Metric"],
                playbook_df["Reading"],
            )
        )

        pulse_metric_grid(
            [
                {
                    "label": "Event",
                    "value": playbook_lookup.get("Event", "N/A"),
                    "detail": "Primary market event.",
                    "tone": "warning",
                },
                {
                    "label": "Opportunity",
                    "value": playbook_lookup.get("Opportunity", "N/A"),
                    "detail": "Dip quality read.",
                    "tone": "info",
                },
                {
                    "label": "Risk",
                    "value": playbook_lookup.get("Risk Level", "N/A"),
                    "detail": "Trading risk level.",
                    "tone": "warning",
                },
                {
                    "label": "Buy-The-Dip",
                    "value": playbook_lookup.get("Buy-The-Dip Score", "N/A"),
                    "detail": playbook_lookup.get("Opportunity Rating", ""),
                    "tone": "neutral",
                },
            ],
            min_width=220,
        )

        st.info(
            playbook_lookup.get(
                "Suggested Action",
                "No playbook action available.",
            )
        )

        help_text(
            "The Playbook converts market conditions into practical "
            "trading actions."
        )

        # =====================================================
        # REGIME HISTORY TRACKER + TRANSITION ENGINE (v55)
        # =====================================================

        st.subheader("📈 Regime History")

        st.caption(
            "What it means: Tracks how market conditions have evolved over time "
            "and identifies regime changes."
        )

        recovery_diagnostics_ready = False
        recovery_diagnostics_metrics = {}
        recovery_details_df = pd.DataFrame()

        try:

            history_view = history_df.copy()

            if history_view.empty:

                st.info(
                    "No historical market events saved yet."
                )

            else:

                column_map = {
                    "timestamp": "Date",
                    "event": "Event",
                    "stress_score": "Stress",
                    "stress_label": "Stress State",
                    "scanner_regime": "Regime",
                    "regime": "Regime",
                    "Regime": "Regime",
                    "Scanner Regime": "Regime",
                    "breadth_state": "Breadth",
                    "Breadth State": "Breadth",
                    "breadth_score": "Breadth Score",
                    "Breadth Score": "Breadth Score",
                    "execution_multiplier": "Position Size",
                    "Position Size": "Position Size",
                    "Date": "Date",
                    "Event": "Event",
                    "Stress Score": "Stress",
                    "Stress Label": "Stress State",
                }

                available_columns = [
                    col
                    for col in column_map
                    if col in history_view.columns
                ]

                if not available_columns:

                    st.info(
                        "Historical market events exist, but no compatible "
                        "columns were found for the regime history view."
                    )

                else:

                    history_view = history_view[
                        available_columns
                    ].rename(
                        columns=column_map
                    )

                    preferred_order = [
                        "Date",
                        "Regime",
                        "Event",
                        "Stress",
                        "Stress State",
                        "Breadth",
                        "Breadth Score",
                        "Position Size",
                    ]

                    history_view = history_view[
                        [
                            col
                            for col in preferred_order
                            if col in history_view.columns
                        ]
                    ]

                    if history_view.empty:

                        st.info(
                            "No usable historical market events found."
                        )

                    else:

                        if "Regime" not in history_view.columns:

                            history_view.insert(
                                1,
                                "Regime",
                                st.session_state.get(
                                    "market_reaction_regime",
                                    scanner_regime,
                                ),
                            )

                        if len(history_view) > 20:
                            history_view = history_view.head(20)

                        st.dataframe(
                            history_view,
                            width="stretch",
                            hide_index=True,
                        )

                        if (
                            "Stress" in history_view.columns
                            and not history_view.empty
                            and len(history_view) >= 2
                        ):

                            current_stress = float(
                                pd.to_numeric(
                                    pd.Series(
                                        [
                                            history_view.iloc[0].get(
                                                "Stress",
                                                0,
                                            )
                                        ]
                                    ),
                                    errors="coerce",
                                ).fillna(0).iloc[0]
                            )

                            previous_stress = float(
                                pd.to_numeric(
                                    pd.Series(
                                        [
                                            history_view.iloc[1].get(
                                                "Stress",
                                                0,
                                            )
                                        ]
                                    ),
                                    errors="coerce",
                                ).fillna(0).iloc[0]
                            )

                            stress_change = (
                                current_stress
                                - previous_stress
                            )

                            if stress_change > 5:

                                st.error(
                                    f"Stress rising (+{stress_change:.0f}) "
                                    "vs previous event."
                                )

                            elif stress_change < -5:

                                st.success(
                                    f"Stress improving "
                                    f"({stress_change:.0f}) "
                                    "vs previous event."
                                )

                            else:

                                st.info(
                                    "Stress relatively unchanged "
                                    "vs previous event."
                                )

                            # =====================================================
                            # REGIME TRANSITION ENGINE (v55)
                            # =====================================================

                            current_regime_raw = history_view.iloc[0].get(
                                "Regime",
                                scanner_regime,
                            )

                            previous_regime_raw = history_view.iloc[1].get(
                                "Regime",
                                "",
                            )

                            current_regime = (
                                ""
                                if current_regime_raw is None
                                or str(current_regime_raw).lower() == "none"
                                or str(current_regime_raw).strip() == ""
                                else str(current_regime_raw).upper().strip()
                            )

                            previous_regime = (
                                ""
                                if previous_regime_raw is None
                                or str(previous_regime_raw).lower() == "none"
                                or str(previous_regime_raw).strip() == ""
                                else str(previous_regime_raw).upper().strip()
                            )

                            transition = ""
                            transition_state = "STABLE"
                            transition_message = (
                                "No regime transition detected."
                            )

                            if (
                                previous_regime
                                and current_regime
                                and current_regime != previous_regime
                            ):

                                transition = (
                                    f"{previous_regime} → {current_regime}"
                                )

                                if current_regime in (
                                    "DEFENSIVE",
                                    "RISK_OFF",
                                    "RISK-OFF",
                                ):

                                    transition_state = "DAMAGE"
                                    transition_message = (
                                        f"Regime Transition: {transition}. "
                                        "Market risk is deteriorating. "
                                        "Reduce new long exposure."
                                    )

                                elif current_regime in (
                                    "CAUTIOUS",
                                    "SELECTIVE",
                                ):

                                    transition_state = "ROTATION"
                                    transition_message = (
                                        f"Regime Transition: {transition}. "
                                        "Market conditions are stabilizing "
                                        "but still selective."
                                    )

                                elif current_regime in (
                                    "RECOVERY",
                                    "RISK_ON",
                                    "RISK-ON",
                                ):

                                    transition_state = "RECOVERY"
                                    transition_message = (
                                        f"Regime Transition: {transition}. "
                                        "Market conditions are improving. "
                                        "Normal exposure may be considered "
                                        "only if risk filters also pass."
                                    )

                                else:

                                    transition_state = "ROTATION"
                                    transition_message = (
                                        f"Regime Transition: {transition}."
                                    )

                            elif current_regime and previous_regime:

                                transition_message = (
                                    f"Regime unchanged: {current_regime}."
                                )

                            elif current_regime and not previous_regime:

                                transition_message = (
                                    f"Current regime: {current_regime}. "
                                    "Historical regime data is not yet "
                                    "available for transition analysis."
                                )

                            else:

                                transition_message = (
                                    "Regime transition data is not "
                                    "available yet."
                                )

                            if transition_state == "DAMAGE":

                                st.error(
                                    transition_message
                                )

                            elif transition_state == "RECOVERY":

                                st.success(
                                    transition_message
                                )

                            elif transition_state == "ROTATION":

                                st.warning(
                                    transition_message
                                )

                            else:

                                st.info(
                                    transition_message
                                )

                            # =====================================================
                            # REGIME RECOVERY TRIGGER + PROBABILITY METER + DURATION + BREADTH METER (v55)
                            # =====================================================

                            current_breadth_score = float(
                                pd.to_numeric(
                                    pd.Series(
                                        [
                                            history_view.iloc[0].get(
                                                "Breadth Score",
                                                0,
                                            )
                                        ]
                                    ),
                                    errors="coerce",
                                ).fillna(0).iloc[0]
                            )

                            current_position_size = float(
                                pd.to_numeric(
                                    pd.Series(
                                        [
                                            history_view.iloc[0].get(
                                                "Position Size",
                                                0,
                                            )
                                        ]
                                    ),
                                    errors="coerce",
                                ).fillna(0).iloc[0]
                            )

                            recovery_score = 0
                            recovery_notes = []

                            if stress_change < -5:
                                recovery_score += 30
                                recovery_notes.append(
                                    "Stress is improving"
                                )

                            if current_breadth_score >= 40:
                                recovery_score += 30
                                recovery_notes.append(
                                    "Breadth has recovered above 40"
                                )

                            elif current_breadth_score >= 25:
                                recovery_score += 15
                                recovery_notes.append(
                                    "Breadth is starting to recover"
                                )

                            else:
                                recovery_notes.append(
                                    "Breadth remains damaged"
                                )

                            if current_regime in (
                                "RECOVERY",
                                "RISK_ON",
                                "RISK-ON",
                            ):
                                recovery_score += 25
                                recovery_notes.append(
                                    "Regime is improving"
                                )

                            elif current_regime in (
                                "CAUTIOUS",
                                "SELECTIVE",
                            ):
                                recovery_score += 10
                                recovery_notes.append(
                                    "Regime is stabilizing"
                                )

                            if current_position_size >= 0.75:
                                recovery_score += 15
                                recovery_notes.append(
                                    "Position size has normalized"
                                )

                            elif current_position_size > 0:
                                recovery_notes.append(
                                    "Position size remains reduced"
                                )

                            recovery_trigger = (
                                recovery_score >= 60
                                and stress_change < -5
                                and current_breadth_score >= 25
                            )

                            recovery_probability = max(
                                0,
                                min(
                                    100,
                                    int(round(recovery_score)),
                                ),
                            )

                            if recovery_probability < 30:
                                recovery_status = "Damage Ongoing"

                            elif recovery_probability < 50:
                                recovery_status = "Stabilizing"

                            elif recovery_probability < 70:
                                recovery_status = "Early Recovery"

                            elif recovery_probability < 90:
                                recovery_status = "Recovery Confirmed"

                            else:
                                recovery_status = "Risk-On Environment"

                            # =====================================================
                            # REGIME DURATION TRACKER (v55)
                            # =====================================================

                            regime_duration_rows = 0
                            regime_start_date = None
                            regime_current_date = None

                            if (
                                "Date" in history_view.columns
                                and current_regime
                            ):

                                regime_current_date = pd.to_datetime(
                                    history_view.iloc[0].get(
                                        "Date",
                                        None,
                                    ),
                                    errors="coerce",
                                )

                                for _, regime_row in history_view.iterrows():

                                    row_regime_raw = regime_row.get(
                                        "Regime",
                                        "",
                                    )

                                    row_regime = (
                                        ""
                                        if row_regime_raw is None
                                        or str(row_regime_raw).lower() == "none"
                                        or str(row_regime_raw).strip() == ""
                                        else str(row_regime_raw).upper().strip()
                                    )

                                    if row_regime != current_regime:
                                        break

                                    regime_duration_rows += 1

                                    regime_start_date = pd.to_datetime(
                                        regime_row.get(
                                            "Date",
                                            None,
                                        ),
                                        errors="coerce",
                                    )

                            regime_days = 0

                            if (
                                regime_current_date is not None
                                and regime_start_date is not None
                                and not pd.isna(regime_current_date)
                                and not pd.isna(regime_start_date)
                            ):

                                regime_days = max(
                                    1,
                                    int(
                                        (
                                            regime_current_date.normalize()
                                            - regime_start_date.normalize()
                                        ).days
                                    )
                                    + 1,
                                )

                            elif regime_duration_rows > 0:

                                regime_days = regime_duration_rows

                            regime_start_label = "N/A"

                            if (
                                regime_start_date is not None
                                and not pd.isna(regime_start_date)
                            ):

                                regime_start_label = (
                                    regime_start_date.strftime(
                                        "%Y-%m-%d",
                                    )
                                )

                            prior_regime_durations = []

                            if (
                                "Date" in history_view.columns
                                and "Regime" in history_view.columns
                                and current_regime
                            ):

                                clean_regime_rows = []

                                for _, regime_row in history_view.iterrows():

                                    row_regime_raw = regime_row.get(
                                        "Regime",
                                        "",
                                    )

                                    row_regime = (
                                        ""
                                        if row_regime_raw is None
                                        or str(row_regime_raw).lower() == "none"
                                        or str(row_regime_raw).strip() == ""
                                        else str(row_regime_raw).upper().strip()
                                    )

                                    row_date = pd.to_datetime(
                                        regime_row.get(
                                            "Date",
                                            None,
                                        ),
                                        errors="coerce",
                                    )

                                    if row_regime and not pd.isna(row_date):
                                        clean_regime_rows.append(
                                            {
                                                "regime": row_regime,
                                                "date": row_date,
                                            }
                                        )

                                active_group = []
                                active_group_regime = ""
                                completed_groups = []

                                for clean_row in clean_regime_rows:

                                    row_regime = clean_row["regime"]
                                    row_date = clean_row["date"]

                                    if not active_group:
                                        active_group = [row_date]
                                        active_group_regime = row_regime
                                        continue

                                    if row_regime == active_group_regime:
                                        active_group.append(row_date)
                                        continue

                                    completed_groups.append(
                                        {
                                            "regime": active_group_regime,
                                            "dates": active_group,
                                        }
                                    )

                                    active_group = [row_date]
                                    active_group_regime = row_regime

                                if active_group:
                                    completed_groups.append(
                                        {
                                            "regime": active_group_regime,
                                            "dates": active_group,
                                        }
                                    )

                                for group_index, group in enumerate(
                                    completed_groups
                                ):

                                    if group_index == 0:
                                        continue

                                    if group["regime"] != current_regime:
                                        continue

                                    group_dates = group["dates"]

                                    group_days = max(
                                        1,
                                        int(
                                            (
                                                max(group_dates).normalize()
                                                - min(group_dates).normalize()
                                            ).days
                                        )
                                        + 1,
                                    )

                                    prior_regime_durations.append(
                                        group_days
                                    )

                            average_regime_duration = "N/A"

                            if prior_regime_durations:

                                average_days = round(
                                    sum(prior_regime_durations)
                                    / len(prior_regime_durations),
                                    1,
                                )

                                average_regime_duration = (
                                    f"{average_days} days"
                                )

                            if regime_days <= 0:
                                regime_duration_status = "N/A"

                            elif regime_days <= 2:
                                regime_duration_status = "New Regime"

                            elif regime_days <= 5:
                                regime_duration_status = "Developing"

                            elif regime_days <= 10:
                                regime_duration_status = "Established"

                            else:
                                regime_duration_status = "Extended"

                            # =====================================================
                            # BREADTH RECOVERY METER (v71 COMPACT RECOVERY ENGINE)
                            # =====================================================

                            breadth_recovery_threshold = 25.0
                            breadth_confirmation_threshold = 40.0

                            breadth_recovery_progress = max(
                                0,
                                min(
                                    100,
                                    int(
                                        round(
                                            (
                                                current_breadth_score
                                                / breadth_recovery_threshold
                                            )
                                            * 100
                                        )
                                    ),
                                ),
                            )

                            breadth_points_needed = max(
                                0.0,
                                breadth_recovery_threshold
                                - current_breadth_score,
                            )

                            if current_breadth_score < 15:
                                breadth_recovery_status = "Severe Damage"

                            elif current_breadth_score < 25:
                                breadth_recovery_status = "Damaged"

                            elif current_breadth_score < 40:
                                breadth_recovery_status = "Recovering"

                            else:
                                breadth_recovery_status = "Confirmed"

                            # =====================================================
                            # RECOVERY FORECAST ENGINE (v71)
                            # =====================================================

                            if current_breadth_score < 15:
                                recovery_confidence = "Very Low"

                            elif current_breadth_score < 25:
                                recovery_confidence = "Low"

                            elif current_breadth_score < 40:
                                recovery_confidence = "Moderate"

                            else:
                                recovery_confidence = "High"

                            if recovery_probability < 30:
                                forecast_state = "Damage Ongoing"

                            elif recovery_probability < 50:
                                forecast_state = "Early Recovery"

                            elif recovery_probability < 70:
                                forecast_state = "Recovery Building"

                            else:
                                forecast_state = "Recovery Confirmed"

                            breadth_improvement_rate = max(
                                1.5,
                                min(
                                    3.0,
                                    abs(stress_change) / 8,
                                ),
                            )

                            estimated_days = int(
                                round(
                                    breadth_points_needed
                                    / breadth_improvement_rate
                                )
                            )

                            estimated_days = max(
                                1,
                                min(
                                    estimated_days,
                                    30,
                                ),
                            )

                            if estimated_days <= 3:
                                recovery_velocity = "Fast"

                            elif estimated_days <= 7:
                                recovery_velocity = "Moderate"

                            else:
                                recovery_velocity = "Slow"

                            if estimated_days <= 2:
                                recovery_eta = "1-2 Days"

                            elif estimated_days <= 5:
                                recovery_eta = "3-5 Days"

                            elif estimated_days <= 10:
                                recovery_eta = "1-2 Weeks"

                            else:
                                recovery_eta = "2+ Weeks"

                            # =====================================================
                            # COMPACT RECOVERY ENGINE DISPLAY (v71)
                            # =====================================================

                            st.subheader("🔄 Recovery Engine")

                            st.caption(
                                "What it means: Detects whether market conditions "
                                "are improving after a period of stress or damage."
                            )

                            re_tone = (
                                "good"
                                if recovery_trigger
                                else "warning"
                            )

                            pulse_metric_grid(
                                [
                                    {
                                        "label": "Recovery Probability",
                                        "value": f"{recovery_probability}%",
                                        "detail": "Recovery odds.",
                                        "tone": re_tone,
                                    },
                                    {
                                        "label": "Recovery Status",
                                        "value": recovery_status,
                                        "detail": "Current phase.",
                                        "tone": re_tone,
                                    },
                                    {
                                        "label": "Recovery ETA",
                                        "value": recovery_eta,
                                        "detail": "Estimated timing.",
                                        "tone": "info",
                                    },
                                    {
                                        "label": "Recovery Trigger",
                                        "value": (
                                            "ACTIVE"
                                            if recovery_trigger
                                            else "Inactive"
                                        ),
                                        "detail": "Recovery signal.",
                                        "tone": re_tone,
                                    },
                                ],
                                min_width=220,
                            )

                            if recovery_trigger:

                                st.success(
                                    "Regime Recovery Trigger: ACTIVE. "
                                    "Stress is improving and breadth has "
                                    "recovered enough for selective "
                                    "exposure."
                                )

                            elif (
                                stress_change < -5
                                and current_breadth_score < 25
                            ):

                                st.warning(
                                    "Regime Recovery Trigger: Stress is "
                                    "improving, but breadth remains "
                                    "damaged. Remain DEFENSIVE until "
                                    "breadth rises above 25."
                                )

                            elif (
                                stress_change < -5
                                and current_breadth_score >= 25
                                and current_breadth_score < 40
                            ):

                                st.info(
                                    "Regime Recovery Trigger: Stress is "
                                    "improving and breadth is starting "
                                    "to recover. Prepare for CAUTIOUS "
                                    "regime if improvement continues."
                                )

                            elif (
                                stress_change < -5
                                and current_breadth_score >= 40
                            ):

                                st.success(
                                    "Regime Recovery Trigger: Stress is "
                                    "improving and breadth has recovered "
                                    "enough for selective exposure."
                                )

                            else:

                                st.caption(
                                    "Regime Recovery Trigger inactive. "
                                    "Waiting for stronger stress and "
                                    "breadth confirmation."
                                )

                            help_text(
                                "Recovery probability increases when stress "
                                "falls, breadth improves, and market regimes "
                                "transition from defensive to constructive."
                            )

                            recovery_diagnostics_ready = True
                            recovery_diagnostics_metrics = {
                                "Days in Regime": (
                                    regime_days
                                    if regime_days > 0
                                    else "N/A"
                                ),
                                "Regime Started": regime_start_label,
                                "Prior Avg Duration": average_regime_duration,
                                "Duration Status": regime_duration_status,
                                "Breadth Score": round(
                                    current_breadth_score,
                                    1,
                                ),
                                "Breadth Recovery": f"{breadth_recovery_progress}%",
                                "Points to Recovery": round(
                                    breadth_points_needed,
                                    1,
                                ),
                                "Breadth Status": breadth_recovery_status,
                                "Recovery Confidence": recovery_confidence,
                                "Forecast State": forecast_state,
                                "Recovery Velocity": recovery_velocity,
                                "Recovery ETA": recovery_eta,
                            }

                            recovery_details_df = pd.DataFrame(
                                [
                                    {
                                        "Current Regime": (
                                            current_regime
                                            if current_regime
                                            else "N/A"
                                        ),
                                        "Previous Regime": (
                                            previous_regime
                                            if previous_regime
                                            else "N/A"
                                        ),
                                        "Transition": (
                                            transition
                                            if transition
                                            else "None"
                                        ),
                                        "Stress Change": round(
                                            stress_change,
                                            2,
                                        ),
                                        "Breadth Score": round(
                                            current_breadth_score,
                                            2,
                                        ),
                                        "Position Size": round(
                                            current_position_size,
                                            2,
                                        ),
                                        "Days in Regime": (
                                            regime_days
                                            if regime_days > 0
                                            else "N/A"
                                        ),
                                        "Regime Started": regime_start_label,
                                        "Duration Status": regime_duration_status,
                                        "Prior Avg Duration": average_regime_duration,
                                        "Breadth Recovery": (
                                            f"{breadth_recovery_progress}%"
                                        ),
                                        "Breadth Status": breadth_recovery_status,
                                        "Points to Recovery": round(
                                            breadth_points_needed,
                                            2,
                                        ),
                                        "Recovery Probability": (
                                            f"{recovery_probability}%"
                                        ),
                                        "Recovery Confidence": recovery_confidence,
                                        "Forecast State": forecast_state,
                                        "Recovery Velocity": recovery_velocity,
                                        "Recovery ETA": recovery_eta,
                                        "Recovery Status": recovery_status,
                                        "Recovery Score": f"{recovery_score}/100",
                                        "Recovery Trigger": (
                                            "ACTIVE"
                                            if recovery_trigger
                                            else "Inactive"
                                        ),
                                        "Notes": (
                                            ", ".join(
                                                recovery_notes
                                            )
                                            if recovery_notes
                                            else "None"
                                        ),
                                    }
                                ]
                            )

                        else:

                            st.caption(
                                "At least two regime history records are needed "
                                "to calculate stress change and recovery details."
                            )

        except Exception as exc:

            st.warning(
                f"Regime history unavailable: {exc}"
            )

        # =====================================================
        # DAMAGE & ROTATION REPORT
        # =====================================================

        st.divider()

        st.subheader("📊 Damage & Rotation Report")

        st.caption(
            "What it means: Shows where institutional money is leaving and "
            "where leadership is emerging."
        )

        # ==========================================
        # DAMAGE REPORT
        # ==========================================

        st.markdown("## Damage Report")

        col1, col2 = responsive_columns(2)

        weakest_sectors = sectors.sort_values(
            "Daily %",
            ascending=True,
            na_position="last",
        ).head(5)

        weakest_megacaps = megacaps.sort_values(
            "Daily %",
            ascending=True,
            na_position="last",
        ).head(5)

        with col1:
            st.markdown("### Weakest Sectors")
            st.dataframe(
                weakest_sectors,
                width="stretch",
                hide_index=True,
            )

        with col2:
            st.markdown("### Weakest Megacaps")
            st.dataframe(
                weakest_megacaps,
                width="stretch",
                hide_index=True,
            )

        st.divider()

        # ==========================================
        # ROTATION REPORT
        # ==========================================

        st.markdown("## Rotation Report")

        col1, col2 = responsive_columns(2)

        strongest_sectors = sectors.sort_values(
            "Daily %",
            ascending=False,
            na_position="last",
        ).head(5)

        strongest_megacaps = megacaps.sort_values(
            "Daily %",
            ascending=False,
            na_position="last",
        ).head(5)

        megacap_title = (
            "Least Damaged Megacaps"
            if all_values_negative(megacaps)
            else "Strongest Megacaps"
        )

        with col1:
            st.markdown("### Strongest Sectors")
            st.dataframe(
                strongest_sectors,
                width="stretch",
                hide_index=True,
            )

        with col2:
            st.markdown(f"### {megacap_title}")
            st.dataframe(
                strongest_megacaps,
                width="stretch",
                hide_index=True,
            )



    with right_col:            
        # =====================================================
        # DECISION CENTER
        # Consolidated market status dashboard.
        # =====================================================

        st.subheader("🎯 Decision Center")

        st.caption(
            "What it means: High-level snapshot of market health, risk, breadth, "
            "regime, and execution conditions."
        )

        dc1, dc2 = responsive_columns(2)

        with dc1:

            pulse_metric_card(
                "Event",
                event.label,
                tone=(
                    "warning"
                    if event.label != "No Major Shock Detected"
                    else "good"
                ),
            )

            pulse_metric_card(
                "Stress",
                f"{stress_score}/100",
                stress_label,
                tone=stress_tone(stress_score),
            )

            pulse_metric_card(
                "Regime",
                f"{regime_icon(scanner_regime)} {scanner_regime}",
                scanner_playbook,
                tone=regime_tone(scanner_regime),
            )

        with dc2:

            pulse_metric_card(
                "Confidence",
                f"{event.confidence}%",
                tone="info",
            )

            pulse_metric_card(
                "Breadth",
                f"{breadth_score:.1f}/100",
                breadth_state,
                tone=breadth_tone(breadth_score),
            )

            pulse_metric_card(
                "Position Size",
                f"{scanner_execution_multiplier:.2f}x",
                "Execution multiplier",
                tone="info",
            )

        st.info(
            decision_support.get(
                "primary_action",
                "No decision guidance available.",
            )
        )

        # =====================================================
        # REGIME GUIDANCE SOURCE
        # Defines the right-rail guidance before the dashboard is displayed.
        # =====================================================

        if scanner_regime == "DEFENSIVE":

            recommended_exposure = "25% - 50%"
            expected_duration = "1 - 3 Weeks"

            recommended_actions = [
                "Reduce new long exposure",
                "Favor defensive sectors",
                "Raise cash levels",
                "Wait for breadth improvement",
            ]

        elif scanner_regime in (
            "CAUTIOUS",
            "SELECTIVE",
        ):

            recommended_exposure = "50% - 75%"
            expected_duration = "Several Days"

            recommended_actions = [
                "Focus on strongest setups",
                "Avoid weak sectors",
                "Use smaller position sizes",
                "Stay selective",
            ]

        else:

            recommended_exposure = "75% - 100%"
            expected_duration = "Trend Dependent"

            recommended_actions = [
                "Normal scanner exposure",
                "Follow leadership stocks",
                "Deploy capital normally",
                "Monitor market internals",
            ]

        # =====================================================
        # TRADE GUIDANCE CENTER
        # Consolidates Action Guidance + Trade Bias + Leadership Focus.
        # =====================================================

        st.divider()

        st.subheader("🎯 Trade Guidance Center")

        st.caption(
            "What it means: Practical trading guidance combining action steps, "
            "trade bias, and current leadership focus."
        )

        action_cards = list(recommended_actions or [])

        while len(action_cards) < 4:
            action_cards.append("Monitor market internals")

        if scanner_regime in (
            "DEFENSIVE",
            "RISK_OFF",
            "RISK-OFF",
        ):
            trade_bias_tone = "risk"
            long_exposure = "Defensive"
            preferred_setup = "Only A+ setups"
            avoid_text = "Weak sectors"
            aggression = "Low"

        elif scanner_regime in (
            "CAUTIOUS",
            "SELECTIVE",
        ):
            trade_bias_tone = "warning"
            long_exposure = "Selective"
            preferred_setup = "Relative-strength leaders"
            avoid_text = "Weak sectors"
            aggression = "Moderate"

        elif scanner_regime in (
            "RISK_ON",
            "RISK-ON",
        ):
            trade_bias_tone = "good"
            long_exposure = "Constructive"
            preferred_setup = "Breakouts / trend continuation"
            avoid_text = "Extended laggards"
            aggression = "Normal"

        else:
            trade_bias_tone = "neutral"
            long_exposure = "Balanced"
            preferred_setup = "Confirmed setups"
            avoid_text = "Low-quality names"
            aggression = "Normal"

        if sectors is not None and not sectors.empty:
            best_sector_row = sectors.sort_values(
                "Daily %",
                ascending=False,
                na_position="last",
            ).iloc[0]

            best_sector = (
                f"{best_sector_row.get('Name', 'N/A')} "
                f"({best_sector_row.get('Symbol', 'N/A')})"
            )

            best_sector_move = format_pct(
                best_sector_row.get("Daily %")
            )

        else:
            best_sector = "N/A"
            best_sector_move = "N/A"

        if megacaps is not None and not megacaps.empty:
            best_mega_row = megacaps.sort_values(
                "Daily %",
                ascending=False,
                na_position="last",
            ).iloc[0]

            best_mega = (
                f"{best_mega_row.get('Name', 'N/A')} "
                f"({best_mega_row.get('Symbol', 'N/A')})"
            )

            best_mega_move = format_pct(
                best_mega_row.get("Daily %")
            )

        else:
            best_mega = "N/A"
            best_mega_move = "N/A"

        leadership_tone = (
            "good"
            if scanner_regime in ("RISK_ON", "RISK-ON")
            else "warning"
            if scanner_regime in ("CAUTIOUS", "SELECTIVE")
            else "risk"
            if scanner_regime in ("DEFENSIVE", "RISK_OFF", "RISK-OFF")
            else "neutral"
        )

        pulse_list_grid(
            [
                {
                    "title": "Action Plan",
                    "rows": [
                        ("1", action_cards[0]),
                        ("2", action_cards[1]),
                        ("3", action_cards[2]),
                        ("4", action_cards[3]),
                    ],
                    "tone": trade_bias_tone,
                },
                {
                    "title": "Trade Bias",
                    "rows": [
                        ("Long Exposure", long_exposure),
                        ("Preferred Setup", preferred_setup),
                        ("Avoid", avoid_text),
                        ("Aggression", aggression),
                        (
                            "Position Size",
                            f"{scanner_execution_multiplier:.2f}x",
                        ),
                    ],
                    "tone": trade_bias_tone,
                },
                {
                    "title": "Leadership Focus",
                    "rows": [
                        ("Leading Sector", best_sector),
                        ("Sector Move", best_sector_move),
                        ("Leading Megacap", best_mega),
                        ("Megacap Move", best_mega_move),
                        (
                            "Confidence",
                            f"{getattr(event, 'confidence', 0):.0f}%",
                        ),
                        (
                            "Market Condition",
                            getattr(event, "label", "N/A"),
                        ),
                    ],
                    "tone": leadership_tone,
                },
            ],
            min_width=300,
        )

        st.caption(
            "Informational leadership read only — not a buy signal."
        )

        help_text(
            "Use the action plan and trade bias to decide how aggressive "
            "the scanner should be. Leadership focus shows where current "
            "institutional strength is concentrated."
        )

        # =====================================================
        # MARKET REGIME DASHBOARD
        # Compact responsive regime dashboard.
        # =====================================================

        st.divider()

        st.subheader("🌐 Market Regime Dashboard")

        st.caption(
            "What it means: Breaks down the current market regime and "
            "exposure levels."
        )

        pulse_metric_grid(
            [
                {
                    "label": "Current Regime",
                    "value": f"{regime_icon(scanner_regime)} {scanner_regime}",
                    "detail": "Market mode.",
                    "tone": regime_tone(scanner_regime),
                },
                {
                    "label": "Confidence",
                    "value": f"{getattr(event, 'confidence', 0):.0f}%",
                    "detail": "Signal confidence.",
                    "tone": "info",
                },
                {
                    "label": "Breadth",
                    "value": breadth_state,
                    "detail": "Participation read.",
                    "tone": breadth_tone(breadth_score),
                },
                {
                    "label": "Exposure",
                    "value": recommended_exposure,
                    "detail": "Suggested exposure.",
                    "tone": regime_tone(scanner_regime),
                },
                {
                    "label": "Position Size",
                    "value": f"{scanner_execution_multiplier:.2f}x",
                    "detail": "Execution sizing.",
                    "tone": "info",
                },
            ],
            min_width=220,
        )

        regime_decision_df = pd.DataFrame(
            [
                {
                    "Metric": "Current Regime",
                    "Reading": scanner_regime,
                },
                {
                    "Metric": "Market Event",
                    "Reading": getattr(
                        event,
                        "label",
                        "Unknown",
                    ),
                },
                {
                    "Metric": "Scanner Playbook",
                    "Reading": scanner_playbook,
                },
                {
                    "Metric": "Stress Score",
                    "Reading": f"{stress_score}/100",
                },
                {
                    "Metric": "Breadth Score",
                    "Reading": f"{breadth_score:.1f}/100",
                },
                {
                    "Metric": "Breadth State",
                    "Reading": breadth_state,
                },
                {
                    "Metric": "Expected Duration",
                    "Reading": expected_duration,
                },
                {
                    "Metric": "Exposure Range",
                    "Reading": recommended_exposure,
                },
                {
                    "Metric": "Position Size",
                    "Reading": f"{scanner_execution_multiplier:.2f}x",
                },
            ]
        )

        with st.expander(
            "Regime Details",
            expanded=False,
        ):
            st.dataframe(
                regime_decision_df,
                width="stretch",
                hide_index=True,
            )

        help_text(
            "Regimes determine exposure levels and scanner aggressiveness."
        )
        
        # =====================================================
        # MARKET SNAPSHOT
        # =====================================================

        st.divider()

        st.subheader("📌 Market Snapshot")

        st.caption(
            "What it means: Quick read of risk assets and defensive assets "
            "to identify institutional positioning."
        )

        pulse_list_card(
            "Risk Assets",
            [
                ("QQQ", format_pct(qqq)),
                ("SPY", format_pct(spy)),
                ("IWM", format_pct(iwm)),
                ("SOXX", format_pct(soxx)),
                ("DIA", format_pct(dia)),
            ],
            tone="neutral",
        )

        pulse_list_card(
            "Defensive / Hedge Assets",
            [
                ("VIXY", format_pct(vixy)),
                ("TLT", format_pct(tlt)),
                ("GLD", format_pct(gld)),
                ("UUP", format_pct(uup)),
                ("HYG", format_pct(hyg)),
            ],
            tone="info",
        )

        # =====================================================
        # MARKET SNAPSHOT INTERPRETATION
        # =====================================================

        snapshot_values = [
            qqq,
            spy,
            iwm,
            soxx,
            dia,
            tlt,
            gld,
            uup,
            hyg,
        ]

        snapshot_negative = sum(
            1
            for value in snapshot_values
            if pd.notna(value) and value < 0
        )

        snapshot_positive = sum(
            1
            for value in snapshot_values
            if pd.notna(value) and value > 0
        )

        if snapshot_negative >= 7:

            st.error(
                "Snapshot: Broad selling pressure. "
                "Most major indexes and asset classes are declining together."
            )

        elif snapshot_negative >= 5:

            st.warning(
                "Snapshot: Weakness is spreading across multiple asset classes. "
                "Trade cautiously."
            )

        elif snapshot_positive >= 7:

            st.success(
                "Snapshot: Broad participation across major indexes and asset classes."
            )

        else:

            st.info(
                "Snapshot: Mixed conditions. Leadership and sector selection matter."
            )

        # =====================================================
        # KEY MARKET TABLES
        # Reference section moved below decision-support blocks.
        # =====================================================

        st.divider()

        st.subheader("📊 Key Market Tables")

        st.caption(
            "What it means: Real-time performance of major indexes, sectors, "
            "and megacap stocks."
        )

        display_compact_market_table(
            "Major Indexes",
            indexes,
            max_rows=10,
        )

        display_compact_market_table(
            "Megacaps",
            megacaps,
            max_rows=10,
        )

        display_compact_market_table(
            "Sector Reaction",
            sectors,
            max_rows=12,
        )
        # =====================================================
        # REFERENCE CENTER
        # Compact reference area.
        # =====================================================

        st.divider()

        st.subheader("📚 Reference Center")

        st.caption(
            "What it means: Historical and diagnostic tools used to validate "
            "the current market reading."
        )

        ref_left, ref_right = responsive_columns(2)

        with ref_left:
            with st.expander(
                "🔎 Similar Past Events",
                expanded=False,
            ):

                if similar_events_df.empty:
                    st.info(
                        "Not enough similar events recorded yet. "
                        "This section becomes more useful as the event database grows."
                    )
                else:
                    st.dataframe(
                        similar_events_df,
                        width="stretch",
                        hide_index=True,
                    )

            with st.expander(
                "📚 Recent Market Events",
                expanded=False,
            ):

                if history_df.empty:

                    st.info(
                        "No market events have been recorded yet."
                    )

                else:

                    display_cols = [
                        col for col in [
                            "Date",
                            "Event",
                            "Confidence",
                            "Stress Score",
                            "Stress Label",
                            "Regime",
                            "Breadth State",
                        ]
                        if col in history_df.columns
                    ]

                    history_view_df = (
                        history_df[display_cols]
                        if display_cols
                        else history_df
                    )

                    st.dataframe(
                        history_view_df,
                        width="stretch",
                        hide_index=True,
                    )

        with ref_right:
            with st.expander(
                "🔄 Recovery Diagnostics",
                expanded=False,
            ):

                if not recovery_diagnostics_ready:
                    st.info(
                        "At least two regime history records are needed "
                        "to calculate recovery diagnostics."
                    )
                else:
                    pulse_metric_grid(
                        [
                            {
                                "label": "Days in Regime",
                                "value": recovery_diagnostics_metrics.get("Days in Regime", "N/A"),
                                "detail": "Current stretch.",
                                "tone": "info",
                            },
                            {
                                "label": "Regime Started",
                                "value": recovery_diagnostics_metrics.get("Regime Started", "N/A"),
                                "detail": "Start date.",
                                "tone": "neutral",
                            },
                            {
                                "label": "Prior Avg Duration",
                                "value": recovery_diagnostics_metrics.get("Prior Avg Duration", "N/A"),
                                "detail": "Historical average.",
                                "tone": "neutral",
                            },
                            {
                                "label": "Duration Status",
                                "value": recovery_diagnostics_metrics.get("Duration Status", "N/A"),
                                "detail": "Regime maturity.",
                                "tone": "info",
                            },
                        ],
                        min_width=220,
                    )

                    pulse_metric_grid(
                        [
                            {
                                "label": "Breadth Score",
                                "value": recovery_diagnostics_metrics.get("Breadth Score", "N/A"),
                                "detail": "Participation score.",
                                "tone": "info",
                            },
                            {
                                "label": "Breadth Recovery",
                                "value": recovery_diagnostics_metrics.get("Breadth Recovery", "N/A"),
                                "detail": "Recovery progress.",
                                "tone": "good",
                            },
                            {
                                "label": "Points to Recovery",
                                "value": recovery_diagnostics_metrics.get("Points to Recovery", "N/A"),
                                "detail": "Needed improvement.",
                                "tone": "warning",
                            },
                            {
                                "label": "Breadth Status",
                                "value": recovery_diagnostics_metrics.get("Breadth Status", "N/A"),
                                "detail": "Current breadth phase.",
                                "tone": "info",
                            },
                        ],
                        min_width=220,
                    )

                    pulse_metric_grid(
                        [
                            {
                                "label": "Recovery Confidence",
                                "value": recovery_diagnostics_metrics.get("Recovery Confidence", "N/A"),
                                "detail": "Forecast confidence.",
                                "tone": "info",
                            },
                            {
                                "label": "Forecast State",
                                "value": recovery_diagnostics_metrics.get("Forecast State", "N/A"),
                                "detail": "Expected phase.",
                                "tone": "neutral",
                            },
                            {
                                "label": "Recovery Velocity",
                                "value": recovery_diagnostics_metrics.get("Recovery Velocity", "N/A"),
                                "detail": "Improvement speed.",
                                "tone": "good",
                            },
                            {
                                "label": "Recovery ETA",
                                "value": recovery_diagnostics_metrics.get("Recovery ETA", "N/A"),
                                "detail": "Estimated timing.",
                                "tone": "info",
                            },
                        ],
                        min_width=220,
                    )

                    st.subheader("Regime Recovery Details")

                    st.dataframe(
                        recovery_details_df,
                        width="stretch",
                        hide_index=True,
                    )

            with st.expander(
                "📋 Market Event Scorecard",
                expanded=False,
            ):
                st.dataframe(
                    scorecard_df,
                    width="stretch",
                    hide_index=True,
                )

        st.caption(
            "Reference tools are collapsed to keep the decision flow clean. "
            "Market tables live in the right rail below decision-support blocks."
        )
