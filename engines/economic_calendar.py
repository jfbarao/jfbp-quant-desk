# =========================================================
# ECONOMIC CALENDAR ENGINE — v4.0
# JFBP Quant Desk
# LOCAL CSV Economic Calendar + Time-Decay Risk Scoring
#
# Data source:
#   data/economic_events.csv
#
# CSV columns supported:
#   date,event,importance,category,country
# Optional:
#   previous,forecast,actual,source
#
# Purpose:
#   Replace DEMO/FMP dependency with reliable local events.
#   Score economic risk by event importance AND time proximity.
# =========================================================

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import csv


# =========================================================
# EVENT MODEL
# =========================================================

@dataclass
class EconomicEvent:
    name: str
    country: str
    event_time: datetime
    importance: str
    category: str
    source: str = "LOCAL"
    previous: Optional[str] = None
    forecast: Optional[str] = None
    actual: Optional[str] = None


# =========================================================
# CONFIG
# =========================================================

LOCAL_CALENDAR_PATH = Path("data/economic_events.csv")
DEFAULT_LOOKAHEAD_DAYS = 45
DEFAULT_LOOKBACK_DAYS = 1

HIGH_IMPACT_KEYWORDS = [
    "CPI",
    "PPI",
    "NFP",
    "NON-FARM",
    "PAYROLLS",
    "FOMC",
    "FED",
    "POWELL",
    "INTEREST RATE",
    "GDP",
    "RETAIL SALES",
    "JOBLESS CLAIMS",
    "UNEMPLOYMENT",
    "ISM",
    "PMI",
    "PCE",
    "CORE PCE",
    "CONSUMER CONFIDENCE",
]

MEDIUM_IMPACT_KEYWORDS = [
    "DURABLE GOODS",
    "HOUSING STARTS",
    "BUILDING PERMITS",
    "INDUSTRIAL PRODUCTION",
    "IMPORT PRICE",
    "EXPORT PRICE",
    "BUSINESS INVENTORIES",
    "FACTORY ORDERS",
]

LOCAL_SOURCES = {
    "LOCAL",
    "CSV",
    "MANUAL",
}

DEMO_SOURCES = {
    "DEMO",
    "SAMPLE",
    "TEST",
}


# =========================================================
# TIME / NORMALIZATION HELPERS
# =========================================================

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def clean_text(value: Any, default: str = "") -> str:
    return str(value if value is not None else default).strip()


def normalize_importance(value: Any) -> str:
    value = str(value or "").strip().upper()

    if value in {"HIGH", "3", "RED", "HIGH IMPACT"}:
        return "HIGH"

    if value in {"MEDIUM", "2", "ORANGE", "MODERATE", "MEDIUM IMPACT"}:
        return "MEDIUM"

    if value in {"LOW", "1", "YELLOW", "LOW IMPACT"}:
        return "LOW"

    if value in {"DEMO", "SAMPLE", "TEST"}:
        return "DEMO"

    return "UNKNOWN"


def normalize_source(value: Any) -> str:
    value = str(value or "").strip().upper()
    return value or "UNKNOWN"


def is_demo_event(event: EconomicEvent) -> bool:
    return normalize_source(event.source) in DEMO_SOURCES


def parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value or "").strip()

        if not text:
            return None

        text = text.replace("Z", "+00:00")

        try:
            dt = datetime.fromisoformat(text)
        except Exception:
            dt = None

        if dt is None:
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%m/%d/%Y %H:%M:%S",
                "%m/%d/%Y %H:%M",
                "%m/%d/%Y",
            ):
                try:
                    parsed = datetime.strptime(text, fmt)

                    # Date-only rows are treated as 12:00 UTC so the event
                    # behaves like a market-day macro release instead of
                    # expiring immediately at midnight.
                    if fmt in ("%Y-%m-%d", "%m/%d/%Y"):
                        parsed = datetime.combine(parsed.date(), time(12, 0))

                    dt = parsed
                    break
                except Exception:
                    continue

        if dt is None:
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def hours_until(event_time: datetime) -> float:
    event_time = parse_datetime(event_time)

    if event_time is None:
        return 0.0

    delta = event_time - utc_now()

    return round(
        delta.total_seconds() / 3600,
        2,
    )


