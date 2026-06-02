# =========================================================
# 🧠 EVENT BUS — SYSTEM NERVOUS SYSTEM (v2 UPGRADED)
# =========================================================

from typing import Callable, Dict, List, Any
import threading


class EventBus:

    def __init__(self):

        # event subscribers
        self._subscribers: Dict[str, List[Callable]] = {}

        # =====================================================
        # 🔥 CRITICAL ADDITION: SHARED STATE STORE
        # =====================================================
        self._latest_prices: Dict[str, float] = {}

        # thread safety for stream updates
        self._lock = threading.Lock()

    # =========================================================
    # SUBSCRIBE
    # =========================================================
    def subscribe(self, event: str, fn: Callable):

        self._subscribers.setdefault(event, []).append(fn)

    # =========================================================
    # EMIT EVENT
    # =========================================================
    def emit(self, event: str, data: Any):

        # -----------------------------------------------------
        # 🔥 SPECIAL CASE: MARKET DATA EVENT
        # -----------------------------------------------------
        if event == "TICK":

            symbol = data.get("symbol")
            price = data.get("price")

            if symbol and price is not None:

                with self._lock:
                    self._latest_prices[symbol] = price

        # -----------------------------------------------------
        # FAN-OUT EVENT DISPATCH
        # -----------------------------------------------------
        for fn in self._subscribers.get(event, []):

            try:
                fn(data)

            except Exception as e:
                print(f"[EventBus] error in {event}: {e}")

    # =========================================================
    # SNAPSHOT (THIS FIXES YOUR "EMPTY SCANNER")
    # =========================================================
    def snapshot(self) -> Dict[str, float]:

        with self._lock:
            return dict(self._latest_prices)

    # =========================================================
    # OPTIONAL: DIRECT PRICE ACCESS
    # =========================================================
    def get_price(self, symbol: str):

        with self._lock:
            return self._latest_prices.get(symbol)