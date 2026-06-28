# =========================================================
# EARNINGS RISK ENGINE — v1.0
# JFBP Quant Desk
# Free Earnings-Date Risk Layer
# =========================================================

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import yfinance as yf


# =========================================================
# EVENT MODEL
# =========================================================

@dataclass
class EarningsEvent:
    symbol: str
    earnings_date: Optional[datetime]
    risk_score: int
    risk_label: str
    days_until: Optional[int]
    source: str = "YFINANCE"
    status: str = "UNKNOWN"
    reason: str = ""


# =========================================================
# CONFIG
# =========================================================

DEFAULT_LOOKAHEAD_DAYS = 14
POST_EARNINGS_COOLDOWN_DAYS = 1

HIGH_RISK_DAYS = 3
MEDIUM_RISK_DAYS = 5
LOW_RISK_DAYS = 10

KNOWN_ETF_SYMBOLS = {
    "SPY", "QQQ", "IWM", "DIA", "TQQQ", "UVXY", "RSP", "VTI", "ACWI", "EFA", "EEM", "TLT",
    "SCHD", "VIG", "VDY.TO", "CDZ.TO", "ZEB.TO", "XEI.TO", "XLV", "XLP", "XLU", "SMH", "XLF",
    "XLE", "USO", "BNO", "GLD", "IAU", "GDX", "GDXJ", "IBIT", "FBTC", "ETHE", "UUP", "FXE",
    "FXY", "FXB", "FXC", "CYB", "XLI", "XLK", "XOP", "OIH", "SLV", "SIL", "IAU", "GLD",
    "VIXY", "XLU", "XLI", "XLV", "XLP", "XLK", "XLE", "XLF", "SMH", "RSP", "VTI", "ACWI",
    "EFA", "EEM", "IBIT", "FBTC", "ETHE", "GDXJ", "GDX", "UUP", "FXE", "FXY", "FXB", "FXC",
    "CYB", "XOP", "OIH", "SLV", "SIL",
}


# =========================================================
# TIME HELPERS
# =========================================================

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_symbol(symbol: Any) -> str:
    return str(symbol or "").upper().strip()


def earnings_exemption_type(symbol: Any) -> Optional[str]:
    symbol = normalize_symbol(symbol)

    if not symbol:
        return None

    if symbol.endswith("=F"):
        return "FUTURES"

    if symbol.endswith("=X"):
        return "FOREX"

    if symbol.endswith("-USD"):
        return "CRYPTO"

    if symbol in KNOWN_ETF_SYMBOLS:
        return "ETF"

    return None


def ensure_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    try:
        if isinstance(value, pd.Timestamp):
            value = value.to_pydatetime()

        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime(
                value.year,
                value.month,
                value.day,
                12,
                0,
                tzinfo=timezone.utc,
            )

        if isinstance(value, str):
            parsed = pd.to_datetime(value, errors="coerce")

            if pd.isna(parsed):
                return None

            value = parsed.to_pydatetime()

        if not isinstance(value, datetime):
            return None

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)

        return value

    except Exception:
        return None


def days_until(event_time: Optional[datetime]) -> Optional[int]:
    event_time = ensure_utc(event_time)

    if event_time is None:
        return None

    today = utc_now().date()
    event_day = event_time.date()

    return int((event_day - today).days)


# =========================================================
# RISK SCORING
# =========================================================

def earnings_risk_label(score: int) -> str:
    if score >= 80:
        return "EXTREME"

    if score >= 60:
        return "HIGH"

    if score >= 35:
        return "MEDIUM"

    if score > 0:
        return "LOW"

    return "NONE"


def earnings_risk_score_from_days(days: Optional[int]) -> int:
    if days is None:
        return 0

    if days < -POST_EARNINGS_COOLDOWN_DAYS:
        return 0

    if days < 0:
        return 65

    if days <= 1:
        return 90

    if days <= HIGH_RISK_DAYS:
        return 75

    if days <= MEDIUM_RISK_DAYS:
        return 50

    if days <= LOW_RISK_DAYS:
        return 25

    return 0


