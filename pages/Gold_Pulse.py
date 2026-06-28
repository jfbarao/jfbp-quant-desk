# =========================================================
# 🥇 GOLD PULSE PAGE — v1.1 STABLE
# JFBP Quant Desk
# Gold Regime + USD Pressure + Rates Proxy + Risk Hedge + Miner Breadth Dashboard
# Built from Crypto Pulse / Forex Pulse / Market Pulse visual standard
# v1.1 STABLE: Final freeze banner added after visual and logic validation
# =========================================================

from __future__ import annotations

import html
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st


# =========================================================
# OPTIONAL DATA PROVIDER
# =========================================================

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None


# =========================================================
# UNIVERSE
# =========================================================

GOLD_UNIVERSE = [
    {"Symbol": "GC=F", "Name": "Gold Futures", "Group": "Gold"},
    {"Symbol": "GLD", "Name": "SPDR Gold Shares", "Group": "Gold ETF"},
    {"Symbol": "IAU", "Name": "iShares Gold Trust", "Group": "Gold ETF"},
    {"Symbol": "GDX", "Name": "VanEck Gold Miners", "Group": "Miners"},
    {"Symbol": "GDXJ", "Name": "VanEck Junior Gold Miners", "Group": "Junior Miners"},
    {"Symbol": "NEM", "Name": "Newmont", "Group": "Senior Miner"},
    {"Symbol": "GOLD", "Name": "Barrick Gold", "Group": "Senior Miner"},
    {"Symbol": "AEM", "Name": "Agnico Eagle", "Group": "Senior Miner"},
    {"Symbol": "FNV", "Name": "Franco-Nevada", "Group": "Royalty"},
    {"Symbol": "WPM", "Name": "Wheaton Precious Metals", "Group": "Royalty"},
    {"Symbol": "SLV", "Name": "iShares Silver Trust", "Group": "Silver"},
    {"Symbol": "SIL", "Name": "Global X Silver Miners", "Group": "Silver Miners"},
    {"Symbol": "UUP", "Name": "US Dollar Bullish Fund", "Group": "USD Proxy"},
    {"Symbol": "TLT", "Name": "20+ Year Treasury Bond ETF", "Group": "Rates Proxy"},
    {"Symbol": "TIP", "Name": "TIPS Bond ETF", "Group": "Inflation Proxy"},
]

GOLD_CORE_SYMBOLS = ["GC=F", "GLD", "IAU"]
MINER_SYMBOLS = ["GDX", "GDXJ", "NEM", "GOLD", "AEM", "FNV", "WPM", "SIL"]
SILVER_SYMBOLS = ["SLV", "SIL"]
MACRO_SYMBOLS = ["UUP", "TLT", "TIP"]


# =========================================================
# RESPONSIVE UI HELPERS
# =========================================================

def inject_gold_pulse_css() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.4rem;
                padding-bottom: 2.5rem;
                max-width: 1500px;
            }

            div[data-testid="stDataFrame"] {
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
            }

            div[data-testid="column"] {
                min-width: 0 !important;
            }

            div[data-testid="stAlert"] {
                overflow-wrap: anywhere;
                word-break: normal;
            }

            .gold-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
                gap: 0.65rem;
                margin: 0.35rem 0 0.75rem 0;
                width: 100%;
            }

            .gold-briefing-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.65rem;
                margin: 0.35rem 0 0.75rem 0;
                width: 100%;
            }

            .gold-briefing-card {
                display: flex;
                flex-direction: column;
                min-height: 126px;
                height: 100%;
            }

            .gold-briefing-card.featured {
                min-height: 144px;
            }

            .gold-card {
                border: 1px solid;
                border-radius: 14px;
                padding: 0.72rem 0.82rem;
                min-width: 0;
                width: 100%;
                box-sizing: border-box;
                overflow: hidden;
            }

            .gold-label {
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #64748b;
                font-weight: 800;
                margin-bottom: 0.28rem;
                line-height: 1.25;
            }

            .gold-value {
                font-size: clamp(1.05rem, 2.2vw, 1.45rem);
                line-height: 1.15;
                font-weight: 850;
                white-space: normal;
                word-break: normal;
            }

            .gold-detail {
                font-size: 0.78rem;
                color: #64748b;
                margin-top: 0.35rem;
                line-height: 1.35;
            }

            .gold-list-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
                gap: 0.75rem;
                margin: 0.45rem 0 0.85rem 0;
            }

            .gold-list-card {
                border: 1px solid;
                border-radius: 16px;
                padding: 0.90rem 1.0rem;
                min-width: 0;
                overflow: hidden;
            }

            .gold-list-title {
                font-size: 1.02rem;
                font-weight: 850;
                color: #1f2937;
                margin-bottom: 0.70rem;
                line-height: 1.2;
            }

            .gold-list-row {
                display: grid;
                grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.35fr);
                gap: 0.65rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.28);
                padding: 0.42rem 0;
            }

            .gold-list-row:last-child {
                border-bottom: none;
            }

            .gold-list-label {
                color: #64748b;
                font-weight: 780;
                line-height: 1.28;
            }

            .gold-list-value {
                color: #1f2937;
                font-weight: 900;
                line-height: 1.28;
            }

            .gold-banner {
                border: 1px solid;
                border-radius: 16px;
                padding: 0.72rem 0.85rem;
                margin: 0.24rem 0 0.46rem 0;
                box-sizing: border-box;
            }

            .gold-banner-title {
                font-size: 0.78rem;
                font-weight: 850;
                letter-spacing: 0.045em;
                text-transform: uppercase;
                margin-bottom: 0.2rem;
            }

            .gold-banner-body {
                font-size: 0.95rem;
                line-height: 1.38;
            }

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

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem;
                    padding-right: 0.9rem;
                }

                .gold-grid,
                .gold-list-grid {
                    grid-template-columns: 1fr;
                }

                .gold-list-row {
                    grid-template-columns: 1fr;
                    gap: 0.16rem;
                }

                h1 { font-size: 1.65rem !important; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def help_text(text: str) -> None:
    st.caption(f"💡 {text}")


def tone_palette(tone: str) -> Tuple[str, str, str]:
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
        "gold": ("#fffbeb", "#fde68a", "#92400e"),
    }
    return palette.get(tone, palette["neutral"])


