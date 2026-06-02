import json

STATE_FILE = "bridge_state.json"
ORDER_FILE = "orders_queue.json"


def get_positions():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f).get("positions", [])
    except:
        return []


def send_order(symbol, qty, action="BUY"):
    try:
        with open(ORDER_FILE, "r") as f:
            orders = json.load(f)
    except:
        orders = []

    orders.append({
        "symbol": symbol,
        "qty": qty,
        "action": action,
        "status": "NEW"
    })

    with open(ORDER_FILE, "w") as f:
        json.dump(orders, f, indent=2)