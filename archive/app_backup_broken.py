st.session_state["stream_status"] = "STOPPED"

# =========================================================
# 🧠 JFBP QUANT DESK — v14 INSTITUTIONAL OMS
# =========================================================
# Features:
# - Scanner / Single Stock / Portfolio
# - SQLite persistence for signals, portfolio, orders, fills, positions, pnl, journal
# - Risk overlay with exposure caps and daily-loss halt
# - Paper / Live routing toggle
# - IBKR live gateway with streaming snapshots (optional)
# - OMS execution blotter and visible tables
# =========================================================

from __future__ import annotations

import asyncio
import json
import queue
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# =========================================================
# PAGE CONFIG (MUST COME FIRST STREAMLIT CALL)
# =========================================================

st.set_page_config(page_title="JFBP Quant Desk v14", layout="wide")

# =========================================================
# PATHS / CONSTANTS
# =========================================================

APP_DIR = Path.cwd()
DB_PATH = APP_DIR / "jfbp_v14_terminal.sqlite"

UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META",
    "TSLA", "GOOG", "AMD", "NFLX",
    "JPM", "BAC", "XOM", "CVX", "SPY"
]

BENCHMARK = "SPY"
MA_LEN = 20
ATR_LEN = 14

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7497
DEFAULT_CLIENT_ID = 7

# =========================================================
# HELPERS
# =========================================================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def ensure_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")

# =========================================================
# SESSION STATE
# =========================================================

def init_state() -> None:
    defaults = {
        "session_id": uuid.uuid4().hex[:10],
        "kill_switch": False,
        "signals": {},              # latest signal per symbol
        "signal_table": [],         # latest scanner output
        "portfolio": {},            # normalized target weights
        "order_plan": [],           # current OMS plan
        "last_execution": [],       # current execution blotter
        "orders": [],               # all routed orders
        "fills": [],                # all fills
        "journal": [],              # operational log
        "live_quotes": {},          # latest quote snapshot
        "live_positions": [],       # latest position snapshot
        "live_pnl": [],             # latest PnL snapshot
        "ibkr_status": "DISCONNECTED",
        "ibkr_last_error": "",
        "stream_status": "STOPPED",
        "routing_mode": "PAPER",
        "last_scan_run": "",
        "last_portfolio_run": "",
        "last_oms_run": "",
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =========================================================
# SQLITE STORE
# =========================================================

class SQLiteStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def _connect(self):
        return sqlite3.connect(self.path, timeout=30, check_same_thread=False)

    def append(self, table: str, df: pd.DataFrame) -> None:
        if df is None or df.empty:
            return
        with self.lock, self._connect() as conn:
            df.to_sql(table, conn, if_exists="append", index=False)

    def read(self, table: str, limit: int = 500) -> pd.DataFrame:
        try:
            with self.lock, self._connect() as conn:
                if limit and limit > 0:
                    q = f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT {int(limit)}"
                else:
                    q = f"SELECT * FROM {table}"
                return pd.read_sql_query(q, conn)
        except Exception:
            return pd.DataFrame()

    def tables(self) -> List[str]:
        try:
            with self.lock, self._connect() as conn:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                return [r[0] for r in rows]
        except Exception:
            return []

store = SQLiteStore(DB_PATH)

def persist_df(table: str, df: pd.DataFrame, extra: Optional[Dict[str, object]] = None) -> None:
    if df is None or df.empty:
        return
    out = df.copy()
    out["session_id"] = st.session_state["session_id"]
    out["created_at"] = utc_now_iso()
    out["table_name"] = table
    if extra:
        for k, v in extra.items():
            out[k] = v
    store.append(table, out)

def journaling(message: str, level: str = "INFO") -> None:
    entry = {
        "Time": utc_now_iso(),
        "Level": level,
        "Message": message,
        "SessionID": st.session_state["session_id"],
    }
    st.session_state["journal"].append(entry)
    persist_df("journal", pd.DataFrame([entry]))

# =========================================================
# DATA LAYER
# =========================================================

@st.cache_data(show_spinner=False)
def get_data(symbol: str) -> Optional[pd.DataFrame]:
    try:
        df = yf.download(symbol, period="6mo", progress=False)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    needed = ["Open", "High", "Low", "Close"]
    if not all(col in df.columns for col in needed):
        return None

    return df[needed].dropna()

# =========================================================
# FEATURE ENGINE
# =========================================================

def build_features(symbol: str) -> Optional[pd.DataFrame]:
    df = get_data(symbol)
    bench = get_data(BENCHMARK)

    if df is None or bench is None:
        return None

    df = df.copy()
    bench_close = bench["Close"].copy()
    df["Benchmark"] = bench_close.reindex(df.index)
    df = df.dropna()

    if df.empty:
        return None

    df["RS"] = df["Close"] / df["Benchmark"]
    df["RS_MA"] = df["RS"].rolling(MA_LEN, min_periods=1).mean()
    df["RS_SCORE"] = df["RS"] / df["RS_MA"]

    df["MA"] = df["Close"].rolling(MA_LEN, min_periods=1).mean()

    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs(),
    ], axis=1).max(axis=1)

    df["ATR"] = tr.rolling(ATR_LEN, min_periods=1).mean()
    return df.dropna()

# =========================================================
# SIGNAL ENGINE
# =========================================================

def signal_engine(df: pd.DataFrame) -> Tuple[str, float]:
    last = df.iloc[-1]

    price = float(last["Close"])
    ma = float(last["MA"])
    rs = float(last["RS_SCORE"])
    atr = float(last["ATR"])

    atr_pct = atr / price if price > 0 else 0.0

    if atr_pct > 0.25:
        return "AVOID", 0.0

    trend = (price - ma) / ma
    momentum = rs - 1.0

    score = (
        0.50 * np.clip(trend, -0.2, 0.2) +
        0.35 * np.clip(momentum, -0.3, 0.5) -
        0.15 * np.clip(atr_pct, 0, 0.1)
    )

    prob = 1 / (1 + np.exp(-9 * score))

    if prob > 0.67:
        return "BUY", float(prob)
    elif prob > 0.52:
        return "WATCH", float(prob)
    return "AVOID", float(prob)

