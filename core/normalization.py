# =========================================================
# 🧭 JFBP CORE NORMALIZATION v18
# SINGLE SEMANTIC CONTRACT LAYER
# =========================================================

from __future__ import annotations

from typing import Any, Dict


NO_TRADE_VALUES = {
    "",
    "NONE",
    "NULL",
    "N/A",
    "NA",
    "HOLD",
    "NO TRADE",
    "NO_TRADE",
    "FLAT",
}


def clean_text(value: Any) -> str:
    return str(value or "").upper().strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def normalize_action_side(action: Any = None, side: Any = None) -> Dict[str, str]:
    action = clean_text(action)
    side = clean_text(side)

    if action in ("BUY", "SELL"):
        return {
            "action": action,
            "side": side if side in ("LONG", "SHORT") else ("LONG" if action == "BUY" else "SHORT"),
        }

    if side in ("BUY", "SELL"):
        return {
            "action": side,
            "side": "LONG" if side == "BUY" else "SHORT",
        }

    if action in NO_TRADE_VALUES or side in NO_TRADE_VALUES:
        return {
            "action": "NONE",
            "side": "FLAT",
        }

    if side == "LONG":
        return {
            "action": "BUY",
            "side": "LONG",
        }

    if side == "SHORT":
        return {
            "action": "SELL",
            "side": "SHORT",
        }

    return {
        "action": "NONE",
        "side": "FLAT",
    }


def normalize_signal_for_engine(signal: Dict[str, Any]) -> Dict[str, Any]:
    signal = dict(signal or {})

    normalized = normalize_action_side(
        action=signal.get("action") or signal.get("execution_action"),
        side=signal.get("side") or signal.get("position_side"),
    )

    signal["action"] = normalized["action"]
    signal["side"] = normalized["side"]

    return signal


def normalize_signal_for_ui(signal: Dict[str, Any]) -> Dict[str, Any]:
    signal = normalize_signal_for_engine(signal)

    if signal.get("signal") == "NO TRADE":
        signal["action"] = "HOLD"
        signal["side"] = "FLAT"

    return signal


def normalize_order_intent(order: Dict[str, Any]) -> Dict[str, Any]:
    order = dict(order or {})

    normalized = normalize_action_side(
        action=order.get("action") or order.get("execution_action"),
        side=order.get("side") or order.get("position_side"),
    )

    order["action"] = normalized["action"]
    order["execution_action"] = normalized["action"]
    order["side"] = normalized["side"]
    order["position_side"] = normalized["side"]

    if not order.get("status"):
        order["status"] = "ORDER_INTENT"

    return order


def normalize_fill(fill: Dict[str, Any]) -> Dict[str, Any]:
    fill = dict(fill or {})

    normalized = normalize_action_side(
        action=fill.get("action") or fill.get("execution_action"),
        side=fill.get("side") or fill.get("position_side"),
    )

    fill["action"] = normalized["action"]
    fill["side"] = normalized["action"]
    fill["position_side"] = normalized["side"]

    fill["qty"] = safe_int(
        fill.get("qty")
        or fill.get("quantity")
        or fill.get("shares")
        or 1,
        default=1,
    )

    fill["price"] = safe_float(
        fill.get("price")
        or fill.get("fill_price")
        or fill.get("last_price")
        or 0.0,
        default=0.0,
    )

    if "fill_price" not in fill:
        fill["fill_price"] = fill["price"]

    return fill