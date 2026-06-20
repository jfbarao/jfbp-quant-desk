# =========================================================
# ₿ CRYPTO PULSE PAGE — v1.2
# JFBP Quant Desk
# Crypto Regime + Breadth + Stress + Leadership Dashboard
# v1.2: Market Clock + BTC Leadership Score + Stablecoin Liquidity Proxy
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

            .crypto-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
                gap: 0.65rem;
                margin: 0.35rem 0 0.75rem 0;
                width: 100%;
            }

            .crypto-card {
                border: 1px solid;
                border-radius: 14px;
                padding: 0.72rem 0.82rem;
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
                gap: 0.75rem;
                margin: 0.45rem 0 0.85rem 0;
            }

            .crypto-list-card {
                border: 1px solid;
                border-radius: 16px;
                padding: 0.85rem 0.95rem;
                min-width: 0;
                overflow: hidden;
            }

            .crypto-list-title {
                font-size: 1.02rem;
                font-weight: 850;
                color: #1f2937;
                margin-bottom: 0.62rem;
                line-height: 1.2;
            }

            .crypto-list-row {
                display: grid;
                grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.35fr);
                gap: 0.65rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.28);
                padding: 0.38rem 0;
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

    st.dataframe(styled, width="stretch", hide_index=True, height=320)



# =========================================================
# v1.2 CRYPTO INTELLIGENCE HELPERS
# =========================================================

