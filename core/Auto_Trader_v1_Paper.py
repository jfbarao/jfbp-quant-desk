# =========================================================
# JFBP QUANT DESK — QUANT EXECUTOR v1.1 PAPER
# Signal Watcher → Paper Execution + Exit Engine
# ---------------------------------------------------------
# Purpose:
#   Runs independently from Streamlit and watches Signal Watcher alerts.
#   When a NEW BUY / STRONG BUY alert appears, it creates a PAPER trade.
#   While positions are open, it manages exits in PAPER mode only.
#
# What it does:
#   ✅ Reads data/signal_watcher_alerts.csv for BUY / STRONG BUY entries
#   ✅ Reads data/signal_watcher_signal_log.csv when available for signal exits
#   ✅ Executes PAPER entries only — no broker orders
#   ✅ Manages PAPER exits:
#        1. Stop Loss
#        2. Trailing Stop
#        3. Take Profit
#        4. Signal Exit
#   ✅ Blocks duplicate paper entries
#   ✅ Writes paper orders, fills, positions, closed trades, and state files
#   ✅ Sends Telegram paper entry and exit confirmations
#   ✅ Publishes dashboard-ready performance statistics
#
# What it does NOT do:
#   ❌ No live IBKR orders
#   ❌ No OMS LIVE routing
#   ❌ No real broker orders
#   ❌ No short selling
# =========================================================

from __future__ import annotations

import csv
import json
import math
import os
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# =========================================================
# PATHS / CONFIG
# =========================================================

APP_ROOT = Path(__file__).resolve().parents[1] if len(Path(__file__).resolve().parents) > 1 else Path.cwd()
DATA_DIR = APP_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SIGNAL_ALERT_LOG_FILE = DATA_DIR / "signal_watcher_alerts.csv"
SIGNAL_LOG_FILE = DATA_DIR / "signal_watcher_signal_log.csv"

AUTO_TRADER_STATE_FILE = DATA_DIR / "auto_trader_paper_state.json"
AUTO_TRADER_CONFIG_FILE = DATA_DIR / "auto_trader_paper_config.json"
AUTO_TRADER_ORDER_LOG_FILE = DATA_DIR / "auto_trader_paper_orders.csv"
AUTO_TRADER_FILL_LOG_FILE = DATA_DIR / "auto_trader_paper_fills.csv"
AUTO_TRADER_POSITION_FILE = DATA_DIR / "auto_trader_paper_positions.json"
AUTO_TRADER_EVENT_LOG_FILE = DATA_DIR / "auto_trader_paper_events.csv"
AUTO_TRADER_CLOSED_TRADE_LOG_FILE = DATA_DIR / "auto_trader_paper_closed_trades.csv"

AUTO_TRADER_VERSION = "v1.1-paper-exit-engine"
AUTO_TRADER_SOURCE = "jfbp_quant_executor_v1_1_paper"


# =========================================================
# DATA MODELS
# =========================================================

@dataclass
class PaperConfig:
    enabled: bool = True
    poll_interval_seconds: int = 10
    paper_account_value: float = 100000.0
    buy_allocation_dollars: float = 5000.0
    strong_buy_allocation_dollars: float = 10000.0
    max_open_positions: int = 10
    max_daily_trades: int = 5
    max_position_dollars: float = 10000.0
    min_score: float = 60.0
    allow_pyramiding: bool = False
    telegram_enabled: bool = True
    dry_run: bool = False

    # Quant Executor v1.1 Exit Engine
    exit_engine_enabled: bool = True
    stop_loss_pct: float = 8.0
    take_profit_pct: float = 15.0
    trailing_activation_pct: float = 10.0
    trailing_stop_pct: float = 10.0
    signal_exit_enabled: bool = True


