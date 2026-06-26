# =========================================================
# 💱 FOREX PULSE PAGE — v1.1 STABLE
# JFBP Quant Desk
# Forex Regime + USD Strength + Risk Appetite + Carry + Leadership Dashboard
# Built from Crypto Pulse / Market Pulse visual standard
# v1.1 STABLE: Qualified-opportunity threshold logic refined and scanner messaging improved
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

FOREX_UNIVERSE = [
    {"Symbol": "EURUSD=X", "Name": "EUR/USD", "Group": "Major"},
    {"Symbol": "GBPUSD=X", "Name": "GBP/USD", "Group": "Major"},
    {"Symbol": "USDJPY=X", "Name": "USD/JPY", "Group": "Major"},
    {"Symbol": "USDCHF=X", "Name": "USD/CHF", "Group": "Major"},
    {"Symbol": "USDCAD=X", "Name": "USD/CAD", "Group": "Major"},
    {"Symbol": "AUDUSD=X", "Name": "AUD/USD", "Group": "Commodity FX"},
    {"Symbol": "NZDUSD=X", "Name": "NZD/USD", "Group": "Commodity FX"},
    {"Symbol": "EURJPY=X", "Name": "EUR/JPY", "Group": "Cross"},
    {"Symbol": "GBPJPY=X", "Name": "GBP/JPY", "Group": "Cross"},
    {"Symbol": "EURGBP=X", "Name": "EUR/GBP", "Group": "Cross"},
    {"Symbol": "CADJPY=X", "Name": "CAD/JPY", "Group": "Carry / Risk"},
    {"Symbol": "AUDJPY=X", "Name": "AUD/JPY", "Group": "Carry / Risk"},
]

MAJOR_SYMBOLS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "USDCAD=X", "AUDUSD=X", "NZDUSD=X"]
RISK_SYMBOLS = ["AUDJPY=X", "CADJPY=X", "GBPJPY=X", "EURJPY=X"]
USD_BASE_SYMBOLS = ["USDJPY=X", "USDCHF=X", "USDCAD=X"]
USD_QUOTE_SYMBOLS = ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X"]


# =========================================================
# RESPONSIVE UI HELPERS
# =========================================================

