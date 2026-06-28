# =========================================================
# ₿ CRYPTO PULSE PAGE — v2.0
# JFBP Quant Desk
# Crypto Regime + Breadth + Stress + Leadership Command Center
# v2.0: Market Clock + BTC Leadership Score + Stablecoin Liquidity Proxy
#       Opportunity Scanner + Crypto Playbook + Crypto Market Cycle
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

CRYPTO_UNIVERSE = [
    {"Symbol": "BTC-USD", "Name": "Bitcoin", "Group": "Core"},
    {"Symbol": "ETH-USD", "Name": "Ethereum", "Group": "Core"},
    {"Symbol": "SOL-USD", "Name": "Solana", "Group": "Layer 1"},
    {"Symbol": "BNB-USD", "Name": "BNB", "Group": "Exchange / L1"},
    {"Symbol": "XRP-USD", "Name": "XRP", "Group": "Payments"},
    {"Symbol": "ADA-USD", "Name": "Cardano", "Group": "Layer 1"},
    {"Symbol": "AVAX-USD", "Name": "Avalanche", "Group": "Layer 1"},
    {"Symbol": "LINK-USD", "Name": "Chainlink", "Group": "Infrastructure"},
    {"Symbol": "DOGE-USD", "Name": "Dogecoin", "Group": "Meme / Beta"},
    {"Symbol": "MATIC-USD", "Name": "Polygon", "Group": "Scaling"},
    {"Symbol": "DOT-USD", "Name": "Polkadot", "Group": "Layer 1"},
    {"Symbol": "LTC-USD", "Name": "Litecoin", "Group": "Legacy"},
]

CORE_SYMBOLS = ["BTC-USD", "ETH-USD"]
ALT_SYMBOLS = [row["Symbol"] for row in CRYPTO_UNIVERSE if row["Symbol"] not in CORE_SYMBOLS]


# =========================================================
# RESPONSIVE UI HELPERS
# =========================================================

