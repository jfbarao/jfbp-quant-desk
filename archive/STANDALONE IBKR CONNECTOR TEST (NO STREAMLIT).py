# =========================================================
# 🧠 STANDALONE IBKR CONNECTOR TEST (NO STREAMLIT)
# =========================================================

import asyncio
import threading
import time

try:
    from ib_insync import IB, Stock, MarketOrder
except Exception as e:
    raise ImportError(f"ib_insync not installed or broken: {e}")


# =========================================================
# 🧠 EVENT LOOP RUNNER (THREAD SAFE)
# =========================================================

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


# =========================================================
# 🧠 IBKR CONNECTOR (MINIMAL DEBUG VERSION)
# =========================================================

class IBKRTestConnector:
    def __init__(self):
        self.ib = IB()
        self.loop_runner = EventLoopThread()
        self.loop = self.loop_runner.start()

        self.connected = False
        self.account = None
        self.last_error = ""

    # ---------------------------------------------------------
    # CONNECT
    # ---------------------------------------------------------
    def connect(self, host="127.0.0.1", port=7497, client_id=1):
        try:
            print("Connecting to IBKR...")

            future = asyncio.run_coroutine_threadsafe(
                self.ib.connectAsync(host, port, clientId=client_id),
                self.loop
            )

            result = future.result(timeout=10)

            if not result:
                self.last_error = "Connection returned False"
                print(self.last_error)
                return False

            self.connected = True

            accounts = self.ib.managedAccounts()
            self.account = accounts[0] if accounts else None

            print("CONNECTED ✔")
            print("Account:", self.account)

            return True

        except Exception as e:
            self.last_error = str(e)
            print("CONNECT FAILED ❌", self.last_error)
            return False

    # ---------------------------------------------------------
    # SNAPSHOT TEST
    # ---------------------------------------------------------
    def test_market_data(self, symbol="AAPL"):
        if not self.connected:
            print("Not connected")
            return

        try:
            contract = Stock(symbol, "SMART", "USD")
            self.ib.qualifyContracts(contract)

            ticker = self.ib.reqMktData(contract)

            time.sleep(3)  # allow data to populate

            print("\n--- MARKET DATA ---")
            print("Symbol:", symbol)
            print("Last:", ticker.last)
            print("Bid:", ticker.bid)
            print("Ask:", ticker.ask)

        except Exception as e:
            print("MARKET DATA ERROR:", str(e))

    # ---------------------------------------------------------
    # DISCONNECT
    # ---------------------------------------------------------
    def disconnect(self):
        try:
            self.ib.disconnect()
            self.connected = False
            print("DISCONNECTED")
        except Exception as e:
            print("DISCONNECT ERROR:", str(e))


# =========================================================
# 🧪 RUN TEST
# =========================================================

if __name__ == "__main__":
    ibkr = IBKRTestConnector()

    ok = ibkr.connect(
        host="127.0.0.1",
        port=7497,   # paper trading default
        client_id=7
    )

    if ok:
        ibkr.test_market_data("AAPL")

        time.sleep(2)
        ibkr.disconnect()