# =========================================================
# 🎨 JFBP QUANT DESK — UI CARDS v1.0
# Shared visual components for command-center pages
# =========================================================

from __future__ import annotations

import html
from typing import Iterable

import streamlit as st


# =========================================================
# FORMATTERS
# =========================================================

def safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def format_money(value, currency: str | None = None) -> str:
    try:
        text = f"${float(value):,.2f}"
    except Exception:
        text = "$0.00"

    if currency:
        return f"{text} {str(currency).upper().strip()}"
    return text


def format_pct(value) -> str:
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "N/A"


# =========================================================
# CSS
# =========================================================

def inject_card_css() -> None:
    """Shared card CSS for JFBP command-center pages."""
    st.markdown(
        """
        <style>
            :root {
                --jfbp-type-h1: clamp(1.75rem, 3.6vw, 2.45rem);
                --jfbp-type-h2: clamp(1.08rem, 2.2vw, 1.45rem);
                --jfbp-type-section: clamp(1.02rem, 1.9vw, 1.22rem);
                --jfbp-type-card-label: 0.72rem;
                --jfbp-type-card-value: clamp(1.05rem, 2.2vw, 1.35rem);
                --jfbp-type-body: 0.94rem;
                --jfbp-type-caption: 0.82rem;
            }

            .jfbp-h1 {
                font-size: var(--jfbp-type-h1);
                line-height: 1.12;
                font-weight: 850;
                color: #1f2937;
                margin: 0;
            }

            .jfbp-h2,
            .jfbp-section-title {
                font-size: var(--jfbp-type-h2);
                line-height: 1.18;
                font-weight: 850;
                color: #1f2937;
                margin: 0;
            }

            .jfbp-section-title {
                font-size: var(--jfbp-type-section);
            }

            .jfbp-body {
                font-size: var(--jfbp-type-body);
                line-height: 1.45;
                font-weight: 700;
                color: #334155;
            }

            .jfbp-caption {
                font-size: var(--jfbp-type-caption);
                line-height: 1.35;
                color: #64748b;
            }

            .jfbp-card {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 0.88rem 0.96rem;
                margin-bottom: 0.72rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
                min-height: 88px;
                box-sizing: border-box;
                overflow: hidden;
                overflow-wrap: anywhere;
            }

            .jfbp-card.neutral { background: #f8fafc; border-color: #dbe3ef; }
            .jfbp-card.info { background: #eff6ff; border-color: #bfdbfe; }
            .jfbp-card.good { background: #ecfdf5; border-color: #bbf7d0; }
            .jfbp-card.warning { background: #fffbeb; border-color: #fde68a; }
            .jfbp-card.risk { background: #fef2f2; border-color: #fecaca; }

            .jfbp-card-label {
                font-size: var(--jfbp-type-card-label);
                text-transform: uppercase;
                letter-spacing: 0.045em;
                color: #64748b;
                font-weight: 850;
                margin-bottom: 0.28rem;
                line-height: 1.28;
            }

            .jfbp-card-title {
                font-size: 0.98rem;
                font-weight: 900;
                color: #111827;
                line-height: 1.20;
                margin-bottom: 0.28rem;
            }

            .jfbp-card-value {
                font-size: var(--jfbp-type-card-value);
                line-height: 1.16;
                font-weight: 900;
                color: #111827;
                overflow-wrap: anywhere;
            }

            .jfbp-card.info .jfbp-card-value { color: #1d4ed8; }
            .jfbp-card.good .jfbp-card-value { color: #166534; }
            .jfbp-card.warning .jfbp-card-value { color: #92400e; }
            .jfbp-card.risk .jfbp-card-value { color: #991b1b; }

            .jfbp-card-detail {
                font-size: 0.80rem;
                color: #64748b;
                margin-top: 0.35rem;
                line-height: 1.35;
                overflow-wrap: anywhere;
            }

            .jfbp-hero {
                border: 1px solid #bfdbfe;
                background: #eff6ff;
                border-radius: 18px;
                padding: 0.88rem 0.92rem;
                margin: 0.60rem 0 0.82rem 0;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
                overflow-wrap: anywhere;
            }

            .jfbp-hero.good { border-color: #bbf7d0; background: #ecfdf5; }
            .jfbp-hero.warning { border-color: #fde68a; background: #fffbeb; }
            .jfbp-hero.risk { border-color: #fecaca; background: #fef2f2; }

            .jfbp-hero-kicker {
                font-size: var(--jfbp-type-card-label);
                font-weight: 850;
                letter-spacing: 0.055em;
                text-transform: uppercase;
                color: #64748b;
                margin-bottom: 0.24rem;
            }

            .jfbp-hero-title {
                font-size: clamp(1.22rem, 2.35vw, 1.62rem);
                font-weight: 880;
                line-height: 1.14;
                margin-bottom: 0.30rem;
                color: #1d4ed8;
            }

            .jfbp-hero.good .jfbp-hero-title { color: #166534; }
            .jfbp-hero.warning .jfbp-hero-title { color: #92400e; }
            .jfbp-hero.risk .jfbp-hero-title { color: #991b1b; }

            .jfbp-hero-text {
                font-size: var(--jfbp-type-body);
                font-weight: 700;
                color: #334155;
                line-height: 1.38;
                margin-bottom: 0.36rem;
            }

            .jfbp-hero-action {
                border-radius: 12px;
                padding: 0.60rem 0.78rem;
                background: rgba(255,255,255,0.76);
                border: 1px solid rgba(148,163,184,0.35);
                color: #111827;
                font-size: var(--jfbp-type-body);
                font-weight: 820;
                line-height: 1.35;
            }

            .jfbp-grid-card-wrap {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 0.75rem;
                margin: 0.35rem 0 1.0rem 0;
            }

            .jfbp-row-card {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                gap: 0.75rem;
                align-items: center;
                background: #f8fafc;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                padding: 0.62rem 0.72rem;
                margin-bottom: 0.42rem;
                color: #111827;
                overflow-wrap: anywhere;
            }

            .jfbp-row-card-value {
                color: #1d4ed8;
                font-weight: 950;
                white-space: nowrap;
            }

            .jfbp-grid-card-wrap {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 0.85rem;
                margin: 0.25rem 0 1.25rem 0;
            }

            @media (max-width: 760px) {
                .jfbp-card { min-height: 82px; padding: 0.85rem 0.92rem; }
                .jfbp-row-card { grid-template-columns: 1fr; }
                .jfbp-row-card-value { white-space: normal; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# COMPONENTS
# =========================================================

def metric_card(label: str, value, detail: str = "", tone: str = "neutral") -> None:
    inject_card_css()
    detail_html = (
        f'<div class="jfbp-card-detail">{html.escape(str(detail))}</div>'
        if detail
        else ""
    )
    st.markdown(
        f"""
        <div class="jfbp-card {html.escape(str(tone))}">
            <div class="jfbp-card-label">{html.escape(str(label))}</div>
            <div class="jfbp-card-value">{html.escape(str(value))}</div>
            {detail_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero_card(
    title: str,
    subtitle: str = "",
    action: str = "",
    kicker: str = "Institutional Command",
    tone: str = "info",
) -> None:
    inject_card_css()
    subtitle_html = (
        f'<div class="jfbp-hero-text">{html.escape(str(subtitle))}</div>'
        if subtitle
        else ""
    )
    action_html = (
        f'<div class="jfbp-hero-action">{html.escape(str(action))}</div>'
        if action
        else ""
    )
    st.markdown(
        f"""
        <div class="jfbp-hero {html.escape(str(tone))}">
            <div class="jfbp-hero-kicker">{html.escape(str(kicker))}</div>
            <div class="jfbp-hero-title">{html.escape(str(title))}</div>
            {subtitle_html}
            {action_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def row_card(label: str, value: str, detail: str = "", tone: str = "info") -> None:
    inject_card_css()
    detail_html = (
        f'<div style="color:#64748b;font-size:0.78rem;margin-top:0.15rem;">{html.escape(str(detail))}</div>'
        if detail
        else ""
    )
    st.markdown(
        f"""
        <div class="jfbp-row-card">
            <div>
                <div style="font-weight:950;">{html.escape(str(label))}</div>
                {detail_html}
            </div>
            <div class="jfbp-row-card-value">{html.escape(str(value))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_row(label: str, score: float, detail: str = "") -> None:
    score = max(0.0, min(100.0, safe_float(score)))
    icon = "✅" if score >= 80 else "🟡" if score >= 60 else "🔴"
    row_card(label=f"{icon} {label}", value=f"{score:.0f}/100", detail=detail)


def card_grid(items: Iterable[dict], columns: int | None = None) -> None:
    """Render a simple auto-fit grid from dictionaries.

    Expected keys: label, value, detail, tone.
    """
    inject_card_css()
    cards = ""
    for item in items:
        label = html.escape(str(item.get("label", "")))
        value = html.escape(str(item.get("value", "")))
        detail = html.escape(str(item.get("detail", "")))
        tone = html.escape(str(item.get("tone", "neutral")))
        detail_html = f'<div class="jfbp-card-detail">{detail}</div>' if detail else ""
        cards += f"""
        <div class="jfbp-card {tone}">
            <div class="jfbp-card-label">{label}</div>
            <div class="jfbp-card-value">{value}</div>
            {detail_html}
        </div>
        """

    grid_style = ""
    if columns and columns > 0:
        grid_style = f"grid-template-columns: repeat({int(columns)}, minmax(0, 1fr));"

    st.markdown(
        f'<div class="jfbp-grid-card-wrap" style="{grid_style}">{cards}</div>',
        unsafe_allow_html=True,
    )
