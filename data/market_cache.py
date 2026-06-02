import time
from typing import Dict, Optional

import pandas as pd

from data.market_data import get_price_history
from core.features import add_signal_features


# =========================================================
# ⚡ MARKET STATE CACHE
# =========================================================

class MarketCache:

    def __init__(self, bars: int = 252, ttl: int = 10):

        self.bars = bars
        self.ttl = ttl  # seconds

        self._data: Dict[str, pd.DataFrame] = {}
        self._ts: Dict[str, float] = {}


    # =====================================================
    # 📊 GET LIVE MARKET STATE
    # =====================================================

    def get(self, symbol: str) -> Optional[pd.DataFrame]:

        now = time.time()

        # -------------------------
        # CACHE HIT
        # -------------------------

        if symbol in self._data:
            if now - self._ts[symbol] < self.ttl:
                return self._data[symbol]

        # -------------------------
        # CACHE MISS → REFRESH
        # -------------------------

        df = get_price_history(symbol=symbol, bars=self.bars)

        if df is None or df.empty:
            return None

        required_cols = ["Open", "High", "Low", "Close", "Volume"]

        for col in required_cols:
            if col not in df.columns:
                return None

        df = df.dropna().copy()

        # -------------------------
        # ADD SIGNAL FEATURES ONCE
        # -------------------------

        df = add_signal_features(df)

        # -------------------------
        # STORE CACHE
        # -------------------------

        self._data[symbol] = df
        self._ts[symbol] = now

        return df


    # =====================================================
    # 🧹 OPTIONAL: FORCE REFRESH
    # =====================================================

    def refresh(self, symbol: str):
        if symbol in self._data:
            del self._data[symbol]
            del self._ts[symbol]