def inject_crypto_pulse_css() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.15rem;
                padding-bottom: 1.9rem;
                max-width: 1500px;
            }

            h1, h2, h3 {
                margin-top: 0.42rem !important;
                margin-bottom: 0.20rem !important;
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

            .crypto-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
                gap: 0.55rem;
                margin: 0.20rem 0 0.42rem 0;
                width: 100%;
            }

            .crypto-briefing-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.55rem;
                margin: 0.20rem 0 0.42rem 0;
                width: 100%;
            }

            .crypto-briefing-grid .crypto-card {
                display: flex;
                flex-direction: column;
                min-height: 122px;
                height: 100%;
            }

            .crypto-card {
                border: 1px solid;
                border-radius: 14px;
                padding: 0.66rem 0.76rem;
                min-width: 0;
                width: 100%;
                box-sizing: border-box;
                overflow: hidden;
            }

            .crypto-label {
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #64748b;
                font-weight: 800;
                margin-bottom: 0.28rem;
                line-height: 1.25;
            }

            .crypto-value {
                font-size: clamp(1.05rem, 2.2vw, 1.45rem);
                line-height: 1.15;
                font-weight: 850;
                white-space: normal;
                word-break: normal;
            }

            .crypto-detail {
                font-size: 0.78rem;
                color: #64748b;
                margin-top: 0.35rem;
                line-height: 1.35;
            }

            .crypto-list-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
                gap: 0.62rem;
                margin: 0.22rem 0 0.46rem 0;
            }

            .crypto-list-card {
                border: 1px solid;
                border-radius: 16px;
                padding: 0.80rem 0.92rem;
                min-width: 0;
                overflow: hidden;
            }

            .crypto-list-title {
                font-size: 1.02rem;
                font-weight: 850;
                color: #1f2937;
                margin-bottom: 0.48rem;
                line-height: 1.2;
            }

            .crypto-list-row {
                display: grid;
                grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.35fr);
                gap: 0.65rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.28);
                padding: 0.42rem 0;
            }

            .crypto-list-row:last-child {
                border-bottom: none;
            }

            .crypto-list-label {
                color: #64748b;
                font-weight: 750;
                line-height: 1.28;
            }

            .crypto-list-value {
                color: #1f2937;
                font-weight: 900;
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

                .crypto-grid,
                .crypto-list-grid {
                    grid-template-columns: 1fr;
                }

                .crypto-list-row {
                    grid-template-columns: 1fr;
                    gap: 0.16rem;
                }

                h1 { font-size: 1.65rem !important; }
            }

            .crypto-banner {
                border: 1px solid;
                border-radius: 16px;
                padding: 0.72rem 0.85rem;
                margin: 0.24rem 0 0.46rem 0;
                box-sizing: border-box;
            }

            .crypto-banner-title {
                font-size: 0.78rem;
                font-weight: 850;
                letter-spacing: 0.045em;
                text-transform: uppercase;
                margin-bottom: 0.2rem;
            }

            .crypto-banner-body {
                font-size: 0.95rem;
                line-height: 1.38;
                font-weight: 720;
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
    pieces = ['<div class="crypto-grid">']

    for card in cards:
        background, border, value_color = tone_palette(str(card.get("tone", "neutral")))
        label = html.escape(str(card.get("label", "")))
        value = html.escape(str(card.get("value", "")))
        detail = html.escape(str(card.get("detail", "")))
        detail_html = f'<div class="crypto-detail">{detail}</div>' if detail else ""
        pieces.append(
            f'<div class="crypto-card" style="background:{background};border-color:{border};">'
            f'<div class="crypto-label">{label}</div>'
            f'<div class="crypto-value" style="color:{value_color};">{value}</div>'
            f'{detail_html}'
            f'</div>'
        )

    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def briefing_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="crypto-briefing-grid">']

    for card in cards:
        background, border, value_color = tone_palette(str(card.get("tone", "neutral")))
        label = html.escape(str(card.get("label", "")))
        value = html.escape(str(card.get("value", "")))
        detail = html.escape(str(card.get("detail", "")))
        detail_html = f'<div class="crypto-detail">{detail}</div>' if detail else ""
        pieces.append(
            f'<div class="crypto-card" style="background:{background};border-color:{border};">'
            f'<div class="crypto-label">{label}</div>'
            f'<div class="crypto-value" style="color:{value_color};">{value}</div>'
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
        <div class="crypto-banner" style="background:{background};border-color:{border};">
            <div class="crypto-banner-title" style="color:{value_color};">{html.escape(title)}</div>
            <div class="crypto-banner-body" style="color:{value_color};font-weight:{body_weight};">{html.escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def list_grid(cards: List[Dict[str, Any]]) -> None:
    pieces = ['<div class="crypto-list-grid">']

    for card in cards:
        background, border, _ = tone_palette(str(card.get("tone", "neutral")))
        title = html.escape(str(card.get("title", "")))
        rows_html = ""

        for label, value in card.get("rows", []):
            rows_html += (
                '<div class="crypto-list-row">'
                f'<div class="crypto-list-label">{html.escape(str(label))}</div>'
                f'<div class="crypto-list-value">{html.escape(str(value))}</div>'
                '</div>'
            )

        pieces.append(
            f'<div class="crypto-list-card" style="background:{background};border-color:{border};">'
            f'<div class="crypto-list-title">{title}</div>'
            f'{rows_html}'
            f'</div>'
        )

    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)


def table_height(row_count: int, max_height: int = 320) -> int:
    return min(max_height, max(132, 56 + row_count * 32))


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
def load_crypto_prices(symbols: Tuple[str, ...], period: str = "7d", interval: str = "1h") -> pd.DataFrame:
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

    for asset in CRYPTO_UNIVERSE:
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
            "1H %": round(one_hour, 2),
            "24H %": round(day, 2),
            "7D %": round(week, 2),
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


def calculate_crypto_breadth(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty or "24H %" not in df.columns:
        return {
            "score": 50.0,
            "state": "Unknown",
            "advancing": 0,
            "declining": 0,
            "total": 0,
            "average_move": 0.0,
            "alt_advance_pct": 0.0,
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
            "alt_advance_pct": 0.0,
        }

    total = len(valid)
    advancing = int((valid["24H %"] > 0).sum())
    declining = int((valid["24H %"] < 0).sum())
    average_move = float(valid["24H %"].mean())
    advance_pct = advancing / total * 100 if total else 0.0

    alt_valid = valid[valid["Symbol"].isin(ALT_SYMBOLS)]
    alt_advance_pct = 0.0
    if not alt_valid.empty:
        alt_advance_pct = float((alt_valid["24H %"] > 0).sum() / len(alt_valid) * 100)

    score = round((advance_pct * 0.65) + (max(0.0, average_move + 5.0) / 10.0 * 35.0), 1)
    score = max(0.0, min(100.0, score))

    if score >= 70:
        state = "Broad Crypto Bid"
    elif score >= 55:
        state = "Constructive"
    elif score >= 40:
        state = "Mixed / Selective"
    elif score >= 25:
        state = "Weak Breadth"
    else:
        state = "Broad Crypto Damage"

    return {
        "score": score,
        "state": state,
        "advancing": advancing,
        "declining": declining,
        "total": total,
        "average_move": average_move,
        "alt_advance_pct": alt_advance_pct,
    }


def calculate_crypto_stress(df: pd.DataFrame, breadth: Dict[str, Any]) -> Tuple[int, str]:
    btc = get_move(df, "BTC-USD")
    eth = get_move(df, "ETH-USD")
    sol = get_move(df, "SOL-USD")

    alt_moves = []
    if df is not None and not df.empty:
        alt_rows = df[df["Symbol"].isin(ALT_SYMBOLS)].copy()
        alt_moves = pd.to_numeric(alt_rows.get("24H %", pd.Series(dtype=float)), errors="coerce").dropna().tolist()

    alt_avg = sum(alt_moves) / len(alt_moves) if alt_moves else 0.0
    score = 0.0

    if btc is not None and btc < 0:
        score += min(abs(btc) * 8, 32)
    if eth is not None and eth < 0:
        score += min(abs(eth) * 7, 25)
    if sol is not None and sol < 0:
        score += min(abs(sol) * 4, 12)
    if alt_avg < 0:
        score += min(abs(alt_avg) * 5, 18)

    breadth_score = safe_float(breadth.get("score"), 50.0)
    if breadth_score < 25:
        score += 18
    elif breadth_score < 40:
        score += 12
    elif breadth_score < 55:
        score += 6

    score = int(max(0, min(100, round(score))))

    if score >= 80:
        label = "Severe Crypto Stress"
    elif score >= 60:
        label = "High Crypto Stress"
    elif score >= 40:
        label = "Moderate Crypto Stress"
    elif score >= 20:
        label = "Low Crypto Stress"
    else:
        label = "Calm Crypto Tape"

    return score, label


def regime_tone(regime: str) -> str:
    key = str(regime or "").upper().strip()
    if key in ("RISK-OFF", "DEFENSIVE"):
        return "risk"
    if key in ("SELECTIVE", "CAUTIOUS"):
        return "warning"
    if key in ("RISK-ON", "ALTCOIN RISK-ON"):
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


def build_crypto_regime(df: pd.DataFrame, breadth: Dict[str, Any], stress_score: int) -> Dict[str, Any]:
    btc = get_move(df, "BTC-USD") or 0.0
    eth = get_move(df, "ETH-USD") or 0.0

    alt_rows = df[df["Symbol"].isin(ALT_SYMBOLS)].copy() if df is not None and not df.empty else pd.DataFrame()
    alt_avg = 0.0
    if not alt_rows.empty:
        alt_avg = float(pd.to_numeric(alt_rows["24H %"], errors="coerce").dropna().mean())
        if math.isnan(alt_avg):
            alt_avg = 0.0

    breadth_score = safe_float(breadth.get("score"), 50.0)
    eth_vs_btc = eth - btc
    alt_vs_btc = alt_avg - btc

    if stress_score >= 70 or breadth_score < 30:
        regime = "RISK-OFF"
        playbook = "Protect capital. Avoid new high-beta crypto entries."
        execution_multiplier = 0.50
        buy_allowed = False
    elif btc > 0 and eth > btc and alt_avg > btc and breadth_score >= 60:
        regime = "ALTCOIN RISK-ON"
        playbook = "Altcoin leadership is expanding. Favor leaders only."
        execution_multiplier = 1.00
        buy_allowed = True
    elif btc > 0 and eth >= 0 and breadth_score >= 55:
        regime = "RISK-ON"
        playbook = "Core crypto trend is constructive. Normal qualified setups allowed."
        execution_multiplier = 0.90
        buy_allowed = True
    elif breadth_score >= 40:
        regime = "SELECTIVE"
        playbook = "Mixed crypto tape. Trade only strongest relative-strength coins."
        execution_multiplier = 0.65
        buy_allowed = True
    else:
        regime = "CAUTIOUS"
        playbook = "Crypto breadth is weak. Reduce size and avoid weak altcoins."
        execution_multiplier = 0.50
        buy_allowed = True

    return {
        "regime": regime,
        "playbook": playbook,
        "execution_multiplier": execution_multiplier,
        "buy_allowed": buy_allowed,
        "btc_24h": btc,
        "eth_24h": eth,
        "alt_avg_24h": alt_avg,
        "eth_vs_btc": eth_vs_btc,
        "alt_vs_btc": alt_vs_btc,
    }


def build_ai_crypto_brief(df: pd.DataFrame, regime: Dict[str, Any], breadth: Dict[str, Any], stress_score: int, stress_label: str) -> Dict[str, str]:
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
        setup = "trend continuation, relative-strength leaders, and selective breakout setups"
        avoid = "late entries in extended coins or low-liquidity laggards"
    elif tone == "warning":
        setup = "only the strongest coins with clean structure"
        avoid = "weak altcoins, oversized positions, and chasing intraday spikes"
    elif tone == "risk":
        setup = "capital protection, cash, and only exceptional A+ setups"
        avoid = "new broad altcoin exposure and averaging down weak coins"
    else:
        setup = "confirmed setups with clear leadership"
        avoid = "forcing trades without confirmation"

    brief = (
        f"Crypto Pulse is reading **{regime_name}**. Stress is **{stress_score}/100 ({stress_label})**, "
        f"breadth is **{safe_float(breadth.get('score'), 0):.1f}/100 ({breadth.get('state')})**, "
        f"BTC is **{format_pct(regime.get('btc_24h'))}**, ETH is **{format_pct(regime.get('eth_24h'))}**, "
        f"and the average altcoin move is **{format_pct(regime.get('alt_avg_24h'))}**. "
        f"The strongest name is **{best}** and the weakest is **{weakest}**. "
        f"Current conditions favor **{setup}**. Avoid **{avoid}**. "
        f"Suggested execution multiplier is **{safe_float(regime.get('execution_multiplier'), 0):.2f}x**."
    )

    return {
        "brief": brief,
        "tone": tone,
        "playbook": str(regime.get("playbook", "No playbook available.")),
    }


def display_price_table(title: str, df: pd.DataFrame, max_rows: int | None = None) -> None:
    st.markdown(f"#### {title}")
    if df is None or df.empty:
        st.info("No crypto data available yet.")
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



# =========================================================
# v2.0 CRYPTO INTELLIGENCE HELPERS
# =========================================================

def crypto_market_clock_card(data_status: Dict[str, Any]) -> None:
    local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    utc_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    provider = str(data_status.get("provider", "yfinance"))
    interval = str(data_status.get("interval", "N/A"))
    period = str(data_status.get("period", "N/A"))

    st.info(
        f"● OPEN 24/7  |  Refresh {local_time}  |  Provider: {provider}  |  {period} • {interval}"
    )


def calculate_btc_dominance_proxy(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate a practical BTC dominance proxy from the loaded symbols.

    Important: this is not global crypto market-cap dominance. It is a dashboard
    proxy that estimates how dominant BTC is inside the loaded Crypto Pulse universe.
    """

    btc_24h = get_move(df, "BTC-USD") or 0.0
    eth_24h = get_move(df, "ETH-USD") or 0.0

    if df is None or df.empty:
        return {
            "dominance_proxy": 0.0,
            "trend": "Unknown",
            "interpretation": "No crypto data available.",
        }

    work = df.copy()
    work["Price"] = pd.to_numeric(work.get("Price", pd.Series(dtype=float)), errors="coerce")
    clean = work.dropna(subset=["Price"])

    btc_price = safe_float(get_row(clean, "BTC-USD").get("Price"), 0.0)
    total_price_proxy = float(clean["Price"].sum()) if not clean.empty else 0.0
    dominance_proxy = (btc_price / total_price_proxy * 100.0) if total_price_proxy > 0 else 0.0

    alt_rows = df[df["Symbol"].isin(ALT_SYMBOLS)].copy()
    alt_avg = 0.0
    if not alt_rows.empty:
        alt_avg = float(pd.to_numeric(alt_rows["24H %"], errors="coerce").dropna().mean())
        if math.isnan(alt_avg):
            alt_avg = 0.0

    if btc_24h > eth_24h and btc_24h > alt_avg:
        trend = "BTC LEADING"
        interpretation = "BTC is leading the loaded crypto universe. Favor BTC and high-quality core exposure first."
    elif alt_avg > btc_24h and eth_24h >= btc_24h:
        trend = "ALT EXPANSION"
        interpretation = "Altcoins are outperforming BTC. Favor relative-strength leaders only."
    elif eth_24h > btc_24h:
        trend = "ETH LEADING"
        interpretation = "ETH is outperforming BTC. Smart-contract leaders may have better momentum."
    else:
        trend = "MIXED"
        interpretation = "No clear dominance signal. Let breadth and leadership confirm direction."

    return {
        "dominance_proxy": round(dominance_proxy, 2),
        "trend": trend,
        "interpretation": interpretation,
    }


def calculate_stablecoin_liquidity_proxy(regime: Dict[str, Any], breadth: Dict[str, Any], stress_score: int) -> Dict[str, Any]:
    """Proxy stablecoin liquidity using risk appetite and breadth."""

    breadth_score = safe_float(breadth.get("score"), 50.0)
    btc = safe_float(regime.get("btc_24h"), 0.0)
    eth = safe_float(regime.get("eth_24h"), 0.0)
    alt_avg = safe_float(regime.get("alt_avg_24h"), 0.0)

    liquidity_score = (
        (breadth_score * 0.55)
        + (max(0.0, btc + eth + alt_avg + 6.0) / 12.0 * 35.0)
        + max(0.0, 10.0 - stress_score / 10.0)
    )
    liquidity_score = max(0.0, min(100.0, liquidity_score))

    if liquidity_score >= 70 and stress_score < 35:
        state = "RISK-ON"
        tone = "good"
        note = "Liquidity proxy supports crypto risk-taking."
    elif liquidity_score >= 45:
        state = "NEUTRAL"
        tone = "warning"
        note = "Liquidity proxy is mixed. Stay selective."
    else:
        state = "RISK-OFF"
        tone = "risk"
        note = "Liquidity proxy is defensive. Reduce broad altcoin exposure."

    return {
        "score": round(liquidity_score, 1),
        "state": state,
        "tone": tone,
        "note": note,
    }


def calculate_crypto_market_cycle(
    regime: Dict[str, Any],
    breadth: Dict[str, Any],
    stress_score: int,
    liquidity: Dict[str, Any],
    btc_dominance: Dict[str, Any],
) -> Dict[str, Any]:
    """Classify the crypto tape into an intuitive market cycle."""

    btc = safe_float(regime.get("btc_24h"), 0.0)
    eth = safe_float(regime.get("eth_24h"), 0.0)
    alt_avg = safe_float(regime.get("alt_avg_24h"), 0.0)
    breadth_score = safe_float(breadth.get("score"), 50.0)
    liquidity_state = str(liquidity.get("state", "NEUTRAL")).upper()
    dominance_trend = str(btc_dominance.get("trend", "MIXED")).upper()

    if stress_score >= 70 or breadth_score < 30 or liquidity_state == "RISK-OFF":
        cycle = "CONTRACTION"
        tone = "risk"
        note = "Capital protection has priority. Avoid broad high-beta exposure."
        icon = "🔴"
    elif btc > 0 and eth >= 0 and breadth_score >= 55 and liquidity_state == "RISK-ON":
        if alt_avg > btc or dominance_trend == "ALT EXPANSION":
            cycle = "EXPANSION"
            note = "Risk appetite is broadening. Favor liquid relative-strength leaders."
        else:
            cycle = "CORE EXPANSION"
            note = "BTC/ETH are constructive. Let altcoin breadth confirm before getting aggressive."
        tone = "good"
        icon = "🟢"
    elif breadth_score >= 40 and stress_score < 60:
        cycle = "CONSOLIDATION"
        tone = "warning"
        note = "Crypto is tradable but selective. Wait for leadership confirmation."
        icon = "🟡"
    else:
        cycle = "DISTRIBUTION WATCH"
        tone = "warning"
        note = "Momentum is weakening. Reduce size if breadth or BTC trend deteriorates."
        icon = "🟠"

    return {
        "cycle": cycle,
        "tone": tone,
        "note": note,
        "icon": icon,
    }


def build_crypto_opportunity_scanner(df: pd.DataFrame, regime: Dict[str, Any], breadth: Dict[str, Any]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()
    for col in ["1H %", "24H %", "7D %"]:
        work[col] = pd.to_numeric(work.get(col, pd.Series(dtype=float)), errors="coerce").fillna(0.0)

    btc_24h = safe_float(regime.get("btc_24h"), 0.0)
    alt_avg = safe_float(regime.get("alt_avg_24h"), 0.0)
    breadth_score = safe_float(breadth.get("score"), 50.0)

    rows = []
    for _, row in work.iterrows():
        one_h = safe_float(row.get("1H %"), 0.0)
        day = safe_float(row.get("24H %"), 0.0)
        week = safe_float(row.get("7D %"), 0.0)
        rs_btc = day - btc_24h
        rs_alt = day - alt_avg

        momentum_score = max(0.0, min(40.0, (day + 5.0) / 10.0 * 40.0))
        trend_score = max(0.0, min(25.0, (week + 8.0) / 16.0 * 25.0))
        relative_score = max(0.0, min(25.0, (rs_btc + 5.0) / 10.0 * 25.0))
        breadth_bonus = max(0.0, min(10.0, breadth_score / 10.0))
        opportunity_score = round(momentum_score + trend_score + relative_score + breadth_bonus, 1)

        if opportunity_score >= 80 and day > 0 and rs_btc > 0:
            recommendation = "STRONG WATCH"
        elif opportunity_score >= 65 and day > 0:
            recommendation = "WATCH"
        elif opportunity_score >= 50:
            recommendation = "NEUTRAL"
        else:
            recommendation = "AVOID"

        rows.append({
            "Rank": 0,
            "Name": row.get("Name"),
            "Symbol": row.get("Symbol"),
            "Group": row.get("Group"),
            "Price": row.get("Price"),
            "1H %": round(one_h, 2),
            "24H %": round(day, 2),
            "7D %": round(week, 2),
            "RS vs BTC": round(rs_btc, 2),
            "RS vs Alt Basket": round(rs_alt, 2),
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


def build_crypto_playbook_cards(
    regime: Dict[str, Any],
    breadth: Dict[str, Any],
    stress_score: int,
    btc_dominance: Dict[str, Any],
    liquidity: Dict[str, Any],
    market_cycle: Dict[str, Any],
) -> List[Dict[str, Any]]:
    regime_name = str(regime.get("regime", "Unknown"))

    if regime_name == "RISK-OFF":
        allowed = "Cash / BTC only"
        avoid = "Broad altcoins"
        setup = "Only exceptional A+ setups"
        risk = "Defensive"
        tone = "risk"
    elif regime_name in ("CAUTIOUS", "SELECTIVE"):
        allowed = "BTC, ETH, strongest leaders"
        avoid = "Weak coins and laggards"
        setup = "Relative-strength pullbacks"
        risk = "Reduced"
        tone = "warning"
    else:
        allowed = "Qualified leaders"
        avoid = "Extended laggards"
        setup = "Breakouts / trend continuation"
        risk = "Normal"
        tone = "good"

    return [
        {
            "title": "Crypto Playbook",
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
            "title": "Liquidity & Dominance",
            "tone": str(liquidity.get("tone", "neutral")),
            "rows": [
                ("Liquidity Proxy", f"{liquidity.get('state')} ({liquidity.get('score')}/100)"),
                ("BTC Leadership Score", f"{btc_dominance.get('dominance_proxy')}%"),
                ("Dominance Trend", btc_dominance.get("trend", "N/A")),
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
    """Publish Crypto Pulse state for Scanner / Quant Executor integration."""

    asset_class = "crypto"
    extra = extra if isinstance(extra, dict) else {}

    best = {}
    if isinstance(opportunity_df, pd.DataFrame) and not opportunity_df.empty:
        try:
            best = opportunity_df.iloc[0].to_dict()
        except Exception:
            best = {}

    trade_allowed = bool(regime.get("buy_allowed", regime.get("trade_allowed", True)))
    score_value = safe_float(best.get("Opportunity Score"), 0.0) if best else 0.0

    payload = {
        "asset_class": asset_class,
        "label": "Crypto Pulse",
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
        "source": "crypto_pulse_signal_bus_v1",
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
    inject_crypto_pulse_css()

    st.title("₿ Crypto Pulse")
    st.caption(
        "Institutional crypto command center for regime, breadth, leadership, and execution readiness."
    )
    st.caption(
        "Crypto Pulse v2.0 — decision-first layout for market environment, research, execution, and diagnostics."
    )

    st.session_state.setdefault("crypto_pulse_period", "7d")
    st.session_state.setdefault("crypto_pulse_interval", "1h")

    period = str(st.session_state.get("crypto_pulse_period", "7d"))
    interval = str(st.session_state.get("crypto_pulse_interval", "1h"))

    if yf is None:
        st.error("yfinance is not available in this environment. Install yfinance to load live crypto data.")
        return

    symbols = tuple(row["Symbol"] for row in CRYPTO_UNIVERSE)

    with st.spinner("Loading crypto market data..."):
        crypto_df = load_crypto_prices(symbols, period=period, interval=interval)

    if crypto_df.empty:
        st.error("Crypto data could not be loaded. Check internet/data access and try again.")
        return

    breadth = calculate_crypto_breadth(crypto_df)
    stress_score, stress_label = calculate_crypto_stress(crypto_df, breadth)
    regime = build_crypto_regime(crypto_df, breadth, stress_score)
    btc_dominance = calculate_btc_dominance_proxy(crypto_df)
    liquidity = calculate_stablecoin_liquidity_proxy(regime, breadth, stress_score)
    market_cycle = calculate_crypto_market_cycle(regime, breadth, stress_score, liquidity, btc_dominance)
    opportunity_df = build_crypto_opportunity_scanner(crypto_df, regime, breadth)
    ai_brief = build_ai_crypto_brief(crypto_df, regime, breadth, stress_score, stress_label)

    # Session exports for future Scanner/Quant Executor integration.
    st.session_state["crypto_pulse_regime"] = regime["regime"]
    st.session_state["crypto_pulse_stress_score"] = int(stress_score)
    st.session_state["crypto_pulse_stress_label"] = stress_label
    st.session_state["crypto_pulse_breadth_score"] = float(breadth["score"])
    st.session_state["crypto_pulse_breadth_state"] = breadth["state"]
    st.session_state["crypto_pulse_buy_allowed"] = bool(regime["buy_allowed"])
    st.session_state["crypto_pulse_execution_multiplier"] = float(regime["execution_multiplier"])
    st.session_state["crypto_pulse_btc_dominance_proxy"] = float(btc_dominance["dominance_proxy"])
    st.session_state["crypto_pulse_liquidity_proxy"] = str(liquidity["state"])
    st.session_state["crypto_pulse_market_cycle"] = str(market_cycle["cycle"])

    crypto_pulse_bus_payload = publish_multi_asset_signal_bus(
        df=crypto_df,
        regime=regime,
        breadth=breadth,
        stress_score=stress_score,
        stress_label=stress_label,
        opportunity_df=opportunity_df,
        extra={"btc_dominance_trend": btc_dominance.get("trend"), "btc_dominance_proxy": btc_dominance.get("dominance_proxy"), "liquidity_state": liquidity.get("state"), "liquidity_score": liquidity.get("score"), "market_cycle": market_cycle.get("cycle")},
    )

    latest_timestamp = str(crypto_df.get("Timestamp", pd.Series(dtype=str)).dropna().iloc[0]) if not crypto_df.empty and "Timestamp" in crypto_df.columns and not crypto_df["Timestamp"].dropna().empty else "N/A"
    volatility_proxy = 0.0
    if not crypto_df.empty and "24H %" in crypto_df.columns:
        volatility_proxy = float(pd.to_numeric(crypto_df["24H %"], errors="coerce").abs().dropna().mean() or 0.0)

    confidence_score = max(
        0.0,
        min(
            100.0,
            round(
                (safe_float(breadth.get("score"), 50.0) * 0.40)
                + (safe_float(liquidity.get("score"), 50.0) * 0.30)
                + (max(0.0, 100.0 - float(stress_score)) * 0.30),
                1,
            ),
        ),
    )

    if confidence_score >= 80:
        institutional_grade = "A"
    elif confidence_score >= 65:
        institutional_grade = "B"
    elif confidence_score >= 50:
        institutional_grade = "C"
    else:
        institutional_grade = "D"

    btc_leadership_score = safe_float(btc_dominance.get("dominance_proxy"), 0.0)
    trend_strength = max(0.0, min(100.0, round(50.0 + (safe_float(regime.get("btc_24h"), 0.0) + safe_float(regime.get("eth_24h"), 0.0)) * 2.25 + (safe_float(breadth.get("score"), 50.0) - 50.0) * 0.35, 1)))
    momentum_proxy = safe_float(crypto_df["24H %"].mean(), 0.0) if not crypto_df.empty and "24H %" in crypto_df.columns else 0.0

    if regime["regime"] == "RISK-OFF":
        execution_status = "AVOID"
        recommendation_sentence = "Defend capital, keep exposure minimal, and restrict activity to the strongest core assets only."
    elif regime["regime"] in ("CAUTIOUS", "SELECTIVE"):
        execution_status = "WAIT"
        recommendation_sentence = "Stay selective and trade only the cleanest relative-strength setups with disciplined sizing."
    elif regime["regime"] == "ALTCOIN RISK-ON":
        execution_status = "BUY"
        recommendation_sentence = "Crypto leadership is broadening; favor liquid leaders and allow altcoin momentum to confirm entries."
    else:
        execution_status = "HOLD"
        recommendation_sentence = "Conditions are constructive but selective; hold a disciplined bias and wait for high-quality confirmation."

    # Executive Briefing
    section_heading("Executive Briefing", "Immediate read on the crypto tape and the required posture.")
    briefing_grid([
        {"label": "Crypto Regime", "value": regime["regime"], "detail": regime["playbook"], "tone": regime_tone(regime["regime"])},
        {"label": "Risk Level", "value": stress_label, "detail": f"Stress {stress_score}/100", "tone": stress_tone(stress_score)},
        {"label": "Institutional Grade", "value": institutional_grade, "detail": f"Confidence {confidence_score:.1f}/100", "tone": "good" if institutional_grade in ("A", "B") else "warning" if institutional_grade == "C" else "risk"},
        {"label": "Execution Status", "value": execution_status, "detail": "BUY / HOLD / WAIT / AVOID", "tone": "good" if execution_status == "BUY" else "warning" if execution_status in ("HOLD", "WAIT") else "risk"},
        {"label": "BTC Leadership", "value": btc_dominance.get("trend", "MIXED"), "detail": f"Leadership score {btc_leadership_score:.2f}%", "tone": "good" if btc_dominance.get("trend") in ("BTC LEADING", "ALT EXPANSION") else "warning"},
    ])
    institutional_banner("Commander’s Recommendation", recommendation_sentence, tone=regime_tone(regime["regime"]))

    # Executive Summary
    section_heading("Executive Summary", "Compact KPI read for the current crypto tape.")
    summary_confidence_note = "Institutional confidence remains low." if confidence_score < 50 else "Institutional confidence is improving."
    metric_grid([
        {"label": "Market Regime", "value": regime["regime"], "detail": market_cycle["cycle"], "tone": regime_tone(regime["regime"])},
        {"label": "Trend Strength", "value": f"{trend_strength:.1f}/100", "detail": "BTC/ETH and breadth alignment", "tone": "good" if trend_strength >= 65 else "warning" if trend_strength >= 45 else "risk"},
        {"label": "Momentum", "value": format_pct(momentum_proxy), "detail": "Loaded universe average 24H move", "tone": "good" if momentum_proxy > 0 else "warning" if momentum_proxy == 0 else "risk"},
        {"label": "Breadth", "value": f"{breadth['score']:.1f}/100", "detail": breadth["state"], "tone": breadth_tone(breadth["score"])},
        {"label": "Volatility", "value": f"{volatility_proxy:.2f}%", "detail": "Average absolute 24H move", "tone": "warning" if volatility_proxy >= 5 else "neutral"},
        {"label": "Institutional Confidence", "value": f"{confidence_score:.1f}/100", "detail": summary_confidence_note, "tone": "good" if confidence_score >= 70 else "warning" if confidence_score >= 50 else "risk"},
    ])

    # Market Environment
    section_heading("Market Environment", "Macro tape, liquidity, and crypto stress.")
    crypto_market_clock_card({"provider": "yfinance", "period": period, "interval": interval})
    metric_grid([
        {"label": "Market Cycle", "value": market_cycle["cycle"], "detail": market_cycle["note"], "tone": market_cycle["tone"]},
        {"label": "Liquidity Proxy", "value": liquidity["state"], "detail": f"{liquidity['score']}/100", "tone": liquidity["tone"]},
        {"label": "Stress", "value": f"{stress_score}/100", "detail": stress_label, "tone": stress_tone(stress_score)},
        {"label": "BTC Dominance Proxy", "value": f"{btc_leadership_score:.2f}%", "detail": btc_dominance["trend"], "tone": "info"},
    ])

    # Bitcoin Leadership
    section_heading("Bitcoin Leadership", "BTC remains the anchor for the rest of the crypto tape.")
    metric_grid([
        {"label": "BTC 24H", "value": format_pct(regime.get("btc_24h")), "detail": "Core market anchor", "tone": "good" if safe_float(regime.get("btc_24h"), 0.0) > 0 else "risk" if safe_float(regime.get("btc_24h"), 0.0) < -2 else "warning"},
        {"label": "ETH 24H", "value": format_pct(regime.get("eth_24h")), "detail": "Smart-contract leader", "tone": "good" if safe_float(regime.get("eth_24h"), 0.0) > 0 else "risk" if safe_float(regime.get("eth_24h"), 0.0) < -2 else "warning"},
        {"label": "ETH vs BTC", "value": format_pct(regime.get("eth_vs_btc")), "detail": "Relative strength", "tone": "good" if safe_float(regime.get("eth_vs_btc"), 0.0) > 0 else "warning"},
        {"label": "Leadership Trend", "value": btc_dominance.get("trend", "MIXED"), "detail": btc_dominance["interpretation"], "tone": "good" if btc_dominance.get("trend") in ("BTC LEADING", "ALT EXPANSION") else "warning"},
    ])

    # Altcoin Strength
    section_heading("Altcoin Strength", "Relative altcoin participation and leadership quality.")
    alt_rows = crypto_df[crypto_df["Symbol"].isin(ALT_SYMBOLS)].copy()
    alt_top = alt_rows.sort_values("24H %", ascending=False, na_position="last").head(5)
    alt_weak = alt_rows.sort_values("24H %", ascending=True, na_position="last").head(5)
    l1, l2 = st.columns(2)
    with l1:
        display_price_table("Strongest Altcoins", alt_top, max_rows=5)
    with l2:
        display_price_table("Weakest Altcoins", alt_weak, max_rows=5)

    # Market Breadth
    section_heading("Market Breadth", "Participation quality across the loaded crypto universe.")
    metric_grid([
        {"label": "Breadth Score", "value": f"{breadth['score']:.1f}/100", "detail": breadth["state"], "tone": breadth_tone(breadth["score"])},
        {"label": "Advancers", "value": f"{breadth['advancing']}/{breadth['total']}", "detail": "Symbols moving higher", "tone": "info"},
        {"label": "Decliners", "value": f"{breadth['declining']}/{breadth['total']}", "detail": "Symbols moving lower", "tone": "warning" if breadth['declining'] else "neutral"},
        {"label": "Alt Advance %", "value": f"{breadth['alt_advance_pct']:.0f}%", "detail": "Altcoin participation", "tone": "good" if breadth["alt_advance_pct"] >= 60 else "warning" if breadth["alt_advance_pct"] >= 40 else "risk"},
        {"label": "Average Move", "value": format_pct(breadth["average_move"]), "detail": "Average 24H move", "tone": "good" if breadth["average_move"] > 0 else "risk" if breadth["average_move"] < -2 else "warning"},
    ])
    institutional_banner("Breadth Read", "Broad participation supports a cleaner crypto tape; weak breadth favors selectivity and smaller size.", tone=breadth_tone(breadth["score"]))

    # Watchlist
    section_heading("Watchlist", "Ranked opportunities for immediate focus.")
    if opportunity_df.empty:
        st.info("No opportunity scores available yet.")
    else:
        best_opportunity = opportunity_df.head(1).iloc[0].to_dict()
        recommendation_text = str(best_opportunity.get("Recommendation", ""))
        institutional_banner(
            "Primary Watchlist Candidate",
            f"{best_opportunity.get('Name')} ({best_opportunity.get('Symbol')}) — Score {best_opportunity.get('Opportunity Score')}/100 — {recommendation_text}",
            tone="good" if recommendation_text.upper() in ("BUY", "STRONG WATCH") else "warning" if recommendation_text.upper() in ("HOLD", "WAIT", "NEUTRAL") else "risk" if recommendation_text.upper() == "AVOID" else "neutral",
        )
        watch_cols = ["Rank", "Name", "Symbol", "Group", "24H %", "7D %", "RS vs BTC", "Opportunity Score", "Recommendation"]
        styled_watch = opportunity_df.head(8)[watch_cols].style.map(style_pct, subset=["24H %", "7D %", "RS vs BTC"])
        st.dataframe(styled_watch, width="stretch", hide_index=True, height=table_height(min(8, len(opportunity_df))))

    # Research
    section_heading("Research", "Institutional interpretation of the crypto environment.")
    macro_env = "Constructive" if regime["regime"] in ("RISK-ON", "ALTCOIN RISK-ON") else "Mixed" if regime["regime"] == "SELECTIVE" else "Defensive"
    market_sentiment = "Improving" if confidence_score >= 65 else "Neutral" if confidence_score >= 50 else "Defensive"
    stablecoin_flow = liquidity["state"]
    key_catalysts = ", ".join([btc_dominance["trend"], market_cycle["cycle"], breadth["state"]])
    list_grid([
        {
            "title": "Institutional Research Summary",
            "tone": regime_tone(regime["regime"]),
            "rows": [
                ("Macro Crypto Environment", macro_env),
                ("Bitcoin Leadership", btc_dominance["interpretation"]),
                ("Altcoin Participation", f"{breadth['alt_advance_pct']:.0f}% advancing across the alt basket"),
                ("Stablecoin Flow", stablecoin_flow),
                ("Market Sentiment", market_sentiment),
                ("Key Catalysts", key_catalysts),
            ],
        }
    ])

    # Technical Analysis
    section_heading("Technical Analysis", "Structure and relative performance without redundant charts.")
    tech_cols = ["Name", "Symbol", "Group", "1H %", "24H %", "7D %", "RS vs BTC", "Recommendation"]
    if not opportunity_df.empty:
        tech_view = opportunity_df.head(10)[tech_cols].copy()
        styled_tech = tech_view.style.map(style_pct, subset=["1H %", "24H %", "7D %", "RS vs BTC"])
        st.dataframe(styled_tech, width="stretch", hide_index=True, height=table_height(min(10, len(opportunity_df))))
    else:
        st.info("No technical structure available yet.")

    # Risk Assessment
    section_heading("Risk Assessment", "How much risk the tape supports right now.")
    risk_view = max(0.0, min(100.0, round((stress_score * 0.55) + (volatility_proxy * 4.0) + (max(0.0, 100.0 - confidence_score) * 0.25), 1)))
    metric_grid([
        {"label": "Risk Score", "value": f"{risk_view:.1f}/100", "detail": "Composite presentation risk", "tone": "risk" if risk_view >= 60 else "warning" if risk_view >= 35 else "good"},
        {"label": "Stress", "value": f"{stress_score}/100", "detail": stress_label, "tone": stress_tone(stress_score)},
        {"label": "Volatility", "value": f"{volatility_proxy:.2f}%", "detail": "Average absolute 24H move", "tone": "warning" if volatility_proxy >= 5 else "neutral"},
        {"label": "Confidence", "value": f"{confidence_score:.1f}/100", "detail": "Institutional confidence", "tone": "good" if confidence_score >= 70 else "warning" if confidence_score >= 50 else "risk"},
    ])

    if risk_view >= 60:
        institutional_banner("Risk Posture", "Defensive posture. Protect capital and avoid broad high-beta crypto exposure.", tone="risk", body_weight=800)
    elif risk_view >= 35:
        institutional_banner("Risk Posture", "Selective posture. Trade only clean relative-strength setups.", tone="warning", body_weight=800)
    else:
        institutional_banner("Risk Posture", "Calm tape. Qualified setups can be considered with discipline.", tone="good", body_weight=800)

    # Execution Plan
    section_heading("Execution Plan", "Decision-ready guidance for current crypto conditions.")
    if execution_status == "BUY":
        direction = "BUY"
        size_guidance = "Normal size, leaders only"
        entry_zone = "Pullback or breakout confirmation"
        stop_level = "Below structure / leader invalidation"
        target_zone = "Prior resistance or measured move"
        rr = "1.8:1 or better"
    elif execution_status == "HOLD":
        direction = "HOLD"
        size_guidance = "Reduced size"
        entry_zone = "Only on confirmation"
        stop_level = "Tighter than normal"
        target_zone = "Near-term mean reversion / breakout retest"
        rr = "1.5:1 or better"
    elif execution_status == "WAIT":
        direction = "WAIT"
        size_guidance = "No broad exposure"
        entry_zone = "Leader confirmation only"
        stop_level = "Protective and tight"
        target_zone = "Selective mean reversion"
        rr = "2.0:1 preferred"
    else:
        direction = "AVOID"
        size_guidance = "Cash / BTC only"
        entry_zone = "No new risk until tape improves"
        stop_level = "N/A"
        target_zone = "N/A"
        rr = "N/A"

    metric_grid([
        {"label": "Trade Direction", "value": direction, "detail": regime["playbook"], "tone": regime_tone(regime["regime"])},
        {"label": "Position Size Guidance", "value": size_guidance, "detail": f"Multiplier {regime['execution_multiplier']:.2f}x", "tone": "info"},
        {"label": "Entry Zone", "value": entry_zone, "detail": "Execution guidance", "tone": "neutral"},
        {"label": "Stop Level", "value": stop_level, "detail": "Risk boundary", "tone": "risk"},
        {"label": "Target Zone", "value": target_zone, "detail": "Profit objective", "tone": "good"},
        {"label": "Risk/Reward", "value": rr, "detail": "Target versus risk", "tone": "info"},
        {"label": "Confidence Score", "value": f"{confidence_score:.1f}/100", "detail": f"Institutional grade {institutional_grade}", "tone": "good" if confidence_score >= 70 else "warning" if confidence_score >= 50 else "risk"},
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
                ("Review Cadence", "Reassess on each regime or breadth change."),
                ("Profit Management", "Take partials into strength and trail the remainder."),
            ],
        },
        {
            "title": "Operational Discipline",
            "tone": "warning" if execution_status in ("WAIT", "HOLD") else "good",
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
    seven_day_leaders = crypto_df.sort_values("7D %", ascending=False, na_position="last").head(5)
    seven_day_laggards = crypto_df.sort_values("7D %", ascending=True, na_position="last").head(5)
    h1, h2 = st.columns(2)
    with h1:
        display_price_table("Relative Strength Leaders", seven_day_leaders, max_rows=5)
    with h2:
        display_price_table("Relative Strength Laggards", seven_day_laggards, max_rows=5)
    list_grid([
        {
            "title": "Historical Read",
            "tone": "info",
            "rows": [
                ("Cycle", market_cycle["cycle"]),
                ("Leadership", btc_dominance["trend"]),
                ("Breadth", breadth["state"]),
                ("Confidence", f"{confidence_score:.1f} / 100"),
            ],
        }
    ])

    # Data Controls
    section_heading("Data Controls", "Operational refresh controls kept below the decision flow.")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("Refresh Crypto Pulse Data", width="stretch"):
            st.cache_data.clear()
            st.rerun()
    with c2:
        st.selectbox("Lookback", ["7d", "14d", "30d"], index=["7d", "14d", "30d"].index(period) if period in ["7d", "14d", "30d"] else 0, key="crypto_pulse_period")
    with c3:
        st.selectbox("Interval", ["1h", "2h", "4h", "1d"], index=["1h", "2h", "4h", "1d"].index(interval) if interval in ["1h", "2h", "4h", "1d"] else 0, key="crypto_pulse_interval")

    # Diagnostics
    section_heading("Diagnostics", "Technical and developer-oriented details are collapsed below.")
    with st.expander("Raw API Responses", expanded=False):
        st.dataframe(crypto_df.head(12), width="stretch", hide_index=True, height=table_height(min(12, len(crypto_df))))
        if not opportunity_df.empty:
            st.dataframe(opportunity_df.head(12), width="stretch", hide_index=True, height=table_height(min(12, len(opportunity_df))))

    with st.expander("Cache Details", expanded=False):
        st.write({
            "crypto_pulse_bus_payload": crypto_pulse_bus_payload,
            "multi_asset_signal_bus": st.session_state.get("multi_asset_signal_bus", {}),
            "crypto_pulse_regime": st.session_state.get("crypto_pulse_regime"),
            "crypto_pulse_market_cycle": st.session_state.get("crypto_pulse_market_cycle"),
            "crypto_pulse_execution_multiplier": st.session_state.get("crypto_pulse_execution_multiplier"),
        })

    with st.expander("Debug Information", expanded=False):
        st.write({
            "regime": regime,
            "breadth": breadth,
            "stress_score": stress_score,
            "stress_label": stress_label,
            "liquidity": liquidity,
            "market_cycle": market_cycle,
            "btc_dominance": btc_dominance,
        })

    with st.expander("Timing Diagnostics", expanded=False):
        st.write({
            "period": period,
            "interval": interval,
            "last_refresh_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_refresh_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "latest_data_timestamp": latest_timestamp,
        })

    with st.expander("Data Quality Checks", expanded=False):
        quality = {
            "rows_loaded": int(crypto_df.shape[0]),
            "missing_price_rows": int(crypto_df["Price"].isna().sum()) if "Price" in crypto_df.columns else 0,
            "missing_24h_rows": int(crypto_df["24H %"].isna().sum()) if "24H %" in crypto_df.columns else 0,
            "missing_7d_rows": int(crypto_df["7D %"].isna().sum()) if "7D %" in crypto_df.columns else 0,
            "opportunity_rows": int(opportunity_df.shape[0]) if isinstance(opportunity_df, pd.DataFrame) else 0,
        }
        st.write(quality)

    help_text("Crypto Pulse is informational only. It does not place trades and does not route orders.")



if __name__ == "__main__":
    st.set_page_config(page_title="Crypto Pulse", page_icon="₿", layout="wide")
    run_page()
