# =========================================================
# 🧠 SIGNAL ENGINE — FEATURE + ALPHA LAYER
# =========================================================

from __future__ import annotations

from typing import Dict, Any, Optional


class SignalEngine:

    def __init__(self, market_data):

        self.market_data = market_data

    # =====================================================
    # MAIN ENTRY
    # =====================================================
    def generate(self, symbol: str, price: float) -> Optional[Dict[str, Any]]:

        reference = self._get_reference(symbol)

        if reference is None:
            return None

        deviation = (price - reference) / reference

        # -------------------------------------------------
        # SIMPLE ALPHA RULESET (v1)
        # -------------------------------------------------

        if deviation < -0.01:
            return {
                "symbol": symbol,
                "side": "BUY",
                "qty": 1,
                "price": price,
                "deviation": deviation,
                "alpha": "MEAN_REVERSION_LONG"
            }

        if deviation > 0.01:
            return {
                "symbol": symbol,
                "side": "SELL",
                "qty": 1,
                "price": price,
                "deviation": deviation,
                "alpha": "MEAN_REVERSION_SHORT"
            }

        return None

    # =====================================================
    # REFERENCE PRICE
    # =====================================================
    def _get_reference(self, symbol: str) -> Optional[float]:

        if hasattr(self.market_data, "snapshot_dict"):
            snap = self.market_data.snapshot_dict()
            data = snap.get(symbol)

            if data:
                return data["price"]

        return self.market_data.get_price(symbol)