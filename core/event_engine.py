# =========================================================
# JFBP QUANT DESK — ENGINE KERNEL (EVENT LOOP CORE)
# =========================================================

from typing import Dict, Any, Callable, Optional

from data.market_data import MarketDataFeed


class EventEngine:
    """
    Central event-driven trading engine.

    Responsibilities:
    - ingest ticks
    - update market state
    - update portfolio marks
    - update risk
    - trigger external strategy layer
    """

    def __init__(
        self,
        market_data: MarketDataFeed,
        portfolio=None,
        risk_manager=None,
        on_tick: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_after_tick: Optional[Callable[[Dict[str, Any]], None]] = None
    ):

        self.market_data = market_data
        self.portfolio = portfolio
        self.risk_manager = risk_manager

        self.on_tick = on_tick
        self.on_after_tick = on_after_tick

    # =====================================================
    # ⚡ MAIN EVENT ENTRY POINT
    # =====================================================

    def process_tick(self, tick: Dict[str, Any]):
        """
        Safe tick handler (robust for Streamlit + live feeds)
        """

        if not isinstance(tick, dict):
            return

        # PRE HOOK
        if self.on_tick:
            self.on_tick(tick)

        symbol = tick.get("symbol")
        price = tick.get("price")

        if symbol is None or price is None:
            return

        # MARKET UPDATE
        self.market_data.update_price(symbol, price)

        # PORTFOLIO UPDATE
        if self.portfolio:
            self.portfolio.update_price(symbol, price)

        # RISK UPDATE
        if self.risk_manager:
            self._update_risk()

        # POST HOOK
        if self.on_after_tick:
            self.on_after_tick(tick)

    # =====================================================
    # 🧠 RISK ENGINE HOOK
    # =====================================================

    def _update_risk(self):

        if self.risk_manager and hasattr(self.risk_manager, "update_pnl"):

            try:
                self.risk_manager.update_pnl(
                    self.portfolio.get_total_pnl()
                )
            except Exception:
                pass