def infer_category(name: str) -> str:
    upper = str(name or "").upper()

    if any(term in upper for term in ("FOMC", "FED", "POWELL", "INTEREST RATE")):
        return "Central Bank"

    if any(term in upper for term in ("CPI", "PPI", "PCE", "INFLATION")):
        return "Inflation"

    if any(term in upper for term in ("NFP", "PAYROLL", "JOBLESS", "UNEMPLOYMENT", "JOLTS")):
        return "Employment"

    if any(term in upper for term in ("GDP", "RETAIL", "ISM", "PMI", "CONFIDENCE")):
        return "Growth"

    if any(term in upper for term in ("TREASURY", "AUCTION", "BOND", "NOTE")):
        return "Rates"

    return "Macro"


def infer_importance(name: str, raw_importance: Any = None) -> str:
    importance = normalize_importance(raw_importance)

    if importance != "UNKNOWN":
        return importance

    upper = str(name or "").upper()

    if any(keyword in upper for keyword in HIGH_IMPACT_KEYWORDS):
        return "HIGH"

    if any(keyword in upper for keyword in MEDIUM_IMPACT_KEYWORDS):
        return "MEDIUM"

    return "LOW"


# =========================================================
# LOCAL CSV LOADER
# =========================================================

def project_root() -> Path:
    # engines/economic_calendar.py -> project root is parent of engines.
    return Path(__file__).resolve().parents[1]


def resolve_calendar_path(path: Optional[str | Path] = None) -> Path:
    if path is None:
        candidate = project_root() / LOCAL_CALENDAR_PATH
    else:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = project_root() / candidate

    return candidate


def local_row_to_event(row: Dict[str, Any]) -> Optional[EconomicEvent]:
    if not isinstance(row, dict):
        return None

    name = clean_text(
        row.get("event")
        or row.get("name")
        or row.get("title")
        or row.get("indicator")
    )

    if not name:
        return None

    event_time = parse_datetime(
        row.get("date")
        or row.get("datetime")
        or row.get("event_time")
        or row.get("time")
    )

    if event_time is None:
        return None

    country = clean_text(
        row.get("country")
        or row.get("region")
        or "United States"
    )

    importance = infer_importance(
        name,
        row.get("importance")
        or row.get("impact")
        or row.get("priority"),
    )

    category = clean_text(
        row.get("category")
        or row.get("type")
        or infer_category(name)
    )

    source = normalize_source(
        row.get("source")
        or "LOCAL"
    )

    if source in DEMO_SOURCES:
        source = "LOCAL"

    previous = row.get("previous")
    forecast = row.get("forecast")
    actual = row.get("actual")

    return EconomicEvent(
        name=name,
        country=country or "United States",
        event_time=event_time,
        importance=importance,
        category=category,
        source=source,
        previous=None if previous in (None, "") else str(previous),
        forecast=None if forecast in (None, "") else str(forecast),
        actual=None if actual in (None, "") else str(actual),
    )


def local_events(
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    lookahead_days: int = DEFAULT_LOOKAHEAD_DAYS,
    path: Optional[str | Path] = None,
) -> List[EconomicEvent]:
    csv_path = resolve_calendar_path(path)

    if not csv_path.exists():
        return []

    now = utc_now()
    start = now - timedelta(days=lookback_days)
    end = now + timedelta(days=lookahead_days)

    events: List[EconomicEvent] = []

    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            event = local_row_to_event(row)

            if event is None:
                continue

            if start <= event.event_time <= end:
                events.append(event)

    events = sorted(
        events,
        key=lambda item: item.event_time,
    )

    return events


def get_calendar_events(
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    lookahead_days: int = DEFAULT_LOOKAHEAD_DAYS,
    fallback_to_demo: bool = False,
) -> List[EconomicEvent]:
    # fallback_to_demo is preserved for backward compatibility, but v4 does
    # not return DEMO events. Missing CSV returns an empty calendar.
    return local_events(
        lookback_days=lookback_days,
        lookahead_days=lookahead_days,
    )


def sample_events() -> List[EconomicEvent]:
    # Backward-compatible scanner entrypoint.
    return get_calendar_events()


def calendar_mode() -> str:
    events = get_calendar_events()

    if not events:
        return "NONE"

    sources = {
        normalize_source(event.source)
        for event in events
    }

    if sources.issubset(LOCAL_SOURCES):
        return "LOCAL"

    if all(is_demo_event(event) for event in events):
        return "DEMO"

    return ", ".join(sorted(sources))


