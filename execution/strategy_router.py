# =========================================================
# 🧠 STRATEGY ROUTER — SIGNAL CONTROL LAYER (CLEAN v2)
# =========================================================

from __future__ import annotations

from typing import Dict, Any, List
import time


class StrategyRouter:

    def __init__(self, pipeline):

        self.pipeline = pipeline

        # =====================================================
        # STATE TRACKING
        # =====================================================
        self.last_routed: List[Dict[str, Any]] = []
        self.last_rejected: List[Dict[str, Any]] = []

        # =====================================================
        # THROTTLE CONTROL (PREVENT SIGNAL FLOODING)
        # =====================================================
        self._last_trade_time: Dict[str, float] = {}
        self.min_trade_interval_sec = 2.0

    # =========================================================
    # 🚦 MAIN ENTRY POINT
    # =========================================================
    def route(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

        results: List[Dict[str, Any]] = []

        for signal in signals:

            # -------------------------------------------------
            # PRE-FILTER CHECK
            # -------------------------------------------------
            if not self._pre_filter(signal):
                self.last_rejected.append(signal)
                continue

            # -------------------------------------------------
            # PIPELINE EXECUTION
            # -------------------------------------------------
            try:

                result = self.pipeline.execute_signal(signal)

                results.append(result)
                self.last_routed.append(signal)

            except Exception as e:

                self.last_rejected.append({
                    "signal": signal,
                    "error": str(e),
                    "time": time.time(),
                })

        return results

    # =========================================================
    # 🧠 PRE-FILTER LOGIC (LIGHTWEIGHT STRATEGY CONTROL)
    # =========================================================
    def _pre_filter(self, signal: Dict[str, Any]) -> bool:

        symbol = signal.get("symbol")
        qty = signal.get("qty")

        if not symbol:
            return False

        if not isinstance(qty, (int, float)) or qty <= 0:
            return False

        symbol = symbol.upper()

        # -------------------------------------------------
        # THROTTLE PER SYMBOL
        # -------------------------------------------------
        now = time.time()
        last = self._last_trade_time.get(symbol, 0.0)

        if now - last < self.min_trade_interval_sec:
            return False

        self._last_trade_time[symbol] = now

        return True

    # =========================================================
    # 📊 DEBUG / MONITORING
    # =========================================================
    def get_stats(self) -> Dict[str, Any]:

        return {
            "routed": len(self.last_routed),
            "rejected": len(self.last_rejected),
            "active_throttle_entries": len(self._last_trade_time),
            "min_trade_interval_sec": self.min_trade_interval_sec,
        }