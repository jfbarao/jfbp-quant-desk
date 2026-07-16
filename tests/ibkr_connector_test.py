import asyncio
import os
import threading
import time

import pytest


class EventLoopThread:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start(self):
        self.thread.start()
        return self.loop


class IBKRTestConnector:
    def __init__(self, ib_module):
        self.ib_module = ib_module
        self.ib = ib_module.IB()
        self.loop_runner = EventLoopThread()
        self.loop = self.loop_runner.start()

        self.connected = False
        self.account = None
        self.last_error = ""

    def connect(self, host="127.0.0.1", port=7497, client_id=1):
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.ib.connectAsync(host, port, clientId=client_id),
                self.loop,
            )

            result = future.result(timeout=10)
            if not result:
                self.last_error = "Connection returned False"
                return False

            self.connected = True
            accounts = self.ib.managedAccounts()
            self.account = accounts[0] if accounts else None
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def test_market_data(self, symbol="AAPL"):
        if not self.connected:
            return None

        contract = self.ib_module.Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract)
        time.sleep(3)
        return {
            "symbol": symbol,
            "last": ticker.last,
            "bid": ticker.bid,
            "ask": ticker.ask,
        }

    def disconnect(self):
        try:
            self.ib.disconnect()
        finally:
            self.connected = False


@pytest.fixture
def require_ibkr_integration() -> None:
    if os.getenv("RUN_IBKR_INTEGRATION_TESTS", "").strip() != "1":
        pytest.skip("IBKR integration tests disabled. Set RUN_IBKR_INTEGRATION_TESTS=1 to enable.")


@pytest.mark.integration
def test_ibkr_async_connect_disconnect(require_ibkr_integration: None) -> None:
    ib_insync = pytest.importorskip("ib_insync")
    connector = IBKRTestConnector(ib_insync)
    try:
        ok = connector.connect(host="127.0.0.1", port=7497, client_id=7)
        assert ok, connector.last_error
        assert connector.connected
    finally:
        connector.disconnect()


@pytest.mark.integration
def test_ibkr_market_data_snapshot(require_ibkr_integration: None) -> None:
    ib_insync = pytest.importorskip("ib_insync")
    connector = IBKRTestConnector(ib_insync)
    try:
        ok = connector.connect(host="127.0.0.1", port=7497, client_id=7)
        assert ok, connector.last_error
        quote = connector.test_market_data("AAPL")
        assert quote is not None
        assert quote["symbol"] == "AAPL"
    finally:
        connector.disconnect()
