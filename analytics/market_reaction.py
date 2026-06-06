# =========================================================
# 🌎 MARKET REACTION ENGINE — v1.5
# JFBP Quant Desk
# Cross-Asset Regime Engine + Actual Portfolio Holdings
# =========================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import warnings

import pandas as pd
import yfinance as yf


# =========================================================
# WARNING CLEANUP
# =========================================================

warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL",
)


# =========================================================
# SYMBOL GROUPS
# =========================================================

MARKET_INDEXES: Dict[str, str] = {
    "QQQ": "Nasdaq 100",
    "SPY": "S&P 500",
    "DIA": "Dow Jones",
    "IWM": "Russell 2000",

    # Growth / Tech
    "SOXX": "Semiconductors",

    # Macro / Intermarket
    "TLT": "20Y Treasury Bonds",
    "GLD": "Gold",
    "UUP": "US Dollar",
    "HYG": "High Yield Credit",

    # Volatility
    "VIXY": "Volatility ETF",
}

SECTOR_ETFS: Dict[str, str] = {
    "XLK": "Technology",
    "XLC": "Communication",
    "XLY": "Consumer Discretionary",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLV": "Healthcare",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
}

MEGACAPS: Dict[str, str] = {
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "META": "Meta",
    "GOOGL": "Alphabet",
    "TSLA": "Tesla",
    "AVGO": "Broadcom",
    "AMD": "AMD",
}


# =========================================================
# ACTUAL PORTFOLIO HOLDINGS
# Approximate market values from current portfolio screenshot.
# SCHD is converted from USD to CAD estimate for weighting only.
# =========================================================

PORTFOLIO_HOLDINGS: Dict[str, float] = {
    "VFV.TO": 79941.04,
    "SCHD": 69000.00,
    "VEQT.TO": 54820.92,
    "VDY.TO": 41059.82,
    "VIU.TO": 31070.30,
    "VCN.TO": 30297.99,
}


# =========================================================
# DATA MODEL
# =========================================================

@dataclass
class MarketEvent:
    label: str
    confidence: int
    explanation: str


# =========================================================
# PRICE HELPERS
# =========================================================

def _to_float(value) -> Optional[float]:
    """
    Safely converts yfinance scalar/Series output to float.
    Handles both normal scalar values and single-element Series.
    """

    try:
        if hasattr(value, "item"):
            return float(value.item())

        return float(value)

    except Exception:
        try:
            if hasattr(value, "iloc"):
                return float(value.iloc[0])

            if hasattr(value, "values"):
                return float(value.values[0])

        except Exception:
            return None

    return None


def _safe_pct_change(symbol: str, period: str = "5d") -> Optional[float]:
    try:
        data = yf.download(
            symbol,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=True,
            group_by="column",
        )

        if data is None or data.empty or len(data) < 2:
            return None

        close = data["Close"].dropna()

        if len(close) < 2:
            return None

        last = _to_float(close.iloc[-1])
        prev = _to_float(close.iloc[-2])

        if last is None or prev is None:
            return None

        if prev == 0:
            return None

        return round(((last - prev) / prev) * 100, 2)

    except Exception:
        return None


def build_reaction_table(symbols: Dict[str, str]) -> pd.DataFrame:
    rows: List[dict] = []

    for symbol, name in symbols.items():
        pct = _safe_pct_change(symbol)

        rows.append(
            {
                "Symbol": symbol,
                "Name": name,
                "Daily %": pct,
            }
        )

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(
            "Daily %",
            ascending=False,
            na_position="last",
        )

    return df


# =========================================================
# PORTFOLIO IMPACT
# =========================================================

def calculate_real_portfolio_impact() -> dict:
    rows: List[dict] = []

    total_value = sum(PORTFOLIO_HOLDINGS.values())
    total_impact = 0.0

    for symbol, market_value in PORTFOLIO_HOLDINGS.items():
        weight = market_value / total_value if total_value else 0.0

        move = _safe_pct_change(symbol)

        if move is None:
            move = 0.0

        contribution = move * weight
        total_impact += contribution

        rows.append(
            {
                "Symbol": symbol,
                "Market Value": round(market_value, 2),
                "Weight %": round(weight * 100, 2),
                "Daily %": round(move, 2),
                "Contribution %": round(contribution, 2),
            }
        )

    portfolio_df = pd.DataFrame(rows)

    if not portfolio_df.empty:
        portfolio_df = portfolio_df.sort_values(
            "Market Value",
            ascending=False,
        )

    return {
        "portfolio_move": round(total_impact, 2),
        "portfolio_df": portfolio_df,
    }


