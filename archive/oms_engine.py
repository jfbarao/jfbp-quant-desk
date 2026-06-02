# =========================================================
# JFBP QUANT DESK — OMS ENGINE (LIVE CORE)
# =========================================================

from dataclasses import dataclass
from typing import Optional, Dict, Any
import time
import uuid


# ---------------------------------------------------------
# Order / Fill Models
# ---------------------------------------------------------

@dataclass
class Order:
    symbol: str
    side: str          # BUY / SELL
    quantity: float
    order_type: str = "MARKET"  # MARKET / LIMIT
    limit_price: Optional[float] = None
    timestamp: float = time.time()
    order_id: str = None

    def __post_init__(self):
        if self.order_id is None:
            self.order_id = str(uuid.uuid4())


@dataclass
class Fill:
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: float = time.time()


# ---------------------------------------------------------
# OMS ENGINE (LIVE)
# ---------------------------------------------------------

class OMSEngine:
    """
    LIVE Order Management System Engine.

    Responsibilities:
    - Accept orders from router
    - Validate orders
    - Send to broker adapter (IBKR placeholder)
    - Emit fills / execution reports
    """

    def __init__(self, broker=None, risk_manager=None, portfolio=None):
        self.broker = broker
        self.risk_manager = risk_manager
        self.portfolio = portfolio

        self.open_orders: Dict[str, Order] = {}
        self.fills: Dict[str, Fill] = {}

    # -----------------------------------------------------
    # Entry Point
    # -----------------------------------------------------

    def submit_order(self, order: Order) -> Dict[str, Any]:
        """
        Main entry point from router / strategy layer.
        """

        # 1. Basic validation
        self._validate_order(order)

        # 2. Risk check (if available)
        if self.risk_manager:
            approved = self.risk_manager.check_order(order)
            if not approved:
                return {
                    "status": "REJECTED",
                    "reason": "Risk manager rejected order",
                    "order_id": order.order_id
                }

        # 3. Store order
        self.open_orders[order.order_id] = order

        # 4. Send to broker (or mock)
        fill = self._send_to_broker(order)

        # 5. Process fill
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

        if order.order_type == "LIMIT" and order.limit_price is None:
            raise ValueError("LIMIT orders require limit_price")

    # -----------------------------------------------------
    # Broker Layer (placeholder)
    # -----------------------------------------------------

    def _send_to_broker(self, order: Order) -> Fill:
        """
        In LIVE mode, this will connect to IBKR.
        For now: simulated immediate fill.
        """

        # TODO: replace with IBKR API call
        mock_price = self._get_mock_price(order.symbol)

        return Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=mock_price
        )

    def _get_mock_price(self, symbol: str) -> float:
        """
        Temporary price generator until market feed is wired.
        """
        return 100.0  # placeholder stable price

    # -----------------------------------------------------
    # Fill Processing
    # -----------------------------------------------------

    def _process_fill(self, fill: Fill):
        self.fills[fill.order_id] = fill

        if self.portfolio:
            self.portfolio.apply_fill(fill)

        if fill.order_id in self.open_orders:
            del self.open_orders[fill.order_id]