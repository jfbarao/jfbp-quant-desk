# =========================================================
# 🚦 JFBP QUANT DESK v18 — EXECUTION ROUTER
# PURE ORDER-INTENT BUILDER + ACTION/SIDE NORMALIZATION
# =========================================================

from __future__ import annotations

from typing import Dict, Any, Optional
import math


class ExecutionRouter:

    def __init__(
        self,
        risk_engine=None,
        portfolio_value: float = 100000.0,
        risk_per_trade_pct: float = 0.005,
        max_order_value_pct: float = 0.05,
        max_order_qty: int = 10,
        mode: str = "SIM",
    ):
        self.risk_engine = risk_engine  # retained for backward compatibility only
        self.mode = "SIM"
        self.last_error = ""

        self.portfolio_value = float(portfolio_value)
        self.risk_per_trade_pct = float(risk_per_trade_pct)
        self.max_order_value_pct = float(max_order_value_pct)
        self.max_order_qty = int(max_order_qty)

        self.set_mode(mode)

    # =====================================================
    # SET MODE
    # =====================================================

    def set_mode(self, mode: str) -> None:

        mode = str(mode).upper().strip()

        allowed = {"LIVE", "SIM", "BACKTEST", "REPLAY"}

        if mode not in allowed:
            raise ValueError(f"Invalid router mode: {mode}")

        self.mode = mode

    # =====================================================
    # CONFIG UPDATE
    # =====================================================

    def configure(
        self,
        portfolio_value: Optional[float] = None,
        risk_per_trade_pct: Optional[float] = None,
        max_order_value_pct: Optional[float] = None,
        max_order_qty: Optional[int] = None,
    ) -> None:

        if portfolio_value is not None:
            self.portfolio_value = self._safe_float(portfolio_value)

        if risk_per_trade_pct is not None:
            self.risk_per_trade_pct = self._safe_float(risk_per_trade_pct)

        if max_order_value_pct is not None:
            self.max_order_value_pct = self._safe_float(max_order_value_pct)

        if max_order_qty is not None:
            self.max_order_qty = int(max_order_qty)

    # =====================================================
    # MAIN ROUTER ENTRY
    # =====================================================

    def route(self, signal: Any) -> Dict[str, Any]:

        self.last_error = ""

        try:
            order = self._build_order_intent(signal)

            if order.get("status") != "ORDER_INTENT":
                self.last_error = order.get("reason", "")
                return order

            order["mode"] = self.mode
            order["risk_approved"] = None

            return order

        except Exception as e:
            self.last_error = str(e)

            return {
                "status": "ERROR",
                "stage": "router",
                "reason": str(e),
                "mode": self.mode,
            }

    # =====================================================
    # BUILD ORDER INTENT
    # =====================================================

    def _build_order_intent(self, signal: Any) -> Dict[str, Any]:

        normalized = self._normalize_signal(signal)

        symbol = normalized["symbol"]
        action = normalized["action"]      # BUY | SELL | NONE
        side = normalized["side"]          # LONG | SHORT | FLAT
        price = normalized["price"]
        atr = normalized["atr"]
        score = normalized["score"]
        source = normalized["source"]

        if not symbol:
            return {
                "status": "NO_TRADE",
                "stage": "router",
                "reason": "missing_symbol",
            }

        if action not in ("BUY", "SELL"):
            return {
                "status": "NO_TRADE",
                "stage": "router",
                "reason": "invalid_or_missing_action",
                "symbol": symbol,
                "action": action,
                "side": side,
                "score": score,
            }

        if side not in ("LONG", "SHORT"):
            side = "LONG" if action == "BUY" else "SHORT"

        if price <= 0:
            return {
                "status": "NO_TRADE",
                "stage": "router",
                "reason": "invalid_price",
                "symbol": symbol,
                "action": action,
                "side": side,
                "score": score,
            }

        qty = self._position_size(
            score=abs(score),
            price=price,
            atr=atr,
        )

        if qty <= 0:
            return {
                "status": "NO_TRADE",
                "stage": "router",
                "reason": "zero_position_size",
                "symbol": symbol,
                "action": action,
                "side": side,
                "score": score,
                "price": price,
                "atr": atr,
            }

        return {
            "symbol": symbol,
            "qty": qty,

            # Execution semantics
            "action": action,              # BUY / SELL
            "execution_action": action,

            # Position semantics
            "side": side,                  # LONG / SHORT
            "position_side": side,

            "score": score,
            "model_score": normalized.get("model_score"),
            "price": price,
            "atr": atr,
            "status": "ORDER_INTENT",
            "source": source,
            "scanner_source": source,
            "sizing_model": "portfolio_atr_risk",
            "risk_approved": None,
            "mode": self.mode,
            "order_id": normalized.get("order_id"),
        }

    # =====================================================
    # NORMALIZE SIGNAL
    # =====================================================

    def _normalize_signal(self, signal: Any) -> Dict[str, Any]:

        if isinstance(signal, dict):

            raw_action = str(
                signal.get("action")
                or signal.get("execution_action")
                or ""
            ).upper().strip()

            raw_side = str(
                signal.get("side")
                or signal.get("position_side")
                or ""
            ).upper().strip()

            action, side = self._normalize_action_side(
                raw_action=raw_action,
                raw_side=raw_side,
            )

            raw_score = (
                signal.get("score")
                if signal.get("score") is not None
                else signal.get("model_score")
            )

            if raw_score is None:
                raw_score = signal.get("composite_score")

            return {
                "symbol": str(
                    signal.get("symbol")
                    or signal.get("ticker")
                    or ""
                ).upper().strip(),
                "action": action,
                "side": side,
                "score": self._safe_float(raw_score),
                "model_score": signal.get("model_score"),
                "price": self._safe_float(
                    signal.get("price")
                    if signal.get("price") is not None
                    else signal.get("last_price")
                    if signal.get("last_price") is not None
                    else signal.get("fill_price")
                ),
                "atr": self._safe_float(
                    signal.get("atr")
                    if signal.get("atr") is not None
                    else signal.get("ATR")
                ),
                "source": str(signal.get("source", "execution_router")),
                "order_id": signal.get("order_id"),
            }

        raw_action = str(
            getattr(signal, "action", None)
            or getattr(signal, "execution_action", None)
            or ""
        ).upper().strip()

        raw_side = str(
            getattr(signal, "side", None)
            or getattr(signal, "position_side", None)
            or ""
        ).upper().strip()

        action, side = self._normalize_action_side(
            raw_action=raw_action,
            raw_side=raw_side,
        )

        raw_score = getattr(signal, "score", None)

        if raw_score is None:
            raw_score = getattr(signal, "model_score", None)

        if raw_score is None:
            raw_score = getattr(signal, "composite_score", 0)

        return {
            "symbol": str(
                getattr(signal, "symbol", None)
                or getattr(signal, "ticker", "")
            ).upper().strip(),
            "action": action,
            "side": side,
            "score": self._safe_float(raw_score),
            "model_score": getattr(signal, "model_score", None),
            "price": self._safe_float(
                getattr(signal, "price", None)
                or getattr(signal, "last_price", None)
                or getattr(signal, "fill_price", None)
            ),
            "atr": self._safe_float(
                getattr(signal, "atr", None)
                or getattr(signal, "ATR", None)
            ),
            "source": str(getattr(signal, "source", "execution_router")),
            "order_id": getattr(signal, "order_id", None),
        }

    # =====================================================
    # ACTION / SIDE NORMALIZATION
    # =====================================================

    def _normalize_action_side(
        self,
        raw_action: str,
        raw_side: str,
    ):

        raw_action = str(raw_action or "").upper().strip()
        raw_side = str(raw_side or "").upper().strip()

        no_trade_values = {
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

        # -------------------------------------------------
        # Direct execution action wins when valid
        # -------------------------------------------------

        if raw_action in ("BUY", "SELL"):

            action = raw_action

            if raw_side in ("LONG", "SHORT"):
                side = raw_side
            else:
                side = "LONG" if action == "BUY" else "SHORT"

            return action, side

        # -------------------------------------------------
        # Backward compatibility:
        # Some older callers may put BUY/SELL in side.
        # -------------------------------------------------

        if raw_side in ("BUY", "SELL"):

            action = raw_side
            side = "LONG" if action == "BUY" else "SHORT"

            return action, side

        # -------------------------------------------------
        # Position-side-only signal is NOT executable.
        # SHORT/LONG alone is descriptive, not an order.
        # -------------------------------------------------

        if raw_action in no_trade_values:
            return "NONE", "FLAT"

        if raw_side in no_trade_values:
            return "NONE", "FLAT"

        # Unknown action/side
        return "NONE", "FLAT"

    # =====================================================
    # POSITION SIZING
    # =====================================================

    def _position_size(
        self,
        score: float,
        price: float,
        atr: Optional[float] = None,
    ) -> int:

        portfolio_value = self._safe_float(self.portfolio_value)
        risk_pct = self._safe_float(self.risk_per_trade_pct)
        max_order_value_pct = self._safe_float(self.max_order_value_pct)
        max_order_qty = int(self.max_order_qty)

        if portfolio_value <= 0 or price <= 0 or max_order_qty <= 0:
            return 0

        risk_dollars = portfolio_value * risk_pct
        max_order_value = portfolio_value * max_order_value_pct

        atr = self._safe_float(atr)

        if atr > 0:
            stop_distance = max(atr, price * 0.01)
        else:
            stop_distance = price * 0.02

        if stop_distance <= 0:
            return 0

        raw_qty_by_risk = math.floor(risk_dollars / stop_distance)
        raw_qty_by_value = math.floor(max_order_value / price)
        conviction_cap = self._conviction_cap(score)

        qty = min(
            raw_qty_by_risk,
            raw_qty_by_value,
            conviction_cap,
            max_order_qty,
        )

        return max(int(qty), 0)

    # =====================================================
    # CONVICTION CAP
    # =====================================================

    def _conviction_cap(self, score: float) -> int:

        score = self._safe_float(score)

        if score >= 5:
            return 10
        if score >= 4:
            return 5
        if score >= 3:
            return 3
        if score >= 2:
            return 2

        return 1

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(self) -> Dict[str, Any]:

        return {
            "mode": self.mode,
            "portfolio_value": self.portfolio_value,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "max_order_value_pct": self.max_order_value_pct,
            "max_order_qty": self.max_order_qty,
            "risk_engine_attached": self.risk_engine is not None,
            "last_error": self.last_error,
        }

    # =====================================================
    # SAFE FLOAT
    # =====================================================

    def _safe_float(self, value: Any) -> float:

        try:
            value = float(value)

            if math.isfinite(value):
                return value

            return 0.0

        except Exception:
            return 0.0