# =========================================================
# 📐 JFBP QUANT DESK — RESPONSIVE FRAMEWORK v1.0
# Shared layout helpers and device guardrails
# =========================================================

from __future__ import annotations

from typing import Sequence

import streamlit as st


# =========================================================
# CSS
# =========================================================

def inject_responsive_css(max_width: int = 1500) -> None:
    """Global responsive guardrails for JFBP pages.

    Safe to call at the top of every page. It keeps wide desktop layouts clean,
    stacks columns on tablets/phones, and prevents tables/cards from breaking
    outside the viewport.
    """
    st.markdown(
        f"""
        <style>
            .block-container {{
                max-width: {int(max_width)}px !important;
                padding-top: 1.35rem !important;
                padding-bottom: 2.5rem !important;
                padding-left: clamp(0.85rem, 2.2vw, 2.35rem) !important;
                padding-right: clamp(0.85rem, 2.2vw, 2.35rem) !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }}

            h1 {{
                font-size: clamp(1.75rem, 3.6vw, 2.45rem) !important;
                line-height: 1.12 !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
                margin: 0 0 0.26rem 0 !important;
            }}

            h2, h3 {{
                font-size: clamp(1.08rem, 2.2vw, 1.45rem) !important;
                line-height: 1.18 !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
                margin: 0.72rem 0 0.28rem 0 !important;
            }}

            div[data-testid="stHeadingWithActionElements"] {{
                margin: 0.10rem 0 0.12rem 0 !important;
            }}

            div[data-testid="stHeadingWithActionElements"] h1,
            div[data-testid="stHeadingWithActionElements"] h2,
            div[data-testid="stHeadingWithActionElements"] h3 {{
                margin: 0 !important;
            }}

            div[data-testid="stHorizontalBlock"] {{
                gap: 0.85rem !important;
                align-items: stretch !important;
            }}

            div[data-testid="stHorizontalBlock"] > div,
            div[data-testid="column"] {{
                min-width: 0 !important;
            }}

            div[data-testid="stDataFrame"],
            div[data-testid="stDataEditor"] {{
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch !important;
                border-radius: 12px !important;
            }}

            div[data-testid="stDataFrame"] div,
            div[data-testid="stDataEditor"] div {{
                max-width: 100% !important;
            }}

            div[data-testid="stMetric"],
            div[data-testid="stAlert"],
            div[data-testid="stMarkdownContainer"] {{
                overflow-wrap: anywhere !important;
            }}

            [data-testid="stMetricLabel"],
            [data-testid="stMetricValue"] {{
                white-space: normal !important;
                overflow-wrap: anywhere !important;
            }}

            div[data-testid="stTabs"] {{
                max-width: 100% !important;
                overflow-x: auto !important;
            }}

            div[data-testid="stTabs"] button {{
                white-space: nowrap !important;
            }}

            .stButton > button {{
                border-radius: 10px !important;
                font-weight: 750 !important;
                min-height: 38px !important;
                white-space: normal !important;
            }}

            .jfbp-scroll-x {{
                width: 100%;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }}

            .jfbp-tight-section h2,
            .jfbp-tight-section h3 {{
                margin-bottom: 0.2rem !important;
            }}

            @media (max-width: 1180px) {{
                .block-container {{
                    max-width: 100% !important;
                    padding-left: 1.10rem !important;
                    padding-right: 1.10rem !important;
                }}

                div[data-testid="stHorizontalBlock"] {{
                    flex-wrap: wrap !important;
                }}

                div[data-testid="stHorizontalBlock"] > div,
                div[data-testid="column"] {{
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }}
            }}

            @media (max-width: 760px) {{
                .block-container {{
                    padding-left: 0.80rem !important;
                    padding-right: 0.80rem !important;
                }}

                h1 {{ font-size: clamp(1.55rem, 7vw, 2.0rem) !important; }}
                h2, h3 {{ font-size: clamp(1.02rem, 5vw, 1.28rem) !important; }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# STREAMLIT COLUMN HELPERS
# =========================================================

def columns(spec: int | Sequence[float], gap: str = "small"):
    """Thin wrapper for st.columns.

    Use this as the future replacement point. CSS handles the stacking rules.
    """
    return st.columns(spec, gap=gap)


def desktop_70_30(gap: str = "large"):
    return columns([0.70, 0.30], gap=gap)


def desktop_60_40(gap: str = "large"):
    return columns([0.60, 0.40], gap=gap)


def desktop_50_50(gap: str = "large"):
    return columns([0.50, 0.50], gap=gap)


def metric_grid(count: int, gap: str = "small"):
    """Return a Streamlit metric grid that stacks cleanly under CSS."""
    count = max(1, int(count or 1))
    return columns(count, gap=gap)


# =========================================================
# COMMON PAGE HEADER
# =========================================================

def page_header(
    title: str,
    caption: str = "",
    workflow: str = "",
    max_width: int = 1500,
) -> None:
    inject_responsive_css(max_width=max_width)
    st.title(title)
    if caption:
        st.caption(caption)
    if workflow:
        st.markdown(
            f"""
            <div style="
                background:#eff6ff;
                border:1px solid #bfdbfe;
                border-radius:12px;
                padding:0.78rem 0.9rem;
                color:#1d4ed8;
                font-weight:850;
                margin:0.85rem 0;
                line-height:1.35;
                overflow-wrap:anywhere;
            ">
                🚀 Workflow: {workflow}
            </div>
            """,
            unsafe_allow_html=True,
        )


def section_spacer(height_rem: float = 0.75) -> None:
    st.markdown(
        f"<div style='height:{float(height_rem):.2f}rem;'></div>",
        unsafe_allow_html=True,
    )
