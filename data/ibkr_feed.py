# =========================================================
# 📡 JFBP QUANT DESK — IBKR MARKET DATA ADAPTER
# =========================================================

from __future__ import annotations

from typing import Dict, Optional

try:
    from ib_insync import IB, Stock
except Exception:
    IB = None
    Stock = None


# =========================================================
# 📡 IBKR MARKET DATA ADAPTER
# =========================================================

class IBKRMarketDataAdapter:
    """
    LIVE market data connector for Interactive Brokers.

    Responsibilities:
    - connect to IBKR
    - subscribe to symbols
    - maintain ticker subscriptions
    - provide controlled access to market streams

    IMPORTANT:
    This adapter MUST NOT expose raw IBKR tickers
    as public system state.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
    ):

        self.host = host
        self.port = port
        self.client_id = client_id

        self.ib: Optional[IB] = None

        # active subscriptions
        self.subs: Dict[str, object] = {}

        self.connected = False

    # =====================================================
    # CONNECT
    # =====================================================

    def connect(self) -> bool:

        if IB is None:
            raise ImportError(
                "ib_insync is not installed"
            )

        self.ib = IB()

        self.ib.connect(
            self.host,
            self.port,
            clientId=self.client_id
        )

        self.connected = self.ib.isConnected()

        return self.connected

    # =====================================================
    # DISCONNECT
    # =====================================================

    def disconnect(self):

        if self.ib is not None:
            self.ib.disconnect()

        self.connected = False

    # =====================================================
    # SUBSCRIBE SYMBOL
    # =====================================================

    def subscribe_symbol(
        self,
        symbol: str,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> str:

        if self.ib is None:
            raise RuntimeError(
                "IBKR connection not initialized"
            )

        contract = Stock(
            symbol,
            exchange,
            currency
        )

        ticker = self.ib.reqMktData(
            contract,
            snapshot=False
        )

        self.subs[symbol] = ticker

        # IMPORTANT:
        # Do NOT expose raw IBKR ticker externally.
        # CoreEngine should consume normalized state only.
        return symbol

    # =====================================================
    # GET TICKER
    # =====================================================

    def get_ticker(self, symbol: str):

        return self.subs.get(symbol)

    # =====================================================
    # UNSUBSCRIBE
    # =====================================================

    def unsubscribe_symbol(self, symbol: str):

        if self.ib is None:
            return

        ticker = self.subs.get(symbol)

        if ticker is None:
            return

        try:
            self.ib.cancelMktData(ticker.contract)
        except Exception:
            pass

        self.subs.pop(symbol, None)

    # =====================================================
    # GET ACTIVE SUBSCRIPTIONS
    # =====================================================

    def active_symbols(self):

        return list(self.subs.keys())

    # =====================================================
    # IS CONNECTED
    # =====================================================

    def is_connected(self) -> bool:

        return self.connected