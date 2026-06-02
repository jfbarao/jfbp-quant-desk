# =========================================================
# 🛡️ EXECUTION SAFETY LAYER — RISK / KILL SWITCH / LIMITS
# =========================================================

from __future__ import annotations

from typing import Dict, Any, Optional


# =========================================================
# 🛡️ SAFETY ENGINE (NOW STATELESS REGARDING POSITIONS)
# =========================================================

class SafetyEngine:

    def __init__(self):

        # =====================================================
        # RISK LIMITS
        # =====================================================

        self.max_order_qty = 100
        self.max_symbol_position = 500
        self.max_daily_trades = 50

        # =====================================================
        # KILL SWITCH
        # =====================================================

        self.kill_switch = False

        # =====================================================
        # TRADE TRACKING ONLY (NOT POSITION STATE)
        # =====================================================

        self.trade_count = 0
        self.last_reject_reason: Optional[str] = None

    # =========================================================
    # KILL SWITCH CONTROL
    # =========================================================

    def enable_kill_switch(self):
        self.kill_switch = True

    def disable_kill_switch(self):
        self.kill_switch = False

    # =========================================================
    # MAIN VALIDATION ENTRY POINT
    # =========================================================

    def validate_signal(
        self,
        signal: Dict[str, Any],
        current_positions: Dict[str, int],
    ) -> bool:

        self.last_reject_reason = None

        symbol = signal.get("symbol")
        side = str(signal.get("side", "")).upper()
        qty = signal.get("qty")

        # -----------------------------------------------------
        # 1. BASIC STRUCTURE CHECK
        # -----------------------------------------------------

        if not symbol or not side or qty is None:
            self.last_reject_reason = "MALFORMED_SIGNAL"
            return False

        if side not in ["BUY", "SELL"]:
            self.last_reject_reason = "INVALID_SIDE"
            return False

        if not isinstance(qty, (int, float)) or qty <= 0:
            self.last_reject_reason = "INVALID_QTY"
            return False

        # -----------------------------------------------------
        # 2. KILL SWITCH
        # -----------------------------------------------------

        if self.kill_switch:
            self.last_reject_reason = "KILL_SWITCH_ACTIVE"
            return False

        # -----------------------------------------------------
        # 3. DAILY TRADE LIMIT
        # -----------------------------------------------------

        if self.trade_count >= self.max_daily_trades:
            self.last_reject_reason = "MAX_DAILY_TRADES_REACHED"
            return False

        # -----------------------------------------------------
        # 4. ORDER SIZE LIMIT
        # -----------------------------------------------------

        if qty > self.max_order_qty:
            self.last_reject_reason = "ORDER_TOO_LARGE"
            return False

        # -----------------------------------------------------
        # 5. POSITION LIMIT CHECK (READ ONLY FROM GATEWAY)
        # -----------------------------------------------------

        current_pos = current_positions.get(symbol, 0)

        projected_pos = (
            current_pos + qty if side == "BUY"
            else current_pos - qty
        )

        if abs(projected_pos) > self.max_symbol_position:
            self.last_reject_reason = "POSITION_LIMIT_EXCEEDED"
            return False

        return True

    # =========================================================
    # POST-TRADE UPDATE (ONLY COUNTING, NO POSITION TRACKING)
    # =========================================================

    def record_trade(self):

        self.trade_count += 1

    # =========================================================
    # RESET (DAILY RESET HOOK)
    # =========================================================

    def reset(self):

        self.trade_count = 0
        self.last_reject_reason = None