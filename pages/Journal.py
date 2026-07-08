# =========================================================
# 📓 JFBP JOURNAL PAGE v29.0
# TRADE JOURNAL INTELLIGENCE
# + JOURNAL v2.1 TRADE LESSONS ARCHIVE
# + INSTITUTIONAL RESPONSIVE MAKEOVER
# + IPAD / MOBILE SAFE CARD GRID
# =========================================================

from __future__ import annotations

import html
from pathlib import Path
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from core.bootstrap import init_core
from analytics.performance import PerformanceAnalyzer

try:
    from core.portfolio_db import (
        load_journal_reviews,
    )
except Exception:  # pragma: no cover
    load_journal_reviews = None

try:
    from pages.SaaS_Core import get_supabase_client
except Exception:  # pragma: no cover
    get_supabase_client = None

try:
    from core.responsive import inject_responsive_css, columns as jfbp_columns
    from core.ui_cards import inject_card_css, card_grid, hero_card
except Exception:  # pragma: no cover
    inject_responsive_css = None
    inject_card_css = None
    card_grid = None
    hero_card = None
    jfbp_columns = None


# =========================================================
# JOURNAL DATA FILES
# =========================================================

DATA_DIR = Path("data")
LESSONS_FILE = DATA_DIR / "journal_trade_lessons.csv"
LESSON_COLUMNS = ["Date", "Symbol", "Grade", "Tag", "Lesson", "Source"]
JOURNAL_LESSONS_TABLE = "journal_reviews"


# =========================================================
# SUPABASE / SAAS HELPERS
# =========================================================

def _current_saas_user_id() -> str:
    """Return the logged-in SaaS user UUID from session_state."""

    # Primary SaaS auth object used by JFBP Quant Desk.
    saas_user = st.session_state.get("saas_user")
    user_id = getattr(saas_user, "user_id", "") if saas_user is not None else ""

    if user_id:
        return str(user_id or "").strip()

    # Fallbacks used by Supabase auth helpers in some pages.
    auth_user = (
        st.session_state.get("user")
        or st.session_state.get("auth_user")
        or {}
    )

    if isinstance(auth_user, dict):
        user_id = auth_user.get("id") or auth_user.get("user_id") or ""
        if user_id:
            return str(user_id or "").strip()

    user_obj = getattr(auth_user, "user", None)
    if user_obj is not None:
        user_id = getattr(user_obj, "id", "") or getattr(user_obj, "user_id", "")
        if user_id:
            return str(user_id or "").strip()

    user_id = getattr(auth_user, "id", "") or getattr(auth_user, "user_id", "")
    return str(user_id or "").strip()


def _journal_review_rows_to_lessons_df(rows) -> pd.DataFrame:
    """Normalize Supabase journal_reviews rows into the Trade Lessons table shape."""

    if not rows:
        return empty_lessons_df()

    normalized = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        created_at = row.get("created_at") or row.get("entry_date") or row.get("timestamp") or ""

        try:
            date_text = pd.to_datetime(created_at).strftime("%Y-%m-%d")
        except Exception:
            date_text = str(created_at or "")[:10]

        if not date_text:
            date_text = datetime.now().strftime("%Y-%m-%d")

        setup_grade = str(row.get("setup_grade") or "").upper().strip()
        execution_grade = str(row.get("execution_grade") or "").upper().strip()
        grade = row.get("grade") or _combined_grade(setup_grade or "C", execution_grade or "C")

        normalized.append({
            "Date": date_text,
            "Symbol": str(row.get("symbol") or "N/A").upper().strip(),
            "Grade": str(grade or "N/A").upper().strip(),
            "Tag": str(row.get("tag") or "Process Review").strip(),
            "Lesson": str(row.get("notes") or row.get("lesson") or "").strip(),
            "Source": str(row.get("source") or "Supabase Review").strip(),
        })

    return clean_lessons_df(pd.DataFrame(normalized, columns=LESSON_COLUMNS))


def _lessons_file_for_user(user_id: str) -> Path:
    user_id = str(user_id or "").strip()
    if not user_id:
        return DATA_DIR / "journal_trade_lessons_anonymous.csv"

    safe_user = "".join(ch for ch in user_id.lower() if ch.isalnum())[:32]
    if not safe_user:
        safe_user = "anonymous"
    return DATA_DIR / f"journal_trade_lessons_{safe_user}.csv"


def _journal_lessons_rows_to_df(rows) -> pd.DataFrame:
    if not rows:
        return empty_lessons_df()

    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        created_at = row.get("created_at") or row.get("timestamp") or ""
        try:
            date_text = pd.to_datetime(created_at).strftime("%Y-%m-%d")
        except Exception:
            date_text = str(created_at or "")[:10]

        if not date_text:
            date_text = datetime.now().strftime("%Y-%m-%d")

        setup_grade = str(row.get("setup_grade") or "C").upper().strip()
        execution_grade = str(row.get("execution_grade") or "C").upper().strip()
        grade = _combined_grade(setup_grade, execution_grade)

        normalized.append(
            {
                "Date": date_text,
                "Symbol": str(row.get("symbol") or "N/A").upper().strip(),
                "Grade": grade,
                "Tag": str(row.get("tag") or "Process Review").strip(),
                "Lesson": str(row.get("notes") or row.get("lesson") or "").strip(),
                "Source": str(row.get("source") or "Manual Trade Review").strip(),
            }
        )

    return clean_lessons_df(pd.DataFrame(normalized, columns=LESSON_COLUMNS))


