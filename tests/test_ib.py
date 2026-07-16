import os

import pytest


HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 1


@pytest.fixture
def require_ibkr_integration() -> None:
    if os.getenv("RUN_IBKR_INTEGRATION_TESTS", "").strip() != "1":
        pytest.skip(
            "IBKR integration tests disabled. Set RUN_IBKR_INTEGRATION_TESTS=1 to enable."
        )


@pytest.mark.integration
def test_ibkr_connect_disconnect(require_ibkr_integration: None) -> None:
    ib_insync = pytest.importorskip("ib_insync")
    ib = ib_insync.IB()
    try:
        connected = ib.connect(HOST, PORT, clientId=CLIENT_ID)
        assert bool(connected)
        assert ib.isConnected()
    finally:
        ib.disconnect()
