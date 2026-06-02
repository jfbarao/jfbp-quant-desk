# =========================================================
# 📡 MARKET DATA HUB v2.1
# JFBP UNIVERSE AUTO-BOOTSTRAP + LIVE GATEWAY PRIORITY
# =========================================================

from __future__ import annotations

from typing import Dict, Optional, Any


# =========================================================
# SAFE UNIVERSE IMPORT
# =========================================================

try:
    from universe.jfbp_universe import JFBP_UNIVERSE
except Exception:
    JFBP_UNIVERSE = {
        "AAPL": {},
        "MSFT": {},
        "NVDA": {},
        "TSLA": {},
        "AMZN": {},
        "META": {},
    }


# =========================================================
# MARKET DATA HUB
# =========================================================

class MarketDataHub:

    def __init__(self):

        self.prices: Dict[str, float] = {}
        self.data: Dict[str, Dict[str, Any]] = {}

        self.gateway = None
        self.mode = "SIM"

        self._bootstrap_universe_data()

    # =====================================================
    # JFBP UNIVERSE BOOTSTRAP
    # =====================================================

    def _bootstrap_universe_data(self) -> None:

        seed_prices = {
            "AAPL": 190.0,
            "MSFT": 420.0,
            "NVDA": 118.0,
            "TSLA": 178.0,
            "AMZN": 184.0,
            "META": 512.0,
            "WMT": 131.0,
            "JPM": 205.0,
            "XOM": 118.0,
            "PG": 165.0,
            "KO": 63.0,
            "LLY": 785.0,
            "JNJ": 152.0,
            "UNH": 490.0,
            "CAT": 345.0,
            "BA": 182.0,
            "AMD": 164.0,
            "AVGO": 1420.0,
            "QCOM": 178.0,
            "COST": 812.0,
        }

        symbols = self._extract_symbols(JFBP_UNIVERSE)

        for symbol in symbols:

            symbol = str(symbol).upper().strip()
            price = float(seed_prices.get(symbol, 100.0))

            self.prices[symbol] = price

            self.data[symbol] = {
                "symbol": symbol,
                "price": price,
                "mode": self.mode,
                "source": "seed",
            }

    # =====================================================
    # SAFE HELPERS
    # =====================================================

    def _extract_symbols(self, universe) -> list[str]:

        if isinstance(universe, dict):
            return list(universe.keys())

        if isinstance(universe, list):
            return [str(x).upper() for x in universe]

        if isinstance(universe, tuple):
            return [str(x).upper() for x in universe]

        return ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META"]

    def _safe_float(
        self,
        value: Any,
        default: float = 0.0,
    ) -> float:

        try:
            if value is None:
                return default

            value = float(value)

            if value != value:
                return default

            if value <= 0:
                return default

            return value

        except Exception:
            return default

    # =====================================================
    # MODE
    # =====================================================

    def set_mode(self, mode: str) -> None:

        mode = str(mode or "SIM").upper().strip()

        if mode not in ("SIM", "LIVE", "REPLAY", "BACKTEST"):
            mode = "SIM"

        self.mode = mode

        for symbol in self.data:
            self.data[symbol]["mode"] = self.mode

    # =====================================================
    # GATEWAY
    # =====================================================

    def attach_gateway(self, gateway) -> None:
        self.gateway = gateway

    # =====================================================
    # LIVE PRICE RESOLUTION
    # =====================================================

    def _gateway_price(self, symbol: str) -> Optional[float]:

        symbol = str(symbol).upper().strip()

        if self.gateway is None:
            return None

        # -------------------------------------------------
        # Refresh subscribed gateway prices first
        # -------------------------------------------------

        try:
            if hasattr(self.gateway, "refresh_market_data"):
                self.gateway.refresh_market_data()
        except Exception:
            pass

        # -------------------------------------------------
        # Gateway method lookup
        # -------------------------------------------------

        for method_name in (
            "get_price",
            "get_quote",
            "latest_price",
            "get_last_price",
            "last_price",
            "market_price",
        ):

            if not hasattr(self.gateway, method_name):
                continue

            try:
                method = getattr(self.gateway, method_name)

                if not callable(method):
                    continue

                value = self._safe_float(method(symbol))

                if value > 0:
                    return value

            except Exception:
                continue

        # -------------------------------------------------
        # Gateway last_quotes dict
        # -------------------------------------------------

        try:
            quotes = getattr(self.gateway, "last_quotes", {})
            quote = quotes.get(symbol)

            if isinstance(quote, dict):

                for key in (
                    "price",
                    "last",
                    "mark",
                    "close",
                    "bid",
                    "ask",
                ):
                    value = self._safe_float(quote.get(key))

                    if value > 0:
                        return value

        except Exception:
            pass

        # -------------------------------------------------
        # Gateway last_quotes_df
        # -------------------------------------------------

        try:
            df = getattr(self.gateway, "last_quotes_df", None)

            if df is not None and not df.empty and "symbol" in df.columns:

                rows = df[
                    df["symbol"]
                    .astype(str)
                    .str.upper()
                    == symbol
                ]

                if not rows.empty:

                    for key in (
                        "price",
                        "last",
                        "mark",
                        "close",
                        "bid",
                        "ask",
                    ):
                        if key in rows.columns:

                            value = self._safe_float(
                                rows.iloc[-1][key]
                            )

                            if value > 0:
                                return value

        except Exception:
            pass

        return None

    # =====================================================
    # UPDATE SINGLE PRICE
    # =====================================================

    def update_price(
        self,
        symbol: str,
        price: float,
        source: str = "manual",
    ) -> None:

        symbol = str(symbol).upper().strip()
        price = self._safe_float(price)

        if not symbol or price <= 0:
            return

        self.prices[symbol] = price

        if symbol not in self.data:
            self.data[symbol] = {"symbol": symbol}

        self.data[symbol]["price"] = price
        self.data[symbol]["mode"] = self.mode
        self.data[symbol]["source"] = source

    # =====================================================
    # UPDATE BATCH
    # =====================================================

    def update_batch(
        self,
        updates: dict,
        source: str = "batch",
    ) -> None:

        if not isinstance(updates, dict):
            return

        for symbol, payload in updates.items():

            symbol = str(symbol).upper().strip()

            try:
                if symbol not in self.data:
                    self.data[symbol] = {"symbol": symbol}

                if isinstance(payload, dict):

                    self.data[symbol].update(payload)

                    price = self._safe_float(
                        payload.get("price")
                    )

                    if price > 0:
                        self.prices[symbol] = price
                        self.data[symbol]["price"] = price

                else:

                    price = self._safe_float(payload)

                    if price > 0:
                        self.prices[symbol] = price
                        self.data[symbol]["price"] = price

                self.data[symbol]["symbol"] = symbol
                self.data[symbol]["mode"] = self.mode
                self.data[symbol]["source"] = source

            except Exception:
                continue

    # =====================================================
    # GET PRICE
    # =====================================================

    def get_price(self, symbol: str) -> Optional[float]:

        symbol = str(symbol).upper().strip()

        if not symbol:
            return None

        # -------------------------------------------------
        # LIVE MODE: gateway is source of truth
        # -------------------------------------------------

        if self.mode == "LIVE":

            live_price = self._gateway_price(symbol)

            if live_price is not None and live_price > 0:
                self.update_price(
                    symbol,
                    live_price,
                    source="gateway_live",
                )
                return live_price

        # -------------------------------------------------
        # Fallback cache / seed
        # -------------------------------------------------

        return self.prices.get(symbol)

    # Aliases for compatibility
    latest_price = get_price
    get_last_price = get_price
    last_price = get_price
    market_price = get_price

    # =====================================================
    # GET FULL DATA
    # =====================================================

    def get(self, symbol: str) -> Dict[str, Any]:

        symbol = str(symbol).upper().strip()

        price = self.get_price(symbol)

        if price is None:
            return {}

        row = {
            "symbol": symbol,
            "price": price,
            "mode": self.mode,
            **self.data.get(symbol, {}),
        }

        row["price"] = price

        if self.mode == "LIVE":
            row["source"] = self.data.get(
                symbol,
                {},
            ).get(
                "source",
                "gateway_live",
            )

        return row

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(self) -> Dict[str, Dict[str, Any]]:

        snapshot: Dict[str, Dict[str, Any]] = {}

        symbols = set(self.prices.keys())

        if isinstance(self.data, dict):
            symbols.update(self.data.keys())

        if self.gateway is not None:
            try:
                quotes = getattr(self.gateway, "last_quotes", {})
                if isinstance(quotes, dict):
                    symbols.update(quotes.keys())
            except Exception:
                pass

            try:
                positions = getattr(self.gateway, "positions", {})
                if isinstance(positions, dict):
                    symbols.update(positions.keys())
            except Exception:
                pass

        for symbol in sorted(symbols):

            symbol = str(symbol).upper().strip()

            if not symbol:
                continue

            price = self.get_price(symbol)

            if price is None:
                continue

            row = {
                "symbol": symbol,
                "price": float(price),
                "mode": self.mode,
                **self.data.get(symbol, {}),
            }

            row["price"] = float(price)

            snapshot[symbol] = row

        return snapshot

    # =====================================================
    # CLEAR / RESET
    # =====================================================

    def clear(self) -> None:
        self.prices.clear()
        self.data.clear()
        self._bootstrap_universe_data()

    reset = clear

    # =====================================================
    # DEBUG
    # =====================================================

    def __len__(self) -> int:
        return len(self.prices)

    def __repr__(self) -> str:
        return (
            f"MarketDataHub("
            f"symbols={len(self.prices)}, "
            f"mode={self.mode})"
        )