def _journal_supabase_persistence_available(user_id: str) -> tuple[bool, str, object]:
    user_id = str(user_id or "").strip()
    if not user_id:
        return False, "Login required to save journal lessons.", None

    if get_supabase_client is None:
        return False, "Supabase client import is unavailable in Journal.", None

    try:
        client = get_supabase_client()
    except Exception as exc:
        return False, f"Supabase client unavailable: {exc}", None

    if client is None:
        return False, "Supabase client unavailable.", None

    try:
        (
            client.table(JOURNAL_LESSONS_TABLE)
            .select("id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        return (
            False,
            "Journal table missing or inaccessible. Expected table: "
            f"{JOURNAL_LESSONS_TABLE}. Error: {exc}",
            client,
        )
    return True, "Available", client


def _ensure_widget_default(key: str, default: Any) -> Any:
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def _insert_journal_lesson(
    client,
    user_id: str,
    symbol: str,
    execution_grade: str,
    setup_grade: str,
    tag: str,
    notes: str,
) -> dict:
    payload = {
        "user_id": user_id,
        "symbol": symbol,
        "execution_grade": execution_grade,
        "setup_grade": setup_grade,
        "tag": tag,
        "notes": notes,
        "source": "Manual Trade Review",
    }

    existing = (
        client.table(JOURNAL_LESSONS_TABLE)
        .select("id")
        .eq("user_id", user_id)
        .eq("symbol", symbol)
        .eq("execution_grade", execution_grade)
        .eq("setup_grade", setup_grade)
        .eq("tag", tag)
        .eq("notes", notes)
        .limit(1)
        .execute()
    )
    existing_rows = getattr(existing, "data", None) or []
    if existing_rows:
        return {
            "status": "DUPLICATE",
            "storage": "supabase",
            "row": existing_rows[0],
        }

    result = client.table(JOURNAL_LESSONS_TABLE).insert(payload).execute()
    return {
        "status": "OK",
        "storage": "supabase",
        "result": result,
    }


def append_trade_lesson(
    symbol: str,
    setup_grade: str,
    execution_grade: str,
    tag: str,
    notes: str,
    mistake: bool = False,
) -> dict:
    """Persist a manual Journal lesson to Supabase for the logged-in user."""

    symbol = str(symbol or "N/A").upper().strip() or "N/A"
    setup_grade = str(setup_grade or "C").upper().strip()
    execution_grade = str(execution_grade or "C").upper().strip()
    notes = str(notes or "").strip()

    final_tag = str(tag or "None").strip()
    if final_tag == "None":
        final_tag = "Mistake" if mistake else "Process Review"

    user_id = _current_saas_user_id()
    ready, reason, client = _journal_supabase_persistence_available(user_id)
    if not ready:
        st.session_state["journal_supabase_last_save"] = "FAILED"
        st.session_state["journal_supabase_last_error"] = reason
        return {
            "status": "FAILED",
            "storage": "none",
            "reason": reason,
        }

    try:
        result = _insert_journal_lesson(
            client=client,
            user_id=user_id,
            symbol=symbol,
            execution_grade=execution_grade,
            setup_grade=setup_grade,
            tag=final_tag,
            notes=notes,
        )
        st.session_state["journal_supabase_last_save"] = result.get("status", "OK")
        st.session_state["journal_supabase_last_error"] = ""
        return result
    except Exception as exc:
        message = f"Journal lesson save failed: {exc}"
        st.session_state["journal_supabase_last_save"] = "FAILED"
        st.session_state["journal_supabase_last_error"] = message
        return {
            "status": "FAILED",
            "storage": "supabase",
            "reason": message,
        }


# =========================================================
# RESPONSIVE UI HELPERS
# =========================================================

def inject_journal_css() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.4rem !important;
                padding-bottom: 2.5rem !important;
                max-width: 1500px !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            h1 {
                font-size: var(--jfbp-type-h1, clamp(1.75rem, 3.6vw, 2.45rem)) !important;
                font-weight: 850 !important;
                line-height: 1.12 !important;
                color: #1f2937 !important;
            }

            h2, h3 {
                font-size: var(--jfbp-type-h2, clamp(1.08rem, 2.2vw, 1.45rem)) !important;
                font-weight: 850 !important;
                line-height: 1.18 !important;
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
                border-radius: 12px !important;
            }

            div[data-testid="stDataFrame"] * {
                white-space: normal !important;
                overflow-wrap: break-word !important;
            }

            div[data-testid="stAlert"] {
                overflow-wrap: break-word !important;
            }

            .journal-card-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 245px), 1fr));
                gap: 0.85rem;
                margin: 0.45rem 0 1.0rem 0;
            }

            .journal-card-grid--compact {
                gap: 0.55rem;
                margin: 0.22rem 0 0.65rem 0;
            }

            .journal-card-grid--compact .journal-card {
                min-height: 84px;
                padding: 0.68rem 0.76rem;
                margin-bottom: 0.18rem;
            }

            .journal-card-grid--compact .journal-card-label {
                margin-bottom: 0.20rem;
            }

            .journal-card-grid--compact .journal-card-detail {
                margin-top: 0.22rem;
            }

            .journal-metric-strip {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 155px), 1fr));
                gap: 0.55rem;
                margin: 0.18rem 0 0.70rem 0;
            }

            .journal-metric-chip {
                background: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                padding: 0.58rem 0.70rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
            }

            .journal-metric-chip-label {
                color: #64748b;
                font-size: 0.68rem;
                font-weight: 850;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                margin-bottom: 0.16rem;
            }

            .journal-metric-chip-value {
                color: #111827;
                font-size: 0.96rem;
                line-height: 1.12;
                font-weight: 880;
                overflow-wrap: anywhere;
            }

            .journal-queue-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 165px), 1fr));
                gap: 0.55rem;
                margin: 0.20rem 0 0.65rem 0;
            }

            .journal-queue-card {
                background: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                padding: 0.60rem 0.68rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
            }

            .journal-queue-symbol {
                color: #111827;
                font-size: 1.0rem;
                font-weight: 900;
                line-height: 1.1;
                margin-bottom: 0.18rem;
            }

            .journal-queue-status {
                color: #334155;
                font-size: 0.78rem;
                font-weight: 800;
                line-height: 1.2;
                margin-bottom: 0.10rem;
            }

            .journal-queue-detail {
                color: #64748b;
                font-size: 0.74rem;
                line-height: 1.28;
                margin-bottom: 0.34rem;
                overflow-wrap: anywhere;
            }

            .journal-summary-strip {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 170px), 1fr));
                gap: 0.55rem;
                margin: 0.20rem 0 0.55rem 0;
            }

            .journal-summary-card {
                background: #f8fafc;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                padding: 0.62rem 0.70rem;
            }

            .journal-summary-label {
                color: #64748b;
                font-size: 0.68rem;
                font-weight: 850;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                margin-bottom: 0.16rem;
            }

            .journal-summary-value {
                color: #111827;
                font-size: 0.94rem;
                font-weight: 890;
                line-height: 1.12;
                overflow-wrap: anywhere;
            }

            .journal-summary-detail {
                color: #64748b;
                font-size: 0.74rem;
                line-height: 1.25;
                margin-top: 0.16rem;
            }

            .journal-review-layout {
                display: grid;
                grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
                gap: 0.75rem;
                margin-top: 0.18rem;
            }

            .journal-review-panel {
                background: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 14px;
                padding: 0.78rem 0.84rem;
            }

            .journal-review-panel-title {
                font-size: 0.72rem;
                font-weight: 900;
                letter-spacing: 0.055em;
                text-transform: uppercase;
                color: #64748b;
                margin-bottom: 0.32rem;
            }

            .journal-review-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 140px), 1fr));
                gap: 0.45rem;
            }

            .journal-review-item {
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 0.50rem 0.56rem;
            }

            .journal-review-item-label {
                color: #64748b;
                font-size: 0.67rem;
                font-weight: 850;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                margin-bottom: 0.14rem;
            }

            .journal-review-item-value {
                color: #111827;
                font-size: 0.86rem;
                line-height: 1.2;
                font-weight: 850;
                overflow-wrap: anywhere;
            }

            .journal-lessons-layout {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
                gap: 0.55rem;
                margin-top: 0.20rem;
            }

            .journal-lessons-layout .stTextArea textarea {
                min-height: 96px !important;
            }

            .journal-coaching-compact .journal-quality-row {
                padding: 0.52rem 0.62rem;
                margin-bottom: 0.32rem;
            }

            .journal-coaching-compact .journal-quality-label {
                font-size: 0.92rem;
            }

            .journal-coaching-compact .journal-quality-detail {
                font-size: 0.72rem;
            }

            .journal-coaching-compact .journal-quality-value {
                font-size: 0.92rem;
            }

            .journal-analytics-empty {
                background: #f8fafc;
                border: 1px dashed #cbd5e1;
                border-radius: 14px;
                padding: 1.0rem 1.0rem;
                color: #334155;
                font-weight: 650;
                line-height: 1.35;
                margin: 0.25rem 0 0.6rem 0;
            }

            .journal-flow {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 12px;
                padding: 0.72rem 0.82rem;
                margin: 0.50rem 0 0.78rem 0;
                overflow-wrap: break-word;
            }

            .journal-card {
                border-radius: 14px;
                padding: 0.82rem 0.92rem;
                min-height: 96px;
                margin-bottom: 0.55rem;
                overflow-wrap: break-word;
                word-break: normal;
            }

            .journal-card-label {
                font-size: var(--jfbp-type-card-label, 0.72rem);
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #64748b;
                font-weight: 850;
                margin-bottom: 0.32rem;
            }

            .journal-card-value {
                font-size: var(--jfbp-type-card-value, clamp(1.05rem, 2.2vw, 1.35rem));
                line-height: 1.15;
                font-weight: 880;
                overflow-wrap: break-word;
                word-break: normal;
            }

            .journal-card-detail {
                color: #64748b;
                font-size: var(--jfbp-type-caption, 0.82rem);
                line-height: 1.35;
                margin-top: 0.35rem;
            }

            .journal-section-card {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                padding: 0.88rem 0.94rem;
                margin: 0.55rem 0 0.82rem 0;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }

            @media (max-width: 1180px) {
                .block-container {
                    padding-left: 1.25rem !important;
                    padding-right: 1.25rem !important;
                }

                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                }

                div[data-testid="stHorizontalBlock"] > div,
                div[data-testid="column"] {
                    flex: 1 1 48% !important;
                    width: 48% !important;
                }
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem !important;
                    padding-right: 0.9rem !important;
                }

                .journal-metric-strip,
                .journal-queue-grid,
                .journal-review-layout,
                .journal-lessons-layout {
                    grid-template-columns: 1fr;
                }

                div[data-testid="stHorizontalBlock"] > div,
                div[data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }

                .journal-card {
                    min-height: 88px;
                    padding: 0.78rem 0.86rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def responsive_columns(spec, gap: str = "small"):
    """Shared responsive column wrapper.

    Uses core.responsive when available so Journal follows the same
    device-stacking rules as the rest of JFBP Quant Desk.
    """
    if jfbp_columns is not None:
        return jfbp_columns(spec, gap=gap)
    return st.columns(spec, gap=gap)

def navigate_to(page_key: str) -> None:
    st.session_state["jfbp_main_navigation"] = page_key
    st.rerun()

def publish_symbol_handoff(symbol: str, destination: str) -> None:
    symbol = str(symbol or "").upper().strip()
    if symbol:
        st.session_state["selected_symbol"] = symbol
        st.session_state["research_symbol"] = symbol
        st.session_state["research_ticker"] = symbol
        st.session_state["trade_command_symbol"] = symbol
        st.session_state["position_command_symbol"] = symbol
        st.session_state["oms_order_symbol"] = symbol
        st.session_state["journal_selected_symbol"] = symbol
    navigate_to(destination)


def journal_tip(text: str) -> None:
    st.caption(f"💡 {text}")


def tone_palette(tone: str) -> tuple[str, str, str]:
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
    }
    return palette.get(tone, palette["neutral"])


def safe_float(value, default: float = 0.0) -> float:
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


def safe_int(value, default: int = 0) -> int:
    try:
        return int(round(safe_float(value, default)))
    except Exception:
        return default


def fmt_money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def fmt_pct(value) -> str:
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "0.00%"


def safe_percent(value, default: float = 0.0) -> float:
    return safe_float(value, default)


