# =========================================================
# 🧠 PORTFOLIO ALLOCATOR — CAPITAL + RISK SIZING ENGINE
# =========================================================

from __future__ import annotations

from typing import Dict, Any, List


class PortfolioAllocator:

    def __init__(self):

        # -------------------------------------------------
        # GLOBAL SETTINGS (START SIMPLE)
        # -------------------------------------------------
        self.base_capital_per_trade = 1000  # notional sizing anchor
        self.max_position_size = 10
        self.max_gross_exposure = 50

    # =====================================================
    # MAIN ENTRY
    # =====================================================
    def size_signal(
        self,
        signal: Dict[str, Any],
        positions: Dict[str, int]
    ) -> Dict[str, Any]:

        symbol = signal.get("symbol")
        side = signal.get("side")
        qty = int(signal.get("qty", 1))
        price = float(signal.get("price", 0) or 1)

        current_pos = positions.get(symbol, 0)

        # -------------------------------------------------
        # 1. BASIC NOTIONAL SIZING
        # -------------------------------------------------
        notional = self.base_capital_per_trade

        raw_qty = int(notional / price)

        # blend scanner qty + allocator qty
        final_qty = max(1, int((qty + raw_qty) / 2))

        # -------------------------------------------------
        # 2. POSITION LIMIT CONTROL
        # -------------------------------------------------
        projected = current_pos + final_qty if side == "BUY" else current_pos - final_qty

        if abs(projected) > self.max_position_size:
            final_qty = max(0, self.max_position_size - abs(current_pos))

        # -------------------------------------------------
        # 3. ZERO SAFETY
        # -------------------------------------------------
        if final_qty <= 0:
            return {
                "approved": False,
                "reason": "POSITION_LIMIT_SATURATED",
                "final_qty": 0,
            }

        return {
            "approved": True,
            "symbol": symbol,
            "side": side,
            "final_qty": final_qty,
            "current_pos": current_pos,
            "projected_pos": projected,
            "notional": notional,
        }