# =========================================================
# CORE EVENT RISK LOGIC — v4 TIME DECAY
# =========================================================

def event_is_market_relevant(event: EconomicEvent) -> bool:
    if is_demo_event(event):
        return False

    name = str(event.name or "").upper()

    if normalize_importance(event.importance) == "HIGH":
        return True

    return any(
        keyword in name
        for keyword in HIGH_IMPACT_KEYWORDS
    )


def time_decay_cap(hours: float) -> int:
    """
    v4 proximity cap.

    < 24h     -> EXTREME cap
    24-72h    -> HIGH cap
    72-168h   -> MEDIUM cap
    > 168h    -> LOW cap
    Past      -> no active risk
    """

    if hours < 0:
        return 0

    if hours <= 24:
        return 85

    if hours <= 72:
        return 60

    if hours <= 168:
        return 35

    return 15


def raw_importance_score(event: EconomicEvent) -> int:
    importance = normalize_importance(event.importance)

    if importance == "HIGH":
        score = 75
    elif importance == "MEDIUM":
        score = 45
    elif importance == "LOW":
        score = 20
    else:
        score = 10

    if event_is_market_relevant(event):
        score += 5

    return min(score, 100)


def economic_event_risk_score(event: EconomicEvent) -> int:
    if is_demo_event(event):
        return 0

    hrs = hours_until(event.event_time)

    if hrs < 0:
        return 0

    raw_score = raw_importance_score(event)
    cap = time_decay_cap(hrs)

    return int(min(raw_score, cap))


def economic_risk_label(score: int) -> str:
    if score >= 80:
        return "EXTREME"

    if score >= 60:
        return "HIGH"

    if score >= 35:
        return "MEDIUM"

    if score > 0:
        return "LOW"

    return "NONE"


def analyze_economic_calendar(
    events: List[EconomicEvent],
) -> Dict[str, object]:

    events = [
        event for event in events
        if isinstance(event, EconomicEvent)
    ]

    rows: List[Dict[str, object]] = []
    max_score = 0
    highest_event = None

    for event in events:
        score = economic_event_risk_score(event)
        hrs = hours_until(event.event_time)

        row = asdict(event)
        row["event_time"] = event.event_time.isoformat()
        row["hours_until"] = hrs
        row["risk_score"] = score
        row["risk_label"] = economic_risk_label(score)
        row["market_relevant"] = event_is_market_relevant(event)
        row["source"] = normalize_source(event.source)
        row["time_decay_cap"] = time_decay_cap(hrs)

        rows.append(row)

        if score > max_score:
            max_score = score
            highest_event = row

    if highest_event is None and rows:
        highest_event = rows[0]

    sources = sorted(
        {
            str(row.get("source", "UNKNOWN")).upper()
            for row in rows
            if isinstance(row, dict)
        }
    )

    calendar_source = (
        ", ".join(sources)
        if sources
        else "NONE"
    )

    return {
        "economic_risk_score": max_score,
        "economic_risk_label": economic_risk_label(max_score),
        "highest_risk_event": highest_event,
        "events": rows,
        "calendar_source": calendar_source,
        "source": calendar_source,
        "is_demo_mode": False,
        "event_count": len(rows),
    }


# =========================================================
# SCANNER / OMS RISK ADJUSTMENT
# =========================================================

def apply_economic_risk_adjustment(
    base_buy_threshold: float,
    base_position_size: float,
    economic_risk_score: int,
) -> Dict[str, float]:

    buy_threshold = float(base_buy_threshold)
    position_size = float(base_position_size)

    if economic_risk_score >= 80:
        buy_threshold += 0.10
        position_size *= 0.25

    elif economic_risk_score >= 60:
        buy_threshold += 0.05
        position_size *= 0.50

    elif economic_risk_score >= 35:
        buy_threshold += 0.025
        position_size *= 0.75

    return {
        "adjusted_buy_threshold": round(buy_threshold, 4),
        "adjusted_position_size": round(position_size, 4),
    }


# =========================================================
# SELF TEST
# =========================================================

if __name__ == "__main__":
    result = analyze_economic_calendar(
        get_calendar_events()
    )

    print(result)