def render_card_grid(cards: list[dict]) -> None:
    pieces = ['<div class="journal-card-grid">']
    for card in cards:
        background, border, value_color = tone_palette(str(card.get("tone", "neutral")))
        pieces.append(
            f'<div class="journal-card" style="background:{background};border:1px solid {border};">'
            f'<div class="journal-card-label">{html.escape(str(card.get("title", "")))}</div>'
            f'<div class="journal-card-value" style="color:{value_color};">{html.escape(str(card.get("value", "")))}</div>'
            f'<div class="journal-card-detail">{html.escape(str(card.get("detail", "")))}</div>'
            f'</div>'
        )
    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_compact_card_grid(cards: list[dict]) -> None:
    pieces = ['<div class="journal-card-grid journal-card-grid--compact">']
    for card in cards:
        background, border, value_color = tone_palette(str(card.get("tone", "neutral")))
        pieces.append(
            f'<div class="journal-card" style="background:{background};border:1px solid {border};">'
            f'<div class="journal-card-label">{html.escape(str(card.get("title", "")))}</div>'
            f'<div class="journal-card-value" style="color:{value_color};">{html.escape(str(card.get("value", "")))}</div>'
            f'<div class="journal-card-detail">{html.escape(str(card.get("detail", "")))}</div>'
            f'</div>'
        )
    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_metric_strip(metrics: list[dict]) -> None:
    pieces = ['<div class="journal-metric-strip">']
    for metric in metrics:
        pieces.append(
            '<div class="journal-metric-chip">'
            f'<div class="journal-metric-chip-label">{html.escape(str(metric.get("label", "")))}</div>'
            f'<div class="journal-metric-chip-value">{html.escape(str(metric.get("value", "")))}</div>'
            '</div>'
        )
    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_summary_strip(metrics: list[dict]) -> None:
    pieces = ['<div class="journal-summary-strip">']
    for metric in metrics:
        pieces.append(
            f'<div class="journal-summary-card"><div class="journal-summary-label">{html.escape(str(metric.get("title", "")))}</div>'
            f'<div class="journal-summary-value">{html.escape(str(metric.get("value", "")))}</div>'
            f'<div class="journal-summary-detail">{html.escape(str(metric.get("detail", "")))}</div></div>'
        )
    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_queue_cards(queue_rows: list[dict]) -> None:
    if not queue_rows:
        st.info("No trade reviews available yet.")
        return

    for chunk_start in range(0, len(queue_rows), 5):
        row_chunk = queue_rows[chunk_start:chunk_start + 5]
        cols = responsive_columns(len(row_chunk))
        for col, item in zip(cols, row_chunk):
            with col:
                tone = "good" if item["status"] in {"Closed Winner", "Executed Well"} else "warning" if item["status"] == "Needs Review" else "risk"
                background, border, value_color = tone_palette(tone)
                try:
                    queue_time = pd.to_datetime(item.get("time_text", ""), errors="coerce")
                    time_label = queue_time.strftime("%b %d • %H:%M") if not pd.isna(queue_time) else str(item.get("time_text", ""))
                except Exception:
                    time_label = str(item.get("time_text", ""))
                st.markdown(
                    f'''
                    <div class="journal-queue-card" style="background:{background};border:1px solid {border};">
                        <div class="journal-queue-symbol" style="color:{value_color};">{html.escape(item["symbol"])} · {html.escape(item["action"] or "Review")}</div>
                        <div class="journal-queue-status">{html.escape(item["status"])}</div>
                        <div class="journal-queue-detail">{html.escape(time_label)}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )
                if st.button("Open Review", key=f"journal_queue_open_{item['key']}", width="stretch"):
                    st.session_state["journal_selected_trade_key"] = item["key"]
                    st.session_state["journal_selected_trade_row"] = item["row"]
                    st.rerun()


def render_review_layout(left_title: str, left_items: list[tuple[str, Any]], right_title: str, right_items: list[tuple[str, Any]]) -> None:
    left_html = ''.join(
        f'<div class="journal-review-item"><div class="journal-review-item-label">{html.escape(str(label))}</div><div class="journal-review-item-value">{html.escape(str(value))}</div></div>'
        for label, value in left_items
    )
    right_html = ''.join(
        f'<div class="journal-review-item"><div class="journal-review-item-label">{html.escape(str(label))}</div><div class="journal-review-item-value">{html.escape(str(value))}</div></div>'
        for label, value in right_items
    )
    st.markdown(
        f'''
        <div class="journal-review-layout">
            <div class="journal-review-panel">
                <div class="journal-review-panel-title">{html.escape(left_title)}</div>
                <div class="journal-review-grid">{left_html}</div>
            </div>
            <div class="journal-review-panel">
                <div class="journal-review-panel-title">{html.escape(right_title)}</div>
                <div class="journal-review-grid">{right_html}</div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value, detail: str = "", tone: str = "neutral") -> None:
    journal_metric_card(label, value, detail, tone)


def render_status_banner(title: str, summary: str, action: str = "", tone: str = "neutral") -> None:
    background, border, _ = tone_palette(tone)
    st.markdown(
        f"""
        <div class="journal-commander-hero {html.escape(tone)}" style="background:{background};border-color:{border};">
            <div class="journal-commander-kicker">{html.escape(title)}</div>
            <div class="journal-commander-summary">{html.escape(summary)}</div>
            {f'<div class="journal-commander-action">{html.escape(action)}</div>' if action else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def journal_metric_card(
    label: str,
    value,
    detail: str = "",
    tone: str = "neutral",
) -> None:
    background, border, value_color = tone_palette(tone)

    card_html = f"""
    <div class="journal-card" style="background:{background};border:1px solid {border};">
        <div class="journal-card-label">{html.escape(str(label))}</div>
        <div class="journal-card-value" style="color:{value_color};">{html.escape(str(value))}</div>
        <div class="journal-card-detail">{html.escape(str(detail))}</div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)


def pnl_tone(value) -> str:
    try:
        num = float(value)
    except Exception:
        return "neutral"

    if num > 0:
        return "good"
    if num < 0:
        return "risk"
    return "neutral"


def ratio_tone(value, good_threshold: float = 1.25, warning_threshold: float = 1.0) -> str:
    try:
        num = float(value)
    except Exception:
        return "neutral"

    if num >= good_threshold:
        return "good"
    if num >= warning_threshold:
        return "warning"
    return "risk"


def pct_tone(value, good_threshold: float = 0.55, warning_threshold: float = 0.45) -> str:
    try:
        num = float(value)
    except Exception:
        return "neutral"

    if num >= good_threshold:
        return "good"
    if num >= warning_threshold:
        return "warning"
    return "risk"


def page():
    run_page()


# =========================================================
# COMMANDER REVIEW SYSTEM — JOURNAL v2.0
# =========================================================