def crypto_market_clock_card(data_status: Dict[str, Any]) -> None:
    local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    utc_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    provider = str(data_status.get("provider", "yfinance"))
    interval = str(data_status.get("interval", "N/A"))
    period = str(data_status.get("period", "N/A"))

    st.info(
        "🟢 Crypto Market Status: OPEN 24/7  |  "
        f"Last Refresh: {local_time}  |  UTC: {utc_time}  |  "
        f"Provider: {provider}  |  Lookback: {period}  |  Interval: {interval}"
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
        "Live crypto regime dashboard for BTC, ETH, altcoin breadth, stress, leadership, and trade bias."
    )
    st.caption(
        "Build: Crypto Pulse v1.2 — Market Clock · BTC Leadership Score · Stablecoin Liquidity Proxy · Opportunity Scanner · Crypto Playbook · Market Cycle"
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        refresh = st.button("Refresh Crypto Pulse Data", width="stretch")
    with c2:
        period = st.selectbox("Lookback", ["7d", "14d", "30d"], index=0)
    with c3:
        interval = st.selectbox("Interval", ["1h", "2h", "4h", "1d"], index=0)

    if refresh:
        st.cache_data.clear()
        st.rerun()

    if yf is None:
        st.error("yfinance is not available in this environment. Install yfinance to load live crypto data.")
        return

    symbols = tuple(row["Symbol"] for row in CRYPTO_UNIVERSE)

    with st.spinner("Loading crypto market data..."):
        crypto_df = load_crypto_prices(symbols, period=period, interval=interval)

    if crypto_df.empty:
        st.error("Crypto data could not be loaded. Check internet/data access and try again.")
        return

    crypto_market_clock_card({"provider": "yfinance", "period": period, "interval": interval})

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

    command_html = (
        f'<div style="display:inline-flex;align-items:center;gap:0.55rem;background:{tone_palette(regime_tone(regime["regime"]))[0]};'
        f'border:1px solid {tone_palette(regime_tone(regime["regime"]))[1]};'
        f'color:{tone_palette(regime_tone(regime["regime"]))[2]};border-radius:999px;padding:0.35rem 0.75rem;'
        f'font-weight:800;margin:0.25rem 0 0.75rem 0;">'
        f'<span>{regime_icon(regime["regime"])}</span>'
        f'<span>Crypto Command Status: {html.escape(regime["regime"])}</span>'
        f'<span style="color:#64748b;font-weight:650;">Stress {stress_score}/100</span>'
        f'<span style="color:#64748b;font-weight:650;">Breadth {breadth["score"]:.1f}/100</span>'
        '</div>'
    )
    st.markdown(command_html, unsafe_allow_html=True)

    st.subheader("🤖 AI Crypto Brief")
    st.caption("What it means: 30-second read of the crypto tape before looking at the full dashboard.")

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
        st.subheader("🚦 Crypto Stress Dashboard")
        st.caption("What it means: Measures whether crypto conditions are calm, mixed, or risk-off.")

        metric_grid([
            {"label": "Stress Score", "value": f"{stress_score}/100", "detail": "Overall crypto risk.", "tone": stress_tone(stress_score)},
            {"label": "Stress State", "value": stress_label, "detail": "Current crypto condition.", "tone": stress_tone(stress_score)},
            {"label": "Crypto Regime", "value": f"{regime_icon(regime['regime'])} {regime['regime']}", "detail": "Trading mode.", "tone": regime_tone(regime["regime"])},
            {"label": "Execution Multiplier", "value": f"{regime['execution_multiplier']:.2f}x", "detail": "Position-size adjustment.", "tone": "info"},
        ])

        if stress_score >= 70:
            st.error("Crypto Stress Interpretation: defensive posture. Avoid broad altcoin exposure.")
        elif stress_score >= 40:
            st.warning("Crypto Stress Interpretation: selective posture. Trade only clean relative-strength leaders.")
        else:
            st.success("Crypto Stress Interpretation: conditions are calm enough for qualified setups.")

        help_text("Crypto stress combines BTC, ETH, altcoin performance, and breadth deterioration.")

        st.divider()
        st.subheader("📊 Crypto Breadth Engine")
        st.caption("What it means: Measures how many crypto assets are participating in the move.")

        metric_grid([
            {"label": "Breadth Score", "value": f"{breadth['score']:.1f}/100", "detail": "Participation strength.", "tone": breadth_tone(breadth["score"])},
            {"label": "Breadth State", "value": breadth["state"], "detail": "Crypto participation.", "tone": breadth_tone(breadth["score"])},
            {"label": "Advancers", "value": f"{breadth['advancing']}/{breadth['total']}", "detail": "Coins moving higher.", "tone": "info"},
            {"label": "Alt Advance %", "value": f"{breadth['alt_advance_pct']:.0f}%", "detail": "Altcoin participation.", "tone": "good" if breadth["alt_advance_pct"] >= 60 else "warning" if breadth["alt_advance_pct"] >= 40 else "risk"},
            {"label": "Average Move", "value": format_pct(breadth["average_move"]), "detail": "Average 24h move.", "tone": "good" if breadth["average_move"] > 0 else "risk" if breadth["average_move"] < -2 else "warning"},
        ])

        if breadth["score"] < 40:
            st.error("Breadth Interpretation: weak participation. New crypto exposure should be reduced.")
        elif breadth["score"] < 60:
            st.warning("Breadth Interpretation: mixed participation. Leadership selection matters.")
        else:
            st.success("Breadth Interpretation: healthy participation. Crypto tape supports qualified setups.")

        help_text("Crypto rallies are more trustworthy when BTC, ETH, and several altcoins participate together.")

        st.divider()
        st.subheader("📈 Leadership & Damage Report")
        st.caption("What it means: Shows strongest and weakest crypto assets in the current tape.")

        strongest = crypto_df.sort_values("24H %", ascending=False, na_position="last").head(5)
        weakest = crypto_df.sort_values("24H %", ascending=True, na_position="last").head(5)

        l1, l2 = st.columns(2)
        with l1:
            display_price_table("Strongest 24H", strongest, max_rows=5)
        with l2:
            display_price_table("Weakest 24H", weakest, max_rows=5)

        st.divider()
        st.subheader("🔎 Crypto Opportunity Scanner")
        st.caption(
            "What it means: Ranks the loaded crypto universe by momentum, "
            "relative strength versus BTC, trend, and breadth support."
        )

        if opportunity_df.empty:
            st.info("No opportunity scores available yet.")
        else:
            top_opportunities = opportunity_df.head(8).copy()
            display_cols = [
                "Rank",
                "Name",
                "Symbol",
                "Group",
                "24H %",
                "7D %",
                "RS vs BTC",
                "Opportunity Score",
                "Recommendation",
            ]
            styled_opportunities = top_opportunities[display_cols].style.map(
                style_pct,
                subset=["24H %", "7D %", "RS vs BTC"],
            )
            st.dataframe(styled_opportunities, width="stretch", hide_index=True, height=320)

            best_opportunity = top_opportunities.iloc[0].to_dict()
            st.success(
                f"Best Opportunity: {best_opportunity.get('Name')} ({best_opportunity.get('Symbol')}) — "
                f"Score {best_opportunity.get('Opportunity Score')}/100 — {best_opportunity.get('Recommendation')}"
            )

        help_text("This is a ranking engine, not an order signal. Use it with chart structure and risk controls.")

    with right_col:
        st.divider()
        st.subheader("🎯 Crypto Decision Center")
        st.caption("What it means: Converts crypto conditions into practical trading guidance.")

        btc = get_move(crypto_df, "BTC-USD")
        eth = get_move(crypto_df, "ETH-USD")

        metric_grid([
            {"label": "Regime", "value": f"{regime_icon(regime['regime'])} {regime['regime']}", "detail": regime["playbook"], "tone": regime_tone(regime["regime"])},
            {"label": "BTC 24H", "value": format_pct(btc), "detail": "Core crypto anchor.", "tone": "good" if safe_float(btc) > 0 else "risk" if safe_float(btc) < -2 else "warning"},
            {"label": "ETH 24H", "value": format_pct(eth), "detail": "Smart-contract leader.", "tone": "good" if safe_float(eth) > 0 else "risk" if safe_float(eth) < -2 else "warning"},
            {"label": "ETH vs BTC", "value": format_pct(regime["eth_vs_btc"]), "detail": "ETH relative strength.", "tone": "good" if regime["eth_vs_btc"] > 0 else "warning"},
            {"label": "Alt Avg 24H", "value": format_pct(regime["alt_avg_24h"]), "detail": "Altcoin basket.", "tone": "good" if regime["alt_avg_24h"] > 0 else "risk" if regime["alt_avg_24h"] < -2 else "warning"},
            {"label": "Buy Allowed", "value": "YES" if regime["buy_allowed"] else "NO", "detail": "Crypto scanner permission.", "tone": "good" if regime["buy_allowed"] else "risk"},
            {"label": "Market Cycle", "value": f"{market_cycle['icon']} {market_cycle['cycle']}", "detail": market_cycle["note"], "tone": market_cycle["tone"]},
            {"label": "BTC Leadership Score", "value": f"{btc_dominance['dominance_proxy']:.2f}%", "detail": btc_dominance["trend"], "tone": "info"},
            {"label": "Liquidity Proxy", "value": liquidity["state"], "detail": f"{liquidity['score']}/100", "tone": liquidity["tone"]},
        ])

        if regime["buy_allowed"]:
            st.info(regime["playbook"])
        else:
            st.error(regime["playbook"])

        if regime["regime"] == "RISK-OFF":
            action_tone = "risk"
            exposure = "25% - 50%"
            preferred = "Cash / BTC only"
            avoid = "Broad altcoin exposure"
            aggression = "Low"
        elif regime["regime"] in ("CAUTIOUS", "SELECTIVE"):
            action_tone = "warning"
            exposure = "40% - 70%"
            preferred = "BTC / ETH / strongest leaders"
            avoid = "Weak altcoins"
            aggression = "Moderate"
        else:
            action_tone = "good"
            exposure = "70% - 100%"
            preferred = "Relative-strength leaders"
            avoid = "Extended laggards"
            aggression = "Normal"

        list_grid([
            {
                "title": "Action Plan",
                "tone": action_tone,
                "rows": [
                    ("1", "Confirm BTC direction first"),
                    ("2", "Check ETH relative strength"),
                    ("3", "Favor coins above the alt basket"),
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

        st.subheader("📘 Crypto Playbook")
        st.caption(
            "What it means: Converts regime, liquidity, dominance, breadth, "
            "stress, and market cycle into a practical crypto playbook."
        )
        list_grid(build_crypto_playbook_cards(regime, breadth, stress_score, btc_dominance, liquidity, market_cycle))
        st.info(btc_dominance["interpretation"])
        st.caption(liquidity["note"])
        st.caption(f"Market Cycle: {market_cycle['cycle']} — {market_cycle['note']}")

        help_text("Crypto Pulse is informational only. It does not place trades and does not route orders.")

        st.divider()
        st.subheader("📌 Crypto Snapshot")
        st.caption("What it means: Quick read of core coins and high-beta altcoins.")

        core_rows = crypto_df[crypto_df["Symbol"].isin(CORE_SYMBOLS)].copy()
        alt_rows = crypto_df[crypto_df["Symbol"].isin(ALT_SYMBOLS)].copy()

        display_price_table("Core Crypto", core_rows, max_rows=5)
        display_price_table("Altcoin Basket", alt_rows.sort_values("24H %", ascending=False, na_position="last"), max_rows=12)

        st.divider()
        st.subheader("📚 Reference Center")
        st.caption("What it means: Diagnostic data used to validate the current crypto read.")

        with st.expander("Crypto Regime Details", expanded=False):
            details_df = pd.DataFrame([
                {"Metric": "Regime", "Reading": regime["regime"]},
                {"Metric": "Stress", "Reading": f"{stress_score}/100 — {stress_label}"},
                {"Metric": "Breadth", "Reading": f"{breadth['score']:.1f}/100 — {breadth['state']}"},
                {"Metric": "BTC 24H", "Reading": format_pct(regime["btc_24h"])},
                {"Metric": "ETH 24H", "Reading": format_pct(regime["eth_24h"])},
                {"Metric": "ETH vs BTC", "Reading": format_pct(regime["eth_vs_btc"])},
                {"Metric": "Alt Avg 24H", "Reading": format_pct(regime["alt_avg_24h"])},
                {"Metric": "Buy Allowed", "Reading": "YES" if regime["buy_allowed"] else "NO"},
                {"Metric": "Execution Multiplier", "Reading": f"{regime['execution_multiplier']:.2f}x"},
                {"Metric": "BTC Leadership Score", "Reading": f"{btc_dominance['dominance_proxy']:.2f}% — {btc_dominance['trend']}"},
                {"Metric": "Stablecoin Liquidity Proxy", "Reading": f"{liquidity['state']} — {liquidity['score']}/100"},
                {"Metric": "Market Cycle", "Reading": f"{market_cycle['cycle']} — {market_cycle['note']}"},
            ])
            st.dataframe(details_df, width="stretch", hide_index=True)

        with st.expander("Data Status", expanded=False):
            st.write({
                "provider": "yfinance",
                "period": period,
                "interval": interval,
                "assets_loaded": int(crypto_df.shape[0]),
                "last_refresh_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_refresh_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })


if __name__ == "__main__":
    st.set_page_config(page_title="Crypto Pulse", page_icon="₿", layout="wide")
    run_page()
