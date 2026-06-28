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

    return True, "", client


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
    r1 = responsive_columns(4)
    r2 = responsive_columns(4)
    with r1[0]: journal_metric_card("Discipline Score", f"{snapshot.get('discipline_score', 0)}/100", snapshot.get("grade", "N/A"), tone=snapshot.get("tone", "warning"))
    with r1[1]: journal_metric_card("Win Rate", f"{snapshot.get('win_rate', 0) * 100:.1f}%", "Winning trades / total", tone=pct_tone(snapshot.get("win_rate", 0)))
    with r1[2]: journal_metric_card("Profit Factor", f"{snapshot.get('profit_factor', 0):.2f}", "Gross wins / gross losses", tone=ratio_tone(snapshot.get("profit_factor", 0)))
    with r1[3]: journal_metric_card("Expectancy", f"${snapshot.get('expectancy', 0):,.2f}", "Average expected trade", tone=pnl_tone(snapshot.get("expectancy", 0)))
    with r2[0]: journal_metric_card("Total Trades", snapshot.get("total_trades", 0), "Ledger entries analyzed", tone="info")
    with r2[1]: journal_metric_card("Winners / Losers", f"{snapshot.get('winners', 0)} / {snapshot.get('losers', 0)}", "Outcome split", tone="good" if snapshot.get('winners', 0) >= snapshot.get('losers', 0) else "warning")
    with r2[2]: journal_metric_card("Total P&L", f"${snapshot.get('total_pnl', 0):,.2f}", "Realized + unrealized", tone=pnl_tone(snapshot.get("total_pnl", 0)))
    with r2[3]: journal_metric_card("Open Positions", snapshot.get("open_positions", 0), "Current book exposure", tone="info")


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

    rows = responsive_columns(3)
    with rows[0]: journal_metric_card("Top Strength", strength, "What is working", tone="good" if snapshot.get("total_trades", 0) else "info")
    with rows[1]: journal_metric_card("Top Weakness", weakness, "What needs attention", tone=tone)
    with rows[2]: journal_metric_card("Focus Next Week", focus, "Next process target", tone="info")


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

    metrics = responsive_columns(4)
    with metrics[0]:
        journal_metric_card("Total Lessons", total_lessons, "Saved lesson archive", tone="info")
    with metrics[1]:
        journal_metric_card("Most Common Error", most_common_error, "Repeated tag / theme", tone="warning" if most_common_error not in ("N/A", "None") else "neutral")
    with metrics[2]:
        journal_metric_card("Last Lesson Added", last_lesson, "Most recent archive entry", tone="info")
    with metrics[3]:
        journal_metric_card("Improvement Trend", improvement_trend, "Coaching signal", tone="warning" if improvement_trend == "Repeated Theme" else "good")

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

    score_left, score_right = responsive_columns([1.0, 1.0], gap="large")
    with score_left:
        render_journal_scorecard(journal_snapshot)
    with score_right:
        render_coaching_engine(journal_snapshot, None)

    # =====================================================
    # PERFORMANCE SUMMARY
    # =====================================================

    st.divider()
    st.subheader("🧠 Performance Summary")
    st.caption(
        "What it means: High-level trading performance, realized and unrealized P&L, "
        "win rate, expectancy, and open position count."
    )

    row_1 = responsive_columns(4)

    with row_1[0]:
        journal_metric_card("Trades", report.total_trades, "Total completed ledger entries.", tone="info")

    with row_1[1]:
        journal_metric_card(
            "Win Rate",
            f"{report.win_rate * 100:.1f}%",
            "Percentage of winning trades.",
            tone=pct_tone(report.win_rate),
        )

    with row_1[2]:
        journal_metric_card(
            "Profit Factor",
            f"{report.profit_factor:.2f}",
            "Gross wins divided by gross losses.",
            tone=ratio_tone(report.profit_factor),
        )

    with row_1[3]:
        journal_metric_card(
            "Expectancy",
            f"${report.expectancy:,.2f}",
            "Average expected P&L per trade.",
            tone=pnl_tone(report.expectancy),
        )

    row_2 = responsive_columns(4)

    with row_2[0]:
        journal_metric_card("Winners", report.winners, "Winning trade count.", tone="good")

    with row_2[1]:
        journal_metric_card("Losers", report.losers, "Losing trade count.", tone="risk" if report.losers else "good")

    with row_2[2]:
        journal_metric_card("Best Trade", f"${report.best_trade:,.2f}", "Largest realized winner.", tone=pnl_tone(report.best_trade))

    with row_2[3]:
        journal_metric_card("Worst Trade", f"${report.worst_trade:,.2f}", "Largest realized loser.", tone=pnl_tone(report.worst_trade))

    row_3 = responsive_columns(4)

    with row_3[0]:
        journal_metric_card("Realized P&L", f"${report.realized_pnl:,.2f}", "Closed-trade profit and loss.", tone=pnl_tone(report.realized_pnl))

    with row_3[1]:
        journal_metric_card("Unrealized P&L", f"${report.unrealized_pnl:,.2f}", "Open-position profit and loss.", tone=pnl_tone(report.unrealized_pnl))

    with row_3[2]:
        journal_metric_card("Total P&L", f"${report.total_pnl:,.2f}", "Realized plus unrealized P&L.", tone=pnl_tone(report.total_pnl))

    with row_3[3]:
        journal_metric_card("Open Positions", len(positions), "Current portfolio positions.", tone="info")

    journal_tip(
        "Use this section first. It tells you whether the trading process is improving, flat, or deteriorating."
    )

    # =====================================================
    # TRADE LEDGER
    # =====================================================

    st.divider()
    st.subheader("📋 Trade Ledger")
    st.caption(
        "What it means: Source-of-truth trade history from the portfolio engine. "
        "Use filters to isolate symbols, actions, sources, winners, and losers."
    )

    if not ledger:
        st.info("No trades available yet.")

        st.divider()
        st.subheader("🩺 Journal Health")
        health = {
            "Portfolio Engine": "ONLINE",
            "Ledger Entries": 0,
            "Filtered Entries": 0,
            "Positions": len(positions),
            "Bootstrap Recovery": st.session_state.get("bootstrap_recovery_status", ""),
            "Runtime/Audit Recovery OK": st.session_state.get("bootstrap_recovered_ok", True),
            "Journal Supabase Loaded": st.session_state.get("journal_supabase_loaded", False),
            "Journal Saved Lessons": st.session_state.get("journal_saved_lessons_count", 0),
            "Journal Supabase Error": st.session_state.get("journal_supabase_load_error", ""),
        }
        st.dataframe(pd.DataFrame(list(health.items()), columns=["Metric", "Value"]), width="stretch", hide_index=True)
        return

    df = pd.DataFrame(ledger)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
        )

    # =====================================================
    # FILTERS
    # =====================================================

    with st.container(border=True):
        st.markdown("#### 🔎 Ledger Filters")
        filter_cols = responsive_columns(4)

        with filter_cols[0]:
            symbols = sorted(df["symbol"].dropna().unique()) if "symbol" in df.columns else []
            selected_symbols = st.multiselect("Symbols", symbols)

        with filter_cols[1]:
            actions = sorted(df["action"].dropna().unique()) if "action" in df.columns else []
            selected_actions = st.multiselect("Actions", actions)

        with filter_cols[2]:
            sources = sorted(df["source"].dropna().unique()) if "source" in df.columns else []
            selected_sources = st.multiselect("Sources", sources)

        with filter_cols[3]:
            pnl_filter = st.selectbox(
                "P&L Filter",
                ["All", "Winners", "Losers", "Breakeven"],
            )

    filtered = df.copy()

    if selected_symbols and "symbol" in filtered.columns:
        filtered = filtered[filtered["symbol"].isin(selected_symbols)]

    if selected_actions and "action" in filtered.columns:
        filtered = filtered[filtered["action"].isin(selected_actions)]

    if selected_sources and "source" in filtered.columns:
        filtered = filtered[filtered["source"].isin(selected_sources)]

    pnl_col = "realized_delta" if "realized_delta" in filtered.columns else "realized_pnl"

    if pnl_col in filtered.columns:
        filtered[pnl_col] = pd.to_numeric(filtered[pnl_col], errors="coerce").fillna(0.0)

        if pnl_filter == "Winners":
            filtered = filtered[filtered[pnl_col] > 0]
        elif pnl_filter == "Losers":
            filtered = filtered[filtered[pnl_col] < 0]
        elif pnl_filter == "Breakeven":
            filtered = filtered[filtered[pnl_col] == 0]

    preferred_cols = [
        "timestamp",
        "symbol",
        "action",
        "qty",
        "fill_price",
        "old_side",
        "old_qty",
        "new_side",
        "new_qty",
        "realized_delta",
        "realized_pnl",
        "source",
        "fill_id",
        "order_id",
    ]

    display_cols = [
        col for col in preferred_cols
        if col in filtered.columns
    ]

    ledger_view = filtered[display_cols] if display_cols else filtered

    if selected_symbols:
        active_symbol = str(selected_symbols[0]).upper().strip()
        with st.container(border=True):
            st.caption(f"Round-trip selected ledger symbol: {active_symbol}")
            r1, r2, r3 = responsive_columns(3)
            with r1:
                if st.button("Analyze Selected", width="stretch", key="journal_selected_research_v31"):
                    publish_symbol_handoff(active_symbol, "Research Stock")
            with r2:
                if st.button("Plan Selected", width="stretch", key="journal_selected_trade_v31"):
                    publish_symbol_handoff(active_symbol, "Trade Command Center")
            with r3:
                if st.button("Manage Selected", width="stretch", key="journal_selected_position_v31"):
                    publish_symbol_handoff(active_symbol, "Position Command Center")

    st.dataframe(
        ledger_view,
        width="stretch",
        hide_index=True,
        height=min(520, max(220, 38 * (len(ledger_view) + 1))),
    )

    st.divider()
    render_mistake_tracker(df)

    # =====================================================
    # PERFORMANCE DETAIL AREA
    # =====================================================

    st.divider()
    detail_left, detail_right = responsive_columns(2)

    with detail_left:
        st.subheader("🏆 Symbol Performance")
        st.caption(
            "What it means: Identifies which symbols are contributing most to realized performance."
        )

        if "symbol" in df.columns and pnl_col in df.columns:

            symbol_perf = (
                df.assign(
                    pnl=pd.to_numeric(df[pnl_col], errors="coerce").fillna(0.0)
                )
                .groupby("symbol", as_index=False)
                .agg(
                    trades=("symbol", "count"),
                    realized_pnl=("pnl", "sum"),
                    avg_trade=("pnl", "mean"),
                    best_trade=("pnl", "max"),
                    worst_trade=("pnl", "min"),
                )
                .sort_values("realized_pnl", ascending=False)
            )

            st.dataframe(
                symbol_perf,
                width="stretch",
                hide_index=True,
                height=min(420, max(180, 38 * (len(symbol_perf) + 1))),
            )

        else:
            st.info("Not enough data for symbol performance.")

    with detail_right:
        st.subheader("📊 Trade Breakdown")
        st.caption(
            "What it means: Summarizes trade activity by action and resulting position side."
        )

        breakdown_top, breakdown_bottom = responsive_columns(2)

        with breakdown_top:
            if "action" in df.columns:
                action_counts = (
                    df["action"]
                    .value_counts()
                    .reset_index()
                )
                action_counts.columns = ["Action", "Count"]
                st.dataframe(action_counts, width="stretch", hide_index=True)
            else:
                st.info("No action data.")

        with breakdown_bottom:
            if "new_side" in df.columns:
                side_counts = (
                    df["new_side"]
                    .value_counts()
                    .reset_index()
                )
                side_counts.columns = ["Post-Trade Side", "Count"]
                st.dataframe(side_counts, width="stretch", hide_index=True)
            else:
                st.info("No side data.")

    # =====================================================
    # DAILY PERFORMANCE
    # =====================================================

    st.divider()
    st.subheader("📅 Daily Review")
    st.caption(
        "What it means: Groups trade results by date to help identify strong and weak trading sessions."
    )

    if "timestamp" in df.columns and pnl_col in df.columns:

        daily_df = df.copy()

        daily_df["date"] = daily_df["timestamp"].dt.date
        daily_df["pnl"] = pd.to_numeric(
            daily_df[pnl_col],
            errors="coerce",
        ).fillna(0.0)

        daily_perf = (
            daily_df.groupby("date", as_index=False)
            .agg(
                trades=("symbol", "count"),
                realized_pnl=("pnl", "sum"),
                avg_trade=("pnl", "mean"),
            )
            .sort_values("date", ascending=False)
        )

        render_daily_command_center(daily_perf)

        st.dataframe(
            daily_perf,
            width="stretch",
            hide_index=True,
            height=min(420, max(180, 38 * (len(daily_perf) + 1))),
        )

    else:
        st.info("No timestamp/P&L data available for daily review.")

    # =====================================================
    # MANUAL REVIEW NOTE
    # =====================================================

    st.divider()
    st.subheader("📝 Manual Trade Review")
    st.caption(
        "What it means: Build a trade-review note for process improvement and save it to your lessons archive."
    )

    current_user_id = _current_saas_user_id()
    supabase_ready, supabase_reason, _ = _journal_supabase_persistence_available(current_user_id)
    st.session_state["journal_supabase_available"] = supabase_ready
    if not supabase_ready:
        st.warning(supabase_reason)

    with st.container(border=True):
        n1, n2, n3 = responsive_columns(3)

        with n1:
            selected_symbol = st.text_input("Symbol").upper().strip()
            setup_grade = st.selectbox("Setup Grade", ["A", "B", "C", "D", "F"])

        with n2:
            execution_grade = st.selectbox("Execution Grade", ["A", "B", "C", "D", "F"])
            mistake = st.checkbox("Mistake?")

        with n3:
            tag = st.selectbox(
                "Tag",
                [
                    "None",
                    "Perfect Execution",
                    "FOMO",
                    "Revenge Trade",
                    "Early Exit",
                    "Late Entry",
                    "Thesis Break",
                    "Good Process",
                    "Bad Process",
                ],
            )

        notes = st.text_area("Notes")

        action_col_1, action_col_2 = st.columns(2)

        with action_col_1:
            if st.button("Preview Journal Note", use_container_width=True, key="journal_preview_note_button"):
                note_payload = {
                    "symbol": selected_symbol,
                    "setup_grade": setup_grade,
                    "execution_grade": execution_grade,
                    "mistake": mistake,
                    "tag": tag,
                    "notes": notes,
                }
                st.success("Journal note preview created.")
                st.json(note_payload)

        with action_col_2:
            save_disabled = (
                not bool(str(current_user_id or "").strip())
                or not bool(str(selected_symbol or "").strip())
                or not bool(str(notes or "").strip())
                or not bool(supabase_ready)
            )
            if st.button(
                "Save Lesson to Archive",
                use_container_width=True,
                key="journal_save_lesson_button",
                disabled=save_disabled,
            ):
                save_report = append_trade_lesson(
                    symbol=selected_symbol or "N/A",
                    setup_grade=setup_grade,
                    execution_grade=execution_grade,
                    tag=tag,
                    notes=notes,
                    mistake=mistake,
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

    render_trade_lessons_archive(df, pnl_col)

    # =====================================================
    # HEALTH
    # =====================================================

    st.divider()
    st.subheader("🩺 Journal Health")
    st.caption(
        "What it means: Confirms that Journal Intelligence can read the portfolio engine, ledger, and runtime recovery state."
    )

    health = {
        "Portfolio Engine": "ONLINE",
        "Ledger Entries": len(ledger),
        "Filtered Entries": len(filtered),
        "Positions": len(positions),
        "Bootstrap Recovery": st.session_state.get("bootstrap_recovery_status", ""),
        "Runtime/Audit Recovery OK": st.session_state.get(
            "bootstrap_recovered_ok",
            True,
        ),
        "Journal Supabase Loaded": st.session_state.get("journal_supabase_loaded", False),
        "Journal Saved Lessons": st.session_state.get("journal_saved_lessons_count", 0),
        "Journal Supabase Error": st.session_state.get("journal_supabase_load_error", ""),
    }

    st.dataframe(
        pd.DataFrame(
            list(health.items()),
            columns=["Metric", "Value"],
        ),
        width="stretch",
        hide_index=True,
    )
