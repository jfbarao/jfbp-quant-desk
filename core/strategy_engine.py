# =========================================================
# 🧠 STRATEGY ENGINE — MULTI-ALPHA ORCHESTRATOR
# =========================================================

from __future__ import annotations

from typing import Dict, Any, List, Protocol


# =========================================================
# 🧩 STRATEGY INTERFACE
# =========================================================

class Strategy(Protocol):

    def generate(self, symbol: str, price: float, context: Dict[str, Any]):
        ...


# =========================================================
# 🧠 STRATEGY ENGINE
# =========================================================

class StrategyEngine:

    def __init__(self, market_data):

        self.market_data = market_data

        # registered strategies
        self.strategies: List[Strategy] = []

        # optional weights per strategy
        self.weights: Dict[str, float] = {}

    # -----------------------------------------------------
    # REGISTER STRATEGY
    # -----------------------------------------------------
    def add_strategy(self, name: str, strategy: Strategy, weight: float = 1.0):

        self.strategies.append(strategy)
        self.weights[name] = weight

    # -----------------------------------------------------
    # MAIN ENTRY
    # -----------------------------------------------------
    def evaluate(self, symbol: str, price: float) -> List[Dict[str, Any]]:

        context = self._build_context(symbol)

        signals = []

        for strat in self.strategies:

            try:
                sig = strat.generate(symbol, price, context)

                if sig:
                    sig["weight"] = self.weights.get(
                        getattr(strat, "__class__", type(strat)).__name__,
                        1.0
                    )
                    signals.append(sig)

            except Exception as e:
                print(f"[StrategyEngine] error: {e}")

        return signals

    # -----------------------------------------------------
    # CONTEXT BUILDER
    # -----------------------------------------------------
    def _build_context(self, symbol: str) -> Dict[str, Any]:

        snap = self.market_data.snapshot_dict()

        return {
            "snapshot": snap,
            "price": snap.get(symbol, {}).get("price"),
        }