# =========================================================
# SCANNER
# =========================================================

def run_scanner() -> pd.DataFrame:
    rows = []

    for symbol in UNIVERSE:
        df = build_features(symbol)
        if df is None:
            continue

        sig, prob = signal_engine(df)
        last_price = float(df["Close"].iloc[-1])

        st.session_state["signals"][symbol] = sig

        rows.append({
            "Symbol": symbol,
            "Signal": sig,
            "Score": round(prob, 4),
            "Last Price": round(last_price, 2),
        })

    out = pd.DataFrame(rows)
    if out.empty:
        st.session_state["signal_table"] = []
        return out

    out = out.sort_values("Score", ascending=False).reset_index(drop=True)
    st.session_state["signal_table"] = out.to_dict("records")
    st.session_state["last_scan_run"] = utc_now_iso()

    persist_df("signals", out, extra={"source": "scanner"})
    journaling("Scanner executed")
    return out

# =========================================================
# SINGLE STOCK
# =========================================================

def single_stock_ui() -> None:
    st.subheader("📊 Single Stock")

    symbol = st.text_input("Symbol", value="AAPL", key="single_stock_symbol").strip().upper()

    if st.button("Run Analysis", key="single_stock_run"):
        if not symbol:
            st.warning("Enter a symbol.")
            return

        df = build_features(symbol)
        if df is None or df.empty:
            st.warning("No data available.")
            return

        sig, prob = signal_engine(df)

        c1, c2, c3 = st.columns(3)
        c1.metric("Signal", sig)
        c2.metric("Probability", f"{prob:.2f}")
        c3.metric("Last Price", f"{df['Close'].iloc[-1]:.2f}")

        st.line_chart(df["Close"], use_container_width=True)
        st.dataframe(df.tail(25), use_container_width=True)

        snap = pd.DataFrame([{
            "Symbol": symbol,
            "Signal": sig,
            "Score": prob,
            "Last Price": float(df["Close"].iloc[-1]),
        }])
        persist_df("signals", snap, extra={"source": "single_stock"})
        journaling(f"Single stock analysis run for {symbol}")

# =========================================================
# PORTFOLIO CONSTRUCTION
# =========================================================

def build_portfolio_from_signals(signals_df: pd.DataFrame) -> pd.DataFrame:
    if signals_df is None or signals_df.empty:
        return pd.DataFrame()

    weights = []
    for _, row in signals_df.iterrows():
        sig = row["Signal"]
        if sig == "BUY":
            w = 1.0
        elif sig == "WATCH":
            w = 0.5
        else:
            w = 0.1
        weights.append(w)

    out = signals_df.copy()
    out["RawWeight"] = weights

    total = float(out["RawWeight"].sum())
    if total <= 0:
        out["Weight"] = 0.0
    else:
        out["Weight"] = out["RawWeight"] / total

    return out[["Symbol", "Signal", "Score", "Last Price", "Weight"]].reset_index(drop=True)

def portfolio_ui() -> None:
    st.subheader("📊 Portfolio")

    c1, c2 = st.columns([1, 1])
    with c1:
        build_btn = st.button("Build Portfolio", key="portfolio_build")
    with c2:
        rebalance_btn = st.button("Rebalance Draft", key="portfolio_rebalance")

    signals_df = pd.DataFrame(st.session_state.get("signal_table", []))
    if signals_df.empty:
        st.info("Run Scanner first to create a signal table.")
        return

    if build_btn or rebalance_btn:
        portfolio_df = build_portfolio_from_signals(signals_df)
        if portfolio_df.empty:
            st.warning("No portfolio could be built.")
            return
        st.session_state["portfolio"] = portfolio_df.set_index("Symbol")["Weight"].to_dict()
        st.session_state["last_portfolio_run"] = utc_now_iso()
        persist_df("portfolio", portfolio_df, extra={"source": "build_portfolio"})
        journaling("Portfolio built")

    portfolio_weights = st.session_state.get("portfolio", {})
    if not portfolio_weights:
        st.info("No portfolio yet. Build one from the current scanner results.")
        return

    weights_df = pd.DataFrame(
        [{"Symbol": k, "Weight": v} for k, v in portfolio_weights.items()]
    ).sort_values("Weight", ascending=False)

    st.dataframe(weights_df, use_container_width=True)

# =========================================================
# RISK OVERLAY
# =========================================================