# =========================================================
# EVENT DETECTION
# =========================================================

def detect_market_event(
    indexes: pd.DataFrame,
    sectors: pd.DataFrame,
    megacaps: pd.DataFrame,
) -> MarketEvent:

    def get_move(df: pd.DataFrame, symbol: str) -> Optional[float]:
        row = df[df["Symbol"] == symbol]

        if row.empty:
            return None

        value = row.iloc[0]["Daily %"]

        if pd.isna(value):
            return None

        return _to_float(value)

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
    xle = get_move(sectors, "XLE")
    xlu = get_move(sectors, "XLU")
    xlp = get_move(sectors, "XLP")

    nvda = get_move(megacaps, "NVDA")
    avgo = get_move(megacaps, "AVGO")
    amd = get_move(megacaps, "AMD")

    # =====================================================
    # 1. Institutional risk-off
    # =====================================================

    if (
        spy is not None and spy < -1
        and qqq is not None and qqq < -1
        and hyg is not None and hyg < 0
        and (
            (tlt is not None and tlt > 0)
            or (gld is not None and gld > 0)
            or (uup is not None and uup > 0)
        )
    ):
        return MarketEvent(
            label="Institutional Risk-Off",
            confidence=88,
            explanation=(
                "Stocks are falling while capital rotates toward defensive assets."
            ),
        )

    # =====================================================
    # 2. Semiconductor-led tech selloff
    # =====================================================

    if (
        qqq is not None and qqq <= -1.25
        and xlk is not None and xlk <= -1.5
        and soxx is not None and soxx <= -2.0
    ):
        return MarketEvent(
            label="Semiconductor-Led Tech Selloff",
            confidence=90,
            explanation=(
                "Nasdaq, technology, and the semiconductor complex are all under pressure."
            ),
        )

    # Fallback if SOXX data fails but major chip stocks confirm weakness
    if (
        qqq is not None and qqq <= -1.25
        and xlk is not None and xlk <= -1.5
        and (
            (nvda is not None and nvda <= -2)
            or (avgo is not None and avgo <= -2)
            or (amd is not None and amd <= -2)
        )
    ):
        return MarketEvent(
            label="Semiconductor-Led Tech Selloff",
            confidence=85,
            explanation=(
                "Nasdaq, technology, and major chip stocks are all under pressure."
            ),
        )

    # =====================================================
    # 3. Broad market risk-off
    # =====================================================

    if (
        spy is not None and spy <= -1.5
        and qqq is not None and qqq <= -1.5
        and iwm is not None and iwm <= -1.5
    ):
        return MarketEvent(
            label="Broad Market Risk-Off",
            confidence=82,
            explanation="Large caps, Nasdaq, and small caps are selling off together.",
        )

    # =====================================================
    # 4. Defensive rotation
    # =====================================================

    if (
        qqq is not None and qqq <= -1
        and (
            (xlu is not None and xlu > 0)
            or (xlp is not None and xlp > 0)
        )
    ):
        return MarketEvent(
            label="Defensive Rotation",
            confidence=72,
            explanation="Growth is weak while defensive sectors are holding up better.",
        )

    # =====================================================
    # 5. Energy rotation
    # =====================================================

    if (
        qqq is not None and qqq <= -1
        and xle is not None and xle >= 1
    ):
        return MarketEvent(
            label="Rotation Into Energy",
            confidence=70,
            explanation="Nasdaq is weak while energy is attracting relative strength.",
        )

    # =====================================================
    # 6. Volatility shock
    # =====================================================

    if (
        vixy is not None and vixy >= 5
        and spy is not None and spy <= -1
    ):
        return MarketEvent(
            label="Volatility Shock",
            confidence=68,
            explanation="Volatility is rising while the broad market is falling.",
        )

    return MarketEvent(
        label="No Major Shock Detected",
        confidence=50,
        explanation="Current moves do not yet meet the event-detection thresholds.",
    )


# =========================================================
# MAIN REPORT
# =========================================================

def generate_market_reaction_report() -> dict:
    indexes = build_reaction_table(MARKET_INDEXES)
    sectors = build_reaction_table(SECTOR_ETFS)
    megacaps = build_reaction_table(MEGACAPS)
    portfolio = calculate_real_portfolio_impact()

    event = detect_market_event(
        indexes,
        sectors,
        megacaps,
    )

    return {
        "event": event,
        "indexes": indexes,
        "sectors": sectors,
        "megacaps": megacaps,
        "portfolio": portfolio,
    }