def inject_journal_commander_css() -> None:
    """Institutional command-center visual layer for Journal v2.1."""
    st.markdown(
        """
        <style>
            .journal-commander-hero {
                border: 1px solid #bfdbfe;
                background: #eff6ff;
                border-radius: 18px;
                padding: 0.88rem 0.92rem;
                margin: 0.60rem 0 0.82rem 0;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
            }
            .journal-commander-hero.good {
                border-color: #bbf7d0;
                background: #ecfdf5;
            }
            .journal-commander-hero.warning {
                border-color: #fde68a;
                background: #fffbeb;
            }
            .journal-commander-hero.risk {
                border-color: #fecaca;
                background: #fef2f2;
            }
            .journal-commander-kicker {
                font-size: var(--jfbp-type-card-label, 0.72rem);
                letter-spacing: 0.055em;
                text-transform: uppercase;
                color: #64748b;
                font-weight: 850;
                margin-bottom: 0.24rem;
            }
            .journal-commander-title {
                font-size: clamp(1.22rem, 2.35vw, 1.62rem);
                line-height: 1.14;
                font-weight: 880;
                color: #1d4ed8;
                margin-bottom: 0.30rem;
            }
            .journal-commander-hero.good .journal-commander-title { color: #166534; }
            .journal-commander-hero.warning .journal-commander-title { color: #92400e; }
            .journal-commander-hero.risk .journal-commander-title { color: #991b1b; }
            .journal-commander-summary {
                font-size: var(--jfbp-type-body, 0.94rem);
                color: #1f2937;
                font-weight: 700;
                line-height: 1.38;
            }
            .journal-commander-action {
                margin-top: 0.36rem;
                background: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                padding: 0.60rem 0.78rem;
                color: #111827;
                font-size: var(--jfbp-type-body, 0.94rem);
                font-weight: 820;
                line-height: 1.35;
            }
            .journal-quality-row {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                gap: 0.75rem;
                align-items: center;
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 0.68rem 0.75rem;
                margin-bottom: 0.45rem;
            }
            .journal-quality-label {
                font-weight: 950;
                color: #111827;
            }
            .journal-quality-detail {
                color: #64748b;
                font-size: 0.78rem;
                margin-top: 0.12rem;
            }
            .journal-quality-value {
                font-weight: 950;
                color: #1d4ed8;
                white-space: nowrap;
            }
            @media (max-width: 760px) {
                .journal-card-grid {
                    grid-template-columns: 1fr;
                }

                .journal-quality-row { grid-template-columns: 1fr; }
                .journal-quality-value { white-space: normal; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _journal_letter_grade(score: float) -> str:
    try:
        score = float(score)
    except Exception:
        score = 0.0
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 85:
        return "A-"
    if score >= 80:
        return "B+"
    if score >= 75:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 60:
        return "C"
    return "D"


def build_journal_commander_snapshot(report, ledger, positions) -> dict:
    total_trades = int(getattr(report, "total_trades", 0) or 0)
    win_rate = float(getattr(report, "win_rate", 0.0) or 0.0)
    profit_factor = float(getattr(report, "profit_factor", 0.0) or 0.0)
    expectancy = float(getattr(report, "expectancy", 0.0) or 0.0)
    total_pnl = float(getattr(report, "total_pnl", 0.0) or 0.0)
    realized_pnl = float(getattr(report, "realized_pnl", 0.0) or 0.0)
    unrealized_pnl = float(getattr(report, "unrealized_pnl", 0.0) or 0.0)
    losers = int(getattr(report, "losers", 0) or 0)
    winners = int(getattr(report, "winners", 0) or 0)

    win_score = min(100.0, max(0.0, win_rate * 100.0 / 0.65)) if win_rate > 0 else 0.0
    pf_score = min(100.0, profit_factor / 2.0 * 100.0) if profit_factor > 0 else 0.0
    exp_score = 85.0 if expectancy > 0 else 55.0 if expectancy == 0 else 25.0
    pnl_score = 85.0 if total_pnl > 0 else 55.0 if total_pnl == 0 else 25.0
    data_score = 90.0 if total_trades >= 20 else 75.0 if total_trades >= 5 else 55.0 if total_trades > 0 else 30.0

    discipline_score = round(
        win_score * 0.25
        + pf_score * 0.25
        + exp_score * 0.20
        + pnl_score * 0.20
        + data_score * 0.10
    )
    discipline_score = int(max(0, min(100, discipline_score)))

    if total_trades == 0:
        status = "NO DATA"
        tone = "warning"
        action = "Generate fills through OMS or Manual Order Ticket, then review performance here."
    elif discipline_score >= 80 and expectancy > 0 and profit_factor >= 1.25:
        status = "DISCIPLINED"
        tone = "good"
        action = "Continue current process. Protect discipline and let A-grade setups work."
    elif total_pnl >= 0 and discipline_score >= 60:
        status = "IMPROVING"
        tone = "good"
        action = "Process is constructive. Review weakest symbols and keep notes after important trades."
    elif discipline_score >= 45:
        status = "NEUTRAL"
        tone = "warning"
        action = "Stay selective. Review losers, mistake tags, and daily performance before adding risk."
    else:
        status = "DETERIORATING"
        tone = "risk"
        action = "Reduce size, review mistakes, and trade only A-grade setups until metrics improve."

    return {
        "status": status,
        "tone": tone,
        "action": action,
        "discipline_score": discipline_score,
        "grade": _journal_letter_grade(discipline_score),
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "total_pnl": total_pnl,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "winners": winners,
        "losers": losers,
        "open_positions": len(positions or {}),
        "data_score": data_score,
    }


def render_commander_review_report(snapshot: dict) -> None:
    tone = snapshot.get("tone", "warning")
    st.subheader("🏅 Commander Review Report")
    st.caption("Fast review read: discipline, win rate, profit factor, expectancy, and immediate coaching action.")
    st.markdown(
        f"""
        <div class="journal-commander-hero {html.escape(tone)}">
            <div class="journal-commander-kicker">Institutional Journal Command · Process Review</div>
            <div class="journal-commander-title">📓 TRADING STATUS: {html.escape(str(snapshot.get('status', 'N/A')))}</div>
            <div class="journal-commander-summary">
                Discipline Score: {snapshot.get('discipline_score', 0)}/100 ·
                Grade: {html.escape(str(snapshot.get('grade', 'N/A')))} ·
                Win Rate: {snapshot.get('win_rate', 0) * 100:.1f}% ·
                Profit Factor: {snapshot.get('profit_factor', 0):.2f} ·
                Expectancy: ${snapshot.get('expectancy', 0):,.2f} ·
                Total P&L: ${snapshot.get('total_pnl', 0):,.2f}
            </div>
            <div class="journal-commander-action">ACTION: {html.escape(str(snapshot.get('action', '')))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_executive_review_brief(snapshot: dict) -> None:
    st.subheader("Executive Review Brief")
    st.caption("Commander-level snapshot before reviewing the ledger, symbols, days, and notes.")
    render_compact_card_grid([
        {"title": "Discipline Score", "value": f"{snapshot.get('discipline_score', 0)}/100", "detail": snapshot.get("grade", "N/A"), "tone": snapshot.get("tone", "warning")},
        {"title": "Win Rate", "value": f"{snapshot.get('win_rate', 0) * 100:.1f}%", "detail": "Winning trades / total", "tone": pct_tone(snapshot.get("win_rate", 0))},
        {"title": "Profit Factor", "value": f"{snapshot.get('profit_factor', 0):.2f}", "detail": "Gross wins / gross losses", "tone": ratio_tone(snapshot.get("profit_factor", 0))},
        {"title": "Expectancy", "value": f"${snapshot.get('expectancy', 0):,.2f}", "detail": "Average expected trade", "tone": pnl_tone(snapshot.get("expectancy", 0))},
    ])
    render_compact_card_grid([
        {"title": "Total Trades", "value": snapshot.get("total_trades", 0), "detail": "Ledger entries analyzed", "tone": "info"},
        {"title": "Winners / Losers", "value": f"{snapshot.get('winners', 0)} / {snapshot.get('losers', 0)}", "detail": "Outcome split", "tone": "good" if snapshot.get('winners', 0) >= snapshot.get('losers', 0) else "warning"},
        {"title": "Total P&L", "value": f"${snapshot.get('total_pnl', 0):,.2f}", "detail": "Realized + unrealized", "tone": pnl_tone(snapshot.get("total_pnl", 0))},
        {"title": "Open Positions", "value": snapshot.get("open_positions", 0), "detail": "Current book exposure", "tone": "info"},
    ])


def render_journal_scorecard(snapshot: dict) -> None:
    st.subheader("📋 Journal Scorecard")
    st.caption("Trader report card for discipline, execution quality, risk control, consistency, and data quality.")
    win_rate = snapshot.get("win_rate", 0)
    profit_factor = snapshot.get("profit_factor", 0)
    expectancy = snapshot.get("expectancy", 0)
    total_pnl = snapshot.get("total_pnl", 0)
    data_score = snapshot.get("data_score", 0)

    scores = [
        ("Discipline", snapshot.get("discipline_score", 0), "Composite of win rate, profit factor, expectancy, P&L, and data depth"),
        ("Execution", min(100, profit_factor / 2.0 * 100) if profit_factor > 0 else 0, f"Profit factor {profit_factor:.2f}"),
        ("Risk Control", 85 if total_pnl >= 0 else 45, f"Total P&L ${total_pnl:,.2f}"),
        ("Consistency", min(100, win_rate / 0.65 * 100) if win_rate > 0 else 0, f"Win rate {win_rate*100:.1f}%"),
        ("Data Quality", data_score, f"{snapshot.get('total_trades', 0)} trade rows analyzed"),
    ]

    for label, score, detail in scores:
        icon = "🟢" if score >= 75 else "🟡" if score >= 55 else "🔴"
        st.markdown(
            f"""
            <div class="journal-quality-row">
                <div>
                    <div class="journal-quality-label">{icon} {html.escape(label)}</div>
                    <div class="journal-quality-detail">{html.escape(detail)}</div>
                </div>
                <div class="journal-quality-value">{score:.0f}/100</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_coaching_engine(snapshot: dict, df: pd.DataFrame | None = None, pnl_col: str = "realized_delta") -> None:
    st.subheader("🧠 Coaching Engine")
    st.caption("Process guidance based on current Journal performance and available ledger patterns.")

    strength = "Data foundation is building."
    weakness = "Not enough closed-trade evidence yet."
    focus = "Keep fills and reviews current so the coaching engine becomes more useful."
    tone = "warning"

    if snapshot.get("total_trades", 0) > 0:
        if snapshot.get("expectancy", 0) > 0:
            strength = "Positive expectancy is present."
        elif snapshot.get("win_rate", 0) >= 0.5:
            strength = "Win rate is holding up."
        else:
            strength = "Journal is identifying weak spots early."

        if snapshot.get("profit_factor", 0) < 1:
            weakness = "Profit factor is below 1.00. Losses are overpowering wins."
            focus = "Reduce size and review the largest losing trades before adding risk."
            tone = "risk"
        elif snapshot.get("expectancy", 0) <= 0:
            weakness = "Expectancy is not yet positive."
            focus = "Improve reward/risk and avoid marginal setups."
            tone = "warning"
        else:
            weakness = "Main risk is discipline drift after profitable periods."
            focus = "Continue current process and document every exception."
            tone = "good"

    render_compact_card_grid([
        {"title": "Top Strength", "value": strength, "detail": "What is working", "tone": "good" if snapshot.get("total_trades", 0) else "info"},
        {"title": "Top Weakness", "value": weakness, "detail": "What needs attention", "tone": tone},
        {"title": "Focus Next Week", "value": focus, "detail": "Next process target", "tone": "info"},
    ])


def render_daily_command_center(daily_perf: pd.DataFrame) -> None:
    if daily_perf is None or daily_perf.empty or "realized_pnl" not in daily_perf.columns:
        return
    best_day = daily_perf.sort_values("realized_pnl", ascending=False).iloc[0]
    worst_day = daily_perf.sort_values("realized_pnl", ascending=True).iloc[0]
    avg_daily = float(pd.to_numeric(daily_perf["realized_pnl"], errors="coerce").fillna(0.0).mean())
    active_days = int(len(daily_perf))
    row = responsive_columns(4)
    with row[0]: journal_metric_card("Best Day", str(best_day.get("date", "N/A")), f"${float(best_day.get('realized_pnl', 0)):,.2f}", tone=pnl_tone(best_day.get("realized_pnl", 0)))
    with row[1]: journal_metric_card("Worst Day", str(worst_day.get("date", "N/A")), f"${float(worst_day.get('realized_pnl', 0)):,.2f}", tone=pnl_tone(worst_day.get("realized_pnl", 0)))
    with row[2]: journal_metric_card("Avg Daily P&L", f"${avg_daily:,.2f}", "Average reviewed day", tone=pnl_tone(avg_daily))
    with row[3]: journal_metric_card("Active Days", active_days, "Days with ledger activity", tone="info")


def render_mistake_tracker(df: pd.DataFrame | None) -> None:
    st.subheader("🚨 Mistake Tracker")
    st.caption("Tracks mistake tags when Journal notes or ledger metadata include review tags.")
    if df is None or df.empty:
        st.info("No ledger rows available for mistake tracking yet.")
        return

    tag_col = None
    for candidate in ("tag", "mistake_tag", "review_tag", "mistake"):
        if candidate in df.columns:
            tag_col = candidate
            break

    if not tag_col:
        st.info("No mistake/tag column found yet. Use Manual Trade Review tags to build this section in a future persistent-note version.")
        return

    mistake_df = (
        df[tag_col]
        .fillna("None")
        .astype(str)
        .str.strip()
        .replace("", "None")
        .value_counts()
        .reset_index()
    )
    mistake_df.columns = ["Mistake / Tag", "Count"]
    st.dataframe(mistake_df, width="stretch", hide_index=True, height=min(360, max(160, 38 * (len(mistake_df) + 1))))


# =========================================================
# TRADE LESSONS ARCHIVE — JOURNAL v2.1
# =========================================================

def empty_lessons_df() -> pd.DataFrame:
    return pd.DataFrame(columns=LESSON_COLUMNS)


def clean_lessons_df(lessons_df: pd.DataFrame | None) -> pd.DataFrame:
    if lessons_df is None or lessons_df.empty:
        return empty_lessons_df()

    df = lessons_df.copy()
    for col in LESSON_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[LESSON_COLUMNS].copy()
    for col in LESSON_COLUMNS:
        df[col] = df[col].fillna("").astype(str)

    df["Date"] = df["Date"].replace("", datetime.now().strftime("%Y-%m-%d"))
    df["Symbol"] = df["Symbol"].str.upper().str.strip()
    df["Grade"] = df["Grade"].str.upper().str.strip().replace("", "N/A")
    df["Tag"] = df["Tag"].str.strip().replace("", "None")
    df["Lesson"] = df["Lesson"].str.strip()
    df["Source"] = df["Source"].str.strip().replace("", "Manual Review")
    df = df[df["Lesson"].astype(str).str.strip() != ""].copy()
    return df.reset_index(drop=True)


def load_trade_lessons(local_only: bool = False) -> pd.DataFrame:
    """Load saved trade lessons. Supabase is preferred; CSV is fallback."""

    user_id = _current_saas_user_id()

    if not local_only:
        ready, reason, client = _journal_supabase_persistence_available(user_id)
        st.session_state["journal_supabase_available"] = ready

        if ready and client is not None:
            try:
                result = (
                    client.table(JOURNAL_LESSONS_TABLE)
                    .select("id,user_id,created_at,symbol,execution_grade,setup_grade,tag,notes,source")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                rows = getattr(result, "data", None) or []
                lessons = _journal_lessons_rows_to_df(rows)

                st.session_state["journal_supabase_loaded"] = True
                st.session_state["journal_supabase_review_count"] = len(lessons)
                st.session_state["journal_saved_lessons_count"] = len(lessons)
                st.session_state["journal_supabase_user_id"] = user_id
                st.session_state["journal_supabase_load_error"] = ""
                return lessons

            except Exception as exc:
                st.session_state["journal_supabase_loaded"] = False
                st.session_state["journal_supabase_load_error"] = f"Supabase load failed: {exc}"
        else:
            st.session_state["journal_supabase_loaded"] = False
            st.session_state["journal_supabase_load_error"] = reason

        if user_id and load_journal_reviews is not None:
            try:
                rows = load_journal_reviews(user_id)
                lessons = _journal_review_rows_to_lessons_df(rows)
                if not lessons.empty:
                    st.session_state["journal_saved_lessons_count"] = len(lessons)
                    return lessons
            except Exception:
                pass

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fallback_file = _lessons_file_for_user(user_id)
    if not fallback_file.exists():
        st.session_state.setdefault("journal_saved_lessons_count", 0)
        return empty_lessons_df()
    try:
        lessons = clean_lessons_df(pd.read_csv(fallback_file))
        st.session_state["journal_saved_lessons_count"] = len(lessons)
        return lessons
    except Exception as exc:
        st.session_state["journal_supabase_load_error"] = f"Local fallback read failed: {exc}"
        st.session_state.setdefault("journal_saved_lessons_count", 0)
        return empty_lessons_df()


def save_trade_lessons(lessons_df: pd.DataFrame, user_id: str | None = None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fallback_file = _lessons_file_for_user(user_id or _current_saas_user_id())
    clean_lessons_df(lessons_df).to_csv(fallback_file, index=False)


def _combined_grade(setup_grade: str, execution_grade: str) -> str:
    order = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
    reverse = {5: "A", 4: "B", 3: "C", 2: "D", 1: "F"}
    s = order.get(str(setup_grade).upper(), 3)
    e = order.get(str(execution_grade).upper(), 3)
    avg = int(round((s + e) / 2))
    return reverse.get(max(1, min(5, avg)), "C")


def infer_trade_lessons_from_ledger(df: pd.DataFrame | None, pnl_col: str = "realized_delta") -> pd.DataFrame:
    if df is None or df.empty or pnl_col not in df.columns:
        return empty_lessons_df()

    work = df.copy()
    work[pnl_col] = pd.to_numeric(work[pnl_col], errors="coerce").fillna(0.0)
    losers = work[work[pnl_col] < 0].copy().sort_values(pnl_col, ascending=True).head(5)

    rows = []
    for _, row in losers.iterrows():
        symbol = str(row.get("symbol", "N/A")).upper()
        date_value = row.get("timestamp", "")
        try:
            date_text = pd.to_datetime(date_value).strftime("%Y-%m-%d")
        except Exception:
            date_text = str(date_value or "")[:10]
        if not date_text or date_text.lower() == "none":
            date_text = datetime.now().strftime("%Y-%m-%d")

        loss_value = abs(float(row.get(pnl_col, 0)))
        rows.append({
            "Date": date_text,
            "Symbol": symbol,
            "Grade": "Review",
            "Tag": "Losing Trade",
            "Lesson": f"Review {symbol}: loss of ${loss_value:,.2f}. Confirm setup quality, size, stop discipline, and exit timing before repeating this pattern.",
            "Source": "Ledger Inference",
        })

    return clean_lessons_df(pd.DataFrame(rows, columns=LESSON_COLUMNS))


def render_trade_lessons_archive(df: pd.DataFrame | None, pnl_col: str = "realized_delta") -> None:
    st.divider()
    st.subheader("📚 Trade Lessons Archive")
    st.caption("Persistent lessons extracted from manual reviews. Repeated themes become coaching priorities.")

    saved_lessons = load_trade_lessons()
    inferred_lessons = infer_trade_lessons_from_ledger(df, pnl_col)
    display_lessons = saved_lessons.copy()
    if display_lessons.empty and not inferred_lessons.empty:
        display_lessons = inferred_lessons.copy()

    total_lessons = int(len(saved_lessons))
    if not display_lessons.empty and "Tag" in display_lessons.columns:
        tag_counts = display_lessons["Tag"].fillna("None").astype(str).value_counts()
        most_common_error = str(tag_counts.index[0]) if not tag_counts.empty else "N/A"
    else:
        tag_counts = pd.Series(dtype=int)
        most_common_error = "N/A"

    last_lesson = "N/A"
    if not saved_lessons.empty:
        last_lesson = str(saved_lessons.tail(1).iloc[0].get("Date", "N/A"))
    elif not inferred_lessons.empty:
        last_lesson = "Inferred from ledger"

    improvement_trend = "Building" if total_lessons < 3 else "Active Review"
    if not tag_counts.empty and int(tag_counts.iloc[0]) >= 3:
        improvement_trend = "Repeated Theme"

    render_compact_card_grid([
        {"title": "Total Lessons", "value": total_lessons, "detail": "Saved lesson archive", "tone": "info"},
        {"title": "Most Common Error", "value": most_common_error, "detail": "Repeated tag / theme", "tone": "warning" if most_common_error not in ("N/A", "None") else "neutral"},
        {"title": "Last Lesson Added", "value": last_lesson, "detail": "Most recent archive entry", "tone": "info"},
        {"title": "Improvement Trend", "value": improvement_trend, "detail": "Coaching signal", "tone": "warning" if improvement_trend == "Repeated Theme" else "good"},
    ])

    if display_lessons.empty:
        st.info("No lessons archived yet. Use Manual Trade Review below, add a note, and save it to build the lessons archive.")
        return

    if not saved_lessons.empty:
        st.success("✅ Lesson archived successfully and synced to your account.")
    else:
        st.info("No saved manual lessons yet. Showing inferred review prompts from losing ledger rows.")

    if st.session_state.get("journal_supabase_load_error"):
        st.warning(str(st.session_state.get("journal_supabase_load_error")))

    top_lesson = str(display_lessons.iloc[0].get("Lesson", "No lesson available."))
    repeat_count = int(tag_counts.iloc[0]) if not tag_counts.empty else 1
    hero_tone = "warning" if repeat_count >= 3 else "good"
    st.markdown(
        f"""
        <div class="journal-commander-hero {hero_tone}">
            <div class="journal-commander-kicker">Journal Intelligence · Lessons Archive</div>
            <div class="journal-commander-title">🧠 TOP LESSON</div>
            <div class="journal-commander-summary">{html.escape(top_lesson)}</div>
            <div class="journal-commander-action">
                REPEATED THEME COUNT: {repeat_count}. Estimated impact: improves discipline score, improves win rate, and reduces repeat losing trades.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(display_lessons[LESSON_COLUMNS], width="stretch", hide_index=True, height=min(420, max(180, 38 * (len(display_lessons) + 1))))

    if not tag_counts.empty:
        ranked = tag_counts.reset_index()
        ranked.columns = ["Lesson Type", "Count"]
        ranked.insert(0, "Rank", ["#" + str(i + 1) for i in range(len(ranked))])
        st.subheader("🧭 Lesson Theme Ranking")
        st.caption("Most repeated lessons and mistake themes. Repeated themes become coaching priorities.")
        st.dataframe(ranked, width="stretch", hide_index=True, height=min(360, max(160, 38 * (len(ranked) + 1))))

    with st.expander("🗑️ Manage Trade Lessons Archive", expanded=False):
        st.caption("This only clears the saved lesson archive. It does not affect trade ledger rows or portfolio data.")
        if st.button("Clear Saved Lessons Archive", width="stretch", key="journal_clear_lessons_archive"):
            user_id = _current_saas_user_id()
            ready, reason, client = _journal_supabase_persistence_available(user_id)
            if ready and client is not None:
                try:
                    client.table(JOURNAL_LESSONS_TABLE).delete().eq("user_id", user_id).execute()
                    st.session_state["journal_saved_lessons_count"] = 0
                    st.success("Saved Trade Lessons Archive cleared.")
                except Exception as exc:
                    st.warning(f"Could not clear Supabase lesson archive: {exc}")
            else:
                save_trade_lessons(empty_lessons_df(), user_id=user_id)
                st.warning(f"Supabase unavailable for archive clear. Local fallback cleared instead. {reason}")
            st.rerun()


def _coerce_timestamp_frame(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    work = df.copy()
    if "timestamp" in work.columns:
        work["timestamp"] = pd.to_datetime(work["timestamp"], errors="coerce")
    return work


def build_daily_performance_brief(df: pd.DataFrame | None, report, pnl_col: str = "realized_delta") -> dict:
    work = _coerce_timestamp_frame(df)
    today = datetime.now().date()
    today_df = pd.DataFrame()

    if not work.empty and "timestamp" in work.columns:
        today_df = work[work["timestamp"].dt.date == today].copy()

    if today_df.empty and work.empty:
        today_df = pd.DataFrame(columns=df.columns if df is not None else [])

    if pnl_col not in today_df.columns and pnl_col in work.columns:
        today_df[pnl_col] = work.loc[today_df.index, pnl_col]

    pnl_series = pd.to_numeric(today_df[pnl_col], errors="coerce").fillna(0.0) if pnl_col in today_df.columns else pd.Series(dtype=float)
    winners = pnl_series[pnl_series > 0]
    losers = pnl_series[pnl_series < 0]

    best_idx = pnl_series.idxmax() if not pnl_series.empty else None
    worst_idx = pnl_series.idxmin() if not pnl_series.empty else None

    def _row_symbol(row_index):
        if row_index is None or today_df.empty or row_index not in today_df.index:
            return "—"
        row = today_df.loc[row_index]
        return str(row.get("symbol") or row.get("Symbol") or "—").upper().strip() or "—"

    def _row_value(row_index):
        if row_index is None or pnl_series.empty or row_index not in pnl_series.index:
            return 0.0
        return float(pnl_series.loc[row_index])

    return {
        "trades_today": int(len(today_df)),
        "winning_trades": int((pnl_series > 0).sum()),
        "losing_trades": int((pnl_series < 0).sum()),
        "win_rate": float((pnl_series > 0).mean()) if len(pnl_series) else 0.0,
        "average_gain": float(winners.mean()) if len(winners) else 0.0,
        "average_loss": float(losers.mean()) if len(losers) else 0.0,
        "net_pnl": float(pnl_series.sum()) if len(pnl_series) else 0.0,
        "best_trade_symbol": _row_symbol(best_idx),
        "best_trade_value": _row_value(best_idx),
        "worst_trade_symbol": _row_symbol(worst_idx),
        "worst_trade_value": _row_value(worst_idx),
        "summary": str(getattr(report, "status", "Review complete")) if report is not None else "Review complete",
        "tone": "good" if float(pnl_series.sum()) > 0 else "warning" if len(pnl_series) else "neutral",
    }


def build_trade_review_queue(df: pd.DataFrame | None, pnl_col: str = "realized_delta", limit: int = 8) -> list[dict]:
    work = _coerce_timestamp_frame(df)
    if work.empty:
        return []

    if "timestamp" in work.columns:
        work = work.sort_values("timestamp", ascending=False, na_position="last")

    queue = []
    queued_by_execution_id: dict[str, dict] = {}
    queued_legacy_keys: set[str] = set()

    for idx, row in work.iterrows():
        symbol = str(row.get("symbol") or row.get("Symbol") or "N/A").upper().strip() or "N/A"
        action = str(row.get("action") or row.get("Action") or row.get("tag") or "Review").strip() or "Review"
        pnl_value = safe_float(row.get(pnl_col), 0.0)
        note_text = str(row.get("notes") or row.get("lesson") or "").strip()
        tag_text = str(row.get("tag") or "").strip().lower()
        queue_status = "Needs Review"
        if any(term in tag_text for term in ("violation", "mistake", "bad process")):
            queue_status = "Rule Violation"
        elif pnl_value > 0 and any(term in tag_text for term in ("good", "perfect", "executed")):
            queue_status = "Executed Well"
        elif pnl_value > 0:
            queue_status = "Closed Winner"
        elif pnl_value < 0:
            queue_status = "Needs Review"

        timestamp = row.get("timestamp")
        if pd.isna(timestamp):
            time_text = "N/A"
        else:
            try:
                time_text = pd.to_datetime(timestamp).strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_text = str(timestamp)

        execution_id = str(
            row.get("execution_id")
            or row.get("exec_id")
            or row.get("order_id")
            or ""
        ).strip()

        queue_item = {
            "key": f"{symbol}|{time_text}|{action}|{idx}",
            "execution_id": execution_id,
            "symbol": symbol,
            "status": queue_status,
            "action": action,
            "pnl": pnl_value,
            "time_text": time_text,
            "note_text": note_text,
            "row": row.to_dict(),

        }

        if execution_id:
            if execution_id in queued_by_execution_id:
                existing = queued_by_execution_id[execution_id]
                if not existing.get("note_text") and note_text:
                    existing["note_text"] = note_text
                    existing["row"] = row.to_dict()
                continue

            queued_by_execution_id[execution_id] = queue_item
            queue.append(queue_item)
        else:
            legacy_key = f"{symbol}|{time_text}|{action}|{pnl_value:.6f}"
            if legacy_key in queued_legacy_keys:
                continue
            queued_legacy_keys.add(legacy_key)
            queue.append(queue_item)

        if len(queue) >= limit:
            break

    return queue


def parse_review_sections(notes: str) -> dict[str, str]:
    text = str(notes or "").strip()
    if not text:
        return {}

    headings = [
        "What went well?",
        "What went wrong?",
        "Would I take this trade again?",
        "Rule followed?",
        "Rule broken?",
        "Improvement for next time",
    ]
    values = {heading: "" for heading in headings}

    current = None
    for line in text.splitlines():
        stripped = line.strip()
        matched = None
        for heading in headings:
            normalized = heading.lower().replace("?", "")
            if stripped.lower().startswith(normalized):
                matched = heading
                break
        if matched:
            current = matched
            remainder = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            if remainder:
                values[current] = remainder
            continue
        if current:
            values[current] = (values[current] + "\n" + stripped).strip()

    return {key: value for key, value in values.items() if value}


def compose_review_notes(sections: dict[str, str]) -> str:
    ordered = [
        "What went well?",
        "What went wrong?",
        "Would I take this trade again?",
        "Rule followed?",
        "Rule broken?",
        "Improvement for next time",
    ]
    chunks = []
    for heading in ordered:
        value = str(sections.get(heading, "")).strip()
        if value:
            chunks.append(f"{heading}\n{value}")
    return "\n\n".join(chunks).strip()


def review_quality_assessment(row: dict, pnl_col: str = "realized_delta") -> list[dict[str, str]]:
    pnl_value = safe_float(row.get(pnl_col), 0.0)
    tag_text = str(row.get("tag") or row.get("action") or "").lower()
    note_text = str(row.get("notes") or row.get("lesson") or "").lower()
    combined = f"{tag_text} {note_text}"

    assessments = {
        "Entry Quality": ("Strong" if pnl_value > 0 or "good" in combined else "Needs Review", "good" if pnl_value > 0 else "warning"),
        "Exit Quality": ("Clean" if pnl_value >= 0 else "Needs Work", "good" if pnl_value >= 0 else "risk"),
        "Risk Management": ("Controlled" if "risk" not in combined or "good" in combined else "Review", "info" if "risk" not in combined else "warning"),
        "Discipline": ("On Plan" if any(term in combined for term in ("good", "perfect", "executed")) else "Watch", "good" if any(term in combined for term in ("good", "perfect", "executed")) else "warning"),
        "Execution": ("Stable" if pnl_value >= 0 else "Needs Improvement", "good" if pnl_value >= 0 else "warning"),
    }

    return [
        {"label": key, "value": value, "tone": tone}
        for key, (value, tone) in assessments.items()
    ]


def render_daily_performance_brief(brief: dict) -> None:
    st.subheader("Daily Performance Brief")
    st.caption("What did we learn from today's decisions?")
    tone = brief.get("tone", "neutral")
    render_status_banner(
        title="Institutional Review Center",
        summary="Readout of today's trade decisions, outcomes, and review priorities.",
        action=f"SUMMARY: {brief.get('summary', 'Review complete')}",
        tone=tone,
    )
    render_metric_strip([
        {"label": "Trades Today", "value": brief.get("trades_today", 0)},
        {"label": "Winning Trades", "value": brief.get("winning_trades", 0)},
        {"label": "Losing Trades", "value": brief.get("losing_trades", 0)},
        {"label": "Win Rate", "value": f"{brief.get('win_rate', 0) * 100:.1f}%"},
        {"label": "Average Gain", "value": f"${brief.get('average_gain', 0):,.2f}"},
    ])
    render_summary_strip([
        {"title": "Average Loss", "value": f"${brief.get('average_loss', 0):,.2f}", "detail": "Average loser"},
        {"title": "Net P&L", "value": f"${brief.get('net_pnl', 0):,.2f}", "detail": "Today's realized total"},
        {"title": "Best Trade", "value": brief.get("best_trade_symbol", "—"), "detail": f"{brief.get('best_trade_value', 0):,.2f}"},
        {"title": "Worst Trade", "value": brief.get("worst_trade_symbol", "—"), "detail": f"{brief.get('worst_trade_value', 0):,.2f}"},
    ])


def render_trade_review_queue(queue_rows: list[dict]) -> None:
    st.subheader("Trades Requiring Review")
    st.caption("One click opens the full review.")
    render_queue_cards(queue_rows)


def render_selected_trade_review(selected_trade: dict | None, pnl_col: str = "realized_delta") -> None:
    st.subheader("Selected Trade Review")
    st.caption("Trade snapshot and decision quality for the selected review.")

    if not selected_trade:
        st.info("No trade selected. Choose a trade above to begin the institutional review.")
        return

    snapshot_row = selected_trade
    summary_items = [
        ("Symbol", str(snapshot_row.get("symbol") or snapshot_row.get("Symbol") or "N/A").upper().strip()),
        ("Side", str(snapshot_row.get("action") or snapshot_row.get("side") or "N/A")),
        ("Entry", snapshot_row.get("entry_price") or snapshot_row.get("avg_price") or snapshot_row.get("fill_price") or "N/A"),
        ("Exit", snapshot_row.get("exit_price") or snapshot_row.get("close_price") or snapshot_row.get("fill_price") or "N/A"),
        ("P&L", f"${safe_float(snapshot_row.get(pnl_col), 0.0):,.2f}"),
        ("Position Size", snapshot_row.get("qty") or snapshot_row.get("size") or "N/A"),
    ]
    quality_items = review_quality_assessment(snapshot_row, pnl_col=pnl_col)
    render_review_layout(
        "Trade Summary",
        summary_items,
        "Decision Quality",
        [(item["label"], item["value"]) for item in quality_items],
    )


def render_lessons_learned_center(selected_trade: dict | None, pnl_col: str = "realized_delta") -> None:
    st.subheader("Lessons Learned")
    if not selected_trade:
        st.caption("Select a trade to begin the review.")
        return

    st.caption("Structured review notes that preserve existing lessons while improving presentation.")

    selected_symbol = str((selected_trade or {}).get("symbol") or (selected_trade or {}).get("Symbol") or "").upper().strip()
    existing_notes = str((selected_trade or {}).get("notes") or (selected_trade or {}).get("lesson") or "").strip()
    parsed_notes = parse_review_sections(existing_notes)
    user_id = _current_saas_user_id()
    availability = _journal_supabase_persistence_available(user_id)
    if not isinstance(availability, tuple) or len(availability) != 3:
        supabase_ready, supabase_reason, supabase_client = False, "Unavailable", None
    else:
        supabase_ready, supabase_reason, supabase_client = availability
    st.session_state["journal_supabase_available"] = supabase_ready
    if not supabase_ready:
        st.warning(supabase_reason)

    if existing_notes:
        with st.expander("Existing note", expanded=False):
            st.write(existing_notes)

    _ensure_widget_default("journal_review_symbol", selected_symbol or st.session_state.get("journal_selected_symbol", ""))
    symbol_input = st.text_input("Symbol", key="journal_review_symbol")
    lesson_cols_top = responsive_columns(3)
    lesson_cols_bottom = responsive_columns(3)
    with lesson_cols_top[0]:
        _ensure_widget_default("journal_review_went_well", parsed_notes.get("What went well?", ""))
        went_well = st.text_area("What went well?", height=96, key="journal_review_went_well")
    with lesson_cols_top[1]:
        _ensure_widget_default("journal_review_went_wrong", parsed_notes.get("What went wrong?", ""))
        went_wrong = st.text_area("What went wrong?", height=96, key="journal_review_went_wrong")
    with lesson_cols_top[2]:
        _ensure_widget_default("journal_review_repeat", parsed_notes.get("Would I take this trade again?", ""))
        would_repeat = st.text_area("Would I take this trade again?", height=96, key="journal_review_repeat")

    with lesson_cols_bottom[0]:
        _ensure_widget_default("journal_review_rule_followed", parsed_notes.get("Rule followed?", ""))
        rule_followed = st.text_area("Rule followed?", height=96, key="journal_review_rule_followed")
    with lesson_cols_bottom[1]:
        _ensure_widget_default("journal_review_rule_broken", parsed_notes.get("Rule broken?", ""))
        rule_broken = st.text_area("Rule broken?", height=96, key="journal_review_rule_broken")
    with lesson_cols_bottom[2]:
        _ensure_widget_default("journal_review_improvement", parsed_notes.get("Improvement for next time", ""))
        improvement = st.text_area("Improvement for next time", height=96, key="journal_review_improvement")

    tag_options = [
        "Process Review",
        "Perfect Execution",
        "FOMO",
        "Revenge Trade",
        "Early Exit",
        "Late Entry",
        "Thesis Break",
        "Good Process",
        "Bad Process",
        "Mistake",
    ]
    tag_default = str((selected_trade or {}).get("tag") or "Process Review")
    try:
        tag_index = tag_options.index(tag_default)
    except ValueError:
        tag_index = 0
    review_tag = st.selectbox("Review Tag", tag_options, index=tag_index, key="journal_review_tag")

    save_disabled = not bool(symbol_input.strip()) or not bool(supabase_ready)
    save_cols = st.columns(2)
    with save_cols[0]:
        if st.button("Preview Lesson", width="stretch", key="journal_preview_lesson"):
            preview_sections = {
                "What went well?": went_well,
                "What went wrong?": went_wrong,
                "Would I take this trade again?": would_repeat,
                "Rule followed?": rule_followed,
                "Rule broken?": rule_broken,
                "Improvement for next time": improvement,
            }
            st.json({
                "symbol": symbol_input.upper().strip(),
                "tag": review_tag,
                "notes": compose_review_notes(preview_sections),
            })
    with save_cols[1]:
        if st.button("Save Lesson to Archive", width="stretch", key="journal_save_lesson_button", disabled=save_disabled):
            note_sections = {
                "What went well?": went_well,
                "What went wrong?": went_wrong,
                "Would I take this trade again?": would_repeat,
                "Rule followed?": rule_followed,
                "Rule broken?": rule_broken,
                "Improvement for next time": improvement,
            }
            composed_notes = compose_review_notes(note_sections)
            save_report = append_trade_lesson(
                symbol=symbol_input or "N/A",
                setup_grade="C",
                execution_grade="C",
                tag=review_tag,
                notes=composed_notes,
                mistake=review_tag == "Mistake",
            )
            storage = str(save_report.get("storage", "unknown"))
            status = str(save_report.get("status", "")).upper()
            if status == "DUPLICATE":
                st.info("Duplicate lesson detected. Existing archive entry was kept; no new row was created.")
            elif storage == "supabase":
                st.success("Lesson saved to Supabase Trade Lessons Archive.")
            else:
                st.warning(str(save_report.get("reason") or "Journal lesson save failed."))
            st.rerun()


def render_performance_analytics_center(df: pd.DataFrame | None, pnl_col: str = "realized_delta") -> None:
    st.subheader("Research & Analytics")
    st.caption("Deeper analytics live below the review workflow.")

    def format_trader_money(value: Any) -> str:
        number = safe_float(value, 0.0)
        if number < 0:
            return f"-${abs(number):,.2f}"
        return f"${number:,.2f}"

    work = _coerce_timestamp_frame(df)
    empty_analytics_message = (
        "No realized trade history available yet.<br>"
        "Analytics will populate automatically after completed trades."
    )
    if work.empty or pnl_col not in work.columns:
        st.markdown(
            f'<div class="journal-analytics-empty">{empty_analytics_message}</div>',
            unsafe_allow_html=True,
        )
        return

    pnl_series = pd.to_numeric(work[pnl_col], errors="coerce").fillna(0.0) if pnl_col in work.columns else pd.Series(dtype=float)
    if len(work) < 2 or float(pnl_series.abs().sum()) == 0.0:
        st.markdown(
            f'<div class="journal-analytics-empty">{empty_analytics_message}</div>',
            unsafe_allow_html=True,
        )
        return

    if "timestamp" in work.columns and not pnl_series.empty:
        work = work.assign(pnl=pnl_series, month=work["timestamp"].dt.to_period("M").astype(str))
    else:
        work = work.assign(pnl=pnl_series if not pnl_series.empty else 0.0, month="N/A")

    tab_winloss, tab_equity, tab_strategy, tab_mistake, tab_monthly = st.tabs([
        "Win/Loss Analysis",
        "Equity Curve",
        "Strategy Performance",
        "Mistake Tracker",
        "Monthly Review",
    ])

    with tab_winloss:
        winners = work[work["pnl"] > 0]
        losers = work[work["pnl"] < 0]
        summary_cols = responsive_columns(4)
        with summary_cols[0]: journal_metric_card("Winning Trades", len(winners), "Positive realized outcomes", tone="good")
        with summary_cols[1]: journal_metric_card("Losing Trades", len(losers), "Trades that need review", tone="risk")
        with summary_cols[2]: journal_metric_card("Average Gain", format_trader_money(winners["pnl"].mean()) if len(winners) else "$0.00", "Average winner", tone="good")
        with summary_cols[3]: journal_metric_card("Average Loss", format_trader_money(losers["pnl"].mean()) if len(losers) else "$0.00", "Average loser", tone="risk")
        breakdown = (
            work.groupby(work["pnl"].apply(lambda value: "🟢 Wins" if value > 0 else "🔴 Losses" if value < 0 else "⚪ Flat"))["pnl"]
            .agg(["count", "sum", "mean"])
            .reset_index()
            .rename(columns={"pnl": "Outcome", "count": "Trades", "sum": "Total P&L", "mean": "Average P&L"})
        )
        if "Total P&L" in breakdown.columns:
            breakdown["Total P&L"] = breakdown["Total P&L"].apply(format_trader_money)
        if "Average P&L" in breakdown.columns:
            breakdown["Average P&L"] = breakdown["Average P&L"].apply(format_trader_money)
        st.dataframe(breakdown, width="stretch", hide_index=True, height=280)

    with tab_equity:
        equity_df = work.copy()
        equity_df = equity_df.sort_values("timestamp") if "timestamp" in equity_df.columns else equity_df
        equity_df["equity_curve"] = equity_df["pnl"].cumsum()
        st.line_chart(equity_df.set_index("timestamp")["equity_curve"] if "timestamp" in equity_df.columns else equity_df["equity_curve"])
        st.dataframe(equity_df[[col for col in ["timestamp", "symbol", "pnl"] if col in equity_df.columns]], width="stretch", hide_index=True, height=320)

    with tab_strategy:
        if "symbol" in work.columns:
            symbol_perf = (
                work.groupby("symbol", as_index=False)
                .agg(trades=("symbol", "count"), realized_pnl=("pnl", "sum"), avg_trade=("pnl", "mean"), best_trade=("pnl", "max"), worst_trade=("pnl", "min"))
                .sort_values("realized_pnl", ascending=False)
            )
            st.dataframe(symbol_perf, width="stretch", hide_index=True, height=360)
        else:
            st.info("No symbol data available for strategy performance.")

    with tab_mistake:
        render_mistake_tracker(work)

    with tab_monthly:
        if "month" in work.columns:
            monthly = work.groupby("month", as_index=False).agg(trades=("month", "count"), realized_pnl=("pnl", "sum"), avg_trade=("pnl", "mean")).sort_values("month", ascending=False)
            st.dataframe(monthly, width="stretch", hide_index=True, height=360)
        else:
            st.info("No monthly grouping data available.")


def render_trade_archive_center(df: pd.DataFrame | None, pnl_col: str = "realized_delta") -> None:
    st.expander("Trade Archive", expanded=False)



# =========================================================
# PAGE
# =========================================================

def run_page():

    if inject_responsive_css is not None:
        inject_responsive_css(max_width=1500)
    if inject_card_css is not None:
        inject_card_css()
    inject_journal_css()
    inject_journal_commander_css()

    gateway, market, oms, portfolio_engine = init_core()

    st.title("📓 Journal")
    st.caption(
        "Journal v2.1 Institutional Edition — commander review report, discipline score, coaching engine, "
        "performance diagnostics, trade ledger, daily review, and process-improvement notes."
    )

    st.markdown(
        """
        <div class="journal-flow">
            <strong>🚀 Workflow:</strong><br>
            OMS Execution → Fills → Portfolio → Position Command Center → Journal → Review → Improve Next Trade
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # WORKFLOW ROUND-TRIP HANDOFF
    # =====================================================

    nav_cols = responsive_columns(5)
    with nav_cols[0]:
        if st.button("OMS", width="stretch", key="journal_nav_oms_v31"):
            navigate_to("OMS Execution")
    with nav_cols[1]:
        if st.button("Position Command", width="stretch", key="journal_nav_position_v31"):
            navigate_to("Position Command Center")
    with nav_cols[2]:
        if st.button("Trade Command", width="stretch", key="journal_nav_trade_v31"):
            navigate_to("Trade Command Center")
    with nav_cols[3]:
        if st.button("Research", width="stretch", key="journal_nav_research_v31"):
            navigate_to("Research Stock")
    with nav_cols[4]:
        if st.button("Database", width="stretch", key="journal_nav_database_v31"):
            navigate_to("Database")

    handoff_note = st.session_state.get("journal_prefill_note") or {}
    pending_reviews = st.session_state.get("pending_trade_review", [])
    pending_symbol = ""

    if isinstance(handoff_note, dict):
        pending_symbol = str(handoff_note.get("symbol") or handoff_note.get("Symbol") or "").upper().strip()

    if not pending_symbol and isinstance(pending_reviews, list) and pending_reviews:
        first_review = pending_reviews[0] if isinstance(pending_reviews[0], dict) else {}
        pending_symbol = str(first_review.get("symbol") or first_review.get("Symbol") or "").upper().strip()

    if pending_symbol:
        with st.container(border=True):
            st.markdown("#### 🔁 Journal Round-Trip Handoff")
            st.caption("A symbol was passed into Journal from Trade Command, OMS, or Position Command. Jump back into the workflow without retyping it.")
            h1, h2, h3, h4 = responsive_columns(4)
            with h1:
                st.metric("Selected Symbol", pending_symbol)
            with h2:
                if st.button("Open Research", width="stretch", key="journal_handoff_research_v31"):
                    publish_symbol_handoff(pending_symbol, "Research Stock")
            with h3:
                if st.button("Open Trade Command", width="stretch", key="journal_handoff_trade_v31"):
                    publish_symbol_handoff(pending_symbol, "Trade Command Center")
            with h4:
                if st.button("Open Position Command", width="stretch", key="journal_handoff_position_v31"):
                    publish_symbol_handoff(pending_symbol, "Position Command Center")

    with st.expander("📘 How to use this page", expanded=False):
        st.markdown(
            """
            1. Start with the Performance Summary to understand your trading quality.
            2. Use the Trade Ledger filters to isolate symbols, actions, sources, and winners/losers.
            3. Review Symbol Performance to find your best and worst tickers.
            4. Check Daily Review to identify good and bad trading days.
            5. Use Manual Trade Review to preview process notes after important trades.
            6. Use Journal Health to confirm the portfolio engine and ledger are available.

            **Important:** Journal reads from the runtime portfolio ledger. It is a review and coaching layer, not an order-entry page.
            """
        )

    if portfolio_engine is None:
        st.error("Portfolio engine unavailable.")
        return

    ledger = []
    positions = {}
    exposure = {}

    if hasattr(portfolio_engine, "ledger_snapshot"):
        try:
            ledger = portfolio_engine.ledger_snapshot()
        except Exception:
            ledger = []

    if hasattr(portfolio_engine, "snapshot"):
        try:
            positions = portfolio_engine.snapshot()
        except Exception:
            positions = {}

    if hasattr(portfolio_engine, "exposure_snapshot"):
        try:
            exposure = portfolio_engine.exposure_snapshot()
        except Exception:
            exposure = {}

    analyzer = PerformanceAnalyzer()

    report = analyzer.analyze(
        ledger=ledger,
        positions_snapshot=positions,
        exposure_snapshot=exposure,
    )

    journal_snapshot = build_journal_commander_snapshot(
        report=report,
        ledger=ledger,
        positions=positions,
    )

    st.divider()
    render_commander_review_report(journal_snapshot)
    render_executive_review_brief(journal_snapshot)

    df = pd.DataFrame(ledger) if ledger else pd.DataFrame()
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    pnl_col = "realized_delta" if (not df.empty and "realized_delta" in df.columns) else "realized_pnl"

    journal_snapshot_dict = journal_snapshot if isinstance(journal_snapshot, dict) else {}
    daily_brief = build_daily_performance_brief(df, report, pnl_col=pnl_col)
    review_queue = build_trade_review_queue(df, pnl_col=pnl_col, limit=8)

    st.divider()
    render_daily_performance_brief(daily_brief)
    render_trade_review_queue(review_queue)

    selected_trade = st.session_state.get("journal_selected_trade_row")
    if selected_trade is None and review_queue:
        selected_key = st.session_state.get("journal_selected_trade_key")
        if selected_key:
            for item in review_queue:
                if item.get("key") == selected_key:
                    selected_trade = item.get("row")
                    break

    render_selected_trade_review(selected_trade, pnl_col=pnl_col)
    render_lessons_learned_center(selected_trade, pnl_col=pnl_col)

    render_trade_lessons_archive(df, pnl_col=pnl_col)

    render_performance_analytics_center(df, pnl_col=pnl_col)

    render_coaching_engine(journal_snapshot, None)

    st.divider()
    st.subheader("Trade Archive")
    st.caption("Historical trades are kept at the bottom and collapsed by default.")
    with st.expander("Trade Archive", expanded=False):
        st.caption("Source-of-truth trade history from the portfolio engine. Use filters to isolate symbols, actions, sources, winners, and losers.")

        if df.empty:
            st.info("No trades available yet.")
        else:
            archive_cols = [col for col in ["timestamp", "symbol", "action", "qty", "fill_price", "realized_delta", "realized_pnl", "source"] if col in df.columns]
            archive_df = df[archive_cols] if archive_cols else df
            st.dataframe(archive_df, width="stretch", hide_index=True, height=min(520, max(220, 38 * (len(archive_df) + 1))))

    st.divider()
    with st.expander("▼ System Diagnostics", expanded=False):
        st.caption(
            "What it means: Confirms that Journal Intelligence can read the portfolio engine, ledger, and runtime recovery state."
        )

        health = {
            "Portfolio Engine": "ONLINE",
            "Ledger Entries": len(ledger),
            "Positions": len(positions),
            "Bootstrap Recovery": st.session_state.get("bootstrap_recovery_status", ""),
            "Runtime/Audit Recovery OK": st.session_state.get("bootstrap_recovered_ok", True),
            "Journal Supabase Loaded": st.session_state.get("journal_supabase_loaded", False),
            "Journal Saved Lessons": st.session_state.get("journal_saved_lessons_count", 0),
            "Journal Supabase Error": st.session_state.get("journal_supabase_load_error", ""),
        }

        st.dataframe(pd.DataFrame(list(health.items()), columns=["Metric", "Value"]), width="stretch", hide_index=True)
