import time
import json
import threading
from datetime import datetime
import pandas as pd

from ib_insync import IB, Stock, MarketOrder

STATE_FILE = "bridge_state.json"
ORDER_FILE = "orders_queue.json"

class IBKRBridge:
    def __init__(self, host="127.0.0.1", port=7497, client_id=2):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id

        self.connected = False
        self.account = None

        self.positions = []
        self.orders = []
        self.pnl = {}

    # -------------------------
    # CONNECT
    # -------------------------
    def connect(self):
        print("Connecting to IBKR...")
        self.ib.connect(self.host, self.port, clientId=self.client_id)

        self.connected = self.ib.isConnected()

        if not self.connected:
            raise Exception("IBKR connection failed")

        accounts = self.ib.managedAccounts()
        self.account = accounts[0] if accounts else None

        print("CONNECTED ✔")
        print("Account:", self.account)

        if self.account:
            self.ib.reqPositions()
            self.ib.reqPnL(self.account)

        # background threads
        threading.Thread(target=self._snapshot_loop, daemon=True).start()
        threading.Thread(target=self._order_loop, daemon=True).start()

    # -------------------------
    # SNAPSHOT LOOP
    # -------------------------
    def _snapshot_loop(self):
        while True:
            try:
                self._refresh_state()
            except Exception as e:
                print("Snapshot error:", e)

            time.sleep(2)

    def _refresh_state(self):
        positions = self.ib.positions()

        pos_data = [{
            "symbol": p.contract.symbol,
            "position": p.position,
            "avgCost": p.avgCost
        } for p in positions]

        state = {
            "timestamp": datetime.utcnow().isoformat(),
            "positions": pos_data,
            "connected": self.connected
        }

        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    # -------------------------
    # ORDER LOOP
    # -------------------------
    def _order_loop(self):
        while True:
            try:
                self._process_orders()
            except Exception as e:
                print("Order loop error:", e)

            time.sleep(1)

    def _process_orders(self):
        try:
            with open(ORDER_FILE, "r") as f:
                orders = json.load(f)
        except:
            return

        if not orders:
            return

        new_queue = []

        for o in orders:
            if o.get("status") == "NEW":
                try:
                    contract = Stock(o["symbol"], "SMART", "USD")
                    order = MarketOrder(o["action"], int(o["qty"]))
                    trade = self.ib.placeOrder(contract, order)

                    o["status"] = "SENT"
                    o["time"] = datetime.utcnow().isoformat()

                except Exception as e:
                    o["status"] = "FAILED"
                    o["error"] = str(e)

            new_queue.append(o)

        with open(ORDER_FILE, "w") as f:
            json.dump(new_queue, f, indent=2)


# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    bridge = IBKRBridge()
    bridge.connect()

    print("IBKR Bridge running...")

    while True:
        time.sleep(10)