# =========================================================
# UTILITIES
# =========================================================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def local_now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "").replace("%", "").strip()
            if not value:
                return default
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def append_csv(path: Path, row: Dict[str, Any]) -> None:
    """Append a row while tolerating schema expansion across versions.

    Older v1.0 files may already exist with fewer columns. When v1.1 adds
    columns, this function rewrites the file with a union header so pandas can
    still read it cleanly later.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    clean_row = {str(k): v for k, v in row.items()}

    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(clean_row.keys()), extrasaction="ignore")
            writer.writeheader()
            writer.writerow(clean_row)
        return

    try:
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            old_fields = list(reader.fieldnames or [])
            old_rows = list(reader)
    except Exception:
        old_fields = []
        old_rows = []

    new_fields = old_fields[:]
    for key in clean_row.keys():
        if key not in new_fields:
            new_fields.append(key)

    if not new_fields:
        new_fields = list(clean_row.keys())

    old_rows.append(clean_row)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=new_fields, extrasaction="ignore")
        writer.writeheader()
        for old_row in old_rows:
            writer.writerow({field: old_row.get(field, "") for field in new_fields})


def read_config() -> PaperConfig:
    raw = read_json(AUTO_TRADER_CONFIG_FILE, {})
    if not isinstance(raw, dict):
        raw = {}
    config = PaperConfig()
    changed = False
    for key, value in raw.items():
        if hasattr(config, key):
            setattr(config, key, value)
    for key, value in asdict(config).items():
        if key not in raw:
            raw[key] = value
            changed = True
    if changed and AUTO_TRADER_CONFIG_FILE.exists():
        write_json(AUTO_TRADER_CONFIG_FILE, raw)
    return config


def ensure_config_exists() -> PaperConfig:
    config = read_config()
    if not AUTO_TRADER_CONFIG_FILE.exists():
        write_json(AUTO_TRADER_CONFIG_FILE, asdict(config))
    return config


def read_state() -> Dict[str, Any]:
    default = {
        "version": AUTO_TRADER_VERSION,
        "processed_alert_keys": [],
        "daily_trade_counts": {},
        "stats": {},
    }
    state = read_json(AUTO_TRADER_STATE_FILE, default)
    if not isinstance(state, dict):
        state = default
    state.setdefault("processed_alert_keys", [])
    state.setdefault("daily_trade_counts", {})
    state.setdefault("stats", {})
    return state


def write_state(state: Dict[str, Any]) -> None:
    state["version"] = AUTO_TRADER_VERSION
    write_json(AUTO_TRADER_STATE_FILE, state)


def read_positions() -> Dict[str, Dict[str, Any]]:
    positions = read_json(AUTO_TRADER_POSITION_FILE, {})
    return positions if isinstance(positions, dict) else {}


def write_positions(positions: Dict[str, Dict[str, Any]]) -> None:
    write_json(AUTO_TRADER_POSITION_FILE, positions)


def read_csv_df(path: Path) -> pd.DataFrame:
    try:
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_csv(path)
        return df if not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def alert_dataframe() -> pd.DataFrame:
    return read_csv_df(SIGNAL_ALERT_LOG_FILE)


def signal_dataframe() -> pd.DataFrame:
    return read_csv_df(SIGNAL_LOG_FILE)


def closed_trades_dataframe() -> pd.DataFrame:
    return read_csv_df(AUTO_TRADER_CLOSED_TRADE_LOG_FILE)


def alert_execution_key(row: Dict[str, Any]) -> str:
    dedup_key = str(row.get("dedup_key") or "").strip()
    if dedup_key:
        return dedup_key
    return "|".join([
        str(row.get("timestamp") or ""),
        str(row.get("symbol") or ""),
        str(row.get("trade_recommendation") or ""),
        str(row.get("price") or ""),
    ])


def parse_timestamp(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


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


def format_paper_entry_message(fill: Dict[str, Any]) -> str:
    return "\n".join([
        "🧠 QUANT EXECUTOR ENTRY",
        "",
        f"Symbol: {fill.get('symbol')}",
        f"Action: {fill.get('action')}",
        f"Quantity: {fill.get('qty')}",
        f"Entry: ${safe_float(fill.get('fill_price')):,.2f}",
        f"Notional: ${safe_float(fill.get('notional')):,.2f}",
        f"Signal: {fill.get('trade_recommendation')}",
        f"Score: {fill.get('opportunity_score_pct')}",
        "",
        f"Time: {local_now_text()}",
        "",
        "PAPER only — no live order sent.",
    ])


def format_paper_exit_message(fill: Dict[str, Any]) -> str:
    pnl_pct = safe_float(fill.get("pnl_pct"), 0.0)
    pnl_dollars = safe_float(fill.get("realized_pnl"), 0.0)
    return "\n".join([
        "🧠 QUANT EXECUTOR EXIT",
        "",
        f"Symbol: {fill.get('symbol')}",
        "Action: SELL",
        "",
        "Reason:",
        str(fill.get("exit_reason") or "UNKNOWN"),
        "",
        f"Entry: ${safe_float(fill.get('entry_price')):,.2f}",
        f"Exit: ${safe_float(fill.get('fill_price')):,.2f}",
        "",
        f"PnL: {pnl_pct:+.2f}%",
        f"PnL $: ${pnl_dollars:+,.2f}",
        "",
        f"Time: {local_now_text()}",
        "",
        "PAPER only — no live order sent.",
    ])


# Backward-compatible alias used by earlier builds.
def format_paper_fill_message(fill: Dict[str, Any]) -> str:
    action = str(fill.get("action") or "").upper().strip()
    if action == "SELL":
        return format_paper_exit_message(fill)
    return format_paper_entry_message(fill)


# =========================================================
# MARKET DATA SNAPSHOT HELPERS
# =========================================================

def latest_rows_by_symbol() -> Dict[str, Dict[str, Any]]:
    """Build latest known row by symbol from signal log and alert log.

    Signal log is preferred because it includes WATCH/SELL/AVOID states. Alert
    log is still useful for latest BUY prices and for older Signal Watcher builds.
    """

    latest: Dict[str, Dict[str, Any]] = {}

    for source_name, df in (
        ("signal_log", signal_dataframe()),
        ("alert_log", alert_dataframe()),
    ):
        if df.empty or "symbol" not in df.columns:
            continue

        work = df.tail(2000).copy()
        if "timestamp" in work.columns:
            work["_parsed_ts"] = work["timestamp"].apply(parse_timestamp)
        else:
            work["_parsed_ts"] = None

        for _, series in work.iterrows():
            row = series.to_dict()
            symbol = str(row.get("symbol") or "").upper().strip()
            if not symbol:
                continue

            parsed_ts = row.get("_parsed_ts")
            current = latest.get(symbol)
            current_ts = current.get("_parsed_ts") if isinstance(current, dict) else None

            if current is None:
                latest[symbol] = {**row, "_source_file": source_name}
            elif parsed_ts is not None and (current_ts is None or parsed_ts >= current_ts):
                latest[symbol] = {**row, "_source_file": source_name}
            elif parsed_ts is None and current_ts is None:
                latest[symbol] = {**row, "_source_file": source_name}

    return latest


def latest_market_row_for_symbol(symbol: str, latest_rows: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    symbol = str(symbol or "").upper().strip()
    rows = latest_rows if latest_rows is not None else latest_rows_by_symbol()
    row = rows.get(symbol, {})
    return row if isinstance(row, dict) else {}


def latest_price_for_symbol(symbol: str, fallback: float = 0.0, latest_rows: Optional[Dict[str, Dict[str, Any]]] = None) -> float:
    row = latest_market_row_for_symbol(symbol, latest_rows=latest_rows)
    for key in ("price", "last_price", "close", "current_price", "fill_price"):
        price = safe_float(row.get(key), 0.0)
        if price > 0:
            return price
    return safe_float(fallback, 0.0)


def latest_recommendation_for_symbol(symbol: str, latest_rows: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    row = latest_market_row_for_symbol(symbol, latest_rows=latest_rows)
    for key in ("trade_recommendation", "recommendation", "scanner_recommendation", "signal"):
        value = str(row.get(key) or "").upper().strip()
        if value:
            return value
    return ""


# =========================================================
# PAPER RISK / ENTRY EXECUTION
# =========================================================

def daily_trade_count(state: Dict[str, Any]) -> int:
    today = date.today().isoformat()
    counts = state.setdefault("daily_trade_counts", {})
    return int(counts.get(today, 0) or 0)


def increment_daily_trade_count(state: Dict[str, Any]) -> None:
    today = date.today().isoformat()
    counts = state.setdefault("daily_trade_counts", {})
    counts[today] = int(counts.get(today, 0) or 0) + 1
    state["daily_trade_counts"] = {today: counts[today]}


def allocation_for_signal(recommendation: str, config: PaperConfig) -> float:
    rec = str(recommendation or "").upper().strip()
    if rec == "STRONG BUY":
        return float(config.strong_buy_allocation_dollars)
    return float(config.buy_allocation_dollars)


def validate_alert(row: Dict[str, Any], state: Dict[str, Any], config: PaperConfig) -> Tuple[bool, str, int, float]:
    symbol = str(row.get("symbol") or "").upper().strip()
    recommendation = str(row.get("trade_recommendation") or "").upper().strip()
    signal = str(row.get("signal") or "").upper().strip()
    price = safe_float(row.get("price"), 0.0)
    score = safe_float(row.get("opportunity_score_pct"), 0.0)
    key = alert_execution_key(row)

    if not config.enabled:
        return False, "Quant Executor disabled", 0, 0.0
    if not symbol:
        return False, "Missing symbol", 0, 0.0
    if recommendation not in ("BUY", "STRONG BUY"):
        return False, f"Not paper-executable recommendation: {recommendation}", 0, 0.0
    if signal and signal != "BUY":
        return False, f"Research signal is not BUY: {signal}", 0, 0.0
    if price <= 0:
        return False, "Invalid price", 0, 0.0
    if score < float(config.min_score):
        return False, f"Score below minimum: {score}", 0, 0.0
    if key in set(state.get("processed_alert_keys", [])):
        return False, "Duplicate paper execution blocked", 0, 0.0
    if daily_trade_count(state) >= int(config.max_daily_trades):
        return False, "Max daily paper trades reached", 0, 0.0

    positions = read_positions()
    open_positions = [p for p in positions.values() if safe_float(p.get("qty"), 0.0) > 0]
    existing = positions.get(symbol)

    if existing and safe_float(existing.get("qty"), 0.0) > 0 and not bool(config.allow_pyramiding):
        return False, f"Pyramiding disabled; existing paper position in {symbol}", 0, 0.0

    if not existing and len(open_positions) >= int(config.max_open_positions):
        return False, "Max open paper positions reached", 0, 0.0

    allocation = min(allocation_for_signal(recommendation, config), float(config.max_position_dollars))
    qty = int(allocation // price)
    if qty <= 0:
        return False, "Allocation too small for one share", 0, 0.0

    notional = round(qty * price, 2)
    return True, "APPROVED", qty, notional


def position_stop_prices(entry_price: float, config: PaperConfig) -> Tuple[float, float]:
    stop_loss_price = round(entry_price * (1.0 - safe_float(config.stop_loss_pct, 8.0) / 100.0), 4)
    take_profit_price = round(entry_price * (1.0 + safe_float(config.take_profit_pct, 15.0) / 100.0), 4)
    return stop_loss_price, take_profit_price


def execute_paper_alert(row: Dict[str, Any], state: Dict[str, Any], config: PaperConfig) -> Dict[str, Any]:
    ok, reason, qty, notional = validate_alert(row, state, config)
    key = alert_execution_key(row)
    timestamp = utc_now_iso()
    symbol = str(row.get("symbol") or "").upper().strip()
    recommendation = str(row.get("trade_recommendation") or "").upper().strip()
    price = safe_float(row.get("price"), 0.0)

    base = {
        "timestamp": timestamp,
        "alert_key": key,
        "symbol": symbol,
        "action": "BUY",
        "trade_recommendation": recommendation,
        "price": price,
        "source_alert_timestamp": row.get("timestamp"),
        "source_scan_id": row.get("scan_id"),
        "opportunity_score_pct": row.get("opportunity_score_pct"),
        "model_score": row.get("model_score"),
        "sector": row.get("sector"),
        "mode": "PAPER",
        "source": AUTO_TRADER_SOURCE,
    }

    if not ok:
        event = {**base, "event": "PAPER_ORDER_BLOCKED", "status": "BLOCKED", "reason": reason}
        append_csv(AUTO_TRADER_EVENT_LOG_FILE, event)
        return event

    order_id = f"PAPER-ORD-{int(time.time())}-{symbol}"
    fill_id = f"PAPER-FILL-{int(time.time())}-{symbol}"

    order = {
        **base,
        "order_id": order_id,
        "qty": qty,
        "notional": notional,
        "status": "SUBMITTED",
        "reason": "Signal Watcher BUY transition",
        "position_action": "OPEN_LONG",
    }

    fill = {
        **base,
        "order_id": order_id,
        "fill_id": fill_id,
        "qty": qty,
        "fill_price": price,
        "notional": notional,
        "status": "FILLED",
        "execution_status": "FILLED",
        "position_action": "OPEN_LONG",
        "is_paper": True,
        "is_true_fill": False,
    }

    append_csv(AUTO_TRADER_ORDER_LOG_FILE, order)
    append_csv(AUTO_TRADER_FILL_LOG_FILE, fill)
    append_csv(AUTO_TRADER_EVENT_LOG_FILE, {**fill, "event": "PAPER_ENTRY_FILL"})

    positions = read_positions()
    existing = positions.get(symbol, {})
    old_qty = safe_float(existing.get("qty"), 0.0)
    old_cost = safe_float(existing.get("avg_price"), 0.0) * old_qty
    new_qty = old_qty + qty
    new_cost = old_cost + notional
    avg_price = round(new_cost / new_qty, 4) if new_qty else 0.0
    old_highest = safe_float(existing.get("highest_price"), 0.0)
    highest_price = max(old_highest, price, avg_price)
    stop_loss_price, take_profit_price = position_stop_prices(avg_price, config)
    gain_pct = ((price - avg_price) / avg_price * 100.0) if avg_price > 0 else 0.0
    trailing_active = bool(existing.get("trailing_active", False)) or gain_pct >= safe_float(config.trailing_activation_pct, 10.0)
    trailing_stop_price = None
    if trailing_active:
        trailing_stop_price = round(highest_price * (1.0 - safe_float(config.trailing_stop_pct, 10.0) / 100.0), 4)

    first_entry_time = existing.get("entry_time") or timestamp

    positions[symbol] = {
        "symbol": symbol,
        "qty": new_qty,
        "side": "LONG",
        "entry_price": avg_price,
        "avg_price": avg_price,
        "last_price": price,
        "highest_price": highest_price,
        "market_value": round(new_qty * price, 2),
        "unrealized_pnl": round((price - avg_price) * new_qty, 2),
        "unrealized_pnl_pct": round(gain_pct, 4),
        "stop_loss_price": stop_loss_price,
        "take_profit_price": take_profit_price,
        "trailing_active": trailing_active,
        "trailing_stop_price": trailing_stop_price,
        "trailing_activation_pct": safe_float(config.trailing_activation_pct, 10.0),
        "trailing_stop_pct": safe_float(config.trailing_stop_pct, 10.0),
        "entry_time": first_entry_time,
        "last_update": timestamp,
        "status": "OPEN",
        "source": AUTO_TRADER_SOURCE,
    }
    write_positions(positions)

    processed = state.setdefault("processed_alert_keys", [])
    if key not in processed:
        processed.append(key)
    state["processed_alert_keys"] = processed[-1000:]
    increment_daily_trade_count(state)

    sent = False
    send_status = "DISABLED"
    if config.telegram_enabled:
        sent, send_status = send_telegram_message(format_paper_entry_message(fill), dry_run=config.dry_run)

    fill["telegram_sent"] = "YES" if sent else "NO"
    fill["telegram_status"] = send_status

    update_performance_stats(state, positions=positions, config=config)
    stats = state.setdefault("stats", {})
    stats.update({
        "version": AUTO_TRADER_VERSION,
        "last_event": "PAPER_ENTRY_FILL",
        "last_status": "FILLED",
        "last_symbol": symbol,
        "last_action": "BUY",
        "last_qty": qty,
        "last_price": price,
        "last_notional": notional,
        "last_trade_time": timestamp,
        "orders_today": daily_trade_count(state),
        "paper_account_value": config.paper_account_value,
    })

    write_state(state)
    return fill


# =========================================================
# EXIT ENGINE v1.1
# =========================================================

def normalize_position(symbol: str, position: Dict[str, Any], config: PaperConfig) -> Dict[str, Any]:
    symbol = str(symbol or position.get("symbol") or "").upper().strip()
    qty = safe_float(position.get("qty"), 0.0)
    avg_price = safe_float(position.get("avg_price"), 0.0)
    entry_price = safe_float(position.get("entry_price"), avg_price)
    last_price = safe_float(position.get("last_price"), entry_price)

    if entry_price <= 0:
        entry_price = avg_price if avg_price > 0 else last_price
    if avg_price <= 0:
        avg_price = entry_price
    if last_price <= 0:
        last_price = entry_price

    highest_price = max(
        safe_float(position.get("highest_price"), 0.0),
        safe_float(position.get("last_price"), 0.0),
        entry_price,
    )

    stop_loss_price, take_profit_price = position_stop_prices(entry_price, config)
    trailing_active = bool(position.get("trailing_active", False))
    trailing_stop_price = position.get("trailing_stop_price")
    trailing_stop_price = safe_float(trailing_stop_price, 0.0) if trailing_stop_price is not None else 0.0

    normalized = {
        **position,
        "symbol": symbol,
        "qty": qty,
        "side": "LONG",
        "entry_price": entry_price,
        "avg_price": avg_price,
        "last_price": last_price,
        "highest_price": highest_price,
        "stop_loss_price": safe_float(position.get("stop_loss_price"), stop_loss_price),
        "take_profit_price": safe_float(position.get("take_profit_price"), take_profit_price),
        "trailing_active": trailing_active,
        "trailing_stop_price": trailing_stop_price if trailing_stop_price > 0 else None,
        "entry_time": position.get("entry_time") or position.get("last_update") or utc_now_iso(),
        "status": "OPEN" if qty > 0 else position.get("status", "CLOSED"),
        "source": position.get("source") or AUTO_TRADER_SOURCE,
    }
    return normalized


def update_position_marks(
    positions: Dict[str, Dict[str, Any]],
    config: PaperConfig,
    latest_rows: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    updated: Dict[str, Dict[str, Any]] = {}
    latest_rows = latest_rows if latest_rows is not None else latest_rows_by_symbol()
    timestamp = utc_now_iso()

    for symbol, raw_position in positions.items():
        if not isinstance(raw_position, dict):
            continue
        position = normalize_position(symbol, raw_position, config)
        qty = safe_float(position.get("qty"), 0.0)
        if qty <= 0:
            continue

        entry_price = safe_float(position.get("entry_price"), safe_float(position.get("avg_price"), 0.0))
        last_price = latest_price_for_symbol(symbol, fallback=safe_float(position.get("last_price"), entry_price), latest_rows=latest_rows)
        highest_price = max(safe_float(position.get("highest_price"), entry_price), last_price, entry_price)
        market_value = round(qty * last_price, 2)
        unrealized_pnl = round((last_price - entry_price) * qty, 2)
        unrealized_pnl_pct = round(((last_price - entry_price) / entry_price * 100.0), 4) if entry_price > 0 else 0.0

        trailing_active = bool(position.get("trailing_active", False))
        if unrealized_pnl_pct >= safe_float(config.trailing_activation_pct, 10.0):
            trailing_active = True

        trailing_stop_price = position.get("trailing_stop_price")
        if trailing_active:
            trailing_stop_price = round(highest_price * (1.0 - safe_float(config.trailing_stop_pct, 10.0) / 100.0), 4)

        stop_loss_price, take_profit_price = position_stop_prices(entry_price, config)

        updated[symbol] = {
            **position,
            "last_price": last_price,
            "highest_price": highest_price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "trailing_active": trailing_active,
            "trailing_stop_price": trailing_stop_price,
            "last_update": timestamp,
            "status": "OPEN",
        }

    return updated


def evaluate_exit_trigger(
    symbol: str,
    position: Dict[str, Any],
    config: PaperConfig,
    latest_rows: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[bool, str, str]:
    """Return one exit decision using strict priority.

    Priority:
      1. Stop Loss
      2. Trailing Stop
      3. Take Profit
      4. Signal Exit
    """

    if not bool(config.exit_engine_enabled):
        return False, "", "Exit engine disabled"

    latest_rows = latest_rows if latest_rows is not None else latest_rows_by_symbol()
    price = safe_float(position.get("last_price"), 0.0)
    stop_loss_price = safe_float(position.get("stop_loss_price"), 0.0)
    trailing_active = bool(position.get("trailing_active", False))
    trailing_stop_price = safe_float(position.get("trailing_stop_price"), 0.0)
    take_profit_price = safe_float(position.get("take_profit_price"), 0.0)

    # 1. Stop Loss
    if stop_loss_price > 0 and price <= stop_loss_price:
        return True, "STOP LOSS", f"Price {price:.2f} <= stop {stop_loss_price:.2f}"

    # 2. Trailing Stop
    if trailing_active and trailing_stop_price > 0 and price <= trailing_stop_price:
        return True, "TRAILING STOP", f"Price {price:.2f} <= trailing stop {trailing_stop_price:.2f}"

    # 3. Take Profit
    if take_profit_price > 0 and price >= take_profit_price:
        return True, "TAKE PROFIT", f"Price {price:.2f} >= target {take_profit_price:.2f}"

    # 4. Signal Exit
    if bool(config.signal_exit_enabled):
        latest_row = latest_market_row_for_symbol(symbol, latest_rows=latest_rows)
        rec = latest_recommendation_for_symbol(symbol, latest_rows=latest_rows)
        source_file = str(latest_row.get("_source_file") or "")

        # Signal Exit requires the full signal log or a clear non-BUY state.
        # The alert log alone is often BUY-only, so it should not force exits.
        if source_file == "signal_log" and rec and rec not in ("BUY", "STRONG BUY"):
            latest_ts = latest_row.get("_parsed_ts") or parse_timestamp(latest_row.get("timestamp"))
            entry_ts = parse_timestamp(position.get("entry_time"))
            if latest_ts is not None and entry_ts is not None and latest_ts < entry_ts:
                return False, "", f"Signal exit ignored; latest signal {rec} is older than entry"
            return True, "SIGNAL EXIT", f"Latest scanner recommendation is {rec}"

    return False, "", "No exit trigger"


def execute_paper_exit(
    symbol: str,
    position: Dict[str, Any],
    exit_reason: str,
    exit_note: str,
    state: Dict[str, Any],
    config: PaperConfig,
) -> Dict[str, Any]:
    timestamp = utc_now_iso()
    qty = safe_float(position.get("qty"), 0.0)
    entry_price = safe_float(position.get("entry_price"), safe_float(position.get("avg_price"), 0.0))
    exit_price = safe_float(position.get("last_price"), 0.0)
    if exit_price <= 0:
        exit_price = entry_price

    notional = round(qty * exit_price, 2)
    cost_basis = round(qty * entry_price, 2)
    realized_pnl = round((exit_price - entry_price) * qty, 2)
    pnl_pct = round(((exit_price - entry_price) / entry_price * 100.0), 4) if entry_price > 0 else 0.0

    order_id = f"PAPER-EXIT-ORD-{int(time.time())}-{symbol}"
    fill_id = f"PAPER-EXIT-FILL-{int(time.time())}-{symbol}"

    base = {
        "timestamp": timestamp,
        "symbol": symbol,
        "action": "SELL",
        "trade_recommendation": latest_recommendation_for_symbol(symbol),
        "price": exit_price,
        "mode": "PAPER",
        "source": AUTO_TRADER_SOURCE,
        "exit_reason": exit_reason,
        "exit_note": exit_note,
        "position_action": "CLOSE_LONG",
    }

    order = {
        **base,
        "order_id": order_id,
        "qty": qty,
        "notional": notional,
        "status": "SUBMITTED",
        "reason": exit_reason,
    }

    fill = {
        **base,
        "order_id": order_id,
        "fill_id": fill_id,
        "qty": qty,
        "fill_price": exit_price,
        "entry_price": entry_price,
        "cost_basis": cost_basis,
        "notional": notional,
        "realized_pnl": realized_pnl,
        "pnl_pct": pnl_pct,
        "status": "FILLED",
        "execution_status": "FILLED",
        "is_paper": True,
        "is_true_fill": False,
    }

    closed_trade = {
        "entry_time": position.get("entry_time"),
        "exit_time": timestamp,
        "symbol": symbol,
        "side": "LONG",
        "qty": qty,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "cost_basis": cost_basis,
        "exit_notional": notional,
        "realized_pnl": realized_pnl,
        "pnl_pct": pnl_pct,
        "exit_reason": exit_reason,
        "exit_note": exit_note,
        "highest_price": position.get("highest_price"),
        "stop_loss_price": position.get("stop_loss_price"),
        "take_profit_price": position.get("take_profit_price"),
        "trailing_active": position.get("trailing_active"),
        "trailing_stop_price": position.get("trailing_stop_price"),
        "mode": "PAPER",
        "source": AUTO_TRADER_SOURCE,
    }

    append_csv(AUTO_TRADER_ORDER_LOG_FILE, order)
    append_csv(AUTO_TRADER_FILL_LOG_FILE, fill)
    append_csv(AUTO_TRADER_EVENT_LOG_FILE, {**fill, "event": "PAPER_EXIT_FILL"})
    append_csv(AUTO_TRADER_CLOSED_TRADE_LOG_FILE, closed_trade)

    positions = read_positions()
    if symbol in positions:
        positions.pop(symbol, None)
    write_positions(positions)

    sent = False
    send_status = "DISABLED"
    if config.telegram_enabled:
        sent, send_status = send_telegram_message(format_paper_exit_message(fill), dry_run=config.dry_run)

    fill["telegram_sent"] = "YES" if sent else "NO"
    fill["telegram_status"] = send_status

    stats = state.setdefault("stats", {})
    stats.update({
        "version": AUTO_TRADER_VERSION,
        "last_event": "PAPER_EXIT_FILL",
        "last_status": "EXIT_FILLED",
        "last_symbol": symbol,
        "last_action": "SELL",
        "last_qty": qty,
        "last_price": exit_price,
        "last_notional": notional,
        "last_trade_time": timestamp,
        "last_exit_reason": exit_reason,
        "last_realized_pnl": realized_pnl,
        "last_pnl_pct": pnl_pct,
        "orders_today": daily_trade_count(state),
        "paper_account_value": config.paper_account_value,
    })
    update_performance_stats(state, positions=positions, config=config)
    write_state(state)

    return fill


def manage_open_positions(state: Dict[str, Any], config: PaperConfig) -> Dict[str, Any]:
    latest_rows = latest_rows_by_symbol()
    positions = read_positions()
    marked_positions = update_position_marks(positions, config=config, latest_rows=latest_rows)
    write_positions(marked_positions)

    exits: List[Dict[str, Any]] = []
    checked = 0

    for symbol, position in list(marked_positions.items()):
        checked += 1
        should_exit, reason, note = evaluate_exit_trigger(symbol, position, config=config, latest_rows=latest_rows)
        if not should_exit:
            continue

        fill = execute_paper_exit(symbol, position, reason, note, state=state, config=config)
        exits.append(fill)
        state = read_state()

    positions_after = read_positions()
    update_performance_stats(state, positions=positions_after, config=config)
    stats = state.setdefault("stats", {})
    stats.update({
        "last_exit_scan_finished": utc_now_iso(),
        "last_exit_positions_checked": checked,
        "last_exit_fills": len(exits),
    })
    write_state(state)

    if exits:
        print(f"[{local_now_text()}] Quant Executor exits={len(exits)} symbols={[x.get('symbol') for x in exits]}")

    return {
        "positions_checked": checked,
        "exits": len(exits),
        "exit_fills": exits,
    }


# =========================================================
# PERFORMANCE STATS
# =========================================================

def max_drawdown_from_closed_trades(closed_df: pd.DataFrame) -> float:
    if closed_df.empty or "realized_pnl" not in closed_df.columns:
        return 0.0
    pnl = pd.to_numeric(closed_df["realized_pnl"], errors="coerce").fillna(0.0).tolist()
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in pnl:
        equity += float(value)
        peak = max(peak, equity)
        drawdown = equity - peak
        max_dd = min(max_dd, drawdown)
    return round(max_dd, 2)


def update_performance_stats(
    state: Dict[str, Any],
    positions: Optional[Dict[str, Dict[str, Any]]] = None,
    config: Optional[PaperConfig] = None,
) -> Dict[str, Any]:
    config = config or read_config()
    positions = positions if positions is not None else read_positions()
    open_positions = [p for p in positions.values() if isinstance(p, dict) and safe_float(p.get("qty"), 0.0) > 0]
    unrealized_pnl = round(sum(safe_float(p.get("unrealized_pnl"), 0.0) for p in open_positions), 2)
    market_value = round(sum(safe_float(p.get("market_value"), 0.0) for p in open_positions), 2)

    closed_df = closed_trades_dataframe()
    closed_positions = int(closed_df.shape[0]) if not closed_df.empty else 0
    realized_pnl = 0.0
    win_rate = 0.0
    profit_factor = 0.0
    average_win = 0.0
    average_loss = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    max_drawdown = 0.0

    if not closed_df.empty and "realized_pnl" in closed_df.columns:
        pnl_series = pd.to_numeric(closed_df["realized_pnl"], errors="coerce").fillna(0.0)
        realized_pnl = round(float(pnl_series.sum()), 2)
        wins = pnl_series[pnl_series > 0]
        losses = pnl_series[pnl_series < 0]
        win_rate = round((len(wins) / len(pnl_series) * 100.0), 2) if len(pnl_series) else 0.0
        gross_profit = round(float(wins.sum()), 2) if len(wins) else 0.0
        gross_loss = round(float(abs(losses.sum())), 2) if len(losses) else 0.0
        profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else (round(gross_profit, 4) if gross_profit > 0 else 0.0)
        average_win = round(float(wins.mean()), 2) if len(wins) else 0.0
        average_loss = round(float(losses.mean()), 2) if len(losses) else 0.0
        max_drawdown = max_drawdown_from_closed_trades(closed_df)

    stats = state.setdefault("stats", {})
    stats.update({
        "version": AUTO_TRADER_VERSION,
        "open_positions": len(open_positions),
        "closed_positions": closed_positions,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": round(realized_pnl + unrealized_pnl, 2),
        "market_value": market_value,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "average_win": average_win,
        "average_loss": average_loss,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "max_drawdown": max_drawdown,
        "paper_account_value": safe_float(config.paper_account_value, 100000.0),
    })
    return stats


# =========================================================
# LOOP
# =========================================================

def scan_for_new_alerts(config: PaperConfig) -> Dict[str, Any]:
    state = read_state()

    exit_report = manage_open_positions(state, config=config)
    state = read_state()

    df = alert_dataframe()

    results: List[Dict[str, Any]] = []
    processed = 0
    blocked = 0
    fills = 0

    if df.empty:
        positions = read_positions()
        stats = state.setdefault("stats", {})
        update_performance_stats(state, positions=positions, config=config)
        stats.update({
            "version": AUTO_TRADER_VERSION,
            "last_scan_finished": utc_now_iso(),
            "last_status": "WAITING_FOR_ALERTS",
            "last_message": "No Signal Watcher alerts found yet",
            "orders_today": daily_trade_count(state),
            "last_exit_positions_checked": exit_report.get("positions_checked", 0),
            "last_exit_fills": exit_report.get("exits", 0),
        })
        write_state(state)
        return stats.copy()

    df = df.tail(200).copy()

    for _, series in df.iterrows():
        row = series.to_dict()
        key = alert_execution_key(row)
        if key in set(state.get("processed_alert_keys", [])):
            continue

        result = execute_paper_alert(row, state, config)
        processed += 1
        if str(result.get("status", "")).upper() == "FILLED":
            fills += 1
        else:
            blocked += 1
        results.append(result)
        state = read_state()

    positions = read_positions()
    update_performance_stats(state, positions=positions, config=config)
    stats = state.setdefault("stats", {})
    stats.update({
        "version": AUTO_TRADER_VERSION,
        "last_scan_finished": utc_now_iso(),
        "last_status": "OK",
        "last_message": "Quant Executor cycle complete",
        "last_alerts_processed": processed,
        "last_fills": fills,
        "last_blocked": blocked,
        "last_exit_positions_checked": exit_report.get("positions_checked", 0),
        "last_exit_fills": exit_report.get("exits", 0),
        "orders_today": daily_trade_count(state),
        "paper_account_value": config.paper_account_value,
    })
    write_state(state)

    if processed or exit_report.get("exits"):
        print(
            f"[{local_now_text()}] Quant Executor "
            f"entries_processed={processed} fills={fills} blocked={blocked} exits={exit_report.get('exits', 0)}"
        )

    return stats.copy()


def run_forever() -> None:
    config = ensure_config_exists()
    print("=" * 70)
    print(f"JFBP Quant Executor {AUTO_TRADER_VERSION}")
    print("Mode: PAPER ONLY")
    print(f"Enabled: {config.enabled}")
    print(f"Poll interval: {config.poll_interval_seconds}s")
    print("Exit Engine: ON" if config.exit_engine_enabled else "Exit Engine: OFF")
    print(
        "Exits: "
        f"Stop {config.stop_loss_pct}% | "
        f"Take Profit {config.take_profit_pct}% | "
        f"Trail {config.trailing_stop_pct}% after +{config.trailing_activation_pct}% | "
        f"Signal Exit {'ON' if config.signal_exit_enabled else 'OFF'}"
    )
    print("No live orders. No IBKR routing. No OMS LIVE.")
    print("=" * 70)

    while True:
        try:
            config = ensure_config_exists()
            scan_for_new_alerts(config)
        except KeyboardInterrupt:
            print("Quant Executor stopped by user.")
            break
        except Exception as exc:
            state = read_state()
            stats = state.setdefault("stats", {})
            stats.update({
                "version": AUTO_TRADER_VERSION,
                "last_scan_finished": utc_now_iso(),
                "last_status": f"ERROR: {exc}",
            })
            write_state(state)
            print(f"[{local_now_text()}] ERROR: {exc}")

        time.sleep(max(5, int(read_config().poll_interval_seconds)))


if __name__ == "__main__":
    run_forever()
