# =========================================================
# 🧪 JFBP QUANT DESK v15 — BACKTEST / REPLAY ENGINE
# =========================================================

from __future__ import annotations

import time
import uuid
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


# =========================================================
# 📦 REPLAY CONFIG
# =========================================================

@dataclass
class ReplayConfig:
    symbol: str
    starting_cash: float = 100000.0
    max_positions: int = 10
    commission_per_trade: float = 0.0


# =========================================================
# 🧠 PORTFOLIO STATE (SIMULATED BROKER)
# =========================================================

class ReplayPortfolio:
    def __init__(self, config: ReplayConfig):
        self.config = config

        self.cash = config.starting_cash
        self.positions: Dict[str, int] = {}
        self.entry_price: Dict[str, float] = {}

        self.realized_pnl = 0.0
        self.trades: List[dict] = []

    # -----------------------------------------------------
    # POSITION UPDATE
    # -----------------------------------------------------

    def update_position(self, symbol: str, action: str, qty: int, price: float):

        pos = self.positions.get(symbol, 0)

        if action == "BUY":
            new_pos = pos + qty
        else:
            new_pos = pos - qty

        # PnL calculation (simple mark-to-trade)
        entry = self.entry_price.get(symbol)

        if entry is None:
            self.entry_price[symbol] = price

        pnl_change = (price - self.entry_price[symbol]) * (new_pos - pos)

        self.cash -= pnl_change
        self.positions[symbol] = new_pos

        # update entry (smoothed like OMS v15)
        self.entry_price[symbol] = (
            0.7 * self.entry_price[symbol] + 0.3 * price
        )

        self.realized_pnl += pnl_change

        self.trades.append({
            "symbol": symbol,
            "action": action,
            "qty": qty,
            "price": price,
            "time": time.time(),
            "pnl": pnl_change,
        })


# =========================================================
# 🧪 REPLAY ENGINE
# =========================================================

class ReplayEngine:

    def __init__(self, core_engine, risk_engine, oms_engine):
        self.core = core_engine
        self.risk = risk_engine
        self.oms = oms_engine

        self.portfolio: Optional[ReplayPortfolio] = None

        self.equity_curve: List[float] = []
        self.timestamps: List[float] = []

    # -----------------------------------------------------
    # INIT BACKTEST
    # -----------------------------------------------------

    def init(self, config: ReplayConfig):
        self.portfolio = ReplayPortfolio(config)

    # -----------------------------------------------------
    # PROCESS SINGLE BAR / TICK
    # -----------------------------------------------------

    def on_tick(self, symbol: str, tick: dict):

        if self.portfolio is None:
            raise RuntimeError("ReplayEngine not initialized")

        price = tick.get("price")

        if price is None or not np.isfinite(price):
            return

        # =====================================================
        # 1. SIGNAL GENERATION (CORE ENGINE)
        # =====================================================

        signal = self.core.compute_signal(symbol, tick)

        if signal is None:
            return

        # =====================================================
        # 2. RISK CHECK
        # =====================================================

        ok, reason = self.risk.risk_check(
            symbol=symbol,
            action=signal,
            price=price,
            portfolio=self.portfolio.positions
        )

        if not ok:
            return

        # =====================================================
        # 3. EXECUTION (SIM OMS)
        # =====================================================

        if signal in ["BUY", "SELL"]:

            qty = 1

            self.portfolio.update_position(
                symbol=symbol,
                action=signal,
                qty=qty,
                price=price
            )

        # =====================================================
        # 4. EQUITY TRACKING
        # =====================================================

        equity = self.portfolio.cash + self.portfolio.realized_pnl

        self.equity_curve.append(equity)
        self.timestamps.append(time.time())

    # -----------------------------------------------------
    # RUN FULL DATASET
    # -----------------------------------------------------

    def run(self, df: pd.DataFrame, symbol: str, price_col: str = "Close"):

        for i in range(len(df)):

            row = df.iloc[i]

            tick = {
                "price": float(row[price_col]),
                "timestamp": row.get("timestamp", time.time())
            }

            self.on_tick(symbol, tick)

        return pd.DataFrame({
            "equity": self.equity_curve,
            "time": self.timestamps
        })


# =========================================================
# 📊 RESULTS SUMMARY
# =========================================================

def summarize_replay(engine: ReplayEngine):

    if engine.portfolio is None:
        return {}

    return {
        "final_equity": engine.equity_curve[-1] if engine.equity_curve else 0,
        "realized_pnl": engine.portfolio.realized_pnl,
        "num_trades": len(engine.portfolio.trades),
        "final_positions": engine.portfolio.positions,
    }