# =========================================================
# 🧠 RISK ENGINE — PORTFOLIO CONTROL LAYER
# =========================================================

from __future__ import annotations

from typing import Dict, Any, List


class RiskEngine:

    def __init__(self):

        # -------------------------------------------------
        # GLOBAL LIMITS (START SIMPLE, EXTEND LATER)
        # -------------------------------------------------
        self.max_position_size = 10
        self.max_gross_exposure = 50
        self.max_daily_trades = 100

        # -------------------------------------------------
        # STATE
        # -------------------------------------------------
        self.trade_count = 0

    # =====================================================
    # MAIN VALIDATION ENTRY
    # =====================================================
    def validate_signal(
        self,
        signal: Dict[str, Any],
        positions: Dict[str, int]
    ) -> Dict[str, Any]:

        symbol = signal.get("symbol")
        side = signal.get("side")
        qty = int(signal.get("qty", 0))

        current_pos = positions.get(symbol, 0)

        # -------------------------------------------------
        # 1. DAILY TRADE LIMIT
        # -------------------------------------------------
        if self.trade_count >= self.max_daily_trades:
            return self._reject("DAILY_LIMIT_REACHED")

        # -------------------------------------------------
        # 2. POSITION SIZE LIMIT
        # -------------------------------------------------
        projected_pos = current_pos + qty if side == "BUY" else current_pos - qty

        if abs(projected_pos) > self.max_position_size:
            return self._reject("POSITION_LIMIT_EXCEEDED")

        # -------------------------------------------------
        # 3. APPROVE
        # -------------------------------------------------
        self.trade_count += 1

        return {
            "approved": True,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "final_qty": qty,
            "reason": "OK"
        }

    # =====================================================
    # REJECT HELPER
    # =====================================================
    def _reject(self, reason: str) -> Dict[str, Any]:

        return {
            "approved": False,
            "reason": reason,
            "final_qty": 0
        }

    # =====================================================
    # RESET (DAILY)
    # =====================================================
    def reset(self):

        self.trade_count = 0