def earnings_status_from_days(days: Optional[int]) -> str:
    if days is None:
        return "NO_DATE"

    if days < -POST_EARNINGS_COOLDOWN_DAYS:
        return "PAST"

    if days < 0:
        return "POST_EARNINGS_COOLDOWN"

    if days == 0:
        return "EARNINGS_TODAY"

    if days == 1:
        return "EARNINGS_TOMORROW"

    return f"EARNINGS_IN_{days}_DAYS"


# =========================================================
# FREE DATA SOURCE — YFINANCE
# =========================================================

def _extract_date_from_calendar_object(calendar: Any) -> Optional[datetime]:
    """
    yfinance calendar responses have changed across versions.
    This function accepts dicts, Series, DataFrames, and lists.
    """

    if calendar is None:
        return None

    candidate_keys = [
        "Earnings Date",
        "Earnings High",
        "Earnings Low",
        "Earnings Average",
        "earningsDate",
        "earnings_date",
    ]

    try:
        if isinstance(calendar, dict):
            for key in candidate_keys:
                value = calendar.get(key)

                if isinstance(value, (list, tuple)) and value:
                    parsed = ensure_utc(value[0])
                else:
                    parsed = ensure_utc(value)

                if parsed is not None:
                    return parsed
    except Exception:
        pass

    try:
        if isinstance(calendar, pd.Series):
            for key in candidate_keys:
                if key in calendar.index:
                    parsed = ensure_utc(calendar.loc[key])

                    if parsed is not None:
                        return parsed
    except Exception:
        pass

    try:
        if isinstance(calendar, pd.DataFrame):
            for key in candidate_keys:
                if key in calendar.index:
                    row = calendar.loc[key]

                    if isinstance(row, pd.Series):
                        for value in row.values:
                            parsed = ensure_utc(value)

                            if parsed is not None:
                                return parsed
                    else:
                        parsed = ensure_utc(row)

                        if parsed is not None:
                            return parsed

                if key in calendar.columns:
                    for value in calendar[key].values:
                        parsed = ensure_utc(value)

                        if parsed is not None:
                            return parsed
    except Exception:
        pass

    try:
        if isinstance(calendar, (list, tuple)):
            for value in calendar:
                parsed = ensure_utc(value)

                if parsed is not None:
                    return parsed
    except Exception:
        pass

    return None


def fetch_next_earnings_date_yfinance(symbol: str) -> Optional[datetime]:
    symbol = normalize_symbol(symbol)

    if not symbol:
        return None

    ticker = yf.Ticker(symbol)

    try:
        calendar = ticker.calendar
        parsed = _extract_date_from_calendar_object(calendar)

        if parsed is not None:
            return parsed
    except Exception:
        pass

    try:
        get_calendar = getattr(ticker, "get_calendar", None)

        if callable(get_calendar):
            calendar = get_calendar()
            parsed = _extract_date_from_calendar_object(calendar)

            if parsed is not None:
                return parsed
    except Exception:
        pass

    try:
        earnings_dates = ticker.get_earnings_dates(
            limit=8,
        )

        if isinstance(earnings_dates, pd.DataFrame) and not earnings_dates.empty:
            index_values = list(earnings_dates.index)
            parsed_dates = [
                ensure_utc(value)
                for value in index_values
            ]
            parsed_dates = [
                value for value in parsed_dates
                if value is not None
            ]

            now = utc_now()
            future_dates = [
                value for value in parsed_dates
                if value >= now - timedelta(days=POST_EARNINGS_COOLDOWN_DAYS)
            ]

            if future_dates:
                return sorted(future_dates)[0]
    except Exception:
        pass

    return None


# =========================================================
# PUBLIC API
# =========================================================

