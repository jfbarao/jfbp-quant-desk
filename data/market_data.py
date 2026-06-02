# =========================================================
# 📡 MARKET DATA FEED v2 — STREAMING + SNAPSHOT HYBRID
# =========================================================

from __future__ import annotations

from typing import Dict, Optional, Callable, Any
import time
import threading
import random


# =========================================================
# 📡 MARKET DATA FEED
# =========================================================

class MarketDataFeed:

    def __init__(self):

        # =====================================================
        # CORE PRICE STORE
        # =====================================================
        self.prices: Dict[str, float] = {}
        self.timestamps: Dict[str, float] = {}

        # =====================================================
        # SUBSCRIBERS (STREAMING ENGINE)
        # =====================================================
        self.subscribers: Dict[str, Callable[[str, float], None]] = {}

        # =====================================================
        # STREAM CONTROL
        # =====================================================
        self.streaming = False
        self._thread = None

        # =====================================================
        # INITIAL DATA
        # =====================================================
        self._load_demo_data()

    # =========================================================
    # 📊 CORE PRICE API
    # =========================================================
    def get_price(self, symbol: str) -> Optional[float]:

        symbol = symbol.upper()
        return self.prices.get(symbol)

    # =========================================================
    # 📊 SNAPSHOT API (USED BY SCANNER)
    # =========================================================
    def snapshot(self) -> Dict[str, Dict[str, Any]]:

        return {
            s: {
                "price": self.prices[s],
                "time": self.timestamps.get(s)
            }
            for s in self.prices
        }

    # =========================================================
    # 📥 PRICE UPDATE (DIRECT INJECTION)
    # =========================================================
    def update_price(self, symbol: str, price: float):

        symbol = symbol.upper()

        self.prices[symbol] = float(price)
        self.timestamps[symbol] = time.time()

        # push to subscribers (streaming layer)
        self._emit(symbol, price)

    # =========================================================
    # 🔌 SUBSCRIPTION SYSTEM
    # =========================================================
    def subscribe(self, symbol: str, callback: Callable[[str, float], None]):

        self.subscribers[symbol.upper()] = callback

    def unsubscribe(self, symbol: str):

        self.subscribers.pop(symbol.upper(), None)

    def _emit(self, symbol: str, price: float):

        cb = self.subscribers.get(symbol.upper())
        if cb:
            try:
                cb(symbol, price)
            except Exception:
                pass

    # =========================================================
    # 📡 LIVE STREAM ENGINE (SIMULATED TICKS)
    # =========================================================
    def start_stream(self, interval: float = 1.0):

        if self.streaming:
            return

        self.streaming = True

        def run():

            while self.streaming:

                for symbol in list(self.prices.keys()):

                    current = self.prices[symbol]

                    # simulate micro-movements
                    drift = random.uniform(-0.25, 0.25)
                    new_price = max(0.01, current + drift)

                    self.update_price(symbol, new_price)

                time.sleep(interval)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop_stream(self):

        self.streaming = False

    # =========================================================
    # 🔄 BULK UPDATE (IBKR OR BACKFILL)
    # =========================================================
    def update_prices(self, data: Dict[str, float]):

        for symbol, price in data.items():
            self.update_price(symbol, price)

    # =========================================================
    # 📦 DEMO DATA
    # =========================================================
    def _load_demo_data(self):

        demo = {
            "AAPL": 192.44,
            "MSFT": 421.11,
            "NVDA": 118.72,
            "TSLA": 177.88,
            "AMZN": 183.55,
            "META": 512.20,
            "GOOGL": 176.30,
            "AMD": 164.90,
        }

        for s, p in demo.items():
            self.update_price(s, p)