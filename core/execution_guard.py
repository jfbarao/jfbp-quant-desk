# =========================================================
# 🚦 JFBP QUANT DESK v15 — EXECUTION ROUTER (CLEAN)
# =========================================================

from __future__ import annotations

from typing import Dict, Any


class ExecutionRouter:

    def __init__(self, risk_engine=None):
        """
        PURE DECISION ENGINE:
        - NO OMS
        - NO execution logic
        - ONLY converts signals → order intent
        """
        self.risk_engine = risk_engine
        self.mode = "SIM"
        self.last_error = ""

    # =====================================================
    # SET MODE
    # =====================================================

    def set_mode(self, mode: str):

        allowed = ["LIVE", "SIM", "BACKTEST"]

        if mode not in allowed:
            raise ValueError(f"Invalid router mode: {mode}")

        self.mode = mode

    # =====================================================
    # 🧠 SIGNAL ENTRY POINT (DECISION ONLY)
    # =====================================================

    def route(self, signal) -> Dict[str, Any]:
        """
        PIPELINE EXPECTS THIS METHOD NAME: route()
        """

        symbol = signal.ticker
        score = signal.composite_score

        if score > 2.5:
            side = "BUY"
            qty = self._position_size(score)

        elif score < 1.0:
            side = "SELL"
            qty = self._position_size(abs(score))

        else:
            return {
                "status": "NO_TRADE",
                "reason": "low_edge"
            }

        return {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "score": score,
            "price": getattr(signal, "last_price", None),
            "status": "ORDER_INTENT"
        }

    # =====================================================
    # 📦 POSITION SIZING
    # =====================================================

    def _position_size(self, score: float) -> int:

        if score > 3.0:
            return 50
        elif score > 2.0:
            return 25
        elif score > 1.5:
            return 10
        else:
            return 5