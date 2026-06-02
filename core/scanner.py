# =========================================================
# 📡 JFBP SCANNER ENGINE
# =========================================================

from __future__ import annotations

from typing import Dict
from typing import Any
from typing import List
from typing import Optional

import pandas as pd


class Scanner:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, universe, market_data):

        self.universe = universe or []

        self.market_data = market_data

        self.last_signals: List[Dict[str, Any]] = []

        self._prev_prices: Dict[str, float] = {}

    # =====================================================
    # MAIN RUN
    # =====================================================

    def run(self) -> pd.DataFrame:

        signals: List[Dict[str, Any]] = []

        snapshot = self._safe_snapshot()

        if not snapshot:
            self.last_signals = []
            return pd.DataFrame([])

        for symbol in self.universe:

            try:

                symbol = str(symbol).upper()

                data = snapshot.get(symbol)

                if not data:
                    continue

                price = data.get("price")

                if price is None:
                    continue

                price = float(price)

                signal = self._generate_signal(
                    symbol=symbol,
                    price=price
                )

                if signal is not None:
                    signals.append(signal)

                # -----------------------------------------
                # UPDATE MEMORY
                # -----------------------------------------

                self._prev_prices[symbol] = price

            except Exception:
                continue

        self.last_signals = signals

        return pd.DataFrame(signals)

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def _safe_snapshot(self) -> Dict[str, Any]:

        try:

            if (
                self.market_data is not None
                and hasattr(self.market_data, "snapshot")
            ):

                snapshot = self.market_data.snapshot()

                if isinstance(snapshot, dict):
                    return snapshot

        except Exception:
            pass

        return {}

    # =====================================================
    # SIGNAL ENGINE
    # =====================================================

    def _generate_signal(
        self,
        symbol: str,
        price: float,
    ) -> Optional[Dict[str, Any]]:

        prev_price = self._prev_prices.get(symbol)

        # -------------------------------------------------
        # NEED HISTORY
        # -------------------------------------------------

        if prev_price is None:
            return None

        if prev_price <= 0:
            return None

        # -------------------------------------------------
        # DEVIATION
        # -------------------------------------------------

        deviation = (price - prev_price) / prev_price

        # -------------------------------------------------
        # BUY
        # -------------------------------------------------

        if deviation < -0.01:

            return {
                "symbol": symbol,
                "action": "BUY",
                "qty": 1,
                "price": round(price, 2),
                "prev_price": round(prev_price, 2),
                "deviation": round(deviation, 5),
                "signal_type": "MEAN_REVERSION_LONG",
            }

        # -------------------------------------------------
        # SELL
        # -------------------------------------------------

        if deviation > 0.01:

            return {
                "symbol": symbol,
                "action": "SELL",
                "qty": 1,
                "price": round(price, 2),
                "prev_price": round(prev_price, 2),
                "deviation": round(deviation, 5),
                "signal_type": "MEAN_REVERSION_SHORT",
            }

        return None

    # =====================================================
    # OUTPUT
    # =====================================================

    def get_trade_signals(self):

        return self.last_signals