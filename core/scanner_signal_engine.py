# =========================================================
# JFBP QUANT DESK — SCANNER SIGNAL ENGINE v1.0
# Shared scanner engine for Scanner Page + Signal Watcher
# ALERTS ONLY COMPATIBLE • NO OMS • NO IBKR • NO ORDERS
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

try:
    from universe.jfbp_universe import JFBP_UNIVERSE
except Exception:
    JFBP_UNIVERSE = {}


def fallback_universe() -> Dict[str, Dict[str, Any]]:
    return {
        "SPY": {"sector": "ETF", "liquidity": 5, "volatility": 2, "regime": ["benchmark"]},
        "QQQ": {"sector": "ETF", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
        "IWM": {"sector": "ETF", "liquidity": 4, "volatility": 3, "regime": ["small_caps"]},
        "DIA": {"sector": "ETF", "liquidity": 4, "volatility": 2, "regime": ["blue_chip"]},
        "TQQQ": {"sector": "ETF", "liquidity": 4, "volatility": 5, "regime": ["leveraged_momentum"]},
        "UVXY": {"sector": "ETF", "liquidity": 4, "volatility": 5, "regime": ["volatility"]},
        "AAPL": {"sector": "Tech", "liquidity": 5, "volatility": 2, "regime": ["defensive_growth"]},
        "MSFT": {"sector": "Tech", "liquidity": 5, "volatility": 2, "regime": ["defensive_growth"]},
        "NVDA": {"sector": "Tech", "liquidity": 5, "volatility": 4, "regime": ["momentum"]},
        "AMZN": {"sector": "Consumer", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
        "COIN": {"sector": "Crypto", "liquidity": 4, "volatility": 5, "regime": ["high_beta"]},
        "DE": {"sector": "Industrial", "liquidity": 3, "volatility": 3, "regime": ["cyclical"]},
        "WMT": {"sector": "Consumer Defensive", "liquidity": 5, "volatility": 2, "regime": ["defensive"]},
        "BA": {"sector": "Industrial", "liquidity": 4, "volatility": 4, "regime": ["cyclical"]},
        "BX": {"sector": "Financial", "liquidity": 4, "volatility": 3, "regime": ["financial"]},
        "LRCX": {"sector": "Semiconductors", "liquidity": 4, "volatility": 4, "regime": ["semis"]},
        "ASML": {"sector": "Semiconductors", "liquidity": 4, "volatility": 3, "regime": ["semis"]},
        "ARM": {"sector": "Semiconductors", "liquidity": 4, "volatility": 5, "regime": ["semis"]},
        "FUTU": {"sector": "Financial", "liquidity": 3, "volatility": 5, "regime": ["high_beta"]},
        "JPM": {"sector": "Financial", "liquidity": 5, "volatility": 2, "regime": ["financial"]},
    }


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def normalize_action(value: Any) -> str:
    action = str(value or "").upper().strip()
    action_map = {
        "LONG": "BUY", "BUY_LONG": "BUY", "ENTER_LONG": "BUY", "OPEN_LONG": "BUY", "BULLISH": "BUY",
        "SHORT": "SELL", "SELL_SHORT": "SELL", "ENTER_SHORT": "SELL", "OPEN_SHORT": "SELL", "BEARISH": "SELL",
        "NO TRADE": "HOLD", "NO_TRADE": "HOLD", "NONE": "HOLD", "FLAT": "HOLD", "NEUTRAL": "HOLD", "": "HOLD",
    }
    return action_map.get(action, action)


def normalize_meta(symbol: str, meta: Any) -> Dict[str, Any]:
    symbol = str(symbol or "").upper().strip()
    meta = meta if isinstance(meta, dict) else {}
    regime = meta.get("regime", [])

    raw_data_symbol = meta.get("data_symbol")
    raw_data_symbols = meta.get("data_symbols", [])
    if raw_data_symbols is None:
        raw_data_symbols = []
    if isinstance(raw_data_symbols, str):
        raw_data_symbols = [raw_data_symbols]
    if not isinstance(raw_data_symbols, (list, tuple)):
        raw_data_symbols = []

    data_symbols = []
    if raw_data_symbol:
        data_symbols.append(raw_data_symbol)
    data_symbols.extend(raw_data_symbols)
    data_symbols.append(symbol)

    cleaned = []
    for item in data_symbols:
        item = str(item or "").upper().strip()
        if item and item not in cleaned:
            cleaned.append(item)

    return {
        "symbol": symbol,
        "data_symbol": cleaned[0] if cleaned else symbol,
        "data_symbols": cleaned,
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


def resolve_data_symbols(symbol: str, meta: Dict[str, Any]) -> List[str]:
    candidates = []
    data_symbols = meta.get("data_symbols")
    if isinstance(data_symbols, (list, tuple)):
        candidates.extend(data_symbols)
    data_symbol = meta.get("data_symbol")
    if data_symbol:
        candidates.append(data_symbol)
    candidates.append(symbol)

    cleaned = []
    for item in candidates:
        item = str(item or "").upper().strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def load_symbol_data(symbol: str) -> pd.DataFrame:
    return yf.download(symbol, period="6mo", interval="1d", progress=False, auto_adjust=False, threads=False)


def load_benchmark_data() -> pd.DataFrame:
    return yf.download("SPY", period="6mo", interval="1d", progress=False, auto_adjust=False, threads=False)


def load_first_valid_symbol(display_symbol: str, meta: Dict[str, Any]):
    attempted_symbols = []
    last_error = None
    for data_symbol in resolve_data_symbols(display_symbol, meta):
        attempted_symbols.append(data_symbol)
        try:
            df = load_symbol_data(data_symbol)
            if df is not None and not df.empty:
                return data_symbol, df, attempted_symbols
            last_error = "No stock data"
        except Exception as exc:
            last_error = str(exc)
    raise RuntimeError(last_error or "No stock data")


def research_model_signal(symbol: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Same core research-model BUY/SELL/NO TRADE logic used by Scanner_page.py."""
    symbol = str(symbol or "").upper().strip()
    meta = normalize_meta(symbol, meta)
    data_symbol = meta.get("data_symbol", symbol)
    attempted_symbols = []

    try:
        data_symbol, df, attempted_symbols = load_first_valid_symbol(symbol, meta)
        benchmark = load_benchmark_data()
        if df is None or df.empty:
            raise RuntimeError("No stock data")
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
            raise RuntimeError("Missing required close column")
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
        prev_close = df["Close"].shift(1)
        tr1 = df["High"] - df["Low"]
        tr2 = (df["High"] - prev_close).abs()
        tr3 = (df["Low"] - prev_close).abs()
        df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["ATR"] = df["TR"].rolling(14).mean()
        df["20D_HIGH"] = df["High"].rolling(20).max()
        df["20D_LOW"] = df["Low"].rolling(20).min()
        df = df.dropna(subset=["Close", "MA20", "MA50", "RS_SCORE", "ATR", "20D_HIGH", "20D_LOW"])
        if df.empty or len(df) < 2:
            raise RuntimeError("Not enough clean indicator data")

        latest_close = round(float(df["Close"].iloc[-1]), 2)
        previous_close = round(float(df["Close"].iloc[-2]), 2)
        latest_ma20 = round(float(df["MA20"].iloc[-1]), 2)
        latest_ma50 = round(float(df["MA50"].iloc[-1]), 2)
        latest_rs_score = round(float(df["RS_SCORE"].iloc[-1]), 4)
        latest_atr = round(float(df["ATR"].iloc[-1]), 4)
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
        if above_ma20: model_score += 1
        if above_ma50: model_score += 1
        if improving_today: model_score += 1
        if strong_rs: model_score += 1
        if near_high: model_score += 1

        if above_ma20 and above_ma50 and improving_today and strong_rs and near_high:
            signal = "BUY"
        elif below_ma20 and below_ma50 and falling_today and weak_rs:
            signal = "SELL"
        else:
            signal = "NO TRADE"

        scanner_action = normalize_action(signal)
        trend = "BULLISH" if above_ma20 and above_ma50 else "BEARISH"

        return {
            "timestamp": now(), "symbol": symbol, "data_symbol": data_symbol,
            "sector": meta["sector"], "liquidity": meta["liquidity"],
            "volatility": meta["volatility"], "regime": meta["regime"],
            "signal": signal, "scanner_action": scanner_action,
            "action": scanner_action, "side": scanner_action, "qty": 1,
            "price": latest_close, "model_score": model_score, "score": model_score,
            "trend": trend, "ma20": latest_ma20, "ma50": latest_ma50,
            "rs_score": latest_rs_score, "atr": latest_atr,
            "support": latest_20d_low, "resistance": latest_20d_high,
            "prev_close": previous_close, "attempted_symbols": ", ".join(attempted_symbols),
            "source": "scanner_signal_engine_v1", "mode": "ALERT_ONLY", "reason": None,
        }
    except Exception as exc:
        return {
            "timestamp": now(), "symbol": symbol, "data_symbol": data_symbol,
            "sector": meta.get("sector", "Unknown"), "liquidity": meta.get("liquidity", 3),
            "volatility": meta.get("volatility", 3), "regime": meta.get("regime", ""),
            "signal": "NO TRADE", "scanner_action": "HOLD", "action": "HOLD", "side": "HOLD",
            "qty": 1, "price": 0.0, "model_score": 0, "score": 0,
            "trend": "UNKNOWN", "ma20": None, "ma50": None, "rs_score": None,
            "atr": None, "support": None, "resistance": None, "prev_close": None,
            "attempted_symbols": ", ".join(attempted_symbols), "reason": str(exc),
            "source": "scanner_signal_engine_v1_error_safe", "mode": "ALERT_ONLY",
        }


def leadership_tier_from_percentile(percentile: Any) -> str:
    pct = safe_float(percentile, 0.0)
    if pct >= 90: return "ELITE"
    if pct >= 75: return "LEADER"
    if pct >= 50: return "STRONG"
    if pct >= 25: return "AVERAGE"
    return "WEAK"


def rating_from_score_pct(score_pct: Any) -> str:
    pct = safe_float(score_pct, 0.0)
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "A-"
    if pct >= 60: return "B"
    if pct >= 50: return "C"
    if pct >= 35: return "D"
    return "F"


def sector_leadership_map(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    sector_groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "").upper().strip()
        sector = str(row.get("sector") or "Unknown").strip()
        rs_score = safe_float(row.get("rs_score"), 0.0)
        if not symbol:
            continue
        sector_groups.setdefault(sector, []).append({
            "symbol": symbol, "sector": sector, "rs_score": rs_score,
            "model_score": safe_float(row.get("model_score"), 0.0),
        })

    leadership: Dict[str, Dict[str, Any]] = {}
    for sector, members in sector_groups.items():
        members = sorted(members, key=lambda item: (safe_float(item.get("rs_score"), 0.0), safe_float(item.get("model_score"), 0.0)), reverse=True)
        count = len(members)
        sector_leader = members[0]["symbol"] if members else ""
        for idx, item in enumerate(members, start=1):
            percentile = 100.0 if count <= 1 else round(((count - idx) / (count - 1)) * 100.0, 1)
            leadership[item["symbol"]] = {
                "sector_rank": idx, "sector_count": count, "sector_percentile": percentile,
                "leadership_tier": leadership_tier_from_percentile(percentile),
                "sector_leader": sector_leader,
            }
    return leadership


def scanner_trade_recommendation(row: Dict[str, Any], score_pct: float, rating: str = "") -> str:
    action = normalize_action(row.get("scanner_action") or row.get("action") or row.get("signal") or row.get("side"))
    trend = str(row.get("trend") or "").upper().strip()
    earnings_label = str(row.get("earnings_risk_label") or "NONE").upper().strip()
    event_risk_label = str(row.get("combined_event_risk_label") or row.get("earnings_risk_label") or "NONE").upper().strip()
    days_until = row.get("earnings_days_until")
    try:
        days_until = int(days_until)
    except Exception:
        days_until = None

    high_event_risk = event_risk_label in ("HIGH", "EXTREME") or earnings_label in ("HIGH", "EXTREME") or (days_until is not None and days_until <= 7)
    if action == "SELL":
        return "SELL"
    if action == "BUY":
        if score_pct >= 80 and not high_event_risk:
            return "STRONG BUY"
        if score_pct >= 60:
            return "WATCH" if high_event_risk else "BUY"
        return "WATCH"
    if trend == "BULLISH" and score_pct >= 50:
        return "WATCH"
    if trend == "BEARISH" and score_pct < 35:
        return "AVOID"
    return "WATCH"


def apply_scanner_quality_overlay(row: Dict[str, Any], leadership_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    symbol = str(row.get("symbol") or "").upper().strip()
    leadership_row = leadership_map.get(symbol, {}) if isinstance(leadership_map, dict) else {}
    if not leadership_row:
        leadership_row = {"sector_rank": None, "sector_count": None, "sector_percentile": 0.0, "leadership_tier": "UNKNOWN", "sector_leader": ""}

    trend = str(row.get("trend") or "").upper().strip()
    action = normalize_action(row.get("scanner_action") or row.get("action") or row.get("signal") or row.get("side"))
    model_score = safe_float(row.get("model_score"), 0.0)
    rs_score = safe_float(row.get("rs_score"), 0.0)
    sector_pct = safe_float(leadership_row.get("sector_percentile"), 0.0)

    # Same 8-point Scanner Page quality score, with watcher v1 using clear/default event-risk context.
    score = 0
    max_score = 8
    if trend == "BULLISH": score += 1
    if rs_score >= 1.05: score += 1
    if sector_pct >= 75: score += 1
    if model_score >= 4: score += 1
    if action == "BUY" or (trend == "BULLISH" and model_score >= 3): score += 1
    score += 1  # earnings clear/default for alert-only watcher v1
    score += 1  # economic clear/default for alert-only watcher v1
    score += 1  # market not risk-off/default for alert-only watcher v1

    score_pct = round((score / max_score) * 100.0, 1)
    rating = rating_from_score_pct(score_pct)
    enriched = {
        **row,
        "sector_rank": leadership_row.get("sector_rank"),
        "sector_count": leadership_row.get("sector_count"),
        "sector_percentile": sector_pct,
        "leadership_tier": leadership_row.get("leadership_tier"),
        "sector_leader": leadership_row.get("sector_leader"),
        "earnings_risk_label": row.get("earnings_risk_label", "NONE"),
        "earnings_risk_score": row.get("earnings_risk_score", 0),
        "economic_risk_label": row.get("economic_risk_label", "NONE"),
        "economic_risk_score": row.get("economic_risk_score", 0),
        "market_reaction_regime": row.get("market_reaction_regime", "NEUTRAL"),
        "combined_event_risk_score": row.get("combined_event_risk_score", 0),
        "combined_event_risk_label": row.get("combined_event_risk_label", "NONE"),
        "opportunity_score": score,
        "opportunity_max_score": max_score,
        "opportunity_score_pct": score_pct,
        "overall_rating": rating,
    }
    enriched["trade_recommendation"] = scanner_trade_recommendation(enriched, score_pct, rating)
    return enriched


def enrich_scanner_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = [row for row in rows if isinstance(row, dict)]
    leadership = sector_leadership_map(rows)
    enriched_rows = [apply_scanner_quality_overlay(row, leadership) for row in rows]
    return sorted(
        enriched_rows,
        key=lambda row: (
            safe_float(row.get("opportunity_score_pct"), 0.0),
            safe_float(row.get("model_score"), 0.0),
            safe_float(row.get("rs_score"), 0.0),
        ),
        reverse=True,
    )


def get_active_universe() -> Dict[str, Dict[str, Any]]:
    return JFBP_UNIVERSE if isinstance(JFBP_UNIVERSE, dict) and JFBP_UNIVERSE else fallback_universe()


def generate_signals(universe: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    universe = universe if isinstance(universe, dict) and universe else get_active_universe()
    rows = []
    for symbol, meta in universe.items():
        symbol = str(symbol or "").upper().strip()
        if not symbol:
            continue
        rows.append(research_model_signal(symbol=symbol, meta=meta if isinstance(meta, dict) else {}))
    return enrich_scanner_rows(rows)


def get_buy_signals(universe: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    rows = generate_signals(universe=universe)
    return [
        row for row in rows
        if str(row.get("trade_recommendation") or "").upper().strip() in {"BUY", "STRONG BUY"}
    ]