def metric_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="gold-grid">']

    for card in cards:
        background, border, value_color = tone_palette(str(card.get("tone", "neutral")))
        label = html.escape(str(card.get("label", "")))
        value = html.escape(str(card.get("value", "")))
        detail = html.escape(str(card.get("detail", "")))
        detail_html = f'<div class="gold-detail">{detail}</div>' if detail else ""
        pieces.append(
            f'<div class="gold-card" style="background:{background};border-color:{border};">'
            f'<div class="gold-label">{label}</div>'
            f'<div class="gold-value" style="color:{value_color};">{value}</div>'
            f'{detail_html}'
            f'</div>'
        )

    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def briefing_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="gold-briefing-grid">']

    for card in cards:
        background, border, value_color = tone_palette(str(card.get("tone", "neutral")))
        featured = bool(card.get("featured", False))
        card_class = "gold-card gold-briefing-card featured" if featured else "gold-card gold-briefing-card"
        label = html.escape(str(card.get("label", "")))
        value = html.escape(str(card.get("value", "")))
        detail = html.escape(str(card.get("detail", "")))
        detail_html = f'<div class="gold-detail">{detail}</div>' if detail else ""
        pieces.append(
            f'<div class="{card_class}" style="background:{background};border-color:{border};">'
            f'<div class="gold-label">{label}</div>'
            f'<div class="gold-value" style="color:{value_color};">{value}</div>'
            f'{detail_html}'
            f'</div>'
        )

    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def section_heading(title: str, subtitle: str | None = None) -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def institutional_banner(title: str, body: str, tone: str = "info", body_weight: int = 720) -> None:
    background, border, value_color = tone_palette(tone)
    st.markdown(
        f"""
        <div class="gold-banner" style="background:{background};border-color:{border};">
            <div class="gold-banner-title" style="color:{value_color};">{html.escape(title)}</div>
            <div class="gold-banner-body" style="color:{value_color};font-weight:{body_weight};">{html.escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def table_height(row_count: int, max_height: int = 320) -> int:
    return min(max_height, max(132, 56 + row_count * 32))


def list_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="gold-list-grid">']

    for card in cards:
        background, border, _ = tone_palette(str(card.get("tone", "neutral")))
        title = html.escape(str(card.get("title", "")))
        rows_html = ""

        for label, value in card.get("rows", []):
            rows_html += (
                '<div class="gold-list-row">'
                f'<div class="gold-list-label">{html.escape(str(label))}</div>'
                f'<div class="gold-list-value">{html.escape(str(value))}</div>'
                '</div>'
            )

        pieces.append(
            f'<div class="gold-list-card" style="background:{background};border-color:{border};">'
            f'<div class="gold-list-title">{title}</div>'
            f'{rows_html}'
            f'</div>'
        )

    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


# =========================================================
# DATA + CALCULATIONS
# =========================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace("%", "").replace("$", "").replace(",", "").strip()
            if not value:
                return default
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default


def format_pct(value: Any) -> str:
    try:
        value = float(value)
    except Exception:
        return "N/A"
    return f"{value:+.2f}%"


def style_pct(value: Any) -> str:
    value = safe_float(value, 0.0)
    if value > 0:
        return "color: green; font-weight: bold;"
    if value < 0:
        return "color: red; font-weight: bold;"
    return ""


@st.cache_data(ttl=120, show_spinner=False)
def load_gold_prices(symbols: Tuple[str, ...], period: str = "7d", interval: str = "1h") -> pd.DataFrame:
    if yf is None:
        return pd.DataFrame()

    try:
        raw = yf.download(
            tickers=list(symbols),
            period=period,
            interval=interval,
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception:
        return pd.DataFrame()

    rows = []
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for asset in GOLD_UNIVERSE:
        symbol = asset["Symbol"]
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                close = raw[(symbol, "Close")].dropna()
            else:
                close = raw["Close"].dropna()
        except Exception:
            close = pd.Series(dtype=float)

        if close.empty or len(close) < 2:
            rows.append({
                "Symbol": symbol,
                "Name": asset["Name"],
                "Group": asset["Group"],
                "Price": None,
                "1H %": None,
                "24H %": None,
                "7D %": None,
                "Timestamp": now_text,
            })
            continue

        last = float(close.iloc[-1])
        one_hour_base = float(close.iloc[-2]) if len(close) >= 2 else last
        day_base = float(close.iloc[-25]) if len(close) >= 25 else float(close.iloc[0])
        week_base = float(close.iloc[0])

        one_hour = ((last / one_hour_base) - 1.0) * 100 if one_hour_base else 0.0
        day = ((last / day_base) - 1.0) * 100 if day_base else 0.0
        week = ((last / week_base) - 1.0) * 100 if week_base else 0.0

        rows.append({
            "Symbol": symbol,
            "Name": asset["Name"],
            "Group": asset["Group"],
            "Price": round(last, 4),
            "1H %": round(one_hour, 3),
            "24H %": round(day, 3),
            "7D %": round(week, 3),
            "Timestamp": now_text,
        })

    return pd.DataFrame(rows)


def get_row(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    if df is None or df.empty:
        return {}
    row = df[df["Symbol"] == symbol]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


def get_move(df: pd.DataFrame, symbol: str, col: str = "24H %") -> float | None:
    row = get_row(df, symbol)
    if not row:
        return None
    value = row.get(col)
    if pd.isna(value):
        return None
    return safe_float(value, 0.0)


def calculate_gold_breadth(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty or "24H %" not in df.columns:
        return {
            "score": 50.0,
            "state": "Unknown",
            "advancing": 0,
            "declining": 0,
            "total": 0,
            "average_move": 0.0,
            "miner_advance_pct": 0.0,
        }

    work = df[~df["Symbol"].isin(MACRO_SYMBOLS)].copy()
    work["24H %"] = pd.to_numeric(work["24H %"], errors="coerce")
    valid = work.dropna(subset=["24H %"])

    if valid.empty:
        return {
            "score": 50.0,
            "state": "Unknown",
            "advancing": 0,
            "declining": 0,
            "total": 0,
            "average_move": 0.0,
            "miner_advance_pct": 0.0,
        }

    total = len(valid)
    advancing = int((valid["24H %"] > 0).sum())
    declining = int((valid["24H %"] < 0).sum())
    average_move = float(valid["24H %"].mean())
    advance_pct = advancing / total * 100 if total else 0.0

    miner_valid = valid[valid["Symbol"].isin(MINER_SYMBOLS)]
    miner_advance_pct = 0.0
    if not miner_valid.empty:
        miner_advance_pct = float((miner_valid["24H %"] > 0).sum() / len(miner_valid) * 100)

    score = round((advance_pct * 0.55) + (miner_advance_pct * 0.25) + (max(0.0, average_move + 2.0) / 4.0 * 20.0), 1)
    score = max(0.0, min(100.0, score))

    if score >= 70:
        state = "Broad Precious Metals Bid"
    elif score >= 55:
        state = "Constructive Gold Tape"
    elif score >= 40:
        state = "Mixed / Selective"
    elif score >= 25:
        state = "Weak Gold Breadth"
    else:
        state = "Precious Metals Damage"

    return {
        "score": score,
        "state": state,
        "advancing": advancing,
        "declining": declining,
        "total": total,
        "average_move": average_move,
        "miner_advance_pct": miner_advance_pct,
    }


def calculate_gold_macro_pressure(df: pd.DataFrame) -> Dict[str, Any]:
    """Positive score supports gold; negative pressure hurts gold."""

    gold = get_move(df, "GC=F") or get_move(df, "GLD") or 0.0
    dollar = get_move(df, "UUP") or 0.0
    tlt = get_move(df, "TLT") or 0.0
    tip = get_move(df, "TIP") or 0.0
    miners = get_move(df, "GDX") or 0.0

    # UUP up is usually gold pressure. TLT/TIP up may support gold through rates/inflation proxy.
    support_score = 50.0
    support_score += gold * 14.0
    support_score -= dollar * 18.0
    support_score += tlt * 8.0
    support_score += tip * 10.0
    support_score += miners * 5.0
    support_score = max(0.0, min(100.0, round(support_score, 1)))

    if support_score >= 65:
        state = "GOLD MACRO SUPPORT"
        tone = "good"
        note = "Dollar/rates proxy is supportive enough for qualified gold setups."
    elif support_score <= 35:
        state = "GOLD MACRO PRESSURE"
        tone = "risk"
        note = "Dollar/rates proxy is pressuring gold. Reduce aggression."
    else:
        state = "MACRO MIXED"
        tone = "warning"
        note = "Macro backdrop is mixed. Let gold price and miners confirm."

    return {
        "score": support_score,
        "state": state,
        "tone": tone,
        "note": note,
        "gold_24h": gold,
        "uup_24h": dollar,
        "tlt_24h": tlt,
        "tip_24h": tip,
        "gdx_24h": miners,
    }


def calculate_gold_stress(df: pd.DataFrame, breadth: Dict[str, Any], macro: Dict[str, Any]) -> Tuple[int, str]:
    gold = safe_float(macro.get("gold_24h"), 0.0)
    miners = safe_float(macro.get("gdx_24h"), 0.0)
    dollar = safe_float(macro.get("uup_24h"), 0.0)
    breadth_score = safe_float(breadth.get("score"), 50.0)

    score = 0.0

    if gold < 0:
        score += min(abs(gold) * 14.0, 28.0)
    if miners < 0:
        score += min(abs(miners) * 8.0, 22.0)
    if dollar > 0:
        score += min(abs(dollar) * 14.0, 20.0)

    if breadth_score < 25:
        score += 22
    elif breadth_score < 40:
        score += 14
    elif breadth_score < 55:
        score += 7

    macro_score = safe_float(macro.get("score"), 50.0)
    if macro_score < 35:
        score += 15
    elif macro_score < 45:
        score += 7

    score = int(max(0, min(100, round(score))))

    if score >= 80:
        label = "Severe Gold Stress"
    elif score >= 60:
        label = "High Gold Stress"
    elif score >= 40:
        label = "Moderate Gold Stress"
    elif score >= 20:
        label = "Low Gold Stress"
    else:
        label = "Calm Gold Tape"

    return score, label


def regime_tone(regime: str) -> str:
    key = str(regime or "").upper().strip()
    if key in ("RISK-OFF GOLD PRESSURE", "DEFENSIVE", "GOLD BREAKDOWN"):
        return "risk"
    if key in ("SELECTIVE", "CAUTIOUS", "MACRO MIXED"):
        return "warning"
    if key in ("GOLD RISK-ON", "GOLD BREAKOUT", "MINERS CONFIRMING"):
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


def stress_tone(score: int) -> str:
    if score >= 60:
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


def build_gold_regime(df: pd.DataFrame, breadth: Dict[str, Any], stress_score: int, macro: Dict[str, Any]) -> Dict[str, Any]:
    gold = safe_float(macro.get("gold_24h"), 0.0)
    gld = get_move(df, "GLD") or gold
    miners = safe_float(macro.get("gdx_24h"), 0.0)
    silver = get_move(df, "SLV") or 0.0
    dollar = safe_float(macro.get("uup_24h"), 0.0)
    breadth_score = safe_float(breadth.get("score"), 50.0)
    macro_score = safe_float(macro.get("score"), 50.0)

    miner_vs_gold = miners - gold
    silver_vs_gold = silver - gold

    if stress_score >= 70 or breadth_score < 30:
        regime = "GOLD BREAKDOWN"
        playbook = "Protect capital. Avoid new gold/miner exposure until breadth improves."
        execution_multiplier = 0.50
        trade_allowed = False
    elif gold > 0 and miners > gold and breadth_score >= 60 and macro_score >= 50:
        regime = "MINERS CONFIRMING"
        playbook = "Gold is bid and miners are confirming. Favor liquid leaders and pullbacks."
        execution_multiplier = 1.00
        trade_allowed = True
    elif gold > 0 and macro_score >= 55 and breadth_score >= 50:
        regime = "GOLD BREAKOUT"
        playbook = "Gold price is constructive. Favor gold ETFs/futures first; miners need confirmation."
        execution_multiplier = 0.90
        trade_allowed = True
    elif breadth_score >= 40:
        regime = "SELECTIVE"
        playbook = "Gold tape is mixed. Trade only the strongest gold or miner setups."
        execution_multiplier = 0.65
        trade_allowed = True
    else:
        regime = "CAUTIOUS"
        playbook = "Gold breadth is weak. Reduce size and avoid lagging miners."
        execution_multiplier = 0.50
        trade_allowed = True

    return {
        "regime": regime,
        "playbook": playbook,
        "execution_multiplier": execution_multiplier,
        "trade_allowed": trade_allowed,
        "gold_24h": gold,
        "gld_24h": gld,
        "gdx_24h": miners,
        "silver_24h": silver,
        "uup_24h": dollar,
        "miner_vs_gold": miner_vs_gold,
        "silver_vs_gold": silver_vs_gold,
    }


def calculate_gold_market_cycle(regime: Dict[str, Any], breadth: Dict[str, Any], stress_score: int, macro: Dict[str, Any]) -> Dict[str, Any]:
    gold = safe_float(regime.get("gold_24h"), 0.0)
    miners = safe_float(regime.get("gdx_24h"), 0.0)
    breadth_score = safe_float(breadth.get("score"), 50.0)
    macro_score = safe_float(macro.get("score"), 50.0)

    if stress_score >= 70 or breadth_score < 30:
        cycle = "CONTRACTION"
        tone = "risk"
        note = "Gold/miner risk is deteriorating. Protect capital and avoid weak miners."
        icon = "🔴"
    elif gold > 0 and miners > gold and breadth_score >= 55:
        cycle = "MINER EXPANSION"
        tone = "good"
        note = "Miners are confirming gold strength. Favor liquid relative-strength leaders."
        icon = "🟢"
    elif gold > 0 and macro_score >= 55:
        cycle = "GOLD EXPANSION"
        tone = "good"
        note = "Gold is constructive. Let miners confirm before increasing aggression."
        icon = "🟢"
    elif breadth_score >= 40 and stress_score < 60:
        cycle = "CONSOLIDATION"
        tone = "warning"
        note = "Gold is tradable but selective. Wait for price and miner confirmation."
        icon = "🟡"
    else:
        cycle = "DISTRIBUTION WATCH"
        tone = "warning"
        note = "Momentum is weakening. Reduce size if gold or miners deteriorate."
        icon = "🟠"

    return {"cycle": cycle, "tone": tone, "note": note, "icon": icon}


def build_gold_opportunity_scanner(df: pd.DataFrame, regime: Dict[str, Any], breadth: Dict[str, Any], macro: Dict[str, Any]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    work = df[~df["Symbol"].isin(MACRO_SYMBOLS)].copy()
    for col in ["1H %", "24H %", "7D %"]:
        work[col] = pd.to_numeric(work.get(col, pd.Series(dtype=float)), errors="coerce").fillna(0.0)

    gold_24h = safe_float(regime.get("gold_24h"), 0.0)
    breadth_score = safe_float(breadth.get("score"), 50.0)
    macro_score = safe_float(macro.get("score"), 50.0)

    rows = []
    for _, row in work.iterrows():
        one_h = safe_float(row.get("1H %"), 0.0)
        day = safe_float(row.get("24H %"), 0.0)
        week = safe_float(row.get("7D %"), 0.0)
        rs_gold = day - gold_24h

        momentum_score = max(0.0, min(40.0, (day + 2.0) / 4.0 * 40.0))
        trend_score = max(0.0, min(25.0, (week + 5.0) / 10.0 * 25.0))
        relative_score = max(0.0, min(20.0, (rs_gold + 3.0) / 6.0 * 20.0))
        breadth_bonus = max(0.0, min(10.0, breadth_score / 10.0))
        macro_bonus = max(0.0, min(5.0, macro_score / 20.0))
        opportunity_score = round(momentum_score + trend_score + relative_score + breadth_bonus + macro_bonus, 1)

        if opportunity_score >= 80 and day > 0:
            recommendation = "STRONG WATCH"
        elif opportunity_score >= 65 and day > 0:
            recommendation = "WATCH"
        elif opportunity_score >= 50:
            recommendation = "NEUTRAL"
        else:
            recommendation = "AVOID"

        bias = "LONG" if day > 0 else "SHORT" if day < 0 else "NEUTRAL"

        rows.append({
            "Rank": 0,
            "Name": row.get("Name"),
            "Symbol": row.get("Symbol"),
            "Group": row.get("Group"),
            "Price": row.get("Price"),
            "1H %": round(one_h, 3),
            "24H %": round(day, 3),
            "7D %": round(week, 3),
            "RS vs Gold": round(rs_gold, 3),
            "Directional Bias": bias,
            "Opportunity Score": opportunity_score,
            "Recommendation": recommendation,
        })

    result = (
        pd.DataFrame(rows)
        .sort_values("Opportunity Score", ascending=False, na_position="last")
        .reset_index(drop=True)
    )
    result["Rank"] = result.index + 1
    return result


def build_ai_gold_brief(
    df: pd.DataFrame,
    regime: Dict[str, Any],
    breadth: Dict[str, Any],
    stress_score: int,
    stress_label: str,
    macro: Dict[str, Any],
    market_cycle: Dict[str, Any],
) -> Dict[str, str]:
    regime_name = regime.get("regime", "Unknown")
    tone = regime_tone(regime_name)

    best = "N/A"
    weakest = "N/A"
    tradable = df[~df["Symbol"].isin(MACRO_SYMBOLS)].copy() if df is not None and not df.empty else pd.DataFrame()
    if not tradable.empty:
        sorted_df = tradable.sort_values("24H %", ascending=False, na_position="last")
        best_row = sorted_df.iloc[0]
        weak_row = sorted_df.iloc[-1]
        best = f"{best_row.get('Name')} ({format_pct(best_row.get('24H %'))})"
        weakest = f"{weak_row.get('Name')} ({format_pct(weak_row.get('24H %'))})"

    if tone == "good":
        setup = "gold trend continuation, miner confirmation, and liquid pullback setups"
        avoid = "thin miners, late entries, and fighting the macro pressure signal"
    elif tone == "warning":
        setup = "only the clearest gold or miner leaders with clean structure"
        avoid = "weak miners, oversized positions, and forcing trades"
    elif tone == "risk":
        setup = "capital protection, smaller size, and only exceptional A+ setups"
        avoid = "new broad miner exposure and averaging down weak names"
    else:
        setup = "confirmed setups with clear gold/miner leadership"
        avoid = "forcing trades without confirmation"

    brief = (
        f"Gold Pulse is reading **{regime_name}**. Market cycle is **{market_cycle.get('cycle')}**, "
        f"stress is **{stress_score}/100 ({stress_label})**, breadth is "
        f"**{safe_float(breadth.get('score'), 0):.1f}/100 ({breadth.get('state')})**, "
        f"and macro support is **{macro.get('state')} ({macro.get('score')}/100)**. "
        f"Gold is **{format_pct(regime.get('gold_24h'))}**, GDX is **{format_pct(regime.get('gdx_24h'))}**, "
        f"and UUP is **{format_pct(regime.get('uup_24h'))}**. "
        f"The strongest name is **{best}** and the weakest is **{weakest}**. "
        f"Current conditions favor **{setup}**. Avoid **{avoid}**. "
        f"Suggested execution multiplier is **{safe_float(regime.get('execution_multiplier'), 0):.2f}x**."
    )

    return {"brief": brief, "tone": tone, "playbook": str(regime.get("playbook", "No playbook available."))}


def gold_market_clock_card(data_status: Dict[str, Any]) -> None:
    local_time = datetime.now().strftime("%H:%M")
    utc_time = datetime.now(timezone.utc).strftime("%H:%M UTC")
    provider = str(data_status.get("provider", "yfinance"))
    interval = str(data_status.get("interval", "N/A"))
    period = str(data_status.get("period", "N/A"))

    st.info(
        f"● OPEN 24/5  |  Refresh {local_time} {utc_time}  |  Provider: {provider}  |  {period} • {interval}"
    )


def display_price_table(title: str, df: pd.DataFrame, max_rows: int | None = None) -> None:
    st.markdown(f"#### {title}")
    if df is None or df.empty:
        st.info("No gold data available yet.")
        return

    view = df.copy()
    if max_rows is not None:
        view = view.head(max_rows)

    display_cols = [col for col in ["Name", "Symbol", "Group", "Price", "1H %", "24H %", "7D %"] if col in view.columns]
    view = view[display_cols]

    pct_cols = [col for col in ["1H %", "24H %", "7D %"] if col in view.columns]
    if pct_cols:
        styled = view.style.map(style_pct, subset=pct_cols)
    else:
        styled = view

    st.dataframe(styled, width="stretch", hide_index=True, height=table_height(len(view)))


def build_gold_playbook_cards(
    regime: Dict[str, Any],
    breadth: Dict[str, Any],
    stress_score: int,
    macro: Dict[str, Any],
    market_cycle: Dict[str, Any],
) -> List[Dict[str, Any]]:
    regime_name = str(regime.get("regime", "Unknown"))

    if regime_name == "GOLD BREAKDOWN":
        allowed = "Cash / defensive only"
        avoid = "Broad miner exposure"
        setup = "Only exceptional A+ setups"
        risk = "Defensive"
        tone = "risk"
    elif regime_name in ("CAUTIOUS", "SELECTIVE"):
        allowed = "Gold ETFs and strongest miners"
        avoid = "Weak miners and laggards"
        setup = "Relative-strength pullbacks"
        risk = "Reduced"
        tone = "warning"
    else:
        allowed = "Qualified gold/miner leaders"
        avoid = "Late entries and thin miners"
        setup = "Breakouts / pullbacks / trend continuation"
        risk = "Normal"
        tone = "good"

    return [
        {
            "title": "Gold Playbook",
            "tone": tone,
            "rows": [
                ("Regime", regime_name),
                ("Market Cycle", market_cycle.get("cycle", "N/A")),
                ("Allowed", allowed),
                ("Preferred Setup", setup),
                ("Avoid", avoid),
                ("Risk Posture", risk),
            ],
        },
        {
            "title": "Macro & Breadth",
            "tone": str(macro.get("tone", "neutral")),
            "rows": [
                ("Macro Support", f"{macro.get('state')} ({macro.get('score')}/100)"),
                ("Gold 24H", format_pct(regime.get("gold_24h"))),
                ("GDX 24H", format_pct(regime.get("gdx_24h"))),
                ("Breadth", f"{safe_float(breadth.get('score'), 0):.1f}/100"),
                ("Stress", f"{stress_score}/100"),
            ],
        },
    ]


# =========================================================
# PAGE
# =========================================================

# =========================================================
# MULTI-ASSET SIGNAL BUS v1.0
# =========================================================

def publish_multi_asset_signal_bus(
    df: pd.DataFrame,
    regime: Dict[str, Any],
    breadth: Dict[str, Any],
    stress_score: int,
    stress_label: str,
    opportunity_df: pd.DataFrame,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Publish Gold Pulse state for Scanner / Quant Executor integration."""

    asset_class = "gold"
    extra = extra if isinstance(extra, dict) else {}

    best = {}
    if isinstance(opportunity_df, pd.DataFrame) and not opportunity_df.empty:
        try:
            best = opportunity_df.iloc[0].to_dict()
        except Exception:
            best = {}

    trade_allowed = bool(regime.get("trade_allowed", regime.get("trade_allowed", True)))
    score_value = safe_float(best.get("Opportunity Score"), 0.0) if best else 0.0

    payload = {
        "asset_class": asset_class,
        "label": "Gold Pulse",
        "regime": str(regime.get("regime", "UNKNOWN")),
        "stress_score": int(stress_score),
        "stress_label": str(stress_label),
        "breadth_score": safe_float(breadth.get("score"), 0.0),
        "breadth_state": str(breadth.get("state", "UNKNOWN")),
        "trade_allowed": trade_allowed,
        "execution_multiplier": safe_float(regime.get("execution_multiplier"), 1.0),
        "market_cycle": str(extra.get("market_cycle", "")),
        "best_symbol": str(best.get("Symbol", "") or "").upper().strip(),
        "best_name": str(best.get("Name", "") or ""),
        "best_recommendation": str(best.get("Recommendation", "") or ""),
        "best_score": score_value,
        "opportunity_rows": int(opportunity_df.shape[0]) if isinstance(opportunity_df, pd.DataFrame) else 0,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "gold_pulse_signal_bus_v1",
        "extra": extra,
    }

    bus = st.session_state.get("multi_asset_signal_bus", {})
    if not isinstance(bus, dict):
        bus = {}
    bus[asset_class] = payload
    st.session_state["multi_asset_signal_bus"] = bus
    st.session_state[f"{asset_class}_pulse_bus"] = payload
    return payload


def run_page() -> None:
    inject_gold_pulse_css()

    st.title("🥇 Gold Pulse")
    st.caption(
        "Institutional gold command center for regime, macro leadership, breadth, and execution readiness."
    )
    st.caption(
        "Gold Pulse v2.0 — decision-first layout for market environment, research, execution, and diagnostics."
    )

    st.session_state.setdefault("gold_pulse_period", "7d")
    st.session_state.setdefault("gold_pulse_interval", "1h")

    period = str(st.session_state.get("gold_pulse_period", "7d"))
    interval = str(st.session_state.get("gold_pulse_interval", "1h"))

    if yf is None:
        st.error("yfinance is not available in this environment. Install yfinance to load live gold data.")
        return

    symbols = tuple(row["Symbol"] for row in GOLD_UNIVERSE)

    with st.spinner("Loading gold market data..."):
        gold_df = load_gold_prices(symbols, period=period, interval=interval)

    if gold_df.empty:
        st.error("Gold data could not be loaded. Check internet/data access and try again.")
        return

    breadth = calculate_gold_breadth(gold_df)
    macro = calculate_gold_macro_pressure(gold_df)
    stress_score, stress_label = calculate_gold_stress(gold_df, breadth, macro)
    regime = build_gold_regime(gold_df, breadth, stress_score, macro)
    market_cycle = calculate_gold_market_cycle(regime, breadth, stress_score, macro)
    opportunity_df = build_gold_opportunity_scanner(gold_df, regime, breadth, macro)
    ai_brief = build_ai_gold_brief(gold_df, regime, breadth, stress_score, stress_label, macro, market_cycle)

    # Session exports for future Scanner/Quant Executor integration.
    st.session_state["gold_pulse_regime"] = regime["regime"]
    st.session_state["gold_pulse_stress_score"] = int(stress_score)
    st.session_state["gold_pulse_stress_label"] = stress_label
    st.session_state["gold_pulse_breadth_score"] = float(breadth["score"])
    st.session_state["gold_pulse_breadth_state"] = breadth["state"]
    st.session_state["gold_pulse_trade_allowed"] = bool(regime["trade_allowed"])
    st.session_state["gold_pulse_execution_multiplier"] = float(regime["execution_multiplier"])
    st.session_state["gold_pulse_macro_support"] = str(macro["state"])
    st.session_state["gold_pulse_market_cycle"] = str(market_cycle["cycle"])

    gold_pulse_bus_payload = publish_multi_asset_signal_bus(
        df=gold_df,
        regime=regime,
        breadth=breadth,
        stress_score=stress_score,
        stress_label=stress_label,
        opportunity_df=opportunity_df,
        extra={"macro_state": macro.get("state"), "macro_score": macro.get("score"), "market_cycle": market_cycle.get("cycle")},
    )

    latest_timestamp = str(gold_df.get("Timestamp", pd.Series(dtype=str)).dropna().iloc[0]) if not gold_df.empty and "Timestamp" in gold_df.columns and not gold_df["Timestamp"].dropna().empty else "N/A"
    volatility_proxy = 0.0
    if not gold_df.empty and "24H %" in gold_df.columns:
        volatility_proxy = float(pd.to_numeric(gold_df["24H %"], errors="coerce").abs().dropna().mean() or 0.0)

    top_score_global = 0.0
    if not opportunity_df.empty:
        try:
            top_score_global = safe_float(opportunity_df.iloc[0].get("Opportunity Score"), 0.0)
        except Exception:
            top_score_global = 0.0

    institutional_grade = "WAIT"
    if regime.get("trade_allowed"):
        institutional_grade = "READY" if top_score_global >= 65 else "PENDING CONFIRMATION"

    if regime["regime"] in ("MINERS CONFIRMING", "GOLD BREAKOUT"):
        execution_status = "BUY"
    elif regime["regime"] == "SELECTIVE":
        execution_status = "HOLD"
    elif regime["regime"] == "CAUTIOUS":
        execution_status = "WAIT"
    else:
        execution_status = "AVOID"

    recommendation_sentence = regime["playbook"]

    tradable_df = gold_df[~gold_df["Symbol"].isin(MACRO_SYMBOLS)].copy()
    strongest = tradable_df.sort_values("24H %", ascending=False, na_position="last").head(5)
    weakest = tradable_df.sort_values("24H %", ascending=True, na_position="last").head(5)

    participation_pct = (breadth["advancing"] / breadth["total"] * 100.0) if breadth["total"] else 0.0
    summary_confidence_note = "Institutional confidence remains low." if top_score_global < 50 else "Institutional confidence is improving."

    # Executive Briefing
    section_heading("Executive Briefing", "Immediate read on the gold tape and the required posture.")
    briefing_grid([
        {"label": "Gold Regime", "value": regime["regime"], "detail": regime["playbook"], "tone": regime_tone(regime["regime"])},
        {"label": "Risk Level", "value": stress_label, "detail": f"Stress {stress_score}/100", "tone": stress_tone(stress_score)},
        {"label": "Institutional Grade", "value": institutional_grade, "detail": f"Confidence {top_score_global:.1f}/100", "tone": "good" if institutional_grade == "READY" else "warning" if institutional_grade in ("PENDING CONFIRMATION", "WAIT") else "risk"},
        {"label": "Execution Status", "value": execution_status, "detail": "BUY / HOLD / WAIT / AVOID", "tone": "good" if execution_status == "BUY" else "warning" if execution_status in ("HOLD", "WAIT") else "risk"},
        {"label": "Dollar / Macro Leadership", "value": macro["state"], "detail": f"Macro score {macro['score']}/100", "tone": macro["tone"]},
        {"label": "Commander's Recommendation", "value": recommendation_sentence, "detail": "Primary desk instruction", "tone": regime_tone(regime["regime"]), "featured": True},
    ])

    # Executive Summary
    section_heading("Executive Summary", "Compact KPI read for the current gold tape.")
    metric_grid([
        {"label": "Market Regime", "value": regime["regime"], "detail": market_cycle["cycle"], "tone": regime_tone(regime["regime"])},
        {"label": "Opportunity Score", "value": f"{top_score_global:.1f}/100", "detail": "Highest institutional score", "tone": "good" if top_score_global >= 65 else "warning" if top_score_global >= 45 else "risk"},
        {"label": "Market Momentum", "value": format_pct(safe_float(tradable_df["24H %"].mean(), 0.0) if not tradable_df.empty and "24H %" in tradable_df.columns else 0.0), "detail": "Loaded universe average 24H move", "tone": "good" if safe_float(tradable_df["24H %"].mean(), 0.0) > 0 else "warning" if safe_float(tradable_df["24H %"].mean(), 0.0) == 0 else "risk"},
        {"label": "Breadth / Participation", "value": f"{participation_pct:.0f}%", "detail": breadth["state"], "tone": breadth_tone(breadth["score"])},
        {"label": "Volatility", "value": f"{volatility_proxy:.2f}%", "detail": "Average absolute 24H move", "tone": "warning" if volatility_proxy >= 1.5 else "neutral"},
        {"label": "Institutional Confidence", "value": f"{top_score_global:.1f}/100", "detail": summary_confidence_note, "tone": "good" if top_score_global >= 70 else "warning" if top_score_global >= 50 else "risk"},
    ])

    # Market Environment
    section_heading("Market Environment", "Macro tape, market status, and stress profile.")
    gold_market_clock_card({"provider": "yfinance", "period": period, "interval": interval})
    metric_grid([
        {"label": "Gold Cycle", "value": market_cycle["cycle"], "detail": market_cycle["note"], "tone": market_cycle["tone"]},
        {"label": "Liquidity", "value": macro["state"], "detail": f"{macro['score']}/100", "tone": macro["tone"]},
        {"label": "Stress", "value": f"{stress_score}/100", "detail": stress_label, "tone": stress_tone(stress_score)},
        {"label": "Dollar Strength", "value": format_pct(regime["uup_24h"]), "detail": "UUP proxy", "tone": "risk" if regime["uup_24h"] > 0 else "good" if regime["uup_24h"] < 0 else "warning"},
    ])

    # Dollar & Macro Leadership
    section_heading("Dollar & Macro Leadership", "Macro drivers behind the current gold posture.")
    metric_grid([
        {"label": "USD Performance", "value": format_pct(regime["uup_24h"]), "detail": "UUP 24H", "tone": "risk" if regime["uup_24h"] > 0 else "good" if regime["uup_24h"] < 0 else "warning"},
        {"label": "Real Yields Proxy", "value": format_pct(macro.get("tlt_24h")), "detail": "TLT 24H", "tone": "good" if safe_float(macro.get("tlt_24h"), 0.0) > 0 else "warning"},
        {"label": "Gold vs USD", "value": format_pct(-regime["uup_24h"] + regime["gold_24h"]), "detail": "Gold and dollar balance", "tone": macro["tone"]},
        {"label": "Macro Read", "value": macro["state"], "detail": "Macro support posture", "tone": macro["tone"]},
    ])
    institutional_banner("Macro Read", f"{macro['state']}. {macro['note']}", tone=macro["tone"])

    # Relative Strength
    section_heading("Relative Strength", "Strongest and weakest precious-metal assets.")
    st.markdown('<div style="margin-top:-0.22rem;"></div>', unsafe_allow_html=True)
    l1, l2 = st.columns(2)
    with l1:
        display_price_table("Strongest Precious Assets", strongest, max_rows=5)
    with l2:
        display_price_table("Weakest Assets", weakest, max_rows=5)

    # Market Breadth
    section_heading("Market Breadth", "Participation quality across the loaded precious-metals universe.")
    metric_grid([
        {"label": "Breadth Score", "value": f"{breadth['score']:.1f}/100", "detail": breadth["state"], "tone": breadth_tone(breadth["score"])},
        {"label": "Advancers", "value": f"{breadth['advancing']}/{breadth['total']}", "detail": "Assets moving higher", "tone": "info"},
        {"label": "Decliners", "value": f"{breadth['declining']}/{breadth['total']}", "detail": "Assets moving lower", "tone": "warning" if breadth['declining'] else "neutral"},
        {"label": "Participation", "value": f"{participation_pct:.0f}%", "detail": "Advancing share of universe", "tone": "good" if participation_pct >= 60 else "warning" if participation_pct >= 40 else "risk"},
        {"label": "Average Move", "value": format_pct(breadth["average_move"]), "detail": "Average 24H move", "tone": "good" if breadth["average_move"] > 0 else "risk" if breadth["average_move"] < -1.0 else "warning"},
    ])
    institutional_banner("Institutional Breadth Read", "Broad participation supports cleaner gold trends; weak breadth favors selective and smaller positioning.", tone=breadth_tone(breadth["score"]))

    # Watchlist
    section_heading("Watchlist", "Ranked opportunities for immediate focus.")
    if opportunity_df.empty:
        st.info("No opportunity scores available yet.")
    else:
        watch_cols = ["Rank", "Symbol", "Group", "Directional Bias", "Opportunity Score", "Recommendation"]
        watch_view = opportunity_df.head(8)[watch_cols].rename(columns={"Directional Bias": "Trend"})
        styled_watch = watch_view.style.apply(
            lambda row: ["background-color: #eff6ff; font-weight: 700;" if row.name == watch_view.index[0] else "" for _ in row],
            axis=1,
        )
        st.dataframe(styled_watch, width="stretch", hide_index=True, height=table_height(min(8, len(opportunity_df))))

    # Research
    section_heading("Research", "Institutional interpretation of the gold environment.")
    macro_env = "Constructive" if regime["regime"] in ("MINERS CONFIRMING", "GOLD BREAKOUT") else "Mixed" if regime["regime"] == "SELECTIVE" else "Defensive"
    market_sentiment = "Improving" if top_score_global >= 65 else "Neutral" if top_score_global >= 50 else "Defensive"
    key_catalysts = ", ".join([macro["state"], market_cycle["cycle"], breadth["state"]])
    list_grid([
        {
            "title": "Institutional Research Summary",
            "tone": regime_tone(regime["regime"]),
            "rows": [
                ("Macro Environment", macro_env),
                ("Dollar Leadership", format_pct(regime["uup_24h"])),
                ("Participation", f"{participation_pct:.0f}% advancing"),
                ("Liquidity", macro["state"]),
                ("Market Sentiment", market_sentiment),
                ("Key Catalysts", key_catalysts),
            ],
        }
    ])

    # Technical Analysis
    section_heading("Technical Analysis", "Structure and relative performance without redundant charts.")
    if not opportunity_df.empty:
        tech_view = opportunity_df.head(10)[["Symbol", "Directional Bias", "1H %", "24H %", "7D %", "RS vs Gold", "Recommendation"]].copy()
        tech_view = tech_view.rename(columns={"Directional Bias": "Trend", "RS vs Gold": "Relative Strength"})
        styled_tech = tech_view.style.map(style_pct, subset=["1H %", "24H %", "7D %", "Relative Strength"])
        st.dataframe(styled_tech, width="stretch", hide_index=True, height=table_height(min(10, len(opportunity_df))))
    else:
        st.info("No technical structure available yet.")

    # Risk Assessment
    section_heading("Risk Assessment", "How much risk the tape supports right now.")
    risk_view = stress_score
    metric_grid([
        {"label": "Risk Score", "value": f"{risk_view}/100", "detail": stress_label, "tone": stress_tone(stress_score)},
        {"label": "Stress", "value": f"{stress_score}/100", "detail": stress_label, "tone": stress_tone(stress_score)},
        {"label": "Volatility", "value": f"{volatility_proxy:.2f}%", "detail": "Average absolute 24H move", "tone": "warning" if volatility_proxy >= 1.5 else "neutral"},
        {"label": "Confidence", "value": f"{top_score_global:.1f}/100", "detail": summary_confidence_note, "tone": "good" if top_score_global >= 70 else "warning" if top_score_global >= 50 else "risk"},
    ])
    if risk_view >= 60:
        institutional_banner("Risk Posture", "Defensive posture. Protect capital and avoid broad miner exposure.", tone="risk", body_weight=800)
    elif risk_view >= 35:
        institutional_banner("Risk Posture", "Selective posture. Trade only clean relative-strength setups.", tone="warning", body_weight=800)
    else:
        institutional_banner("Risk Posture", "Calm tape. Qualified setups can be considered with discipline.", tone="good", body_weight=800)

    # Execution Plan
    section_heading("Execution Plan", "Decision-ready guidance for current gold conditions.")
    if regime["regime"] == "GOLD BREAKDOWN":
        direction = "AVOID"
        size_guidance = "Reduced size"
        entry_zone = "Only exceptional A+ setups"
        stop_level = "Preserve capital"
        target_zone = "Defensive / capital preservation"
        rr = "Favor protection"
    elif regime["regime"] in ("CAUTIOUS", "SELECTIVE"):
        direction = "WAIT"
        size_guidance = "Reduced size"
        entry_zone = "Gold ETFs / strongest miners"
        stop_level = "Below clear structure"
        target_zone = "Directional continuation / pullbacks"
        rr = "Moderate"
    else:
        direction = "BUY"
        size_guidance = "Normal size"
        entry_zone = "Gold/miner leaders"
        stop_level = "Below structure"
        target_zone = "Continuation / breakout"
        rr = "Positive"

    metric_grid([
        {"label": "Trade Direction", "value": direction, "detail": regime["playbook"], "tone": regime_tone(regime["regime"])},
        {"label": "Position Size", "value": size_guidance, "detail": f"Multiplier {regime['execution_multiplier']:.2f}x", "tone": "info"},
        {"label": "Entry Zone", "value": entry_zone, "detail": "Execution guidance", "tone": "neutral"},
        {"label": "Stop Level", "value": stop_level, "detail": "Risk boundary", "tone": "risk"},
        {"label": "Target", "value": target_zone, "detail": "Profit objective", "tone": "good"},
        {"label": "Risk/Reward", "value": rr, "detail": "Target versus risk", "tone": "info"},
        {"label": "Institutional Grade", "value": institutional_grade, "detail": f"Confidence {top_score_global:.1f}/100", "tone": "good" if top_score_global >= 70 else "warning" if top_score_global >= 50 else "risk"},
    ])

    # Trade Management
    section_heading("Trade Management", "How to manage the position if execution is approved.")
    list_grid([
        {
            "title": "Management Framework",
            "tone": "info",
            "rows": [
                ("Scale In", "Use confirmation only; do not average into weakness."),
                ("Invalidation", "Exit on structure failure, not emotion."),
                ("Review", "Reassess on each regime or breadth change."),
                ("Profit Management", "Take partials into strength and trail the remainder."),
            ],
        },
        {
            "title": "Operational Discipline",
            "tone": "warning" if regime["regime"] in ("CAUTIOUS", "SELECTIVE") else "good",
            "rows": [
                ("No Chase Rule", "Avoid extended entries after vertical moves."),
                ("Liquidity", "Prefer the most liquid names in the universe."),
                ("Exposure", "Respect the current regime multiplier."),
                ("Time Stop", "If the move stalls, reduce or exit."),
            ],
        },
    ])

    # Historical Context
    section_heading("Historical Context", "Recent price action context for the current tape.")
    seven_day_leaders = tradable_df.sort_values("7D %", ascending=False, na_position="last").head(5)
    seven_day_laggards = tradable_df.sort_values("7D %", ascending=True, na_position="last").head(5)
    h1, h2 = st.columns(2)
    with h1:
        display_price_table("Strongest Performers", seven_day_leaders, max_rows=5)
    with h2:
        display_price_table("Weakest Performers", seven_day_laggards, max_rows=5)
    list_grid([
        {
            "title": "Historical Read",
            "tone": "info",
            "rows": [
                ("Cycle", market_cycle["cycle"]),
                ("Leadership", macro["state"]),
                ("Breadth", breadth["state"]),
                ("Confidence", f"{top_score_global:.1f} / 100"),
            ],
        }
    ])

    # Data Controls
    section_heading("Data Controls", "Operational refresh controls kept below the decision flow.")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("Refresh Gold Pulse Data", width="stretch"):
            st.cache_data.clear()
            st.rerun()
    with c2:
        st.selectbox("Lookback", ["7d", "14d", "30d"], index=["7d", "14d", "30d"].index(period) if period in ["7d", "14d", "30d"] else 0, key="gold_pulse_period")
    with c3:
        st.selectbox("Interval", ["1h", "2h", "4h", "1d"], index=["1h", "2h", "4h", "1d"].index(interval) if interval in ["1h", "2h", "4h", "1d"] else 0, key="gold_pulse_interval")

    # Diagnostics
    section_heading("Diagnostics", "Technical and developer-oriented details are collapsed below.")
    with st.expander("Raw API Responses", expanded=False):
        st.dataframe(gold_df.head(12), width="stretch", hide_index=True, height=table_height(min(12, len(gold_df))))
        if not opportunity_df.empty:
            st.dataframe(opportunity_df.head(12), width="stretch", hide_index=True, height=table_height(min(12, len(opportunity_df))))

    with st.expander("Cache Status", expanded=False):
        st.write({
            "gold_pulse_bus_payload": gold_pulse_bus_payload,
            "multi_asset_signal_bus": st.session_state.get("multi_asset_signal_bus", {}),
            "gold_pulse_regime": st.session_state.get("gold_pulse_regime"),
            "gold_pulse_market_cycle": st.session_state.get("gold_pulse_market_cycle"),
            "gold_pulse_execution_multiplier": st.session_state.get("gold_pulse_execution_multiplier"),
        })

    with st.expander("Debug Information", expanded=False):
        st.write({
            "regime": regime,
            "breadth": breadth,
            "stress_score": stress_score,
            "stress_label": stress_label,
            "macro": macro,
            "market_cycle": market_cycle,
        })

    with st.expander("Timing Diagnostics", expanded=False):
        st.write({
            "period": period,
            "interval": interval,
            "last_refresh_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_refresh_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "latest_data_timestamp": latest_timestamp,
        })

    help_text("Gold Pulse is informational only. It does not place trades and does not route orders.")


if __name__ == "__main__":
    st.set_page_config(page_title="Gold Pulse", page_icon="🥇", layout="wide")
    run_page()