def analyze_symbol_earnings_risk(symbol: str) -> EarningsEvent:
    symbol = normalize_symbol(symbol)

    if not symbol:
        return EarningsEvent(
            symbol="",
            earnings_date=None,
            risk_score=0,
            risk_label="NONE",
            days_until=None,
            source="NONE",
            status="NO_SYMBOL",
            reason="Missing symbol.",
        )

    exemption_type = earnings_exemption_type(symbol)

    if exemption_type is not None:
        pretty_label = "Not Applicable (ETF)" if exemption_type == "ETF" else f"Not Applicable ({exemption_type.title()})"

        return EarningsEvent(
            symbol=symbol,
            earnings_date=None,
            risk_score=0,
            risk_label="NONE",
            days_until=None,
            source="ASSET_CLASS_SKIP",
            status=f"NOT_APPLICABLE_{exemption_type}",
            reason=pretty_label,
        )

    try:
        earnings_date = fetch_next_earnings_date_yfinance(symbol)
        days = days_until(earnings_date)
        score = earnings_risk_score_from_days(days)
        label = earnings_risk_label(score)
        status = earnings_status_from_days(days)

        return EarningsEvent(
            symbol=symbol,
            earnings_date=earnings_date,
            risk_score=score,
            risk_label=label,
            days_until=days,
            source="YFINANCE",
            status=status,
            reason=(
                "No upcoming earnings date found."
                if earnings_date is None
                else "Upcoming earnings date found."
            ),
        )

    except Exception as exc:
        return EarningsEvent(
            symbol=symbol,
            earnings_date=None,
            risk_score=0,
            risk_label="NONE",
            days_until=None,
            source="ERROR_SAFE",
            status="ERROR",
            reason="Earnings lookup unavailable.",
        )


def analyze_earnings_risk(
    symbols: Iterable[str],
) -> Dict[str, Any]:

    rows: List[Dict[str, Any]] = []
    max_score = 0
    highest_risk_event = None

    cleaned_symbols = []

    for symbol in symbols:
        symbol = normalize_symbol(symbol)

        if symbol and symbol not in cleaned_symbols:
            cleaned_symbols.append(symbol)

    for symbol in cleaned_symbols:
        event = analyze_symbol_earnings_risk(symbol)
        row = asdict(event)

        if event.earnings_date is not None:
            row["earnings_date"] = event.earnings_date.isoformat()
        else:
            row["earnings_date"] = None

        rows.append(row)

        if event.risk_score > max_score:
            max_score = event.risk_score
            highest_risk_event = row

    return {
        "earnings_risk_score": max_score,
        "earnings_risk_label": earnings_risk_label(max_score),
        "highest_risk_event": highest_risk_event,
        "events": rows,
        "symbol_count": len(cleaned_symbols),
        "source": "YFINANCE",
    }


def apply_earnings_risk_adjustment(
    action: str,
    qty: float,
    earnings_risk_score: int,
) -> Dict[str, Any]:

    action = str(action or "HOLD").upper().strip()

    try:
        qty = float(qty)
    except Exception:
        qty = 0.0

    adjusted_action = action
    adjusted_qty = qty
    reason = "EARNINGS_RISK_NONE"

    if action == "BUY":
        if earnings_risk_score >= 80:
            adjusted_action = "HOLD"
            adjusted_qty = 0.0
            reason = "EARNINGS_RISK_EXTREME_BUY_BLOCKED"

        elif earnings_risk_score >= 60:
            adjusted_qty = max(0.0, round(qty * 0.50, 4))
            reason = "EARNINGS_RISK_HIGH_SIZE_REDUCED"

        elif earnings_risk_score >= 35:
            reason = "EARNINGS_RISK_MEDIUM_WARNING"

    return {
        "adjusted_action": adjusted_action,
        "adjusted_qty": adjusted_qty,
        "earnings_overlay_reason": reason,
    }


# =========================================================
# SAMPLE SYMBOLS / SELF TEST
# =========================================================

def sample_symbols() -> List[str]:
    return [
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
        "META",
        "TSLA",
    ]


if __name__ == "__main__":
    result = analyze_earnings_risk(
        sample_symbols()
    )

    print(result)