class RiskOverlay:
    def __init__(
        self,
        max_single_weight: float = 0.18,
        max_gross: float = 1.0,
        min_order_notional: float = 100.0,
        daily_loss_limit: float = 1000.0,
    ):
        self.max_single_weight = max_single_weight
        self.max_gross = max_gross
        self.min_order_notional = min_order_notional
        self.daily_loss_limit = daily_loss_limit

    def daily_loss_breached(self, pnl_df: pd.DataFrame) -> Tuple[bool, str]:
        if pnl_df is None or pnl_df.empty or "DailyPnL" not in pnl_df.columns:
            return False, ""
        daily = ensure_numeric(pnl_df["DailyPnL"]).fillna(0).sum()
        if daily <= -abs(self.daily_loss_limit):
            return True, f"Daily loss limit breached ({daily:,.2f})"
        return False, ""

    def apply(self, plan_df: pd.DataFrame, capital: float, pnl_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        if plan_df is None or plan_df.empty:
            return pd.DataFrame()

        out = plan_df.copy()
        out["RiskStatus"] = "OK"
        out["CanRoute"] = True

        breached, reason = self.daily_loss_breached(pnl_df)
        if breached:
            out["RiskStatus"] = reason
            out["CanRoute"] = False
            out["Qty"] = 0
            out["TargetNotional"] = 0.0
            return out

        out["TargetWeight"] = ensure_numeric(out["TargetWeight"]).fillna(0.0)

        # cap individual weights
        capped_weights = []
        cap_msgs = []
        for w in out["TargetWeight"].tolist():
            if w > self.max_single_weight:
                capped_weights.append(self.max_single_weight)
                cap_msgs.append(f"Capped to {self.max_single_weight:.0%}")
            else:
                capped_weights.append(float(w))
                cap_msgs.append("OK")
        out["TargetWeight"] = capped_weights
        out["RiskStatus"] = cap_msgs

        # cap total gross
        gross = float(out["TargetWeight"].sum())
        if gross > self.max_gross and gross > 0:
            out["TargetWeight"] = out["TargetWeight"] / gross * self.max_gross
            out["RiskStatus"] = "Gross capped"

        out["TargetNotional"] = out["TargetWeight"] * float(capital)
        out["Qty"] = np.floor(out["TargetNotional"] / ensure_numeric(out["Price"]).replace(0, np.nan)).fillna(0).astype(int)

        out.loc[out["TargetNotional"] < self.min_order_notional, "CanRoute"] = False
        out.loc[out["TargetNotional"] < self.min_order_notional, "RiskStatus"] = "Below min notional"
        out.loc[out["Qty"] <= 0, "CanRoute"] = False
        out.loc[out["Qty"] <= 0, "RiskStatus"] = "Qty zero"

        return out

risk_overlay = RiskOverlay()

# =========================================================
# IBKR GATEWAY
# =========================================================

class IBKRGateway:
    def __init__(self):
        self.ib = None
        self.Stock = None
        self.MarketOrder = None
        self.connected = False
        self.account = None
        self.streaming = False
        self.stop_event = threading.Event()
        self.thread = None
        self.lock = threading.Lock()

        self.contracts = {}
        self.tickers = {}
        self.pnl_handle = None
        self.pnl_single_handles = {}

        self.last_quotes_df = pd.DataFrame()
        self.last_positions_df = pd.DataFrame()
        self.last_pnl_df = pd.DataFrame()
        self.last_open_orders_df = pd.DataFrame()
        self.last_error = ""


    def ensure_runtime_fields(self):
        defaults = {
            "last_quotes_df": pd.DataFrame(),
            "last_positions_df": pd.DataFrame(),
            "last_pnl_df": pd.DataFrame(),
            "last_open_orders_df": pd.DataFrame(),
            "last_error": "",
        }
        for name, value in defaults.items():
            if not hasattr(self, name):
                setattr(self, name, value.copy() if isinstance(value, pd.DataFrame) else value)
        return self

    def connect(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1, account: Optional[str] = None) -> bool:
        self.ensure_runtime_fields()
        try:
            from ib_insync import IB, Stock, MarketOrder
        except Exception as e:
            self.last_error = f"ib_insync import failed: {e}"
            self.connected = False
            st.session_state["ibkr_status"] = "IBINSYNC_MISSING"
            st.session_state["ibkr_last_error"] = self.last_error
            return False

        try:
            ib = IB()
            ib.connect(host, int(port), clientId=int(client_id), timeout=5)
            ib.reqMarketDataType(1)
            self.ib = ib
            self.Stock = Stock
            self.MarketOrder = MarketOrder

            self.account = (account or "").strip() or (ib.managedAccounts()[0] if ib.managedAccounts() else None)
            st.session_state["ibkr_account"] = self.account or ""

            self.connected = ib.isConnected()
            st.session_state["ibkr_status"] = "CONNECTED" if self.connected else "DISCONNECTED"
            st.session_state["ibkr_last_error"] = ""

            if self.connected and self.account:
                try:
                    self.pnl_handle = ib.reqPnL(self.account)
                except Exception as e:
                    self.last_error = f"PnL subscription failed: {e}"
                    st.session_state["ibkr_last_error"] = self.last_error

                try:
                    ib.reqPositions()
                except Exception as e:
                    self.last_error = f"Position subscription failed: {e}"
                    st.session_state["ibkr_last_error"] = self.last_error

            self.ensure_runtime_fields()
            return self.connected
        except Exception as e:
            self.last_error = str(e)
            self.connected = False
            st.session_state["ibkr_status"] = "DISCONNECTED"
            st.session_state["ibkr_last_error"] = self.last_error
            return False

    def disconnect(self) -> None:
        self.stop_stream()
        try:
            if self.ib and self.ib.isConnected():
                self.ib.disconnect()
        except Exception:
            pass
        self.connected = False
        st.session_state["ibkr_status"] = "DISCONNECTED"

    def _qualify_contract(self, symbol: str):
        if not self.connected or self.ib is None or self.Stock is None:
            return None
        if symbol in self.contracts:
            return self.contracts[symbol]

        contract = self.Stock(symbol, "SMART", "USD")
        try:
            qualified = self.ib.qualifyContracts(contract)
            if qualified:
                self.contracts[symbol] = qualified[0]
                return qualified[0]
        except Exception as e:
            self.last_error = f"qualifyContracts({symbol}) failed: {e}"
        return None

    def subscribe_market_data(self, symbols: List[str]) -> None:
        if not self.connected or self.ib is None:
            return

        for symbol in symbols:
            contract = self._qualify_contract(symbol)
            if contract is None or symbol in self.tickers:
                continue
            try:
                ticker = self.ib.reqMktData(contract, "", False, False)
                self.tickers[symbol] = ticker
            except Exception as e:
                self.last_error = f"reqMktData({symbol}) failed: {e}"

    def subscribe_pnl_single(self, symbols: List[str]) -> None:
        if not self.connected or self.ib is None or not self.account:
            return

        for symbol in symbols:
            contract = self._qualify_contract(symbol)
            if contract is None:
                continue
            con_id = getattr(contract, "conId", None)
            if not con_id or symbol in self.pnl_single_handles:
                continue
            try:
                self.pnl_single_handles[symbol] = self.ib.reqPnLSingle(self.account, "", con_id)
            except Exception as e:
                self.last_error = f"reqPnLSingle({symbol}) failed: {e}"

    def snapshot_quotes(self) -> pd.DataFrame:
        rows = []
        for symbol, ticker in list(self.tickers.items()):
            try:
                bid = float(ticker.bid) if ticker.bid == ticker.bid else np.nan
                ask = float(ticker.ask) if ticker.ask == ticker.ask else np.nan
                last = float(ticker.last) if ticker.last == ticker.last else np.nan
                close = float(ticker.close) if ticker.close == ticker.close else np.nan
                mark = float(ticker.markPrice) if ticker.markPrice == ticker.markPrice else np.nan

                fallback = last
                if np.isnan(fallback):
                    if not np.isnan(mark):
                        fallback = mark
                    elif not np.isnan(close):
                        fallback = close
                    elif not np.isnan(bid) and not np.isnan(ask):
                        fallback = (bid + ask) / 2.0

                rows.append({
                    "Symbol": symbol,
                    "Bid": bid,
                    "Ask": ask,
                    "Last": last,
                    "Close": close,
                    "Mark": mark,
                    "Mid": (bid + ask) / 2.0 if not np.isnan(bid) and not np.isnan(ask) else np.nan,
                    "PriceUsed": fallback,
                    "Time": getattr(ticker, "time", None),
                })
            except Exception:
                continue

        quotes_df = pd.DataFrame(rows)
        with self.lock:
            self.last_quotes_df = quotes_df
        if not quotes_df.empty:
            persist_df("quotes", quotes_df)
        return quotes_df

    def snapshot_positions(self) -> pd.DataFrame:
        if not self.connected or self.ib is None:
            return pd.DataFrame()

        positions = []
        try:
            for p in self.ib.positions():
                symbol = getattr(p.contract, "symbol", None)
                if not symbol:
                    continue
                positions.append({
                    "Account": getattr(p, "account", self.account),
                    "Symbol": symbol,
                    "Position": float(getattr(p, "position", 0.0)),
                    "AvgCost": float(getattr(p, "avgCost", 0.0)),
                    "ConId": int(getattr(p.contract, "conId", 0) or 0),
                })
        except Exception as e:
            self.last_error = f"positions snapshot failed: {e}"
            return pd.DataFrame()

        pos_df = pd.DataFrame(positions)
        if pos_df.empty:
            with self.lock:
                self.last_positions_df = pos_df
            return pos_df

        quotes_df = self.snapshot_quotes()
        if not quotes_df.empty:
            pos_df = pos_df.merge(
                quotes_df[["Symbol", "PriceUsed"]],
                on="Symbol",
                how="left"
            )
        else:
            pos_df["PriceUsed"] = np.nan

        pos_df["PriceUsed"] = pos_df["PriceUsed"].fillna(pos_df["AvgCost"])
        pos_df["MarketValue"] = pos_df["Position"] * pos_df["PriceUsed"]
        pos_df["UnrealizedPnL"] = (pos_df["PriceUsed"] - pos_df["AvgCost"]) * pos_df["Position"]

        total_mv = float(pos_df["MarketValue"].abs().sum())
        pos_df["Weight"] = np.where(total_mv > 0, pos_df["MarketValue"].abs() / total_mv, 0.0)

        with self.lock:
            self.last_positions_df = pos_df
        persist_df("positions", pos_df)
        return pos_df

    def snapshot_open_orders(self) -> pd.DataFrame:
        if not self.connected or self.ib is None:
            return pd.DataFrame()

        rows = []
        try:
            # openTrades/openOrders are the preferred live view in ib_insync.
            trades = []
            try:
                trades = self.ib.openTrades()
            except Exception:
                trades = self.ib.reqOpenOrders()
            for tr in trades:
                contract = getattr(tr, "contract", None)
                order = getattr(tr, "order", None)
                status = getattr(tr, "orderStatus", None)
                rows.append({
                    "Symbol": getattr(contract, "symbol", None),
                    "Action": getattr(order, "action", None),
                    "Qty": float(getattr(order, "totalQuantity", 0.0)),
                    "Status": getattr(status, "status", None),
                    "LimitPrice": float(getattr(order, "lmtPrice", np.nan)) if getattr(order, "lmtPrice", None) is not None else np.nan,
                    "AuxPrice": float(getattr(order, "auxPrice", np.nan)) if getattr(order, "auxPrice", None) is not None else np.nan,
                })
        except Exception as e:
            self.last_error = f"open orders snapshot failed: {e}"
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        with self.lock:
            self.last_open_orders_df = df
        if not df.empty:
            persist_df("open_orders", df)
        return df

    def snapshot_pnl(self) -> pd.DataFrame:
        rows = []

        if self.pnl_handle is not None:
            try:
                rows.append({
                    "Scope": "ACCOUNT",
                    "Symbol": "ALL",
                    "DailyPnL": float(getattr(self.pnl_handle, "dailyPnL", np.nan)),
                    "UnrealizedPnL": float(getattr(self.pnl_handle, "unrealizedPnL", np.nan)),
                    "RealizedPnL": float(getattr(self.pnl_handle, "realizedPnL", np.nan)),
                })
            except Exception:
                pass

        pos_df = self.last_positions_df.copy()
        if not pos_df.empty:
            for _, row in pos_df.iterrows():
                rows.append({
                    "Scope": "MTM",
                    "Symbol": row["Symbol"],
                    "DailyPnL": np.nan,
                    "UnrealizedPnL": float(row.get("UnrealizedPnL", np.nan)),
                    "RealizedPnL": np.nan,
                })

        pnl_df = pd.DataFrame(rows)
        with self.lock:
            self.last_pnl_df = pnl_df
        if not pnl_df.empty:
            persist_df("pnl", pnl_df)
        return pnl_df

    def refresh_all(self) -> Dict[str, pd.DataFrame]:
        quotes_df = self.snapshot_quotes()
        positions_df = self.snapshot_positions()
        open_orders_df = self.snapshot_open_orders()
        pnl_df = self.snapshot_pnl()
        return {
            "quotes": quotes_df,
            "positions": positions_df,
            "open_orders": open_orders_df,
            "pnl": pnl_df,
        }

    async def _stream_worker(self, symbols: List[str], poll_seconds: float = 2.0) -> None:
        if not self.connected:
            self.connected = False
            return

        self.subscribe_market_data(symbols)
        self.subscribe_pnl_single(symbols)

        self.streaming = True
        st.session_state["stream_status"] = "RUNNING"

        while not self.stop_event.is_set() and self.connected:
            try:
                self.refresh_all()
            except Exception as e:
                self.last_error = str(e)
            await asyncio.sleep(poll_seconds)

        self.streaming = False
        st.session_state["stream_status"] = "STOPPED"

    def start_stream(self, symbols: List[str]) -> bool:
        if not self.connected:
            return False
        if self.streaming and self.thread and self.thread.is_alive():
            return True

        self.stop_event.clear()

        def runner():
            try:
                asyncio.run(self._stream_worker(symbols))
            except Exception as e:
                self.last_error = f"stream thread failed: {e}"
                self.streaming = False
                st.session_state["stream_status"] = "STOPPED"

        self.thread = threading.Thread(target=runner, daemon=True)
        self.thread.start()
        return True

    def stop_stream(self) -> None:
        self.stop_event.set()
        self.streaming = False
        st.session_state["stream_status"] = "STOPPED"

    def place_order(self, symbol: str, qty: int, action: str = "BUY") -> Optional[dict]:
        if not self.connected or self.ib is None or self.MarketOrder is None:
            return None

def start_stream(self, symbols: List[str]) -> bool:
    if not self.connected:
        return False

    if self.streaming and self.thread and self.thread.is_alive():
        return True

    # subscribe once
    self.subscribe_market_data(symbols)
    self.subscribe_pnl_single(symbols)

    self.streaming = True
    self.stop_event.clear()
    st.session_state["stream_status"] = "RUNNING"

    def loop():
        while self.streaming and not self.stop_event.is_set():
            try:
                self.refresh_all()
                time.sleep(2)
            except Exception as e:
                self.last_error = str(e)
                st.session_state["ibkr_last_error"] = self.last_error

        self.streaming = False
        st.session_state["stream_status"] = "STOPPED"

    self.thread = threading.Thread(target=loop, daemon=True)
    self.thread.start()
    return True


def stop_stream(self) -> None:
    self.stop_event.set()
    self.streaming = False
    st.session_state["stream_status"] = "STOPPED"
        if contract is None:
            return None

        try:
            order = self.MarketOrder(action, int(qty))
            trade = self.ib.placeOrder(contract, order)

            entry = {
                "Time": utc_now_iso(),
                "Symbol": symbol,
                "Action": action,
                "Qty": int(qty),
                "Status": getattr(trade.orderStatus, "status", "SUBMITTED"),
                "OrderId": getattr(trade.order, "orderId", None),
                "PermId": getattr(trade.orderStatus, "permId", None),
                "Live": True,
        
            st.session_state["orders"].append(entry)
            persist_df("orders", pd.DataFrame([entry]))
            return entry
        except Exception as e:
            self.last_error = f"placeOrder({symbol}) failed: {e}"
            st.session_state["ibkr_last_error"] = self.last_error
            return None

@st.cache_resource
def get_gateway() -> IBKRGateway:
    gateway = IBKRGateway()
    return gateway.ensure_runtime_fields()

# =========================================================
# ORDER PLAN / ROUTING
# =========================================================

def current_price_lookup(gateway: IBKRGateway, symbol: str) -> Optional[float]:
    quotes_df = gateway.last_quotes_df
    if quotes_df is not None and not quotes_df.empty and "Symbol" in quotes_df.columns:
        hit = quotes_df.loc[quotes_df["Symbol"] == symbol]
        if not hit.empty:
            for col in ("PriceUsed", "Last", "Mark", "Close", "Mid"):
                if col in hit.columns:
                    value = hit.iloc[0][col]
                    if pd.notna(value) and float(value) > 0:
                        return float(value)

    df = build_features(symbol)
    if df is None or df.empty:
        return None
    return float(df["Close"].iloc[-1])

def build_order_plan(
    capital: float,
    prices: Optional[pd.DataFrame] = None,
    weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    weights = weights or st.session_state.get("portfolio", {})
    if not weights:
        return pd.DataFrame()

    price_lookup = {}
    if prices is not None and not prices.empty and "Symbol" in prices.columns:
        tmp = prices.copy()
        for _, row in tmp.iterrows():
            for col in ("PriceUsed", "Last", "Mark", "Close", "Mid"):
                if col in tmp.columns and pd.notna(row.get(col, np.nan)) and float(row.get(col, 0) or 0) > 0:
                    price_lookup[row["Symbol"]] = float(row[col])
                    break

    rows = []
    for symbol, weight in weights.items():
        price = price_lookup.get(symbol)

        if price is None or not np.isfinite(price) or price <= 0:
            price = current_price_lookup(get_gateway(), symbol)

        if price is None or not np.isfinite(price) or price <= 0:
            continue

        target_notional = float(capital) * float(weight)
        qty = int(target_notional / price) if price > 0 else 0

        rows.append({
            "Symbol": symbol,
            "Side": "BUY",
            "TargetWeight": float(weight),
            "Price": round(price, 2),
            "TargetNotional": round(target_notional, 2),
            "Qty": qty,
        })

    plan = pd.DataFrame(rows)
    if plan.empty:
        return plan

    plan["Capital"] = float(capital)
    return plan

def route_orders(
    plan_df: pd.DataFrame,
    gateway: IBKRGateway,
    live: bool = False
) -> pd.DataFrame:
    if plan_df is None or plan_df.empty:
        return pd.DataFrame()

    executed = []
    for _, row in plan_df.iterrows():
        if int(row.get("Qty", 0)) <= 0:
            continue

        symbol = str(row["Symbol"])
        qty = int(row["Qty"])
        price = float(row["Price"])
        route_live = bool(live and gateway.connected)

        if route_live:
            routed = gateway.place_order(symbol=symbol, qty=qty, action=str(row.get("Side", "BUY")))
            status = str(routed.get("Status", "SUBMITTED")) if routed else "REJECTED"
            mode = "LIVE"
        else:
            status = "SIM_FILLED"
            mode = "PAPER"
            entry = {
                "Time": utc_now_iso(),
                "Symbol": symbol,
                "Action": str(row.get("Side", "BUY")),
                "Qty": qty,
                "Status": status,
                "OrderId": None,
                "PermId": None,
                "Live": False,
            }
            st.session_state["orders"].append(entry)
            persist_df("orders", pd.DataFrame([entry]))

        fill = {
            "Time": utc_now_iso(),
            "Symbol": symbol,
            "Qty": qty,
            "Price": price,
            "RiskStatus": str(row.get("RiskStatus", "OK")),
            "Status": status,
            "Mode": mode,
        }

        executed.append(fill)
        st.session_state["fills"].append(fill)

    exec_df = pd.DataFrame(executed)
    if not exec_df.empty:
        persist_df("fills", exec_df)
    return exec_df

# =========================================================
# UI HELPERS
# =========================================================

def show_table(title: str, df: pd.DataFrame, height: int = 260) -> None:
    st.markdown(f"### {title}")
    if df is None or df.empty:
        st.info("No rows yet.")
        return
    st.dataframe(df, use_container_width=True, height=height)

def fmt_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return df.copy()


def safe_gateway_df(gateway, attr: str) -> pd.DataFrame:
    value = getattr(gateway, attr, pd.DataFrame())
    if value is None or not isinstance(value, pd.DataFrame) or value.empty:
        return pd.DataFrame()
    return value.copy()

# =========================================================
# PAGES
# =========================================================

def page_scanner() -> None:
    st.subheader("📡 Scanner")

    c1, c2 = st.columns([1, 2])
    with c1:
        run_btn = st.button("Run Scan", key="scan_run_btn")
    with c2:
        st.caption("Generate signals for the full universe and store them for portfolio construction.")

    if run_btn:
        df = run_scanner()
        st.dataframe(df, width="stretch")
    else:
        preview = pd.DataFrame(st.session_state.get("signal_table", []))
        if not preview.empty:
            st.dataframe(preview, use_container_width=True)
        else:
            st.info("Press Run Scan to generate signal rows.")

def page_single_stock() -> None:
    single_stock_ui()

def page_portfolio() -> None:
    st.subheader("📊 Portfolio")

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        build_btn = st.button("Build Portfolio", key="portfolio_build")
    with c2:
        rebalance_btn = st.button("Rebalance Draft", key="portfolio_rebalance")
    with c3:
        load_btn = st.button("Load From DB", key="portfolio_load_db")

    signals_df = pd.DataFrame(st.session_state.get("signal_table", []))
    if signals_df.empty and load_btn:
        signals_df = store.read("signals", limit=200)
        if not signals_df.empty and "source" in signals_df.columns:
            signals_df = signals_df.drop_duplicates(subset=["Symbol"], keep="last")

    if signals_df.empty:
        st.info("Run Scanner first to create a signal table.")
        preview = store.read("portfolio", limit=50)
        if not preview.empty:
            show_table("Stored Portfolio", preview, height=240)
        return

    if build_btn or rebalance_btn:
        portfolio_df = build_portfolio_from_signals(signals_df)
        if portfolio_df.empty:
            st.warning("No portfolio could be built.")
            return
        st.session_state["portfolio"] = portfolio_df.set_index("Symbol")["Weight"].to_dict()
        st.session_state["last_portfolio_run"] = utc_now_iso()
        persist_df("portfolio", portfolio_df, extra={"source": "build_portfolio"})
        journaling("Portfolio built")

    portfolio_weights = st.session_state.get("portfolio", {})
    if not portfolio_weights:
        st.info("No portfolio yet. Build one from the current scanner results.")
        return

    weights_df = pd.DataFrame(
        [{"Symbol": k, "Weight": v} for k, v in portfolio_weights.items()]
    ).sort_values("Weight", ascending=False)

    st.dataframe(weights_df, use_container_width=True)

def page_live_ibkr() -> None:
    st.subheader("📡 Live IBKR Gateway")

    gateway = get_gateway().ensure_runtime_fields()

    col1, col2, col3 = st.columns(3)
    with col1:
        host = st.text_input("Host", value=st.session_state.get("ibkr_host", DEFAULT_HOST), key="ib_host")
    with col2:
        port = st.number_input("Port", value=int(st.session_state.get("ibkr_port", DEFAULT_PORT)), step=1, key="ib_port")
    with col3:
        client_id = st.number_input("Client ID", value=int(st.session_state.get("ibkr_client_id", DEFAULT_CLIENT_ID)), step=1, key="ib_client_id")

    account = st.text_input("Account (optional)", value=st.session_state.get("ibkr_account", gateway.account or ""), key="ib_account")

    b1, b2, b3, b4 = st.columns(4)
    with b1:
        connect_btn = st.button("Connect IBKR", key="ib_connect_btn")
    with b2:
        start_btn = st.button("Start Stream", key="ib_start_btn")
    with b3:
        stop_btn = st.button("Stop Stream", key="ib_stop_btn")
    with b4:
        refresh_btn = st.button("Refresh Snapshot", key="ib_refresh_btn")

    if connect_btn:
        st.session_state["ibkr_host"] = host
        st.session_state["ibkr_port"] = int(port)
        st.session_state["ibkr_client_id"] = int(client_id)
        st.session_state["ibkr_account"] = account.strip()

        ok = gateway.connect(
            host=host.strip() or DEFAULT_HOST,
            port=int(port),
            client_id=int(client_id),
            account=account.strip() or None,
        )
        if ok:
            gateway.refresh_all()
            st.success("Connected to IBKR / TWS / Gateway.")
            journaling("IBKR connected")
        else:
            st.error(f"IBKR connection failed: {gateway.last_error}")
            journaling(f"IBKR connect failed: {gateway.last_error}")

    if start_btn:
        symbols = list(st.session_state.get("portfolio", {}).keys()) or UNIVERSE
        ok = gateway.start_stream(list(symbols))
        if ok:
            st.success("Live stream started.")
            journaling("Live stream started")
        else:
            st.warning("Could not start stream. Connect IBKR first.")

    if stop_btn:
        gateway.stop_stream()
        st.info("Live stream stopped.")
        journaling("Live stream stopped")

    if refresh_btn:
        gateway.refresh_all()
        journaling("Live snapshot refreshed")

    status_col1, status_col2, status_col3 = st.columns(3)
    status_col1.metric("IBKR Status", st.session_state.get("ibkr_status", "UNKNOWN"))
    status_col2.metric("Stream Status", st.session_state.get("stream_status", "STOPPED"))
    status_col3.metric("Quotes", len(safe_gateway_df(gateway, "last_quotes_df")))

    show_table("Live Quotes", safe_gateway_df(gateway, "last_quotes_df"), height=260)
    show_table("Live Positions", safe_gateway_df(gateway, "last_positions_df"), height=260)
    show_table("Open Orders", safe_gateway_df(gateway, "last_open_orders_df"), height=220)

    pnl_df = safe_gateway_df(gateway, "last_pnl_df")
    if not pnl_df.empty:
        total_unreal = pnl_df.get("UnrealizedPnL", pd.Series(dtype=float)).fillna(0).sum()
        total_daily = pnl_df.get("DailyPnL", pd.Series(dtype=float)).fillna(0).sum()
        total_real = pnl_df.get("RealizedPnL", pd.Series(dtype=float)).fillna(0).sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Unrealized PnL", f"{total_unreal:,.2f}")
        m2.metric("Daily PnL", f"{total_daily:,.2f}")
        m3.metric("Realized PnL", f"{total_real:,.2f}")
    show_table("PnL Table", pnl_df, height=260)

    if gateway.last_error:
        st.warning(f"Last IBKR message: {gateway.last_error}")

def page_oms_execution() -> None:
    st.subheader("⚙️ OMS Execution Layer")

    gateway = get_gateway().ensure_runtime_fields()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        capital = st.number_input("Capital ($)", value=100000.0, step=10000.0, key="oms_capital")
    with c2:
        live_mode = st.toggle("Live Routing", value=False, key="oms_live_mode")
    with c3:
        max_single_weight = st.number_input("Max Single Weight", value=0.18, min_value=0.01, max_value=1.0, step=0.01, key="oms_max_single_weight")
    with c4:
        max_daily_loss = st.number_input("Daily Loss Limit ($)", value=1000.0, min_value=0.0, step=100.0, key="oms_daily_loss_limit")

    risk_overlay.max_single_weight = float(max_single_weight)
    risk_overlay.daily_loss_limit = float(max_daily_loss)

    refresh_btn = st.button("Refresh Quotes", key="oms_refresh_quotes_btn")
    if refresh_btn:
        gateway.refresh_all()
        journaling("OMS quotes refreshed")

    c5, c6, c7 = st.columns(3)
    with c5:
        build_btn = st.button("Build OMS Plan", key="oms_build_plan_btn")
    with c6:
        send_orders_btn = st.button("Send Orders", key="oms_send_orders_btn")
    with c7:
        clear_btn_pressed = st.button("Clear Blotter", key="oms_clear_btn")

    if clear_btn_pressed:
        st.session_state["orders"] = []
        st.session_state["fills"] = []
        st.session_state["order_plan"] = []
        st.session_state["last_execution"] = []
        journaling("OMS blotter cleared")
        st.success("Cleared blotter.")

    portfolio_weights = st.session_state.get("portfolio", {})
    signals_df = pd.DataFrame(st.session_state.get("signal_table", []))

    if build_btn:
        if portfolio_weights:
            base_weights = portfolio_weights
        elif not signals_df.empty:
            draft = build_portfolio_from_signals(signals_df)
            base_weights = dict(zip(draft["Symbol"], draft["Weight"])) if not draft.empty else {}
        else:
            base_weights = {}

        if not base_weights:
            st.warning("Build a portfolio or run the scanner first.")
            return

        plan = build_order_plan(capital=float(capital), prices=gateway.last_quotes_df, weights=base_weights)
        if plan.empty:
            st.warning("No OMS plan could be built.")
            return

        plan = risk_overlay.apply(plan, capital=float(capital), pnl_df=gateway.last_pnl_df)
        st.session_state["order_plan"] = plan.to_dict("records")
        st.session_state["last_oms_run"] = utc_now_iso()
        persist_df("order_plan", plan, extra={"source": "oms_build"})
        journaling("OMS plan built")

    plan_df = pd.DataFrame(st.session_state.get("order_plan", []))
    show_table("Order Plan", plan_df, height=260)

    if not plan_df.empty:
        routeable = int(plan_df.get("CanRoute", pd.Series(dtype=bool)).fillna(False).sum()) if "CanRoute" in plan_df.columns else 0
        blocked = int(len(plan_df) - routeable)
        a, b, c = st.columns(3)
        a.metric("Routeable", routeable)
        b.metric("Blocked", blocked)
        c.metric("Mode", "LIVE" if live_mode and gateway.connected else "PAPER")

    if send_orders_btn:
        if plan_df.empty:
            st.warning("Build an OMS plan first.")
            return

        route_mode = bool(live_mode and gateway.connected)
        if live_mode and not gateway.connected:
            st.warning("Live routing requested but IBKR is not connected. Falling back to PAPER routing.")

        allowed_plan = plan_df.copy()
        if "CanRoute" in allowed_plan.columns:
            allowed_plan = allowed_plan.loc[allowed_plan["CanRoute"].astype(bool)].copy()
        else:
            allowed_plan = allowed_plan.copy()

        if allowed_plan.empty:
            st.warning("No orders passed the risk overlay.")
            return

        exec_df = route_orders(allowed_plan, gateway, live=route_mode)
        st.session_state["last_execution"] = exec_df.to_dict("records")
        st.session_state["routing_mode"] = "LIVE" if route_mode else "PAPER"
        journaling(f"Orders routed ({'LIVE' if route_mode else 'PAPER'})")
        st.success("Orders processed.")

        if not exec_df.empty:
            persist_df("execution", exec_df, extra={"source": "oms_route"})

    exec_df = pd.DataFrame(st.session_state.get("last_execution", []))
    show_table("Execution Blotter", exec_df, height=260)

    fills_df = pd.DataFrame(st.session_state.get("fills", []))
    show_table("Fills", fills_df, height=220)

    if not gateway.last_positions_df.empty:
        show_table("Risk / Position Snapshot", safe_gateway_df(gateway, "last_positions_df"), height=260)

    if not gateway.last_pnl_df.empty:
        show_table("PnL Snapshot", safe_gateway_df(gateway, "last_pnl_df"), height=260)

    st.caption(
        "IBKR routing uses the TWS/IB Gateway API; market data subscriptions and account PnL / position updates are exposed by the API, and ib_insync wraps the API with asyncio networking. "
        "Live market data requires the relevant subscriptions."
    )

def page_journal() -> None:
    st.subheader("🧾 Journal")

    c1, c2 = st.columns([1, 1])
    with c1:
        refresh_btn = st.button("Refresh Journal", key="journal_refresh_btn")
    with c2:
        export_btn = st.button("Export DB Tables", key="journal_export_btn")

    if refresh_btn:
        journaling("Journal refreshed")

    if export_btn:
        journaling("DB export requested")
        st.info(f"SQLite database path: {DB_PATH}")

    journal_df = pd.DataFrame(st.session_state.get("journal", []))
    show_table("Event Journal", journal_df, height=300)

def page_database() -> None:
    st.subheader("🗄️ SQLite Database")

    tables = store.tables()
    if not tables:
        st.info("No tables yet.")
        return

    selected = st.selectbox("Table", tables, key="db_table_select")
    limit = st.slider("Rows", 50, 2000, 300, key="db_limit_slider")

    if st.button("Load Table", key="db_load_btn"):
        st.session_state["db_loaded_table"] = selected

    table_name = st.session_state.get("db_loaded_table", selected)
    df = store.read(table_name, limit=limit)
    show_table(f"Table: {table_name}", df, height=380)

# =========================================================
# ROUTER
# =========================================================

def main() -> None:
    st.sidebar.title("🧠 JFBP Quant Desk v14")

    if st.sidebar.button("🚨 Kill Switch", key="kill_switch_btn"):
        st.session_state["kill_switch"] = True

    if st.session_state["kill_switch"]:
        st.error("SYSTEM DISABLED")
        st.stop()

    mode = st.sidebar.radio(
        "Mode",
        ["Scanner", "Single Stock", "Portfolio", "Live IBKR", "OMS Execution", "Journal", "Database"],
        index=0,
        key="main_mode_radio"
    )

    st.sidebar.divider()
    st.sidebar.write(f"IBKR: {st.session_state.get('ibkr_status', 'DISCONNECTED')}")
    st.sidebar.write(f"Stream: {st.session_state.get('stream_status', 'STOPPED')}")
    st.sidebar.write(f"Route Mode: {st.session_state.get('routing_mode', 'PAPER')}")
    st.sidebar.write(f"SQLite: {DB_PATH.name}")

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Signals", len(st.session_state.get("signal_table", [])))
    top2.metric("Orders", len(st.session_state.get("orders", [])))
    top3.metric("Fills", len(st.session_state.get("fills", [])))
    top4.metric("Journal", len(st.session_state.get("journal", [])))

    if mode == "Scanner":
        page_scanner()
    elif mode == "Single Stock":
        page_single_stock()
    elif mode == "Portfolio":
        page_portfolio()
    elif mode == "Live IBKR":
        page_live_ibkr()
    elif mode == "OMS Execution":
        page_oms_execution()
    elif mode == "Journal":
        page_journal()
    elif mode == "Database":
        page_database()

# =========================================================
# BOOT
# =========================================================

if __name__ == "__main__":
    main()
