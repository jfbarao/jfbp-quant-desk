# =========================================================
# 🧪 JFBP QUANT DESK v15 — SIMULATED OMS ENGINE
# =========================================================

from __future__ import annotations

import time
import uuid
import numpy as np
import pandas as pd

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# =========================================================
# 📦 SIM ORDER
# =========================================================

@dataclass
class SimOrder:
    symbol: str
    action: str
    qty: int
    price: float

    timestamp: float = field(default_factory=time.time)

    status: str = "FILLED"

    order_id: str = field(
        default_factory=lambda: uuid.uuid4().hex
    )


# =========================================================
# 📦 SIM POSITION
# =========================================================

@dataclass
class SimPosition:
    symbol: str
    qty: int = 0
    avg_price: float = 0.0


# =========================================================
# 🧠 SIM OMS ENGINE
# =========================================================

class SimOMSEngine:

    def __init__(self):

        self.orders: List[SimOrder] = []

        self.positions: Dict[str, SimPosition] = {}

        self.realized_pnl = 0.0

        self.last_order_time: Dict[str, float] = {}

        self.trade_log: List[dict] = []

    # -----------------------------------------------------
    # POSITION LOOKUP
    # -----------------------------------------------------

    def get_position(self, symbol: str) -> int:

        pos = self.positions.get(symbol)

        if pos is None:
            return 0

        return pos.qty

    # -----------------------------------------------------
    # THROTTLE
    # -----------------------------------------------------

    def can_trade(
        self,
        symbol: str,
        cooldown_seconds: int = 5
    ) -> bool:

        now = time.time()

        last = self.last_order_time.get(symbol, 0)

        return (now - last) >= cooldown_seconds

    # -----------------------------------------------------
    # EXECUTE ORDER
    # -----------------------------------------------------

    def place_order(
        self,
        symbol: str,
        action: str,
        qty: int,
        price: float
    ) -> Optional[SimOrder]:

        # =====================================================
        # INPUT VALIDATION
        # =====================================================

        if action not in ["BUY", "SELL"]:
            return None

        if qty <= 0:
            return None

        if (
            price is None
            or not np.isfinite(price)
            or price <= 0
        ):
            return None

        # =====================================================
        # THROTTLE
        # =====================================================

        if not self.can_trade(symbol):
            return None

        self.last_order_time[symbol] = time.time()

        # =====================================================
        # CREATE ORDER
        # =====================================================

        order = SimOrder(
            symbol=symbol,
            action=action,
            qty=qty,
            price=price
        )

        self.orders.append(order)

        # =====================================================
        # POSITION UPDATE
        # =====================================================

        if symbol not in self.positions:
            self.positions[symbol] = SimPosition(symbol=symbol)

        pos = self.positions[symbol]

        old_qty = pos.qty
        old_avg = pos.avg_price

        # =====================================================
        # BUY
        # =====================================================

        if action == "BUY":

            new_qty = old_qty + qty

            if new_qty != 0:

                pos.avg_price = (
                    (old_qty * old_avg) + (qty * price)
                ) / new_qty

            pos.qty = new_qty

        # =====================================================
        # SELL
        # =====================================================

        else:

            realized = (price - old_avg) * qty

            self.realized_pnl += realized

            pos.qty -= qty

            # short entry reset
            if pos.qty <= 0:
                pos.avg_price = price

        # =====================================================
        # TRADE LOG
        # =====================================================

        self.trade_log.append({
            "symbol": symbol,
            "action": action,
            "qty": qty,
            "price": price,
            "timestamp": order.timestamp,
            "realized_pnl": self.realized_pnl,
        })

        return order

    # -----------------------------------------------------
    # MARK TO MARKET
    # -----------------------------------------------------

    def mark_to_market(
        self,
        market_prices: Dict[str, float]
    ) -> float:

        unrealized = 0.0

        for symbol, pos in self.positions.items():

            if pos.qty == 0:
                continue

            market_price = market_prices.get(symbol)

            if (
                market_price is None
                or not np.isfinite(market_price)
            ):
                continue

            unrealized += (
                (market_price - pos.avg_price)
                * pos.qty
            )

        return unrealized

    # -----------------------------------------------------
    # TOTAL EQUITY
    # -----------------------------------------------------

    def total_equity(
        self,
        market_prices: Dict[str, float]
    ) -> float:

        unrealized = self.mark_to_market(market_prices)

        return self.realized_pnl + unrealized

    # -----------------------------------------------------
    # EXPORT TRADES
    # -----------------------------------------------------

    def trades_df(self) -> pd.DataFrame:

        return pd.DataFrame(self.trade_log)

    # -----------------------------------------------------
    # EXPORT POSITIONS
    # -----------------------------------------------------

    def positions_df(self) -> pd.DataFrame:

        rows = []

        for symbol, pos in self.positions.items():

            rows.append({
                "Symbol": symbol,
                "Qty": pos.qty,
                "AvgPrice": pos.avg_price,
            })

        return pd.DataFrame(rows)