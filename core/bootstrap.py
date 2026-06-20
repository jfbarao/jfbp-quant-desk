# =========================================================
# 🧠 JFBP QUANT DESK — CORE BOOTSTRAP v33.9
# LIVE GATEWAY REBUILD + PORTFOLIO → RISK RECONCILIATION
# =========================================================

from __future__ import annotations

import streamlit as st

from data.market_data_hub import MarketDataHub
from brokers.ibkr_gateway import IBKRGateway

from execution.oms import OMS
from execution.pipeline import TradingPipeline

from portfolio.engine import PortfolioEngine
from portfolio.garbage_collector import PortfolioGarbageCollector

from risk.engine import RiskEngine
from audit.store import AuditStore

from core.ibkr_gateway_live import IBKRLiveGateway


# =========================================================
# SAFE CALL
# =========================================================

def _safe_call(obj, method_name: str, *args, **kwargs):
    if obj is None or not hasattr(obj, method_name):
        return None

    try:
        return getattr(obj, method_name)(*args, **kwargs)

    except Exception as exc:
        st.session_state["bootstrap_last_error"] = (
            f"{obj.__class__.__name__}.{method_name} failed: {exc}"
        )
        return None


# =========================================================
# SAFE UNIVERSE LOADER
# =========================================================

def _load_universe():
    candidates = []

    try:
        from config.universe import OST_UNIVERSE
        candidates.append(OST_UNIVERSE)
    except Exception:
        pass

    try:
        from config.universe import UNIVERSE
        candidates.append(UNIVERSE)
    except Exception:
        pass

    try:
        from data.universe import OST_UNIVERSE
        candidates.append(OST_UNIVERSE)
    except Exception:
        pass

    try:
        from data.universe import UNIVERSE
        candidates.append(UNIVERSE)
    except Exception:
        pass

    try:
        from universe import OST_UNIVERSE
        candidates.append(OST_UNIVERSE)
    except Exception:
        pass

    try:
        from universe import UNIVERSE
        candidates.append(UNIVERSE)
    except Exception:
        pass

    for universe in candidates:
        if isinstance(universe, dict) and universe:
            return universe

        if isinstance(universe, list) and universe:
            return {str(symbol).upper(): {} for symbol in universe}

    return {
        "SPY": {"sector": "ETF", "liquidity": 5, "volatility": 3, "regime": ["broad_market"]},
        "QQQ": {"sector": "ETF", "liquidity": 5, "volatility": 4, "regime": ["tech_beta_risk_on"]},
        "IWM": {"sector": "ETF", "liquidity": 4, "volatility": 4, "regime": ["small_cap_risk_sentiment"]},
        "DIA": {"sector": "ETF", "liquidity": 4, "volatility": 2, "regime": ["blue_chip"]},
        "TQQQ": {"sector": "ETF", "liquidity": 4, "volatility": 5, "regime": ["leveraged_momentum"]},
        "UVXY": {"sector": "ETF", "liquidity": 4, "volatility": 5, "regime": ["volatility_risk_off"]},
        "AAPL": {"sector": "Tech", "liquidity": 5, "volatility": 2, "regime": ["defensive_growth"]},
        "MSFT": {"sector": "Tech", "liquidity": 5, "volatility": 2, "regime": ["cloud_quality"]},
        "NVDA": {"sector": "Tech", "liquidity": 5, "volatility": 5, "regime": ["ai_momentum_risk_on"]},
        "AMZN": {"sector": "Tech", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
    }


# =========================================================
# FALLBACK SCANNER
# =========================================================

class FallbackScanner:
    def __init__(self, universe=None, market_data=None):
        self.universe = universe or {}
        self.market_data = market_data
        self.last_signals = []
        self.source = "fallback_scanner_v33_8"

    def run(self):
        import pandas as pd

        rows = []

        for symbol, meta in self.universe.items():
            symbol = str(symbol).upper().strip()
            meta = meta if isinstance(meta, dict) else {}

            price = self._price(symbol)

            action = "HOLD"
            side = "FLAT"
            signal = "NO TRADE"

            if symbol in {"TQQQ", "AAPL", "COIN", "LRCX", "ASML", "ARM"}:
                action = "BUY"
                side = "BUY"
                signal = "BUY"

            elif symbol in {"UVXY", "DE", "WMT", "BA", "BX", "JPM"}:
                action = "SELL"
                side = "SELL"
                signal = "SELL"

            regime = meta.get("regime", [])

            rows.append({
                "symbol": symbol,
                "data_symbol": meta.get("data_symbol", symbol),
                "sector": meta.get("sector", "Unknown"),
                "liquidity": int(meta.get("liquidity", 3) or 3),
                "volatility": int(meta.get("volatility", 3) or 3),
                "regime": ",".join(regime) if isinstance(regime, list) else str(regime),
                "signal": signal,
                "action": action,
                "side": side,
                "qty": 1,
                "price": price,
                "model_score": 4 if signal != "NO TRADE" else 0,
                "score": 4 if signal != "NO TRADE" else 0,
                "trend": "BULLISH" if action == "BUY" else "BEARISH" if action == "SELL" else "NEUTRAL",
                "source": self.source,
                "mode": st.session_state.get("mode", "SIM"),
            })

        self.last_signals = rows
        return pd.DataFrame(rows)

    def snapshot(self):
        return {
            "source": self.source,
            "symbols": len(self.universe),
            "last_signals": len(self.last_signals),
        }

    def _price(self, symbol):
        try:
            if self.market_data and hasattr(self.market_data, "get_price"):
                price = self.market_data.get_price(symbol)
                if price:
                    return float(price)
        except Exception:
            pass

        defaults = {
            "SPY": 745.0,
            "QQQ": 717.0,
            "IWM": 285.0,
            "DIA": 506.0,
            "TQQQ": 77.0,
            "UVXY": 33.0,
            "AAPL": 309.0,
            "MSFT": 419.0,
            "NVDA": 215.0,
            "AMZN": 266.0,
            "COIN": 185.0,
            "DE": 529.0,
            "WMT": 120.0,
            "BA": 215.0,
            "BX": 114.0,
            "LRCX": 305.0,
            "ASML": 1632.0,
            "ARM": 298.0,
            "FUTU": 124.0,
            "JPM": 296.0,
        }

        return float(defaults.get(symbol, 100.0))


def _create_scanner(universe, market):
    scanner_classes = []

    try:
        from scanner.engine import Scanner
        scanner_classes.append(Scanner)
    except Exception:
        pass

    try:
        from scanner.scanner import Scanner
        scanner_classes.append(Scanner)
    except Exception:
        pass

    try:
        from core.scanner import Scanner
        scanner_classes.append(Scanner)
    except Exception:
        pass

    try:
        from scanners.engine import Scanner
        scanner_classes.append(Scanner)
    except Exception:
        pass

    for ScannerCls in scanner_classes:
        try:
            return ScannerCls(universe=universe, market_data=market)
        except TypeError:
            try:
                return ScannerCls(universe, market)
            except Exception:
                pass
        except Exception:
            pass

    return FallbackScanner(universe=universe, market_data=market)


# =========================================================
# POSITION SNAPSHOT NORMALIZATION
# =========================================================

def _portfolio_snapshot_rows(portfolio_engine):
    """
    Returns full position rows with signed_qty + price.
    This is the source passed to RiskEngine.sync_positions().
    """

    rows = {}

    if portfolio_engine is None:
        return rows

    # 1. preferred snapshot()
    try:
        if hasattr(portfolio_engine, "snapshot"):
            snap = portfolio_engine.snapshot()

            if isinstance(snap, dict):
                for symbol, row in snap.items():
                    symbol = str(symbol or "").upper().strip()

                    if not symbol:
                        continue

                    clean = _coerce_position_row(symbol, row)

                    if abs(clean["signed_qty"]) > 1e-9:
                        rows[symbol] = clean
    except Exception as exc:
        st.session_state["bootstrap_last_error"] = f"portfolio snapshot failed: {exc}"

    if rows:
        return rows

    # 2. positions_snapshot()
    try:
        if hasattr(portfolio_engine, "positions_snapshot"):
            snap = portfolio_engine.positions_snapshot()

            if isinstance(snap, dict):
                for symbol, row in snap.items():
                    symbol = str(symbol or "").upper().strip()
                    clean = _coerce_position_row(symbol, row)

                    if abs(clean["signed_qty"]) > 1e-9:
                        rows[symbol] = clean
    except Exception as exc:
        st.session_state["bootstrap_last_error"] = f"positions_snapshot failed: {exc}"

    if rows:
        return rows

    # 3. risk_positions fallback
    try:
        if hasattr(portfolio_engine, "risk_positions"):
            risk_positions = portfolio_engine.risk_positions()

            if isinstance(risk_positions, dict):
                for symbol, qty in risk_positions.items():
                    symbol = str(symbol or "").upper().strip()

                    try:
                        qty = float(qty or 0)
                    except Exception:
                        qty = 0.0

                    if abs(qty) > 1e-9:
                        rows[symbol] = {
                            "symbol": symbol,
                            "side": "LONG" if qty > 0 else "SHORT",
                            "qty": abs(qty),
                            "signed_qty": qty,
                            "avg_price": 0.0,
                            "last_price": 0.0,
                            "price": 0.0,
                        }
    except Exception as exc:
        st.session_state["bootstrap_last_error"] = f"risk_positions fallback failed: {exc}"

    if rows:
        return rows

    # 4. raw positions
    try:
        raw = getattr(portfolio_engine, "positions", {})

        if isinstance(raw, dict):
            for symbol, row in raw.items():
                symbol = str(symbol or "").upper().strip()
                clean = _coerce_position_row(symbol, row)

                if abs(clean["signed_qty"]) > 1e-9:
                    rows[symbol] = clean
    except Exception as exc:
        st.session_state["bootstrap_last_error"] = f"raw positions fallback failed: {exc}"

    return rows


def _coerce_position_row(symbol, row):
    symbol = str(symbol or "").upper().strip()

    if isinstance(row, dict):
        signed_qty = row.get("signed_qty", row.get("quantity", row.get("qty", 0)))
        side = str(row.get("side", "") or "").upper()

        try:
            signed_qty = float(signed_qty or 0)
        except Exception:
            signed_qty = 0.0

        if "signed_qty" not in row and side == "SHORT":
            signed_qty = -abs(signed_qty)

        avg_price = row.get("avg_price", row.get("price", 0))
        last_price = row.get("last_price", avg_price)

    else:
        signed_qty = getattr(row, "quantity", getattr(row, "qty", 0.0))

        try:
            signed_qty = float(signed_qty or 0)
        except Exception:
            signed_qty = 0.0

        avg_price = getattr(row, "avg_price", 0.0)
        last_price = avg_price

    try:
        avg_price = float(avg_price or 0)
    except Exception:
        avg_price = 0.0

    try:
        last_price = float(last_price or avg_price or 0)
    except Exception:
        last_price = avg_price

    return {
        "symbol": symbol,
        "side": "LONG" if signed_qty > 0 else "SHORT" if signed_qty < 0 else "FLAT",
        "qty": abs(signed_qty),
        "signed_qty": signed_qty,
        "avg_price": avg_price,
        "last_price": last_price,
        "price": last_price or avg_price,
    }


def _force_sync_risk_from_portfolio(portfolio_engine, risk_engine):
    """
    v33.8 hard fix:
    always send full portfolio rows to RiskEngine.
    """

    if portfolio_engine is None or risk_engine is None:
        return False

    try:
        rows = _portfolio_snapshot_rows(portfolio_engine)

        if hasattr(risk_engine, "sync_positions"):
            try:
                risk_engine.sync_positions(rows, historical=True)
            except TypeError:
                risk_engine.sync_positions(rows)

            st.session_state["portfolio_risk_sync_status"] = "SYNCED"
            st.session_state["portfolio_risk_sync_count"] = len(rows)
            st.session_state["portfolio_risk_sync_rows"] = rows

            return True

    except Exception as exc:
        st.session_state["portfolio_risk_sync_status"] = "FAILED"
        st.session_state["bootstrap_last_error"] = f"forced risk sync failed: {exc}"

    return False


# =========================================================
# RUNTIME HELPERS
# =========================================================

def _runtime_fill_count(oms):
    fills = _safe_call(oms, "fills_snapshot") or getattr(oms, "fills", []) or []
    return len(fills) if isinstance(fills, list) else 0


def _audit_fill_count(audit_store):
    stats = _safe_call(audit_store, "stats")

    if isinstance(stats, dict):
        return int(stats.get("audit_fills", 0) or 0)

    return 0


def _portfolio_ledger_count(portfolio_engine):
    ledger = _safe_call(portfolio_engine, "ledger_snapshot") or []
    return len(ledger) if isinstance(ledger, list) else 0


# =========================================================
# SINGLETON REGISTRY
# =========================================================

def _runtime_registry():
    st.session_state.setdefault("runtime_registry", {})

    registry = st.session_state["runtime_registry"]

    for key in (
        "gateway",
        "market",
        "oms",
        "portfolio_engine",
        "portfolio_gc",
        "risk_engine",
        "audit_store",
        "pipeline",
        "scanner",
        "universe",
    ):
        if key in st.session_state and st.session_state.get(key) is not None:
            registry[key] = st.session_state[key]

    return registry


def _get_or_create(key: str, factory):
    registry = _runtime_registry()
    existing = st.session_state.get(key) or registry.get(key)

    if existing is None:
        existing = factory()

    st.session_state[key] = existing
    registry[key] = existing

    return existing


def _publish_runtime(
    gateway,
    market,
    oms,
    portfolio_engine,
    portfolio_gc,
    risk_engine,
    audit_store,
    pipeline,
    scanner,
    universe,
):
    registry = _runtime_registry()

    runtime_objects = {
        "gateway": gateway,
        "market": market,
        "market_data": market,
        "oms": oms,
        "portfolio_engine": portfolio_engine,
        "portfolio": portfolio_engine,
        "portfolio_gc": portfolio_gc,
        "garbage_collector": portfolio_gc,
        "risk_engine": risk_engine,
        "risk": risk_engine,
        "audit_store": audit_store,
        "audit": audit_store,
        "pipeline": pipeline,
        "scanner": scanner,
        "universe": universe,
    }

    for key, value in runtime_objects.items():
        if value is not None:
            st.session_state[key] = value

    registry.update({
        "gateway": gateway,
        "market": market,
        "oms": oms,
        "portfolio_engine": portfolio_engine,
        "portfolio_gc": portfolio_gc,
        "risk_engine": risk_engine,
        "audit_store": audit_store,
        "pipeline": pipeline,
        "scanner": scanner,
        "universe": universe,
    })


# =========================================================
# WIRING
# =========================================================

def _wire_oms(oms, gateway, portfolio_engine, audit_store):
    if oms is None:
        return

    for attr, value in {
        "gateway": gateway,
        "portfolio_engine": portfolio_engine,
        "portfolio": portfolio_engine,
        "audit_store": audit_store,
        "audit": audit_store,
    }.items():
        try:
            setattr(oms, attr, value)
        except Exception:
            pass


def _wire_pipeline(
    pipeline,
    gateway,
    market,
    oms,
    portfolio_engine,
    risk_engine,
    audit_store,
):
    if pipeline is None:
        return

    if hasattr(pipeline, "attach"):
        try:
            pipeline.attach(
                gateway=gateway,
                market=market,
                market_data=market,
                oms=oms,
                risk_engine=risk_engine,
                risk=risk_engine,
                audit_store=audit_store,
                audit=audit_store,
                portfolio_engine=portfolio_engine,
                portfolio=portfolio_engine,
            )
        except Exception:
            pass

    for attr, value in {
        "gateway": gateway,
        "market": market,
        "market_data": market,
        "oms": oms,
        "portfolio_engine": portfolio_engine,
        "portfolio": portfolio_engine,
        "risk_engine": risk_engine,
        "risk": risk_engine,
        "audit_store": audit_store,
        "audit": audit_store,
    }.items():
        try:
            setattr(pipeline, attr, value)
        except Exception:
            pass


def _wire_portfolio_gc(portfolio_gc, portfolio_engine):
    if portfolio_gc is None:
        return

    if hasattr(portfolio_gc, "attach"):
        try:
            portfolio_gc.attach(portfolio_engine)
        except Exception as exc:
            st.session_state["bootstrap_last_error"] = (
                f"PortfolioGarbageCollector.attach failed: {exc}"
            )
    else:
        try:
            setattr(portfolio_gc, "portfolio_engine", portfolio_engine)
        except Exception:
            pass


def _wire_scanner(scanner, universe, market):
    if scanner is None:
        return

    for attr, value in {
        "universe": universe,
        "market_data": market,
        "market": market,
    }.items():
        try:
            setattr(scanner, attr, value)
        except Exception:
            pass


def _wire_runtime(
    gateway,
    market,
    oms,
    portfolio_engine,
    portfolio_gc,
    risk_engine,
    audit_store,
    pipeline,
    scanner,
    universe,
):
    _wire_oms(oms, gateway, portfolio_engine, audit_store)

    _wire_pipeline(
        pipeline=pipeline,
        gateway=gateway,
        market=market,
        oms=oms,
        portfolio_engine=portfolio_engine,
        risk_engine=risk_engine,
        audit_store=audit_store,
    )

    _wire_portfolio_gc(portfolio_gc, portfolio_engine)
    _wire_scanner(scanner, universe, market)

    _force_sync_risk_from_portfolio(portfolio_engine, risk_engine)

    _publish_runtime(
        gateway=gateway,
        market=market,
        oms=oms,
        portfolio_engine=portfolio_engine,
        portfolio_gc=portfolio_gc,
        risk_engine=risk_engine,
        audit_store=audit_store,
        pipeline=pipeline,
        scanner=scanner,
        universe=universe,
    )


# =========================================================
# AUDIT RECOVERY
# =========================================================

def _recover_runtime_from_audit(
    oms,
    portfolio_engine,
    portfolio_gc,
    risk_engine,
    audit_store,
):
    audit_fills = _audit_fill_count(audit_store)

    if audit_fills <= 0:
        st.session_state["bootstrap_recovery_status"] = "NO_AUDIT_FILLS"
        _force_sync_risk_from_portfolio(portfolio_engine, risk_engine)
        return False

    runtime_fills = _runtime_fill_count(oms)
    ledger_count = _portfolio_ledger_count(portfolio_engine)

    if runtime_fills == audit_fills and ledger_count == audit_fills:
        st.session_state["bootstrap_recovery_status"] = "ALREADY_MATCHED"
        _safe_call(portfolio_gc, "run")
        _force_sync_risk_from_portfolio(portfolio_engine, risk_engine)
        return True

    if hasattr(audit_store, "replay_fills"):
        replay_result = audit_store.replay_fills(
            oms=oms,
            portfolio=portfolio_engine,
            risk=risk_engine,
        )
    elif hasattr(audit_store, "rebuild_runtime_state"):
        replay_result = audit_store.rebuild_runtime_state(
            oms=oms,
            portfolio=portfolio_engine,
            risk=risk_engine,
        )
    else:
        replay_result = {
            "status": "SKIPPED",
            "reason": "Audit store has no replay method",
        }

    _safe_call(portfolio_gc, "run")

    runtime_after = _runtime_fill_count(oms)
    ledger_after = _portfolio_ledger_count(portfolio_engine)

    st.session_state["bootstrap_replay_result"] = replay_result
    st.session_state["bootstrap_runtime_fills_after"] = runtime_after
    st.session_state["bootstrap_portfolio_ledger_after"] = ledger_after
    st.session_state["bootstrap_audit_fills"] = audit_fills

    _force_sync_risk_from_portfolio(portfolio_engine, risk_engine)

    if runtime_after == audit_fills and ledger_after == audit_fills:
        st.session_state["bootstrap_recovery_status"] = "RECOVERED_FROM_AUDIT"
        return True

    st.session_state["bootstrap_recovery_status"] = "RECOVERY_MISMATCH"
    return False


# =========================================================
# INIT CORE
# =========================================================

def init_core():
    st.session_state.setdefault("mode", "SIM")
    st.session_state.setdefault("live_trading_armed", False)
    st.session_state.setdefault("risk_kill_switch", False)

    st.session_state.setdefault("bootstrap_initialized", False)
    st.session_state.setdefault("bootstrap_recovered", False)
    st.session_state.setdefault("bootstrap_recovered_ok", False)
    st.session_state.setdefault("bootstrap_recovery_status", "NOT_STARTED")
    st.session_state.setdefault("bootstrap_last_error", "")
    st.session_state.setdefault("bootstrap_replay_result", {})
    st.session_state.setdefault("bootstrap_runtime_fills_after", 0)
    st.session_state.setdefault("bootstrap_portfolio_ledger_after", 0)
    st.session_state.setdefault("bootstrap_audit_fills", 0)

    st.session_state.setdefault("portfolio_gc_enabled", False)
    st.session_state.setdefault("portfolio_gc_auto_boot", False)
    st.session_state.setdefault("portfolio_gc_last_report", {})
    st.session_state.setdefault("portfolio_risk_sync_status", "NOT_STARTED")
    st.session_state.setdefault("portfolio_risk_sync_count", 0)
    st.session_state.setdefault("portfolio_risk_sync_rows", {})

    st.session_state.setdefault("live_gateway_callbacks_bound", False)

    # Multi-Asset Signal Bus
    # Pulse pages publish regime/stress/breadth/opportunity state here.
    # Scanner and Quant Executor can read this without importing Pulse pages.
    st.session_state.setdefault("multi_asset_signal_bus", {})
    st.session_state.setdefault("multi_asset_signal_bus_version", "v1.0")

    mode = st.session_state.get("mode", "SIM")

    universe = _get_or_create(
        "universe",
        lambda: _load_universe(),
    )

    # =====================================================
    # GATEWAY SELECTION
    # =====================================================
    # v33.9 reconnect fix:
    #
    # In LIVE mode this app uses IBKRLiveGateway from
    # core.ibkr_gateway_live, not the SIM gateway from
    # brokers.ibkr_gateway.
    #
    # After a manual disconnect, some IBKR/ib_insync client
    # objects can remain stale inside the existing gateway
    # instance. Restarting Streamlit works because it creates
    # a fresh gateway. This block gives us that same clean
    # gateway rebuild automatically whenever LIVE mode is
    # active and the existing live gateway is disconnected.
    #
    # Connected live gateways are never replaced.

    existing_gateway = st.session_state.get("gateway")

    def _gateway_connected_for_bootstrap(candidate) -> bool:
        if candidate is None:
            return False

        try:
            if hasattr(candidate, "verify_connection"):
                return bool(candidate.verify_connection())
        except Exception:
            return False

        try:
            connected_attr = getattr(candidate, "connected", False)

            if callable(connected_attr):
                return bool(connected_attr())

            return bool(connected_attr)

        except Exception:
            return False

    if mode == "LIVE":

        existing_gateway_class = (
            existing_gateway.__class__.__name__
            if existing_gateway is not None
            else ""
        )

        existing_live_gateway_connected = _gateway_connected_for_bootstrap(
            existing_gateway
        )

        gateway_needs_replace = (
            existing_gateway is None
            or existing_gateway_class != "IBKRLiveGateway"
            or not existing_live_gateway_connected
        )

        if gateway_needs_replace:
            try:
                if existing_gateway is not None and hasattr(existing_gateway, "disconnect"):
                    existing_gateway.disconnect()
            except Exception:
                pass

            gateway = IBKRLiveGateway(mode="LIVE")
            st.session_state["gateway"] = gateway
            st.session_state["live_gateway_callbacks_bound"] = False

            st.session_state["bootstrap_live_gateway_rebuilt"] = True
            st.session_state["bootstrap_live_gateway_rebuild_reason"] = (
                "MISSING_OR_DISCONNECTED_LIVE_GATEWAY"
            )
        else:
            gateway = existing_gateway
            st.session_state["bootstrap_live_gateway_rebuilt"] = False
            st.session_state["bootstrap_live_gateway_rebuild_reason"] = "CONNECTED_GATEWAY_REUSED"

    else:

        gateway_needs_replace = (
            existing_gateway is None
            or existing_gateway.__class__.__name__ == "IBKRLiveGateway"
        )

        if gateway_needs_replace:
            gateway = IBKRGateway(mode=mode)
            st.session_state["gateway"] = gateway
            st.session_state["live_gateway_callbacks_bound"] = False
        else:
            gateway = existing_gateway

            if hasattr(gateway, "mode"):
                try:
                    gateway.mode = mode
                except Exception:
                    pass

    # =====================================================
    # CORE OBJECTS
    # =====================================================

    market = _get_or_create(
        "market",
        lambda: MarketDataHub(),
    )

    # =====================================================
    # HARD LIVE MARKET WIRING
    # IBKR FIRST → YFINANCE FALLBACK
    # =====================================================

    try:
        if hasattr(market, "set_mode"):
            market.set_mode(mode)
    except Exception:
        pass

    try:
        if hasattr(market, "attach_gateway"):
            market.attach_gateway(gateway)
    except Exception:
        pass

    try:
        if hasattr(gateway, "attach_market_data"):
            gateway.attach_market_data(market)
    except Exception:
        pass

    try:
        market.gateway = gateway
    except Exception:
        pass

    try:
        gateway.market_data = market
    except Exception:
        pass

    try:
        market.enable_yfinance_fallback = True
        market.use_yfinance_backup = True
        market.allow_yfinance = True
        market.fallback_to_yfinance = True
    except Exception:
        pass

    # =====================================================
    # SAFE PRICE RESOLUTION PATCH
    # =====================================================

    try:

        if not hasattr(market, "_jfbp_original_get_price"):
            market._jfbp_original_get_price = getattr(
                market,
                "get_price",
                None,
            )

        original_get_price = market._jfbp_original_get_price

        def safe_get_price(symbol: str):

            symbol = str(symbol or "").upper().strip()

            if not symbol:
                return 0.0

            # ---------------------------------------------
            # 1) TRY IBKR / EXISTING MARKET HUB FIRST
            # ---------------------------------------------

            try:
                if callable(original_get_price):
                    value = original_get_price(symbol)

                    if value is not None:
                        value = float(value)

                        if value > 0:
                            return value
            except Exception:
                pass

            # ---------------------------------------------
            # 2) TRY GATEWAY QUOTE CACHE DIRECTLY
            # ---------------------------------------------

            try:
                quotes = getattr(gateway, "last_quotes", {}) or {}
                quote = quotes.get(symbol)

                if isinstance(quote, dict):
                    value = float(
                        quote.get("price")
                        or quote.get("last")
                        or quote.get("mark")
                        or quote.get("close")
                        or 0
                    )

                    if value > 0:
                        return value
            except Exception:
                pass

            # ---------------------------------------------
            # 3) TRY MARKET CACHE ONLY
            # ---------------------------------------------

            try:
                value = getattr(market, "prices", {}).get(symbol)

                if value is not None:
                    value = float(value)

                    if value > 0:
                        return value
            except Exception:
                pass

            # ---------------------------------------------
            # 4) YFINANCE DISABLED DURING PAGE RENDER
            # ---------------------------------------------

            # Do NOT call yfinance here.
            # This function may be called many times during page navigation.
            # External price refresh must be manual/background only.
            return 0.0

        market.get_price = safe_get_price
        market.latest_price = safe_get_price
        market.get_last_price = safe_get_price
        market.last_price = safe_get_price
        market.market_price = safe_get_price

    except Exception:
        pass

    portfolio_engine = _get_or_create(
        "portfolio_engine",
        lambda: PortfolioEngine(),
    )

    portfolio_gc = _get_or_create(
        "portfolio_gc",
        lambda: PortfolioGarbageCollector(
            portfolio_engine=portfolio_engine,
        ),
    )

    risk_engine = _get_or_create(
        "risk_engine",
        lambda: RiskEngine(),
    )

    audit_store = _get_or_create(
        "audit_store",
        lambda: AuditStore(),
    )

    # =====================================================
    # OMS
    # =====================================================

    existing_oms = st.session_state.get("oms")

    if existing_oms is None:
        oms = OMS(
            gateway=gateway,
            portfolio_engine=portfolio_engine,
            audit_store=audit_store,
            mode=mode,
        )
        st.session_state["oms"] = oms
    else:
        oms = existing_oms

        try:
            oms.attach_gateway(gateway)
        except Exception:
            pass

        try:
            oms.attach_portfolio_engine(portfolio_engine)
        except Exception:
            pass

        try:
            oms.attach_audit_store(audit_store)
        except Exception:
            pass

        try:
            oms.set_mode(mode)
        except Exception:
            pass

    # =====================================================
    # LIVE CALLBACK WIRING
    # =====================================================

    def _broker_fill_journal_callback(fill_event):
        try:
            if not isinstance(fill_event, dict):
                return

            journal_event = dict(fill_event)

            journal_event["event"] = (
                journal_event.get("event")
                or "BROKER_EXECUTION_FILL"
            )

            journal_event["event_type"] = "BROKER_EXECUTION_FILL"
            journal_event["source"] = (
                journal_event.get("source")
                or "ibkr_live_gateway"
            )
            journal_event["broker_fill_journaled"] = True
            journal_event["journal_source"] = "live_gateway_callback"
            journal_event["is_true_fill"] = True

            if audit_store is not None and hasattr(audit_store, "record_event"):
                audit_store.record_event(
                    "BROKER_EXECUTION_FILL",
                    journal_event,
                )

            if audit_store is not None and hasattr(audit_store, "record_fill"):
                audit_store.record_fill(journal_event)

            st.session_state["last_broker_fill_journal_event"] = journal_event
            st.session_state["last_broker_fill_journal_status"] = "RECORDED"

        except Exception as exc:
            st.session_state["last_broker_fill_journal_status"] = (
                f"FAILED: {exc}"
            )

    if (
        mode == "LIVE"
        and hasattr(gateway, "on_fill")
        and hasattr(gateway, "on_order_update")
    ):
        try:
            gateway.fill_callbacks = []
            gateway.order_callbacks = []
        except Exception:
            pass

        try:
            gateway.on_fill(oms.ingest_broker_fill)
        except Exception:
            pass

        try:
            gateway.on_fill(_broker_fill_journal_callback)
        except Exception:
            pass

        try:
            gateway.on_order_update(oms.ingest_broker_order_status)
        except Exception:
            pass

        st.session_state["live_gateway_callbacks_bound"] = True
        st.session_state["broker_fill_journal_callback_bound"] = True

    else:
        st.session_state["broker_fill_journal_callback_bound"] = False

    # =====================================================
    # PIPELINE
    # =====================================================

    existing_pipeline = st.session_state.get("pipeline")

    if existing_pipeline is None:
        pipeline = TradingPipeline(
            gateway=gateway,
            market=market,
            market_data=market,
            oms=oms,
            risk_engine=risk_engine,
            risk=risk_engine,
            audit_store=audit_store,
            audit=audit_store,
            portfolio_engine=portfolio_engine,
            portfolio=portfolio_engine,
            mode=mode,
        )
        st.session_state["pipeline"] = pipeline

    else:
        pipeline = existing_pipeline

        if hasattr(pipeline, "gateway"):
            pipeline.gateway = gateway

        if hasattr(pipeline, "oms"):
            pipeline.oms = oms

        if hasattr(pipeline, "market"):
            pipeline.market = market

        if hasattr(pipeline, "market_data"):
            pipeline.market_data = market

        if hasattr(pipeline, "risk_engine"):
            pipeline.risk_engine = risk_engine

        if hasattr(pipeline, "risk"):
            pipeline.risk = risk_engine

        if hasattr(pipeline, "audit_store"):
            pipeline.audit_store = audit_store

        if hasattr(pipeline, "audit"):
            pipeline.audit = audit_store

        if hasattr(pipeline, "portfolio_engine"):
            pipeline.portfolio_engine = portfolio_engine

        if hasattr(pipeline, "portfolio"):
            pipeline.portfolio = portfolio_engine

        if hasattr(pipeline, "mode"):
            pipeline.mode = mode
    # =====================================================
    # SCANNER
    # =====================================================

    scanner = _get_or_create(
        "scanner",
        lambda: _create_scanner(
            universe=universe,
            market=market,
        ),
    )

    # =====================================================
    # FORCE WIRING BEFORE RECOVERY
    # =====================================================

    _wire_runtime(
        gateway=gateway,
        market=market,
        oms=oms,
        portfolio_engine=portfolio_engine,
        portfolio_gc=portfolio_gc,
        risk_engine=risk_engine,
        audit_store=audit_store,
        pipeline=pipeline,
        scanner=scanner,
        universe=universe,
    )

    _safe_call(gateway, "set_mode", mode)
    _safe_call(market, "set_mode", mode)
    _safe_call(oms, "set_mode", mode)
    _safe_call(risk_engine, "set_mode", mode)
    _safe_call(pipeline, "set_mode", mode)

    # =====================================================
    # ONE-TIME AUDIT RECOVERY
    # =====================================================

    if not st.session_state.get("bootstrap_recovered", False):
        recovered = _recover_runtime_from_audit(
            oms=oms,
            portfolio_engine=portfolio_engine,
            portfolio_gc=portfolio_gc,
            risk_engine=risk_engine,
            audit_store=audit_store,
        )

        st.session_state["bootstrap_recovered"] = True
        st.session_state["bootstrap_recovered_ok"] = recovered

        # Recovery already rebuilds runtime/portfolio/risk state.
        st.session_state["portfolio_risk_forced_sync"] = True

    else:
        if st.session_state.get("portfolio_gc_auto_boot", False):
            report = _safe_call(portfolio_gc, "run") or {}
            st.session_state["portfolio_gc_last_report"] = report

    # =====================================================
    # FINAL HARD SYNC — ONE TIME ONLY
    # =====================================================

    if not st.session_state.get("portfolio_risk_forced_sync", False):
        _force_sync_risk_from_portfolio(
            portfolio_engine,
            risk_engine,
        )

        st.session_state["portfolio_risk_forced_sync"] = True

    _wire_runtime(
        gateway=gateway,
        market=market,
        oms=oms,
        portfolio_engine=portfolio_engine,
        portfolio_gc=portfolio_gc,
        risk_engine=risk_engine,
        audit_store=audit_store,
        pipeline=pipeline,
        scanner=scanner,
        universe=universe,
    )

    st.session_state["bootstrap_initialized"] = True
    st.session_state["shared_runtime_unified"] = True
    st.session_state["portfolio_gc_wired"] = True
    st.session_state["scanner_wired"] = True

    return gateway, market, oms, portfolio_engine