# =========================================================
# JFBP QUANT DESK — SIGNAL WATCHER v2.0 SCANNER-INTEGRATED
# Background BUY-signal alert engine — Scanner BUY logic embedded
# ---------------------------------------------------------
# Purpose:
#   Runs independently from Streamlit so BUY alerts can fire
#   even when the Scanner page is not open.
#
# What it does:
#   ✅ Scans JFBP universe stocks on a timer
#   ✅ Uses the Scanner Page research-model BUY conditions
#   ✅ Detects BUY / STRONG BUY transitions
#   ✅ Blocks duplicate alerts
#   ✅ Sends Telegram alerts
#   ✅ Logs every scan and alert to CSV
#
# What it does NOT do:
#   ❌ No OMS routing
#   ❌ No IBKR orders
#   ❌ No paper trading
#   ❌ No live trading
# =========================================================

from __future__ import annotations

import csv
import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import yfinance as yf


# =========================================================
# CONFIG
# =========================================================

APP_ROOT = Path(__file__).resolve().parents[1] if len(Path(__file__).resolve().parents) > 1 else Path.cwd()
DATA_DIR = APP_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "signal_watcher_state.json"
SCAN_LOG_FILE = DATA_DIR / "signal_watcher_scans.csv"
ALERT_LOG_FILE = DATA_DIR / "signal_watcher_alerts.csv"

DEFAULT_SCAN_INTERVAL_MINUTES = 5
DEFAULT_MARKET_OPEN_ONLY = False
DEFAULT_ALERT_ON = {"BUY", "STRONG BUY"}
DEFAULT_DEDUP_MODE = "symbol_signal_day"  # symbol_signal_day | symbol_day | symbol_signal_price_day

WATCHER_VERSION = "v2.0-scanner-integrated"
WATCHER_SOURCE = "jfbp_signal_watcher_v2_scanner_integrated"


# =========================================================
# OPTIONAL UNIVERSE IMPORT
# =========================================================

try:
    from universe.jfbp_universe import JFBP_UNIVERSE  # type: ignore
except Exception:
    JFBP_UNIVERSE = {}


# =========================================================
# FALLBACK UNIVERSE
# =========================================================

