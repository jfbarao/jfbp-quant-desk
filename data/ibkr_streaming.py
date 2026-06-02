# =========================================================
# 📡 IBKR STREAMING LAYER — HUB EVENT ENGINE (v2 FIXED CLEAN)
# =========================================================

from __future__ import annotations

import time
import threading
from typing import Dict, Optional, Callable, List


class IBKRStreamingEngine:

    def __init__(
        self,
        gateway,
        market_data,
        mode: str = "SIM"
    ):

        self.gateway = gateway
        self.market_data = market_data
        self.mode = mode

        self.running = False
        self.thread: Optional[threading.Thread] = None

        # =====================================================
        # OPTIONAL SUBSCRIBERS (UI / STRATEGY / DEBUG)
        # =====================================================
        self.subscribers: List[Callable[[str, float], None]] = []

        # optional external IBKR feed hook
        self.external_tick_source: Optional[Callable[[], Dict[str, float]]] = None

    # =========================================================
    # SUBSCRIBE
    # =========================================================
    def subscribe(self, callback: Callable[[str, float], None]):

        if callable(callback):
            self.subscribers.append(callback)

    # =========================================================
    # START STREAM
    # =========================================================
    def start(self):

        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )
        self.thread.start()

    # =========================================================
    # STOP STREAM
    # =========================================================
    def stop(self):

        self.running = False

    # =========================================================
    # MAIN LOOP (CLEAN HUB PIPELINE)
    # =========================================================
    def _run_loop(self):

        hub = self.market_data  # 🔥 SINGLE SOURCE OF TRUTH

        while self.running:

            try:

                ticks = self._get_ticks()

                if not ticks:
                    time.sleep(1)
                    continue

                # =================================================
                # 1. PUSH TO HUB ONLY (NO DUPLICATE SOURCES)
                # =================================================
                hub.update_batch(ticks)

                # =================================================
                # 2. OPTIONAL SUBSCRIBER BROADCAST (READ-ONLY)
                # =================================================
                for symbol, price in ticks.items():

                    for fn in list(self.subscribers):
                        try:
                            fn(symbol, price)
                        except Exception as e:
                            print(f"[SUBSCRIBER ERROR] {e}")

                    # optional legacy gateway sync
                    if hasattr(self.gateway, "update_quote"):
                        self.gateway.update_quote(symbol, price)

                time.sleep(1)

            except Exception as e:
                print(f"[STREAM ERROR] {e}")
                time.sleep(2)

    # =========================================================
    # TICK SOURCE
    # =========================================================
    def _get_ticks(self) -> Dict[str, float]:

        # -----------------------------------------------------
        # SIM MODE
        # -----------------------------------------------------
        if self.mode == "SIM":

            import random

            return {
                "AAPL": 190 + random.random(),
                "MSFT": 420 + random.random(),
                "NVDA": 118 + random.random(),
                "TSLA": 177 + random.random(),
                "AMZN": 183 + random.random(),
                "META": 512 + random.random(),
            }

        # -----------------------------------------------------
        # LIVE MODE (IBKR hook)
        # -----------------------------------------------------
        if self.external_tick_source:
            return self.external_tick_source()

        return {}