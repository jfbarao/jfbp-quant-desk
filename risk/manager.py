# =========================================================
# JFBP QUANT DESK — RISK MANAGER (PRE-TRADE GATE)
# =========================================================

from dataclasses import dataclass
from typing import Dict, Optional
from execution.oms_engine import Order


@dataclass
class RiskLimits:
    max_position_size: float = 1000.0
    max_gross_exposure: float = 100000.0
    max_single_order_size: float = 500.0
    max_daily_loss: Optional[float] = None  # optional hard stop


class RiskManager:
    """
    Pre-trade risk validation layer.

    Called BEFORE OMS execution (LIVE or SIM).
    """

    def __init__(self, portfolio, limits: RiskLimits = RiskLimits()):
        self.portfolio = portfolio
        self.limits = limits
        self.daily_pnl = 0.0

    # -----------------------------------------------------
    # MAIN ENTRY
    # -----------------------------------------------------

    def check_order(self, order: Order) -> bool:
        """
        Returns True if order is approved, False if rejected.
        """

        # 1. Basic size checks
        if not self._check_order_size(order):
            return False

        # 2. Position exposure check
        if not self._check_position_limit(order):
            return False

        # 3. Gross exposure check
        if not self._check_gross_exposure(order):
            return False

        # 4. Daily loss check (if enabled)
        if self.limits.max_daily_loss is not None:
            if self.daily_pnl <= -abs(self.limits.max_daily_loss):
                return False

        return True

    # -----------------------------------------------------
    # RULES
    # -----------------------------------------------------

    def _check_order_size(self, order: Order) -> bool:
        return order.quantity <= self.limits.max_single_order_size

    def _check_position_limit(self, order: Order) -> bool:
        """
        Ensures per-symbol exposure is not exceeded.
        """

        current_pos = self.portfolio.get_position(order.symbol)

        projected = current_pos + (
            order.quantity if order.side == "BUY" else -order.quantity
        )

        return abs(projected) <= self.limits.max_position_size

    def _check_gross_exposure(self, order: Order) -> bool:
        """
        Simple gross exposure approximation.
        """

        positions = self.portfolio.get_all_positions()

        gross = sum(abs(pos) for pos in positions.values())

        gross += order.quantity

        return gross <= self.limits.max_gross_exposure

    # -----------------------------------------------------
    # RISK FEEDBACK LOOP
    # -----------------------------------------------------

    def update_pnl(self, pnl: float):
        """
        Called by portfolio engine after mark-to-market.
        """
        self.daily_pnl += pnl