def inject_forex_pulse_css() -> None:
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

            .forex-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
                gap: 0.65rem;
                margin: 0.35rem 0 0.75rem 0;
                width: 100%;
            }

            .forex-card {
                border: 1px solid;
                border-radius: 14px;
                padding: 0.72rem 0.82rem;
                min-width: 0;
                width: 100%;
                box-sizing: border-box;
                overflow: hidden;
            }

            .forex-label {
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #64748b;
                font-weight: 800;
                margin-bottom: 0.28rem;
                line-height: 1.25;
            }

            .forex-value {
                font-size: clamp(1.05rem, 2.2vw, 1.45rem);
                line-height: 1.15;
                font-weight: 850;
                white-space: normal;
                word-break: normal;
            }

            .forex-detail {
                font-size: 0.78rem;
                color: #64748b;
                margin-top: 0.35rem;
                line-height: 1.35;
            }

            .forex-list-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
                gap: 0.75rem;
                margin: 0.45rem 0 0.85rem 0;
            }

            .forex-list-card {
                border: 1px solid;
                border-radius: 16px;
                padding: 0.85rem 0.95rem;
                min-width: 0;
                overflow: hidden;
            }

            .forex-list-title {
                font-size: 1.02rem;
                font-weight: 850;
                color: #1f2937;
                margin-bottom: 0.62rem;
                line-height: 1.2;
            }

            .forex-list-row {
                display: grid;
                grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.35fr);
                gap: 0.65rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.28);
                padding: 0.38rem 0;
            }

            .forex-list-row:last-child {
                border-bottom: none;
            }

            .forex-list-label {
                color: #64748b;
                font-weight: 750;
                line-height: 1.28;
            }

            .forex-list-value {
                color: #1f2937;
                font-weight: 850;
                line-height: 1.28;
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

                .forex-grid,
                .forex-list-grid {
                    grid-template-columns: 1fr;
                }

                .forex-list-row {
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
    }
    return palette.get(tone, palette["neutral"])


def metric_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="forex-grid">']

    for card in cards:
        background, border, value_color = tone_palette(str(card.get("tone", "neutral")))
        label = html.escape(str(card.get("label", "")))
        value = html.escape(str(card.get("value", "")))
        detail = html.escape(str(card.get("detail", "")))
        detail_html = f'<div class="forex-detail">{detail}</div>' if detail else ""
        pieces.append(
            f'<div class="forex-card" style="background:{background};border-color:{border};">'
            f'<div class="forex-label">{label}</div>'
            f'<div class="forex-value" style="color:{value_color};">{value}</div>'
            f'{detail_html}'
            f'</div>'
        )

    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def list_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="forex-list-grid">']

    for card in cards:
        background, border, _ = tone_palette(str(card.get("tone", "neutral")))
        title = html.escape(str(card.get("title", "")))
        rows_html = ""

        for label, value in card.get("rows", []):
            rows_html += (
                '<div class="forex-list-row">'
                f'<div class="forex-list-label">{html.escape(str(label))}</div>'
                f'<div class="forex-list-value">{html.escape(str(value))}</div>'
                '</div>'
            )

        pieces.append(
            f'<div class="forex-list-card" style="background:{background};border-color:{border};">'
            f'<div class="forex-list-title">{title}</div>'
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
def load_forex_prices(symbols: Tuple[str, ...], period: str = "7d", interval: str = "1h") -> pd.DataFrame:
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

    for asset in FOREX_UNIVERSE:
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
            "Price": round(last, 6),
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


def usd_direction_adjusted_move(row: pd.Series) -> float:
    """Positive means USD strength, negative means USD weakness."""

    symbol = str(row.get("Symbol", ""))
    move = safe_float(row.get("24H %"), 0.0)

    if symbol in USD_BASE_SYMBOLS:
        return move
    if symbol in USD_QUOTE_SYMBOLS:
        return -move

    return 0.0


def calculate_usd_strength(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"score": 50.0, "state": "Unknown", "avg_usd_move": 0.0, "tone": "neutral"}

    work = df[df["Symbol"].isin(USD_BASE_SYMBOLS + USD_QUOTE_SYMBOLS)].copy()
    if work.empty:
        return {"score": 50.0, "state": "Unknown", "avg_usd_move": 0.0, "tone": "neutral"}

    work["USD Move"] = work.apply(usd_direction_adjusted_move, axis=1)
    avg_usd_move = float(work["USD Move"].mean())

    score = round(50.0 + avg_usd_move * 35.0, 1)
    score = max(0.0, min(100.0, score))

    if score >= 65:
        state = "USD STRONG"
        tone = "good"
    elif score <= 35:
        state = "USD WEAK"
        tone = "risk"
    else:
        state = "USD MIXED"
        tone = "warning"

    return {
        "score": score,
        "state": state,
        "avg_usd_move": round(avg_usd_move, 3),
        "tone": tone,
    }


def calculate_forex_breadth(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty or "24H %" not in df.columns:
        return {
            "score": 50.0,
            "state": "Unknown",
            "advancing": 0,
            "declining": 0,
            "total": 0,
            "average_move": 0.0,
            "risk_advance_pct": 0.0,
        }

    work = df.copy()
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
            "risk_advance_pct": 0.0,
        }

    total = len(valid)
    advancing = int((valid["24H %"] > 0).sum())
    declining = int((valid["24H %"] < 0).sum())
    average_move = float(valid["24H %"].mean())
    advance_pct = advancing / total * 100 if total else 0.0

    risk_valid = valid[valid["Symbol"].isin(RISK_SYMBOLS)]
    risk_advance_pct = 0.0
    if not risk_valid.empty:
        risk_advance_pct = float((risk_valid["24H %"] > 0).sum() / len(risk_valid) * 100)

    score = round((advance_pct * 0.55) + (risk_advance_pct * 0.25) + (max(0.0, average_move + 1.0) / 2.0 * 20.0), 1)
    score = max(0.0, min(100.0, score))

    if score >= 70:
        state = "Broad FX Risk Bid"
    elif score >= 55:
        state = "Constructive FX Tape"
    elif score >= 40:
        state = "Mixed / Selective"
    elif score >= 25:
        state = "Weak FX Breadth"
    else:
        state = "FX Risk-Off Breadth"

    return {
        "score": score,
        "state": state,
        "advancing": advancing,
        "declining": declining,
        "total": total,
        "average_move": average_move,
        "risk_advance_pct": risk_advance_pct,
    }


def calculate_forex_stress(df: pd.DataFrame, breadth: Dict[str, Any], usd: Dict[str, Any]) -> Tuple[int, str]:
    usd_jpy = get_move(df, "USDJPY=X") or 0.0
    aud_jpy = get_move(df, "AUDJPY=X") or 0.0
    cad_jpy = get_move(df, "CADJPY=X") or 0.0
    eur_usd = get_move(df, "EURUSD=X") or 0.0
    gbp_usd = get_move(df, "GBPUSD=X") or 0.0

    score = 0.0

    # FX stress is usually visible when carry/risk crosses weaken and USD becomes defensive.
    if aud_jpy < 0:
        score += min(abs(aud_jpy) * 18.0, 28.0)
    if cad_jpy < 0:
        score += min(abs(cad_jpy) * 14.0, 18.0)
    if usd_jpy < 0:
        score += min(abs(usd_jpy) * 12.0, 18.0)
    if eur_usd < 0:
        score += min(abs(eur_usd) * 10.0, 14.0)
    if gbp_usd < 0:
        score += min(abs(gbp_usd) * 8.0, 10.0)

    breadth_score = safe_float(breadth.get("score"), 50.0)
    if breadth_score < 25:
        score += 18
    elif breadth_score < 40:
        score += 12
    elif breadth_score < 55:
        score += 6

    if str(usd.get("state", "")).upper() == "USD STRONG" and aud_jpy < 0:
        score += 8

    score = int(max(0, min(100, round(score))))

    if score >= 80:
        label = "Severe FX Stress"
    elif score >= 60:
        label = "High FX Stress"
    elif score >= 40:
        label = "Moderate FX Stress"
    elif score >= 20:
        label = "Low FX Stress"
    else:
        label = "Calm FX Tape"

    return score, label


def regime_tone(regime: str) -> str:
    key = str(regime or "").upper().strip()
    if key in ("RISK-OFF", "DEFENSIVE", "USD DEFENSIVE"):
        return "risk"
    if key in ("SELECTIVE", "CAUTIOUS", "USD MIXED"):
        return "warning"
    if key in ("RISK-ON", "CARRY RISK-ON", "USD TREND"):
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


def calculate_forex_liquidity_proxy(breadth: Dict[str, Any], stress_score: int, usd: Dict[str, Any]) -> Dict[str, Any]:
    breadth_score = safe_float(breadth.get("score"), 50.0)
    usd_score = safe_float(usd.get("score"), 50.0)

    # Liquidity proxy: broad risk FX + controlled stress + not an extreme USD squeeze.
    score = (breadth_score * 0.60) + ((100 - stress_score) * 0.25) + ((100 - abs(usd_score - 50) * 1.5) * 0.15)
    score = max(0.0, min(100.0, score))

    if score >= 70:
        state = "RISK-ON"
        tone = "good"
        note = "FX liquidity proxy supports carry/risk trades."
    elif score >= 45:
        state = "NEUTRAL"
        tone = "warning"
        note = "FX liquidity proxy is mixed. Trade selectively."
    else:
        state = "RISK-OFF"
        tone = "risk"
        note = "FX liquidity proxy is defensive. Reduce carry/risk exposure."

    return {"score": round(score, 1), "state": state, "tone": tone, "note": note}


def build_forex_regime(df: pd.DataFrame, breadth: Dict[str, Any], stress_score: int, usd: Dict[str, Any]) -> Dict[str, Any]:
    aud_jpy = get_move(df, "AUDJPY=X") or 0.0
    cad_jpy = get_move(df, "CADJPY=X") or 0.0
    eur_usd = get_move(df, "EURUSD=X") or 0.0
    gbp_usd = get_move(df, "GBPUSD=X") or 0.0
    usd_jpy = get_move(df, "USDJPY=X") or 0.0

    breadth_score = safe_float(breadth.get("score"), 50.0)
    usd_state = str(usd.get("state", "USD MIXED")).upper()

    carry_avg = (aud_jpy + cad_jpy) / 2.0
    europe_avg = (eur_usd + gbp_usd) / 2.0

    if stress_score >= 70 or breadth_score < 30:
        regime = "RISK-OFF"
        playbook = "Protect capital. Avoid new carry/risk FX exposure."
        execution_multiplier = 0.50
        trade_allowed = False
    elif carry_avg > 0 and breadth_score >= 60 and stress_score < 35:
        regime = "CARRY RISK-ON"
        playbook = "Carry/risk FX is bid. Favor strong JPY crosses and clean trend continuation."
        execution_multiplier = 1.00
        trade_allowed = True
    elif usd_state == "USD STRONG" and breadth_score >= 45:
        regime = "USD TREND"
        playbook = "USD trend is dominant. Favor clean USD continuation setups."
        execution_multiplier = 0.85
        trade_allowed = True
    elif breadth_score >= 40:
        regime = "SELECTIVE"
        playbook = "FX tape is mixed. Trade only the strongest directional pairs."
        execution_multiplier = 0.65
        trade_allowed = True
    else:
        regime = "CAUTIOUS"
        playbook = "FX breadth is weak. Reduce size and avoid noisy crosses."
        execution_multiplier = 0.50
        trade_allowed = True

    return {
        "regime": regime,
        "playbook": playbook,
        "execution_multiplier": execution_multiplier,
        "trade_allowed": trade_allowed,
        "aud_jpy_24h": aud_jpy,
        "cad_jpy_24h": cad_jpy,
        "eur_usd_24h": eur_usd,
        "gbp_usd_24h": gbp_usd,
        "usd_jpy_24h": usd_jpy,
        "carry_avg_24h": carry_avg,
        "europe_avg_24h": europe_avg,
    }


def calculate_forex_market_cycle(
    regime: Dict[str, Any],
    breadth: Dict[str, Any],
    stress_score: int,
    liquidity: Dict[str, Any],
    usd: Dict[str, Any],
) -> Dict[str, Any]:
    breadth_score = safe_float(breadth.get("score"), 50.0)
    liquidity_state = str(liquidity.get("state", "NEUTRAL")).upper()
    usd_state = str(usd.get("state", "USD MIXED")).upper()
    carry_avg = safe_float(regime.get("carry_avg_24h"), 0.0)

    if stress_score >= 70 or breadth_score < 30 or liquidity_state == "RISK-OFF":
        cycle = "CONTRACTION"
        tone = "risk"
        note = "FX risk appetite is deteriorating. Protect capital and avoid carry exposure."
        icon = "🔴"
    elif carry_avg > 0 and breadth_score >= 55 and liquidity_state == "RISK-ON":
        cycle = "CARRY EXPANSION"
        tone = "good"
        note = "Carry/risk appetite is broadening. Favor liquid trend leaders."
        icon = "🟢"
    elif usd_state in ("USD STRONG", "USD WEAK") and breadth_score >= 45:
        cycle = "USD TREND"
        tone = "good"
        note = "USD direction is the main driver. Favor clean dollar pairs."
        icon = "🟢"
    elif breadth_score >= 40 and stress_score < 60:
        cycle = "CONSOLIDATION"
        tone = "warning"
        note = "FX is tradable but selective. Wait for pair-level confirmation."
        icon = "🟡"
    else:
        cycle = "DISTRIBUTION WATCH"
        tone = "warning"
        note = "Momentum is weakening. Reduce size if risk crosses deteriorate."
        icon = "🟠"

    return {"cycle": cycle, "tone": tone, "note": note, "icon": icon}


def build_forex_opportunity_scanner(df: pd.DataFrame, usd: Dict[str, Any], breadth: Dict[str, Any]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()
    for col in ["1H %", "24H %", "7D %"]:
        work[col] = pd.to_numeric(work.get(col, pd.Series(dtype=float)), errors="coerce").fillna(0.0)

    breadth_score = safe_float(breadth.get("score"), 50.0)
    usd_score = safe_float(usd.get("score"), 50.0)

    rows = []
    for _, row in work.iterrows():
        one_h = safe_float(row.get("1H %"), 0.0)
        day = safe_float(row.get("24H %"), 0.0)
        week = safe_float(row.get("7D %"), 0.0)
        abs_day = abs(day)
        abs_week = abs(week)

        momentum_score = max(0.0, min(40.0, abs_day / 1.2 * 40.0))
        trend_score = max(0.0, min(25.0, abs_week / 3.0 * 25.0))
        continuation_score = max(0.0, min(20.0, abs(one_h) / 0.35 * 20.0))
        breadth_bonus = max(0.0, min(10.0, breadth_score / 10.0))
        usd_bonus = 5.0 if abs(usd_score - 50) >= 12 and row.get("Symbol") in (USD_BASE_SYMBOLS + USD_QUOTE_SYMBOLS) else 0.0

        opportunity_score = round(momentum_score + trend_score + continuation_score + breadth_bonus + usd_bonus, 1)

        if opportunity_score >= 80:
            recommendation = "STRONG WATCH"
        elif opportunity_score >= 65:
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


def build_ai_forex_brief(
    df: pd.DataFrame,
    regime: Dict[str, Any],
    breadth: Dict[str, Any],
    stress_score: int,
    stress_label: str,
    usd: Dict[str, Any],
    market_cycle: Dict[str, Any],
) -> Dict[str, str]:
    regime_name = regime.get("regime", "Unknown")
    tone = regime_tone(regime_name)

    best = "N/A"
    weakest = "N/A"
    if df is not None and not df.empty:
        sorted_df = df.sort_values("24H %", ascending=False, na_position="last")
        best_row = sorted_df.iloc[0]
        weak_row = sorted_df.iloc[-1]
        best = f"{best_row.get('Name')} ({format_pct(best_row.get('24H %'))})"
        weakest = f"{weak_row.get('Name')} ({format_pct(weak_row.get('24H %'))})"

    if tone == "good":
        setup = "trend continuation, liquid majors, and clean carry/risk setups"
        avoid = "thin crosses, late entries, and fighting the dominant USD trend"
    elif tone == "warning":
        setup = "only the clearest directional pairs with clean structure"
        avoid = "noisy crosses, oversized positions, and forcing trades"
    elif tone == "risk":
        setup = "capital protection, smaller size, and only exceptional A+ setups"
        avoid = "new broad carry exposure and averaging into weak pairs"
    else:
        setup = "confirmed setups with clear directional leadership"
        avoid = "forcing trades without confirmation"

    brief = (
        f"Forex Pulse is reading **{regime_name}**. Market cycle is **{market_cycle.get('cycle')}**, "
        f"stress is **{stress_score}/100 ({stress_label})**, breadth is "
        f"**{safe_float(breadth.get('score'), 0):.1f}/100 ({breadth.get('state')})**, "
        f"and USD strength is **{usd.get('state')} ({usd.get('score')}/100)**. "
        f"The strongest pair is **{best}** and the weakest is **{weakest}**. "
        f"Current conditions favor **{setup}**. Avoid **{avoid}**. "
        f"Suggested execution multiplier is **{safe_float(regime.get('execution_multiplier'), 0):.2f}x**."
    )

    return {"brief": brief, "tone": tone, "playbook": str(regime.get("playbook", "No playbook available."))}


def forex_market_clock_card(data_status: Dict[str, Any]) -> None:
    local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    utc_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    provider = str(data_status.get("provider", "yfinance"))
    interval = str(data_status.get("interval", "N/A"))
    period = str(data_status.get("period", "N/A"))

    st.info(
        "🟢 Forex Market Status: 24/5  |  "
        f"Last Refresh: {local_time}  |  UTC: {utc_time}  |  "
        f"Provider: {provider}  |  Lookback: {period}  |  Interval: {interval}"
    )


def display_price_table(title: str, df: pd.DataFrame, max_rows: int | None = None) -> None:
    st.markdown(f"#### {title}")
    if df is None or df.empty:
        st.info("No forex data available yet.")
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

    st.dataframe(styled, width="stretch", hide_index=True, height=320)


def build_forex_playbook_cards(
    regime: Dict[str, Any],
    breadth: Dict[str, Any],
    stress_score: int,
    usd: Dict[str, Any],
    liquidity: Dict[str, Any],
    market_cycle: Dict[str, Any],
) -> List[Dict[str, Any]]:
    regime_name = str(regime.get("regime", "Unknown"))

    if regime_name == "RISK-OFF":
        allowed = "USD / JPY safe-haven focus"
        avoid = "Broad carry trades"
        setup = "Only exceptional A+ setups"
        risk = "Defensive"
        tone = "risk"
    elif regime_name in ("CAUTIOUS", "SELECTIVE"):
        allowed = "Majors and strongest pairs"
        avoid = "Noisy crosses"
        setup = "Relative-strength trend continuation"
        risk = "Reduced"
        tone = "warning"
    else:
        allowed = "Qualified trend leaders"
        avoid = "Late entries and thin crosses"
        setup = "Breakouts / pullbacks / trend continuation"
        risk = "Normal"
        tone = "good"

    return [
        {
            "title": "Forex Playbook",
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
            "title": "USD & Liquidity",
            "tone": str(liquidity.get("tone", "neutral")),
            "rows": [
                ("USD Strength", f"{usd.get('state')} ({usd.get('score')}/100)"),
                ("Liquidity Proxy", f"{liquidity.get('state')} ({liquidity.get('score')}/100)"),
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
    """Publish Forex Pulse state for Scanner / Quant Executor integration."""

    asset_class = "forex"
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
        "label": "Forex Pulse",
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
        "source": "forex_pulse_signal_bus_v1",
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
    inject_forex_pulse_css()

    st.title("💱 Forex Pulse")
    st.caption(
        "Live forex regime dashboard for USD strength, majors, crosses, carry risk, breadth, stress, and trade bias."
    )
    st.caption(
        "Build: Forex Pulse v1.1 STABLE — Market Clock · USD Strength · FX Liquidity Proxy · Opportunity Scanner · Forex Playbook · Market Cycle"
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        refresh = st.button("Refresh Forex Pulse Data", width="stretch")
    with c2:
        period = st.selectbox("Lookback", ["7d", "14d", "30d"], index=0)
    with c3:
        interval = st.selectbox("Interval", ["1h", "2h", "4h", "1d"], index=0)

    if refresh:
        st.cache_data.clear()
        st.rerun()

    if yf is None:
        st.error("yfinance is not available in this environment. Install yfinance to load live forex data.")
        return

    symbols = tuple(row["Symbol"] for row in FOREX_UNIVERSE)

    with st.spinner("Loading forex market data..."):
        forex_df = load_forex_prices(symbols, period=period, interval=interval)

    if forex_df.empty:
        st.error("Forex data could not be loaded. Check internet/data access and try again.")
        return

    forex_market_clock_card({"provider": "yfinance", "period": period, "interval": interval})

    usd = calculate_usd_strength(forex_df)
    breadth = calculate_forex_breadth(forex_df)
    stress_score, stress_label = calculate_forex_stress(forex_df, breadth, usd)
    liquidity = calculate_forex_liquidity_proxy(breadth, stress_score, usd)
    regime = build_forex_regime(forex_df, breadth, stress_score, usd)
    market_cycle = calculate_forex_market_cycle(regime, breadth, stress_score, liquidity, usd)
    opportunity_df = build_forex_opportunity_scanner(forex_df, usd, breadth)
    ai_brief = build_ai_forex_brief(forex_df, regime, breadth, stress_score, stress_label, usd, market_cycle)

    # Session exports for future Scanner/Quant Executor integration.
    st.session_state["forex_pulse_regime"] = regime["regime"]
    st.session_state["forex_pulse_stress_score"] = int(stress_score)
    st.session_state["forex_pulse_stress_label"] = stress_label
    st.session_state["forex_pulse_breadth_score"] = float(breadth["score"])
    st.session_state["forex_pulse_breadth_state"] = breadth["state"]
    st.session_state["forex_pulse_trade_allowed"] = bool(regime["trade_allowed"])
    st.session_state["forex_pulse_execution_multiplier"] = float(regime["execution_multiplier"])
    st.session_state["forex_pulse_usd_strength"] = str(usd["state"])
    st.session_state["forex_pulse_liquidity_proxy"] = str(liquidity["state"])
    st.session_state["forex_pulse_market_cycle"] = str(market_cycle["cycle"])


    forex_pulse_bus_payload = publish_multi_asset_signal_bus(
        df=forex_df,
        regime=regime,
        breadth=breadth,
        stress_score=stress_score,
        stress_label=stress_label,
        opportunity_df=opportunity_df,
        extra={"usd_strength": usd.get("state"), "usd_score": usd.get("score"), "liquidity_state": liquidity.get("state"), "liquidity_score": liquidity.get("score"), "market_cycle": market_cycle.get("cycle")},
    )

    command_html = (
        f'<div style="display:inline-flex;align-items:center;gap:0.55rem;background:{tone_palette(regime_tone(regime["regime"]))[0]};'
        f'border:1px solid {tone_palette(regime_tone(regime["regime"]))[1]};'
        f'color:{tone_palette(regime_tone(regime["regime"]))[2]};border-radius:999px;padding:0.35rem 0.75rem;'
        f'font-weight:800;margin:0.25rem 0 0.75rem 0;">'
        f'<span>{regime_icon(regime["regime"])}</span>'
        f'<span>Forex Command Status: {html.escape(regime["regime"])}</span>'
        f'<span style="color:#64748b;font-weight:650;">Stress {stress_score}/100</span>'
        f'<span style="color:#64748b;font-weight:650;">Breadth {breadth["score"]:.1f}/100</span>'
        '</div>'
    )
    st.markdown(command_html, unsafe_allow_html=True)

    st.subheader("🤖 AI Forex Brief")
    st.caption("What it means: 30-second read of the forex tape before looking at the full dashboard.")

    if ai_brief["tone"] == "good":
        st.success(ai_brief["brief"])
    elif ai_brief["tone"] == "warning":
        st.warning(ai_brief["brief"])
    elif ai_brief["tone"] == "risk":
        st.error(ai_brief["brief"])
    else:
        st.info(ai_brief["brief"])
    st.caption(ai_brief["playbook"])

    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.divider()
        st.subheader("🚦 Forex Stress Dashboard")
        st.caption("What it means: Measures whether FX conditions are calm, mixed, or risk-off.")

        metric_grid([
            {"label": "Stress Score", "value": f"{stress_score}/100", "detail": "Overall FX risk.", "tone": stress_tone(stress_score)},
            {"label": "Stress State", "value": stress_label, "detail": "Current FX condition.", "tone": stress_tone(stress_score)},
            {"label": "Forex Regime", "value": f"{regime_icon(regime['regime'])} {regime['regime']}", "detail": "Trading mode.", "tone": regime_tone(regime["regime"])},
            {"label": "Execution Multiplier", "value": f"{regime['execution_multiplier']:.2f}x", "detail": "Position-size adjustment.", "tone": "info"},
        ])

        if stress_score >= 70:
            st.error("Forex Stress Interpretation: defensive posture. Avoid broad carry/risk FX exposure.")
        elif stress_score >= 40:
            st.warning("Forex Stress Interpretation: selective posture. Trade only clean directional leaders.")
        else:
            st.success("Forex Stress Interpretation: conditions are calm enough for qualified setups.")

        help_text("Forex stress combines carry crosses, USD behavior, majors, and breadth deterioration.")

        st.divider()
        st.subheader("📊 Forex Breadth Engine")
        st.caption("What it means: Measures how many FX pairs are participating in the move.")

        metric_grid([
            {"label": "Breadth Score", "value": f"{breadth['score']:.1f}/100", "detail": "Participation strength.", "tone": breadth_tone(breadth["score"])},
            {"label": "Breadth State", "value": breadth["state"], "detail": "FX participation.", "tone": breadth_tone(breadth["score"])},
            {"label": "Advancers", "value": f"{breadth['advancing']}/{breadth['total']}", "detail": "Pairs moving higher.", "tone": "info"},
            {"label": "Risk Cross Advance %", "value": f"{breadth['risk_advance_pct']:.0f}%", "detail": "Carry/risk participation.", "tone": "good" if breadth["risk_advance_pct"] >= 60 else "warning" if breadth["risk_advance_pct"] >= 40 else "risk"},
            {"label": "Average Move", "value": format_pct(breadth["average_move"]), "detail": "Average 24h move.", "tone": "good" if breadth["average_move"] > 0 else "risk" if breadth["average_move"] < -0.5 else "warning"},
        ])

        if breadth["score"] < 40:
            st.error("Breadth Interpretation: weak participation. FX exposure should be reduced.")
        elif breadth["score"] < 60:
            st.warning("Breadth Interpretation: mixed participation. Pair selection matters.")
        else:
            st.success("Breadth Interpretation: healthy participation. FX tape supports qualified setups.")

        help_text("Forex moves are more trustworthy when USD direction, majors, and risk crosses confirm together.")

        st.divider()
        st.subheader("📈 Leadership & Damage Report")
        st.caption("What it means: Shows strongest and weakest FX pairs in the current tape.")

        strongest = forex_df.sort_values("24H %", ascending=False, na_position="last").head(5)
        weakest = forex_df.sort_values("24H %", ascending=True, na_position="last").head(5)

        l1, l2 = st.columns(2)
        with l1:
            display_price_table("Strongest 24H", strongest, max_rows=5)
        with l2:
            display_price_table("Weakest 24H", weakest, max_rows=5)

        st.divider()
        st.subheader("🔎 Forex Opportunity Scanner")
        st.caption(
            "What it means: Ranks the loaded FX universe by momentum, trend, "
            "USD direction, breadth support, and directional clarity."
        )

        # determine top score for UI-grade mapping
        top_score_global = 0.0
        if opportunity_df.empty:
            st.info("No opportunity scores available yet.")
        else:
            try:
                top_score_global = safe_float(opportunity_df.iloc[0].get("Opportunity Score"), 0.0)
            except Exception:
                top_score_global = 0.0
        
            top_opportunities = opportunity_df.head(8).copy()
            display_cols = [
                "Rank",
                "Name",
                "Symbol",
                "Group",
                "24H %",
                "7D %",
                "Directional Bias",
                "Opportunity Score",
                "Recommendation",
            ]
            styled_opportunities = top_opportunities[display_cols].style.map(
                style_pct,
                subset=["24H %", "7D %"],
            )
            st.dataframe(styled_opportunities, width="stretch", hide_index=True, height=320)

            best_opportunity = top_opportunities.iloc[0].to_dict()
            top_score = safe_float(best_opportunity.get("Opportunity Score"), 0.0)
            top_recommendation = str(best_opportunity.get("Recommendation", "AVOID"))

            # UI-only: if research says AVOID but market/regime allows trading, present as Pending Confirmation
            display_recommendation = top_recommendation
            try:
                if str(top_recommendation).strip().upper() == "AVOID" and regime.get("trade_allowed"):
                    display_recommendation = "Pending Confirmation"
            except Exception:
                display_recommendation = top_recommendation

            # Compute an institutional grade for the top opportunity (UI-only mapping)
            institutional_grade = "BLOCKED"
            if regime.get("trade_allowed"):
                institutional_grade = "READY" if top_score >= 65 else "PENDING CONFIRMATION"

            if top_score >= 65:
                st.success(
                    f"Best Opportunity: {best_opportunity.get('Name')} ({best_opportunity.get('Symbol')}) — "
                    f"Bias {best_opportunity.get('Directional Bias')} — "
                    f"Score {top_score:.1f}/100 — {display_recommendation}"
                )
            else:
                st.warning(
                    "No Qualified Opportunities Currently Available\n\n"
                    f"Highest Score: {top_score:.1f}/100 — "
                    f"{best_opportunity.get('Name')} "
                    f"({best_opportunity.get('Symbol')})\n\n"
                    "No pairs currently meet the minimum qualification threshold."
                )

        help_text("This is a ranking engine, not an order signal. Use it with chart structure and risk controls.")

    with right_col:
        st.divider()
        st.subheader("🎯 Forex Decision Center")
        st.caption("What it means: Converts FX conditions into practical trading guidance.")

        # Institutional Grade derived from regime permission + top opportunity score (UI-only)
        if regime["trade_allowed"]:
            institutional_grade = "READY" if top_score_global >= 65 else "PENDING CONFIRMATION"
        else:
            institutional_grade = "BLOCKED"

        metric_grid([
            {"label": "Regime", "value": f"{regime_icon(regime['regime'])} {regime['regime']}", "detail": regime["playbook"], "tone": regime_tone(regime["regime"])},
            {"label": "USD Strength", "value": usd["state"], "detail": f"{usd['score']}/100", "tone": usd["tone"]},
            {"label": "AUD/JPY 24H", "value": format_pct(regime["aud_jpy_24h"]), "detail": "Carry/risk barometer.", "tone": "good" if regime["aud_jpy_24h"] > 0 else "risk" if regime["aud_jpy_24h"] < -0.5 else "warning"},
            {"label": "USD/JPY 24H", "value": format_pct(regime["usd_jpy_24h"]), "detail": "Dollar-yen / rates pulse.", "tone": "good" if regime["usd_jpy_24h"] > 0 else "risk" if regime["usd_jpy_24h"] < -0.5 else "warning"},
            {"label": "Carry Avg 24H", "value": format_pct(regime["carry_avg_24h"]), "detail": "AUDJPY + CADJPY.", "tone": "good" if regime["carry_avg_24h"] > 0 else "risk" if regime["carry_avg_24h"] < -0.5 else "warning"},
            {"label": "Trade Allowed", "value": "YES" if regime["trade_allowed"] else "NO", "detail": "Forex scanner permission.", "tone": "good" if regime["trade_allowed"] else "risk"},
            {"label": "Institutional Grade", "value": institutional_grade, "detail": "UI grade: readiness for capital deployment.", "tone": "good" if institutional_grade == "READY" else "warning" if "PENDING" in institutional_grade else "risk"},
            {"label": "Market Cycle", "value": f"{market_cycle['icon']} {market_cycle['cycle']}", "detail": market_cycle["note"], "tone": market_cycle["tone"]},
            {"label": "Liquidity Proxy", "value": liquidity["state"], "detail": f"{liquidity['score']}/100", "tone": liquidity["tone"]},
        ])

        if regime["trade_allowed"]:
            st.info(regime["playbook"])
        else:
            st.error(regime["playbook"])

        # Show more: concise rationale and conditional change triggers (UI-only explanatory text)
        with st.expander("Show more", expanded=False):
            st.markdown(f"**Why:** {regime['playbook']} — Stress {stress_score}/100, Breadth {breadth['score']:.1f}/100.")
            st.markdown(f"**What to do:** { 'Follow desk action plan and confirm setups' if institutional_grade == 'READY' else 'Wait for qualified setups or confirmation from Scanner/Research' }.")
            st.markdown(f"**What would change this recommendation:** A qualified opportunity with score >= 65 or a change in regime/trade permission would move Institutional Grade to READY.")

        if regime["regime"] == "RISK-OFF":
            action_tone = "risk"
            exposure = "25% - 50%"
            preferred = "USD / JPY defensive pairs"
            avoid = "Broad carry exposure"
            aggression = "Low"
        elif regime["regime"] in ("CAUTIOUS", "SELECTIVE"):
            action_tone = "warning"
            exposure = "40% - 70%"
            preferred = "Majors / strongest directional pairs"
            avoid = "Noisy crosses"
            aggression = "Moderate"
        else:
            action_tone = "good"
            exposure = "70% - 100%"
            preferred = "Trend leaders"
            avoid = "Late entries and thin crosses"
            aggression = "Normal"

        list_grid([
            {
                "title": "Action Plan",
                "tone": action_tone,
                "rows": [
                    ("1", "Confirm USD direction first"),
                    ("2", "Check JPY and carry crosses"),
                    ("3", "Favor liquid pairs with clean trend"),
                    ("4", "Reduce size when breadth weakens"),
                ],
            },
            {
                "title": "Trade Bias",
                "tone": action_tone,
                "rows": [
                    ("Exposure", exposure),
                    ("Preferred Setup", preferred),
                    ("Avoid", avoid),
                    ("Aggression", aggression),
                    ("Position Size", f"{regime['execution_multiplier']:.2f}x"),
                ],
            },
        ])

        st.subheader("📘 Forex Playbook")
        st.caption(
            "What it means: Converts regime, USD strength, liquidity, breadth, "
            "stress, and market cycle into a practical forex playbook."
        )
        list_grid(build_forex_playbook_cards(regime, breadth, stress_score, usd, liquidity, market_cycle))
        st.info(market_cycle["note"])
        st.caption(liquidity["note"])

        help_text("Forex Pulse is informational only. It does not place trades and does not route orders.")

        st.divider()
        st.subheader("📌 Forex Snapshot")
        st.caption("What it means: Quick read of majors, crosses, and carry/risk pairs.")

        major_rows = forex_df[forex_df["Symbol"].isin(MAJOR_SYMBOLS)].copy()
        risk_rows = forex_df[forex_df["Symbol"].isin(RISK_SYMBOLS)].copy()
        cross_rows = forex_df[~forex_df["Symbol"].isin(MAJOR_SYMBOLS)].copy()

        display_price_table("Major FX Pairs", major_rows, max_rows=8)
        display_price_table("Carry / Risk Crosses", risk_rows.sort_values("24H %", ascending=False, na_position="last"), max_rows=8)
        display_price_table("FX Crosses", cross_rows.sort_values("24H %", ascending=False, na_position="last"), max_rows=8)

        st.divider()
        st.subheader("📚 Reference Center")
        st.caption("What it means: Diagnostic data used to validate the current forex read.")

        with st.expander("Forex Regime Details", expanded=False):
            details_df = pd.DataFrame([
                {"Metric": "Regime", "Reading": regime["regime"]},
                {"Metric": "Stress", "Reading": f"{stress_score}/100 — {stress_label}"},
                {"Metric": "Breadth", "Reading": f"{breadth['score']:.1f}/100 — {breadth['state']}"},
                {"Metric": "USD Strength", "Reading": f"{usd['state']} — {usd['score']}/100"},
                {"Metric": "Liquidity Proxy", "Reading": f"{liquidity['state']} — {liquidity['score']}/100"},
                {"Metric": "Market Cycle", "Reading": f"{market_cycle['cycle']} — {market_cycle['note']}"},
                {"Metric": "AUD/JPY 24H", "Reading": format_pct(regime["aud_jpy_24h"])},
                {"Metric": "CAD/JPY 24H", "Reading": format_pct(regime["cad_jpy_24h"])},
                {"Metric": "EUR/USD 24H", "Reading": format_pct(regime["eur_usd_24h"])},
                {"Metric": "GBP/USD 24H", "Reading": format_pct(regime["gbp_usd_24h"])},
                {"Metric": "Trade Allowed", "Reading": "YES" if regime["trade_allowed"] else "NO"},
                {"Metric": "Execution Multiplier", "Reading": f"{regime['execution_multiplier']:.2f}x"},
            ])
            st.dataframe(details_df, width="stretch", hide_index=True)

        with st.expander("Data Status", expanded=False):
            st.write({
                "provider": "yfinance",
                "period": period,
                "interval": interval,
                "assets_loaded": int(forex_df.shape[0]),
                "last_refresh_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_refresh_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })


if __name__ == "__main__":
    st.set_page_config(page_title="Forex Pulse", page_icon="💱", layout="wide")
    run_page()