def fallback_universe() -> Dict[str, Dict[str, Any]]:
    return {
        "SPY": {"sector": "ETF", "liquidity": 5, "volatility": 2, "regime": ["benchmark"]},
        "QQQ": {"sector": "ETF", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
        "IWM": {"sector": "ETF", "liquidity": 4, "volatility": 3, "regime": ["small_caps"]},
        "DIA": {"sector": "ETF", "liquidity": 4, "volatility": 2, "regime": ["blue_chip"]},
        "AAPL": {"sector": "Technology", "liquidity": 5, "volatility": 2, "regime": ["defensive_growth"]},
        "MSFT": {"sector": "Technology", "liquidity": 5, "volatility": 2, "regime": ["defensive_growth"]},
        "NVDA": {"sector": "Technology", "liquidity": 5, "volatility": 4, "regime": ["momentum"]},
        "AMZN": {"sector": "Consumer Discretionary", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
        "META": {"sector": "Communication Services", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
        "GOOGL": {"sector": "Communication Services", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
        "AVGO": {"sector": "Semiconductors", "liquidity": 5, "volatility": 3, "regime": ["semis"]},
        "AMD": {"sector": "Semiconductors", "liquidity": 5, "volatility": 4, "regime": ["semis"]},
        "ARM": {"sector": "Semiconductors", "liquidity": 4, "volatility": 5, "regime": ["semis"]},
        "JPM": {"sector": "Financials", "liquidity": 5, "volatility": 2, "regime": ["financial"]},
    }


def get_active_universe() -> Dict[str, Dict[str, Any]]:
    if isinstance(JFBP_UNIVERSE, dict) and JFBP_UNIVERSE:
        return JFBP_UNIVERSE
    return fallback_universe()


# =========================================================
# DATA MODELS
# =========================================================

@dataclass
class WatcherConfig:
    scan_interval_minutes: int = DEFAULT_SCAN_INTERVAL_MINUTES
    market_open_only: bool = DEFAULT_MARKET_OPEN_ONLY
    alert_on: Tuple[str, ...] = tuple(sorted(DEFAULT_ALERT_ON))
    dedup_mode: str = DEFAULT_DEDUP_MODE
    min_opportunity_score_pct: float = 60.0
    max_symbols_per_scan: int = 250
    telegram_enabled: bool = True
    dry_run: bool = False


@dataclass
class SignalRow:
    timestamp: str
    symbol: str
    data_symbol: str
    sector: str
    signal: str
    trade_recommendation: str
    price: float
    model_score: int
    opportunity_score_pct: float
    trend: str
    rs_score: Optional[float]
    ma20: Optional[float]
    ma50: Optional[float]
    support: Optional[float]
    resistance: Optional[float]
    source: str = WATCHER_SOURCE
    reason: str = ""


# =========================================================
# UTILS
# =========================================================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def local_now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def normalize_action(value: Any) -> str:
    action = str(value or "").upper().strip()
    mapping = {
        "LONG": "BUY",
        "BUY_LONG": "BUY",
        "ENTER_LONG": "BUY",
        "BULLISH": "BUY",
        "SHORT": "SELL",
        "SELL_SHORT": "SELL",
        "ENTER_SHORT": "SELL",
        "BEARISH": "SELL",
        "NO TRADE": "HOLD",
        "NO_TRADE": "HOLD",
        "NONE": "HOLD",
        "FLAT": "HOLD",
        "NEUTRAL": "HOLD",
        "": "HOLD",
    }
    return mapping.get(action, action)


def normalize_meta(symbol: str, meta: Any) -> Dict[str, Any]:
    symbol = str(symbol or "").upper().strip()
    if not isinstance(meta, dict):
        meta = {}

    raw_data_symbol = meta.get("data_symbol")
    raw_data_symbols = meta.get("data_symbols", [])

    if isinstance(raw_data_symbols, str):
        raw_data_symbols = [raw_data_symbols]
    if not isinstance(raw_data_symbols, (list, tuple)):
        raw_data_symbols = []

    candidates = []
    if raw_data_symbol:
        candidates.append(raw_data_symbol)
    candidates.extend(raw_data_symbols)
    candidates.append(symbol)

    data_symbols = []
    for item in candidates:
        item = str(item or "").upper().strip()
        if item and item not in data_symbols:
            data_symbols.append(item)

    regime = meta.get("regime", [])

    return {
        "symbol": symbol,
        "data_symbol": data_symbols[0] if data_symbols else symbol,
        "data_symbols": data_symbols or [symbol],
        "sector": meta.get("sector", "Unknown"),
        "liquidity": int(meta.get("liquidity", 3) or 3),
        "volatility": int(meta.get("volatility", 3) or 3),
        "regime": ",".join(regime) if isinstance(regime, list) else str(regime),
    }


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = ["_".join([str(i) for i in col if i]) for col in frame.columns]
    return frame


def find_col(frame: pd.DataFrame, name: str) -> Optional[str]:
    exact = [c for c in frame.columns if str(c).lower() == name.lower()]
    if exact:
        return exact[0]
    matches = [c for c in frame.columns if name.lower() in str(c).lower()]
    return matches[0] if matches else None


def load_symbol_data(symbol: str) -> pd.DataFrame:
    return yf.download(
        symbol,
        period="6mo",
        interval="1d",
        progress=False,
        auto_adjust=False,
        threads=False,
    )


def load_benchmark_data() -> pd.DataFrame:
    return yf.download(
        "SPY",
        period="6mo",
        interval="1d",
        progress=False,
        auto_adjust=False,
        threads=False,
    )


def load_first_valid_symbol(display_symbol: str, meta: Dict[str, Any]) -> Tuple[str, pd.DataFrame, List[str]]:
    attempted = []
    last_error = "No stock data"
    for data_symbol in meta.get("data_symbols", [display_symbol]):
        data_symbol = str(data_symbol or "").upper().strip()
        if not data_symbol:
            continue
        attempted.append(data_symbol)
        try:
            df = load_symbol_data(data_symbol)
            if df is not None and not df.empty:
                return data_symbol, df, attempted
        except Exception as exc:
            last_error = str(exc)
    raise RuntimeError(last_error)


# =========================================================
# SCANNER MODEL — MATCHES SCANNER PAGE BUY LOGIC
# =========================================================

def research_model_signal(symbol: str, meta: Dict[str, Any], benchmark: pd.DataFrame) -> SignalRow:
    symbol = str(symbol or "").upper().strip()
    meta = normalize_meta(symbol, meta)
    data_symbol = meta.get("data_symbol", symbol)

    try:
        data_symbol, df, attempted_symbols = load_first_valid_symbol(symbol, meta)

        if benchmark is None or benchmark.empty:
            raise RuntimeError("No benchmark data")

        df = normalize_columns(df)
        benchmark = normalize_columns(benchmark)

        close_col = find_col(df, "Close")
        high_col = find_col(df, "High")
        low_col = find_col(df, "Low")
        open_col = find_col(df, "Open")
        bench_close_col = find_col(benchmark, "Close")

        if close_col is None:
            raise RuntimeError("Missing close column")
        if bench_close_col is None:
            raise RuntimeError("Missing benchmark close column")

        df["Open"] = pd.to_numeric(df[open_col] if open_col else df[close_col], errors="coerce")
        df["High"] = pd.to_numeric(df[high_col] if high_col else df[close_col], errors="coerce")
        df["Low"] = pd.to_numeric(df[low_col] if low_col else df[close_col], errors="coerce")
        df["Close"] = pd.to_numeric(df[close_col], errors="coerce")
        benchmark["Benchmark"] = pd.to_numeric(benchmark[bench_close_col], errors="coerce")

        df = df.sort_index()
        benchmark = benchmark.sort_index()
        df = df[~df.index.duplicated(keep="last")]
        benchmark = benchmark[~benchmark.index.duplicated(keep="last")]

        df = df.join(benchmark[["Benchmark"]], how="left")
        df["Benchmark"] = df["Benchmark"].ffill().bfill()
        df = df.dropna(subset=["Open", "High", "Low", "Close", "Benchmark"])

        if len(df) < 30:
            raise RuntimeError("Not enough historical data")

        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA50"] = df["Close"].rolling(50).mean() if len(df) >= 50 else df["MA20"]
        df["RS"] = df["Close"] / df["Benchmark"]
        df["RS_MA20"] = df["RS"].rolling(20).mean()
        df["RS_SCORE"] = df["RS"] / df["RS_MA20"]
        df["20D_HIGH"] = df["High"].rolling(20).max()
        df["20D_LOW"] = df["Low"].rolling(20).min()

        df = df.dropna(subset=["Close", "MA20", "MA50", "RS_SCORE", "20D_HIGH", "20D_LOW"])
        if df.empty or len(df) < 2:
            raise RuntimeError("Not enough clean indicator data")

        latest_close = round(float(df["Close"].iloc[-1]), 2)
        previous_close = round(float(df["Close"].iloc[-2]), 2)
        latest_ma20 = round(float(df["MA20"].iloc[-1]), 2)
        latest_ma50 = round(float(df["MA50"].iloc[-1]), 2)
        latest_rs_score = round(float(df["RS_SCORE"].iloc[-1]), 4)
        latest_20d_high = round(float(df["20D_HIGH"].iloc[-1]), 2)
        latest_20d_low = round(float(df["20D_LOW"].iloc[-1]), 2)

        above_ma20 = latest_close > latest_ma20
        above_ma50 = latest_close > latest_ma50
        improving_today = latest_close > previous_close
        strong_rs = latest_rs_score >= 1.05
        near_high = latest_close >= latest_20d_high * 0.98

        weak_rs = latest_rs_score <= 0.97
        below_ma20 = latest_close < latest_ma20
        below_ma50 = latest_close < latest_ma50
        falling_today = latest_close < previous_close

        model_score = 0
        model_score += 1 if above_ma20 else 0
        model_score += 1 if above_ma50 else 0
        model_score += 1 if improving_today else 0
        model_score += 1 if strong_rs else 0
        model_score += 1 if near_high else 0

        if above_ma20 and above_ma50 and improving_today and strong_rs and near_high:
            signal = "BUY"
        elif below_ma20 and below_ma50 and falling_today and weak_rs:
            signal = "SELL"
        else:
            signal = "NO TRADE"

        trend = "BULLISH" if above_ma20 and above_ma50 else "BEARISH"

        # Lightweight opportunity score for alert filtering.
        score = 0
        if trend == "BULLISH":
            score += 1
        if latest_rs_score >= 1.05:
            score += 1
        if model_score >= 4:
            score += 1
        if signal == "BUY":
            score += 1
        if near_high:
            score += 1

        opportunity_score_pct = round((score / 5) * 100.0, 1)

        if signal == "BUY" and opportunity_score_pct >= 80:
            trade_recommendation = "STRONG BUY"
        elif signal == "BUY":
            trade_recommendation = "BUY"
        elif trend == "BULLISH" and opportunity_score_pct >= 60:
            trade_recommendation = "WATCH"
        elif signal == "SELL":
            trade_recommendation = "SELL"
        else:
            trade_recommendation = "WATCH"

        return SignalRow(
            timestamp=utc_now_iso(),
            symbol=symbol,
            data_symbol=data_symbol,
            sector=str(meta.get("sector", "Unknown")),
            signal=signal,
            trade_recommendation=trade_recommendation,
            price=latest_close,
            model_score=model_score,
            opportunity_score_pct=opportunity_score_pct,
            trend=trend,
            rs_score=latest_rs_score,
            ma20=latest_ma20,
            ma50=latest_ma50,
            support=latest_20d_low,
            resistance=latest_20d_high,
            reason="; ".join([f"attempted={','.join(attempted_symbols)}"]),
        )

    except Exception as exc:
        return SignalRow(
            timestamp=utc_now_iso(),
            symbol=symbol,
            data_symbol=data_symbol,
            sector=str(meta.get("sector", "Unknown")),
            signal="NO TRADE",
            trade_recommendation="WATCH",
            price=0.0,
            model_score=0,
            opportunity_score_pct=0.0,
            trend="UNKNOWN",
            rs_score=None,
            ma20=None,
            ma50=None,
            support=None,
            resistance=None,
            source=f"{WATCHER_SOURCE}_error_safe",
            reason=str(exc),
        )


# =========================================================
# STATE / LOGGING
# =========================================================

def read_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {"last_signal_by_symbol": {}, "alert_keys": [], "stats": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"last_signal_by_symbol": {}, "alert_keys": [], "stats": {}}


def write_state(state: Dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def append_csv(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def alert_key(row: SignalRow, config: WatcherConfig) -> str:
    today = date.today().isoformat()
    signal = row.trade_recommendation.upper().strip()
    if config.dedup_mode == "symbol_day":
        return f"{today}|{row.symbol}"
    if config.dedup_mode == "symbol_signal_price_day":
        return f"{today}|{row.symbol}|{signal}|{row.price}"
    return f"{today}|{row.symbol}|{signal}"


def should_alert(row: SignalRow, state: Dict[str, Any], config: WatcherConfig) -> Tuple[bool, str]:
    recommendation = row.trade_recommendation.upper().strip()
    signal = row.signal.upper().strip()

    if recommendation not in set(config.alert_on):
        return False, f"Not alertable recommendation: {recommendation}"

    if row.opportunity_score_pct < float(config.min_opportunity_score_pct):
        return False, f"Score below threshold: {row.opportunity_score_pct}"

    last_by_symbol = state.setdefault("last_signal_by_symbol", {})
    previous = str(last_by_symbol.get(row.symbol, "")).upper().strip()

    # Alert only when the ticker changes into BUY/STRONG BUY territory.
    if previous in set(config.alert_on):
        return False, f"Duplicate state blocked: previous={previous}"

    key = alert_key(row, config)
    alert_keys = set(state.setdefault("alert_keys", []))
    if key in alert_keys:
        return False, "Duplicate alert key blocked"

    if signal != "BUY":
        return False, f"Research model signal is not BUY: {signal}"

    return True, "NEW BUY transition"


def update_signal_state(rows: Iterable[SignalRow], state: Dict[str, Any], config: WatcherConfig) -> None:
    last_by_symbol = state.setdefault("last_signal_by_symbol", {})
    for row in rows:
        last_by_symbol[row.symbol] = row.trade_recommendation.upper().strip()

    # Keep alert keys from growing forever: retain current day only.
    today_prefix = date.today().isoformat() + "|"
    state["alert_keys"] = [key for key in state.get("alert_keys", []) if str(key).startswith(today_prefix)]


def mark_alerted(row: SignalRow, state: Dict[str, Any], config: WatcherConfig) -> None:
    keys = state.setdefault("alert_keys", [])
    key = alert_key(row, config)
    if key not in keys:
        keys.append(key)


# =========================================================
# TELEGRAM
# =========================================================

def telegram_credentials() -> Tuple[str, str]:
    token = os.getenv("JFBP_TELEGRAM_BOT_TOKEN", "").strip() or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("JFBP_TELEGRAM_CHAT_ID", "").strip() or os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return token, chat_id


def send_telegram_message(text: str, dry_run: bool = False) -> Tuple[bool, str]:
    if dry_run:
        print("\n[DRY RUN TELEGRAM]\n" + text + "\n")
        return True, "DRY_RUN"

    token, chat_id = telegram_credentials()
    if not token or not chat_id:
        return False, "Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID environment variables"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")

    try:
        request = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
        return True, body[:250]
    except Exception as exc:
        return False, str(exc)


def format_alert(row: SignalRow) -> str:
    return "\n".join(
        [
            "🚨 JFBP BUY SIGNAL",
            "",
            f"Symbol: {row.symbol}",
            f"Recommendation: {row.trade_recommendation}",
            f"Price: ${row.price:,.2f}",
            f"Sector: {row.sector}",
            f"Score: {row.opportunity_score_pct:.1f}/100",
            f"Model Score: {row.model_score}/5",
            f"Trend: {row.trend}",
            f"RS Score: {row.rs_score if row.rs_score is not None else 'N/A'}",
            f"Support: {row.support if row.support is not None else 'N/A'}",
            f"Resistance: {row.resistance if row.resistance is not None else 'N/A'}",
            "",
            f"Time: {local_now_text()}",
            "",
            "Signal Watcher only — no order sent.",
        ]
    )


# =========================================================
# SCAN ENGINE
# =========================================================

def run_scan(config: WatcherConfig) -> Dict[str, Any]:
    universe = get_active_universe()
    symbols = list(universe.keys())[: int(config.max_symbols_per_scan)]
    state = read_state()

    started = utc_now_iso()
    benchmark = load_benchmark_data()

    rows: List[SignalRow] = []
    alerts_sent = 0
    duplicates_blocked = 0
    errors = 0

    print(f"[{local_now_text()}] Signal Watcher scan started: {len(symbols)} symbols")

    for symbol in symbols:
        meta = universe.get(symbol, {})
        row = research_model_signal(symbol, meta, benchmark)
        rows.append(row)

        if row.source.endswith("error_safe"):
            errors += 1

        ok, reason = should_alert(row, state, config)

        if ok:
            alert_text = format_alert(row)
            sent, send_status = send_telegram_message(alert_text, dry_run=config.dry_run or not config.telegram_enabled)

            append_csv(
                ALERT_LOG_FILE,
                {
                    "timestamp": utc_now_iso(),
                    "symbol": row.symbol,
                    "data_symbol": row.data_symbol,
                    "sector": row.sector,
                    "signal": row.signal,
                    "trade_recommendation": row.trade_recommendation,
                    "price": row.price,
                    "model_score": row.model_score,
                    "opportunity_score_pct": row.opportunity_score_pct,
                    "telegram_sent": "YES" if sent else "NO",
                    "telegram_status": send_status,
                    "dedup_key": alert_key(row, config),
                    "source": row.source,
                },
            )

            mark_alerted(row, state, config)
            alerts_sent += 1
            print(f"  ALERT {row.symbol} {row.trade_recommendation} @ {row.price}: {send_status}")

        elif row.trade_recommendation.upper().strip() in set(config.alert_on):
            duplicates_blocked += 1
            print(f"  BLOCKED {row.symbol}: {reason}")

    update_signal_state(rows, state, config)

    stats = state.setdefault("stats", {})
    stats.update(
        {
            "watcher_version": WATCHER_VERSION,
            "last_scan_started": started,
            "last_scan_finished": utc_now_iso(),
            "last_scan_symbol_count": len(symbols),
            "last_scan_rows": len(rows),
            "last_scan_alerts_sent": alerts_sent,
            "last_scan_duplicates_blocked": duplicates_blocked,
            "last_scan_errors": errors,
            "last_scan_interval_minutes": config.scan_interval_minutes,
            "last_scan_status": "OK",
        }
    )

    write_state(state)

    append_csv(
        SCAN_LOG_FILE,
        {
            "timestamp": utc_now_iso(),
            "symbols_scanned": len(symbols),
            "rows": len(rows),
            "alerts_sent": alerts_sent,
            "duplicates_blocked": duplicates_blocked,
            "errors": errors,
            "scan_interval_minutes": config.scan_interval_minutes,
            "source": WATCHER_SOURCE,
        },
    )

    print(
        f"[{local_now_text()}] Scan finished: alerts={alerts_sent}, duplicates={duplicates_blocked}, errors={errors}"
    )

    return stats.copy()


def run_forever(config: WatcherConfig) -> None:
    interval_seconds = max(30, int(config.scan_interval_minutes) * 60)
    print("=" * 70)
    print(f"JFBP Signal Watcher {WATCHER_VERSION}")
    print(f"Interval: {config.scan_interval_minutes} minute(s)")
    print(f"Telegram enabled: {config.telegram_enabled}")
    print(f"Dry run: {config.dry_run}")
    print("No OMS. No IBKR. No orders. Alerts only.")
    print("=" * 70)

    while True:
        try:
            run_scan(config)
        except KeyboardInterrupt:
            print("Signal Watcher stopped by user.")
            break
        except Exception as exc:
            state = read_state()
            stats = state.setdefault("stats", {})
            stats.update(
                {
                    "last_scan_finished": utc_now_iso(),
                    "last_scan_status": f"ERROR: {exc}",
                }
            )
            write_state(state)
            print(f"[{local_now_text()}] ERROR: {exc}")

        time.sleep(interval_seconds)


# =========================================================
# CLI
# =========================================================

def parse_config_from_env() -> WatcherConfig:
    interval = int(os.getenv("JFBP_SIGNAL_WATCHER_INTERVAL_MINUTES", DEFAULT_SCAN_INTERVAL_MINUTES))
    min_score = float(os.getenv("JFBP_SIGNAL_WATCHER_MIN_SCORE", "60"))
    max_symbols = int(os.getenv("JFBP_SIGNAL_WATCHER_MAX_SYMBOLS", "250"))
    dry_run = os.getenv("JFBP_SIGNAL_WATCHER_DRY_RUN", "0").strip().lower() in ("1", "true", "yes", "y")
    telegram_enabled = os.getenv("JFBP_SIGNAL_WATCHER_TELEGRAM", "1").strip().lower() not in ("0", "false", "no", "n")

    return WatcherConfig(
        scan_interval_minutes=interval,
        min_opportunity_score_pct=min_score,
        max_symbols_per_scan=max_symbols,
        telegram_enabled=telegram_enabled,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    config = parse_config_from_env()
    run_forever(config)
