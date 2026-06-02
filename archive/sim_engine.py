# =========================================================
# JFBP QUANT DESK — SIMULATION OMS ENGINE
# =========================================================

from typing import Dict, Any, Optional
from execution.oms_engine import Order, Fill
import time
import uuid
import random


class SimEngine:
    """
    SIMULATION Order Management System Engine.

    Mirrors OMSEngine interface for:
    - backtesting
    - paper trading
    - deterministic strategy validation
    """

    def __init__(self, portfolio=None, risk_manager=None, slippage_bps: float = 1.0):
        self.portfolio = portfolio
        self.risk_manager = risk_manager
        self.slippage_bps = slippage_bps

        self.open_orders: Dict[str, Order] = {}
        self.fills: Dict[str, Fill] = {}

    # -----------------------------------------------------
    # MAIN ENTRY POINT (same as LIVE engine)
    # -----------------------------------------------------

    def submit_order(self, order: Order) -> Dict[str, Any]:
        self._validate_order(order)

        if self.risk_manager:
            approved = self.risk_manager.check_order(order)
            if not approved:
                return {
                    "status": "REJECTED",
                    "reason": "Risk manager rejected order",
                    "order_id": order.order_id
                }

        self.open_orders[order.order_id] = order

        fill = self._simulate_fill(order)

        self._process_fill(fill)

        return {
            "status": "FILLED",
            "order_id": order.order_id,
            "fill_price": fill.price,
            "quantity": fill.quantity
        }

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    def _validate_order(self, order: Order):
        if order.quantity <= 0:
            raise ValueError("Order quantity must be > 0")

        if order.side not in ("BUY", "SELL"):
            raise ValueError("Order side must be BUY or SELL")

    # -----------------------------------------------------
    # SIMULATION LOGIC
    # -----------------------------------------------------

    def _simulate_fill(self, order: Order) -> Fill:
        base_price = self._get_mock_price(order.symbol)

        # simple slippage model
        slippage = base_price * (self.slippage_bps / 10000)

        if order.side == "BUY":
            fill_price = base_price + slippage
        else:
            fill_price = base_price - slippage

        # optional randomness (tiny market noise)
        fill_price += random.uniform(-0.02, 0.02)

        return Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=round(fill_price, 4),
            timestamp=time.time()
        )

    def _get_mock_price(self, symbol: str) -> float:
        """
        Placeholder deterministic price.
        Later this will connect to replay_engine.
        """
        return 100.0

    # -----------------------------------------------------
    # Fill processing
    # -----------------------------------------------------

    def _process_fill(self, fill: Fill):
        self.fills[fill.order_id] = fill

        if self.portfolio:
            self.portfolio.apply_fill(fill)

        if fill.order_id in self.open_orders:
            del self.open_orders[fill.order_id]