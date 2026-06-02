# =========================================================
# 📡 STREAM MONITOR — REAL-TIME HEALTH + LATENCY
# =========================================================

from __future__ import annotations

import time
from typing import Dict, Any


class StreamMonitor:

    def __init__(self):

        self.last_tick_time: float = 0.0

        self.tick_count: int = 0

        self.symbol_updates: Dict[str, int] = {}

        self.started_at = time.time()

    # =====================================================
    # RECORD TICK
    # =====================================================

    def record_tick(
        self,
        symbol: str
    ):

        self.last_tick_time = time.time()

        self.tick_count += 1

        self.symbol_updates[symbol] = (
            self.symbol_updates.get(symbol, 0) + 1
        )

    # =====================================================
    # HEALTH SNAPSHOT
    # =====================================================

    def snapshot(self) -> Dict[str, Any]:

        now = time.time()

        uptime = now - self.started_at

        silence = now - self.last_tick_time

        ticks_per_sec = 0.0

        if uptime > 0:
            ticks_per_sec = (
                self.tick_count / uptime
            )

        return {
            "uptime_sec": round(uptime, 2),
            "ticks": self.tick_count,
            "ticks_per_sec": round(ticks_per_sec, 2),
            "last_tick_age_sec": round(silence, 2),
            "symbols": len(self.symbol_updates),
            "symbol_updates": self.symbol_updates,
            "healthy": silence < 5,
        }