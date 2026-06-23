# =========================================================
# 📡 JFBP SCANNER PAGE v86.2
# TRADING DESK LAYOUT + TRADER PRESETS + INDEX + FUTURES + TRUE FOREX UNIVERSES
# RESPONSIVE CLEANUP + CUSTOM BATCH + RESEARCH-MODEL SIGNAL TRUTH
# ACCOUNT-AWARE EQUAL-WEIGHT POSITION SIZING
# LIVE MODE USES IBKR BROKER POSITIONS ONLY
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from math import floor
from typing import Dict, Any, List

import pandas as pd
import streamlit as st
import yfinance as yf

from core.responsive import inject_responsive_css, columns as responsive_columns
from core.ui_cards import inject_card_css

from core.bootstrap import init_core

try:
    from universe.jfbp_universe import JFBP_UNIVERSE
except Exception:
    JFBP_UNIVERSE = {}

try:
    from engines.economic_calendar import (
        analyze_economic_calendar,
        get_calendar_events,
    )
except Exception:
    analyze_economic_calendar = None
    get_calendar_events = None

try:
    from engines.earnings_risk import (
        analyze_earnings_risk,
        analyze_symbol_earnings_risk,
        apply_earnings_risk_adjustment,
    )
except Exception:
    analyze_earnings_risk = None
    analyze_symbol_earnings_risk = None
    apply_earnings_risk_adjustment = None


# =========================================================
# PAGE ALIAS
# =========================================================

def page():
    run_page()


# =========================================================
# FALLBACK UNIVERSE
# =========================================================

def fallback_universe():
    return {
        "SPY": {"sector": "ETF", "liquidity": 5, "volatility": 2, "regime": ["benchmark"]},
        "QQQ": {"sector": "ETF", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
        "IWM": {"sector": "ETF", "liquidity": 4, "volatility": 3, "regime": ["small_caps"]},
        "DIA": {"sector": "ETF", "liquidity": 4, "volatility": 2, "regime": ["blue_chip"]},
        "TQQQ": {"sector": "ETF", "liquidity": 4, "volatility": 5, "regime": ["leveraged_momentum"]},
        "UVXY": {"sector": "ETF", "liquidity": 4, "volatility": 5, "regime": ["volatility"]},
        "AAPL": {"sector": "Tech", "liquidity": 5, "volatility": 2, "regime": ["defensive_growth"]},
        "MSFT": {"sector": "Tech", "liquidity": 5, "volatility": 2, "regime": ["defensive_growth"]},
        "NVDA": {"sector": "Tech", "liquidity": 5, "volatility": 4, "regime": ["momentum"]},
        "AMZN": {"sector": "Consumer", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
        "COIN": {"sector": "Crypto", "liquidity": 4, "volatility": 5, "regime": ["high_beta"]},
        "DE": {"sector": "Industrial", "liquidity": 3, "volatility": 3, "regime": ["cyclical"]},
        "WMT": {"sector": "Consumer Defensive", "liquidity": 5, "volatility": 2, "regime": ["defensive"]},
        "BA": {"sector": "Industrial", "liquidity": 4, "volatility": 4, "regime": ["cyclical"]},
        "BX": {"sector": "Financial", "liquidity": 4, "volatility": 3, "regime": ["financial"]},
        "LRCX": {"sector": "Semiconductors", "liquidity": 4, "volatility": 4, "regime": ["semis"]},
        "ASML": {"sector": "Semiconductors", "liquidity": 4, "volatility": 3, "regime": ["semis"]},
        "ARM": {"sector": "Semiconductors", "liquidity": 4, "volatility": 5, "regime": ["semis"]},
        "FUTU": {"sector": "Financial", "liquidity": 3, "volatility": 5, "regime": ["high_beta"]},
        "JPM": {"sector": "Financial", "liquidity": 5, "volatility": 2, "regime": ["financial"]},
    }


# =========================================================
# CACHED EVENT-RISK HELPERS
# =========================================================

@st.cache_data(ttl=3600)
def cached_symbol_earnings_context(symbol: str) -> Dict[str, Any]:
    symbol = str(symbol or "").upper().strip()

    if not symbol or analyze_symbol_earnings_risk is None:
        return {
            "symbol": symbol,
            "earnings_date": None,
            "days_until": None,
            "risk_score": 0,
            "risk_label": "NONE",
            "status": "UNAVAILABLE",
            "source": "UNAVAILABLE",
            "reason": "Earnings engine unavailable.",
        }

    try:
        event = analyze_symbol_earnings_risk(symbol)

        if hasattr(event, "__dict__"):
            row = dict(event.__dict__)
        elif isinstance(event, dict):
            row = dict(event)
        else:
            row = {}

        earnings_date = row.get("earnings_date")

        if earnings_date is not None and hasattr(earnings_date, "isoformat"):
            row["earnings_date"] = earnings_date.isoformat()

        return {
            "symbol": symbol,
            "earnings_date": row.get("earnings_date"),
            "days_until": row.get("days_until"),
            "risk_score": int(float(row.get("risk_score") or 0)),
            "risk_label": str(row.get("risk_label") or "NONE").upper().strip(),
            "status": str(row.get("status") or "UNKNOWN"),
            "source": str(row.get("source") or "YFINANCE"),
            "reason": str(row.get("reason") or ""),
        }

    except Exception as exc:
        return {
            "symbol": symbol,
            "earnings_date": None,
            "days_until": None,
            "risk_score": 0,
            "risk_label": "NONE",
            "status": "ERROR",
            "source": "ERROR_SAFE",
            "reason": str(exc),
        }


@st.cache_data(ttl=3600)
def cached_universe_earnings_context(symbols: tuple) -> Dict[str, Any]:
    symbols = tuple(str(symbol or "").upper().strip() for symbol in symbols)
    symbols = tuple(symbol for symbol in symbols if symbol)

    if analyze_earnings_risk is None:
        return {
            "earnings_risk_score": 0,
            "earnings_risk_label": "NONE",
            "highest_risk_event": None,
            "events": [],
            "symbol_count": len(symbols),
            "source": "UNAVAILABLE",
        }

    try:
        result = analyze_earnings_risk(symbols)
        return result if isinstance(result, dict) else {}
    except Exception as exc:
        return {
            "earnings_risk_score": 0,
            "earnings_risk_label": "NONE",
            "highest_risk_event": None,
            "events": [],
            "symbol_count": len(symbols),
            "source": "ERROR_SAFE",
            "error": str(exc),
        }


def run_page():

    inject_responsive_css()
    inject_card_css()

    gateway, market, oms, portfolio_engine = init_core()

    risk_engine = st.session_state.get("risk_engine")
    pipeline = st.session_state.get("pipeline")

    # =====================================================
    # POSITION SIZING CONFIG
    # =====================================================
    # Option B:
    #   Trading Equity = Cash + Open Positions
    #
    # Priority:
    #   1) Manual scanner equity override
    #   2) Explicit account / net liquidation values
    #   3) Cash + positions from snapshots
    #   4) Gross exposure / portfolio positions
    #   5) Safe $50k fallback for SIM/testing

    SCANNER_FALLBACK_PORTFOLIO_VALUE = 50_000.0
    SCANNER_TARGET_POSITION_PCT = 0.05
    SCANNER_MIN_QTY = 1

    def scanner_positions_value() -> float:
        try:
            positions = get_portfolio_positions()

            if isinstance(positions, dict) and positions:
                total = sum(
                    safe_float(row.get("position_value"), 0.0)
                    for row in positions.values()
                    if isinstance(row, dict)
                )

                if total > 0:
                    return float(total)

        except Exception:
            pass

        try:
            risk_snapshot = safe_snapshot(risk_engine)

            for key in (
                "gross_exposure",
                "long_exposure",
                "net_exposure",
            ):
                value = safe_float(risk_snapshot.get(key), 0.0)

                if value > 0:
                    return float(value)

        except Exception:
            pass

        return 0.0

    def scanner_cash_value() -> float:
        cash_keys = [
            "cash",
            "available_cash",
            "available_funds",
            "buying_power",
            "cash_balance",
            "settled_cash",
            "excess_liquidity",
            "ibkr_cash",
            "ibkr_available_funds",
            "ibkr_buying_power",
        ]

        for key in cash_keys:
            value = safe_float(st.session_state.get(key), 0.0)

            if value > 0:
                return float(value)

        def read_cash_from_mapping(mapping: Any) -> float:
            if not isinstance(mapping, dict):
                return 0.0

            for key in cash_keys:
                value = safe_float(mapping.get(key), 0.0)

                if value > 0:
                    return float(value)

            ibkr_keys = [
                "AvailableFunds",
                "BuyingPower",
                "TotalCashValue",
                "SettledCash",
                "ExcessLiquidity",
                "CashBalance",
            ]

            for key in ibkr_keys:
                value = safe_float(mapping.get(key), 0.0)

                if value > 0:
                    return float(value)

            return 0.0

        def read_cash_from_object(obj: Any) -> float:
            if obj is None:
                return 0.0

            for attr in cash_keys:
                try:
                    value = getattr(obj, attr, None)

                    if callable(value):
                        value = value()

                    value = safe_float(value, 0.0)

                    if value > 0:
                        return float(value)

                except Exception:
                    pass

            for method in (
                "account_summary",
                "account_values",
                "account_snapshot",
                "snapshot",
            ):
                try:
                    fn = getattr(obj, method, None)

                    if not callable(fn):
                        continue

                    data = fn()

                    value = read_cash_from_mapping(data)

                    if value > 0:
                        return float(value)

                    if isinstance(data, dict):
                        for item in data.values():
                            nested = read_cash_from_mapping(item)

                            if nested > 0:
                                return float(nested)

                except Exception:
                    pass

            return 0.0

        for obj in (
            gateway,
            portfolio_engine,
            risk_engine,
            oms,
        ):
            value = read_cash_from_object(obj)

            if value > 0:
                return float(value)

        return 0.0

    def scanner_account_equity() -> float:
        manual_equity = safe_float(
            st.session_state.get("scanner_account_equity_override"),
            0.0,
        )

        if manual_equity > 0:
            return float(manual_equity)

        equity_keys = [
            "account_equity",
            "net_liquidation",
            "net_liquidation_value",
            "ibkr_net_liquidation",
            "portfolio_equity",
            "portfolio_value",
            "account_value",
            "total_account_value",
            "scanner_account_equity",
        ]

        for key in equity_keys:
            value = safe_float(st.session_state.get(key), 0.0)

            if value > 0:
                return float(value)

        def read_equity_from_mapping(mapping: Any) -> float:
            if not isinstance(mapping, dict):
                return 0.0

            value_keys = [
                "account_equity",
                "net_liquidation",
                "NetLiquidation",
                "net_liquidation_value",
                "equity",
                "portfolio_equity",
                "portfolio_value",
                "account_value",
                "total_value",
                "total_account_value",
                "cash_plus_positions",
            ]

            for key in value_keys:
                value = safe_float(mapping.get(key), 0.0)

                if value > 0:
                    return float(value)

            return 0.0

        def read_equity_from_object(obj: Any) -> float:
            if obj is None:
                return 0.0

            for attr in (
                "account_equity",
                "net_liquidation",
                "portfolio_equity",
                "portfolio_value",
                "account_value",
                "total_value",
            ):
                try:
                    value = getattr(obj, attr, None)

                    if callable(value):
                        value = value()

                    value = safe_float(value, 0.0)

                    if value > 0:
                        return float(value)

                except Exception:
                    pass

            for method in (
                "account_summary",
                "account_values",
                "account_snapshot",
                "snapshot",
            ):
                try:
                    fn = getattr(obj, method, None)

                    if not callable(fn):
                        continue

                    data = fn()

                    direct_value = read_equity_from_mapping(data)

                    if direct_value > 0:
                        return float(direct_value)

                    if isinstance(data, dict):
                        for value in data.values():
                            nested_value = read_equity_from_mapping(value)

                            if nested_value > 0:
                                return float(nested_value)

                except Exception:
                    pass

            return 0.0

        for obj in (
            gateway,
            portfolio_engine,
            risk_engine,
            oms,
        ):
            value = read_equity_from_object(obj)

            if value > 0:
                return float(value)

        cash_value = scanner_cash_value()
        positions_value = scanner_positions_value()
        trading_equity = cash_value + positions_value

        if trading_equity > 0:
            return float(trading_equity)

        return float(SCANNER_FALLBACK_PORTFOLIO_VALUE)

    def scanner_target_position_value() -> float:
        return float(scanner_account_equity() * SCANNER_TARGET_POSITION_PCT)

    def parse_custom_batch_symbols(raw_text: str) -> List[str]:
        """
        Parse user-entered ticker symbols from commas, spaces, semicolons,
        tabs, or new lines. Keeps symbols unique while preserving order.
        """

        text = str(raw_text or "").upper().strip()

        for separator in (",", ";", "|", "\t", "\n", "\r"):
            text = text.replace(separator, " ")

        symbols = []

        for item in text.split(" "):
            symbol = item.strip().upper()

            if not symbol:
                continue

            # Keep common ticker formats safe: BRK.B, BRK-B, SHOP.TO, RY.TO.
            symbol = symbol.replace("$", "")

            if symbol and symbol not in symbols:
                symbols.append(symbol)

        return symbols

    def build_custom_batch_universe(raw_text: str) -> Dict[str, Dict[str, Any]]:
        symbols = parse_custom_batch_symbols(raw_text)

        return {
            symbol: {
                "sector": "Custom Batch",
                "liquidity": 3,
                "volatility": 3,
                "regime": ["custom_batch"],
            }
            for symbol in symbols
        }


    def scanner_preset_universe(mode: str) -> Dict[str, Dict[str, Any]]:
        """Institutional scanner presets.

        These presets keep the Universe dropdown useful for daily trading while
        preserving JFBP, FALLBACK, and CUSTOM BATCH behavior. Metadata is
        intentionally simple because the research model supplies the signal
        truth from price, trend, relative strength, leadership, and event risk.
        """

        mode = str(mode or "").upper().strip()

        presets: Dict[str, List[tuple[str, str, int, int, List[str]]]] = {
            "INDEXES": [
                ("SPY", "Index ETF", 5, 2, ["sp500", "benchmark"]),
                ("QQQ", "Index ETF", 5, 3, ["nasdaq100", "growth"]),
                ("DIA", "Index ETF", 4, 2, ["dow", "blue_chip"]),
                ("IWM", "Index ETF", 4, 3, ["russell2000", "small_caps"]),
                ("RSP", "Index ETF", 4, 2, ["equal_weight_sp500"]),
                ("VTI", "Index ETF", 5, 2, ["total_us_market"]),
                ("ACWI", "Index ETF", 4, 2, ["global_equity"]),
                ("EFA", "Index ETF", 4, 2, ["developed_international"]),
                ("EEM", "Index ETF", 4, 3, ["emerging_markets"]),
                ("TLT", "Bond ETF", 5, 3, ["long_bonds", "rates"]),
            ],
            "INDEX FUTURES": [
                ("ES=F", "Index Futures", 5, 4, ["sp500", "emini", "futures"]),
                ("NQ=F", "Index Futures", 5, 5, ["nasdaq100", "emini", "futures"]),
                ("YM=F", "Index Futures", 4, 3, ["dow", "emini", "futures"]),
                ("RTY=F", "Index Futures", 4, 4, ["russell2000", "emini", "futures"]),
            ],
            "COMMODITY FUTURES": [
                ("CL=F", "Commodity Futures", 5, 5, ["wti", "crude_oil", "futures"]),
                ("BZ=F", "Commodity Futures", 4, 5, ["brent", "crude_oil", "futures"]),
                ("GC=F", "Commodity Futures", 5, 3, ["gold", "futures"]),
                ("SI=F", "Commodity Futures", 4, 4, ["silver", "futures"]),
                ("NG=F", "Commodity Futures", 4, 5, ["natural_gas", "futures"]),
                ("HG=F", "Commodity Futures", 4, 4, ["copper", "futures"]),
            ],
            "FX FUTURES": [
                ("6E=F", "FX Futures", 4, 3, ["euro", "currency", "futures"]),
                ("6J=F", "FX Futures", 4, 3, ["yen", "currency", "futures"]),
                ("6B=F", "FX Futures", 4, 3, ["pound", "currency", "futures"]),
                ("6C=F", "FX Futures", 4, 3, ["canadian_dollar", "currency", "futures"]),
                ("DX=F", "FX Futures", 4, 3, ["dollar_index", "currency", "futures"]),
            ],
            "RATES FUTURES": [
                ("ZT=F", "Rates Futures", 4, 2, ["2_year_note", "rates", "futures"]),
                ("ZF=F", "Rates Futures", 4, 2, ["5_year_note", "rates", "futures"]),
                ("ZN=F", "Rates Futures", 5, 3, ["10_year_note", "rates", "futures"]),
                ("ZB=F", "Rates Futures", 5, 4, ["30_year_bond", "rates", "futures"]),
            ],
            "FUTURES DASHBOARD": [
                ("ES=F", "Index Futures", 5, 4, ["sp500", "emini", "futures"]),
                ("NQ=F", "Index Futures", 5, 5, ["nasdaq100", "emini", "futures"]),
                ("YM=F", "Index Futures", 4, 3, ["dow", "emini", "futures"]),
                ("RTY=F", "Index Futures", 4, 4, ["russell2000", "emini", "futures"]),
                ("CL=F", "Commodity Futures", 5, 5, ["wti", "crude_oil", "futures"]),
                ("BZ=F", "Commodity Futures", 4, 5, ["brent", "crude_oil", "futures"]),
                ("GC=F", "Commodity Futures", 5, 3, ["gold", "futures"]),
                ("SI=F", "Commodity Futures", 4, 4, ["silver", "futures"]),
                ("NG=F", "Commodity Futures", 4, 5, ["natural_gas", "futures"]),
                ("HG=F", "Commodity Futures", 4, 4, ["copper", "futures"]),
                ("6E=F", "FX Futures", 4, 3, ["euro", "currency", "futures"]),
                ("6J=F", "FX Futures", 4, 3, ["yen", "currency", "futures"]),
                ("6B=F", "FX Futures", 4, 3, ["pound", "currency", "futures"]),
                ("6C=F", "FX Futures", 4, 3, ["canadian_dollar", "currency", "futures"]),
                ("DX=F", "FX Futures", 4, 3, ["dollar_index", "currency", "futures"]),
                ("ZN=F", "Rates Futures", 5, 3, ["10_year_note", "rates", "futures"]),
                ("ZB=F", "Rates Futures", 5, 4, ["30_year_bond", "rates", "futures"]),
            ],
            "MOMENTUM": [
                ("NVDA", "Semiconductors", 5, 4, ["momentum", "ai"]),
                ("AVGO", "Semiconductors", 5, 3, ["momentum", "ai"]),
                ("PLTR", "Technology", 5, 5, ["momentum", "ai"]),
                ("TSLA", "Consumer Discretionary", 5, 5, ["momentum", "high_beta"]),
                ("COIN", "Crypto", 4, 5, ["momentum", "high_beta"]),
                ("SMCI", "Technology", 4, 5, ["momentum", "servers"]),
                ("ARM", "Semiconductors", 4, 5, ["momentum", "semis"]),
                ("TQQQ", "ETF", 4, 5, ["leveraged_momentum"]),
            ],
            "SWING TRADING": [
                ("AAPL", "Technology", 5, 2, ["swing", "quality"]),
                ("MSFT", "Technology", 5, 2, ["swing", "quality"]),
                ("NVDA", "Semiconductors", 5, 4, ["swing", "momentum"]),
                ("AMZN", "Consumer Discretionary", 5, 3, ["swing", "growth"]),
                ("META", "Communication Services", 5, 3, ["swing", "growth"]),
                ("AVGO", "Semiconductors", 5, 3, ["swing", "quality"]),
                ("JPM", "Financials", 5, 2, ["swing", "quality"]),
                ("XLE", "ETF", 5, 3, ["swing", "energy"]),
            ],
            "BREAKOUTS": [
                ("NVDA", "Semiconductors", 5, 4, ["breakout", "ai"]),
                ("AVGO", "Semiconductors", 5, 3, ["breakout", "ai"]),
                ("PLTR", "Technology", 5, 5, ["breakout", "ai"]),
                ("SMCI", "Technology", 4, 5, ["breakout", "servers"]),
                ("ANET", "Technology", 4, 3, ["breakout", "networking"]),
                ("VRT", "Industrials", 4, 4, ["breakout", "data_centers"]),
                ("LLY", "Healthcare", 5, 3, ["breakout", "pharma"]),
                ("ARM", "Semiconductors", 4, 5, ["breakout", "semis"]),
            ],
            "DEFENSIVE": [
                ("WMT", "Consumer Staples", 5, 2, ["defensive"]),
                ("COST", "Consumer Staples", 5, 2, ["defensive"]),
                ("PG", "Consumer Staples", 5, 2, ["defensive"]),
                ("KO", "Consumer Staples", 5, 2, ["defensive"]),
                ("JNJ", "Healthcare", 5, 2, ["defensive"]),
                ("UNH", "Healthcare", 5, 2, ["defensive"]),
                ("XLV", "ETF", 5, 2, ["healthcare_etf"]),
                ("XLP", "ETF", 5, 2, ["staples_etf"]),
                ("XLU", "ETF", 5, 2, ["utilities_etf"]),
            ],
            "DIVIDEND INCOME": [
                ("SCHD", "Dividend ETF", 5, 2, ["dividend", "quality"]),
                ("VIG", "Dividend ETF", 5, 2, ["dividend_growth"]),
                ("VDY.TO", "Canada Dividend ETF", 4, 2, ["canada", "dividend"]),
                ("CDZ.TO", "Canada Dividend ETF", 4, 2, ["canada", "dividend_growth"]),
                ("ZEB.TO", "Canada Financials ETF", 4, 2, ["canada", "banks"]),
                ("XEI.TO", "Canada Dividend ETF", 4, 2, ["canada", "income"]),
                ("ENB.TO", "Canada Energy", 4, 2, ["canada", "pipeline", "dividend"]),
            ],
            "AI LEADERS": [
                ("NVDA", "Semiconductors", 5, 4, ["ai", "leader"]),
                ("MSFT", "Technology", 5, 2, ["ai", "cloud"]),
                ("AVGO", "Semiconductors", 5, 3, ["ai", "networking"]),
                ("AMD", "Semiconductors", 5, 4, ["ai", "chips"]),
                ("META", "Communication Services", 5, 3, ["ai"]),
                ("GOOGL", "Communication Services", 5, 2, ["ai"]),
                ("AMZN", "Consumer Discretionary", 5, 3, ["ai", "cloud"]),
                ("ORCL", "Technology", 4, 3, ["ai", "cloud"]),
                ("ANET", "Technology", 4, 3, ["ai", "networking"]),
                ("VRT", "Industrials", 4, 4, ["ai", "data_centers"]),
            ],
            "EARNINGS WATCH": [
                ("NVDA", "Semiconductors", 5, 4, ["earnings_watch", "ai"]),
                ("AAPL", "Technology", 5, 2, ["earnings_watch"]),
                ("MSFT", "Technology", 5, 2, ["earnings_watch"]),
                ("AMZN", "Consumer Discretionary", 5, 3, ["earnings_watch"]),
                ("META", "Communication Services", 5, 3, ["earnings_watch"]),
                ("GOOGL", "Communication Services", 5, 2, ["earnings_watch"]),
                ("TSLA", "Consumer Discretionary", 5, 5, ["earnings_watch", "high_beta"]),
                ("JPM", "Financials", 5, 2, ["earnings_watch"]),
                ("LLY", "Healthcare", 5, 3, ["earnings_watch"]),
                ("AVGO", "Semiconductors", 5, 3, ["earnings_watch"]),
            ],
            "MAG 7": [
                ("AAPL", "Technology", 5, 2, ["mega_cap", "quality_growth"]),
                ("MSFT", "Technology", 5, 2, ["mega_cap", "quality_growth", "ai"]),
                ("NVDA", "Semiconductors", 5, 4, ["ai", "momentum"]),
                ("AMZN", "Consumer Discretionary", 5, 3, ["mega_cap", "growth"]),
                ("META", "Communication Services", 5, 3, ["mega_cap", "ai"]),
                ("GOOGL", "Communication Services", 5, 2, ["mega_cap", "ai"]),
                ("TSLA", "Consumer Discretionary", 5, 5, ["high_beta", "momentum"]),
            ],
            "SEMICONDUCTORS": [
                ("NVDA", "Semiconductors", 5, 4, ["ai", "momentum"]),
                ("AMD", "Semiconductors", 5, 4, ["ai", "high_beta"]),
                ("AVGO", "Semiconductors", 5, 3, ["ai", "quality_growth"]),
                ("ARM", "Semiconductors", 4, 5, ["ai", "high_beta"]),
                ("ASML", "Semiconductors", 4, 3, ["semis", "equipment"]),
                ("LRCX", "Semiconductors", 4, 4, ["semis", "equipment"]),
                ("AMAT", "Semiconductors", 4, 3, ["semis", "equipment"]),
                ("MU", "Semiconductors", 5, 4, ["memory", "cyclical"]),
                ("TSM", "Semiconductors", 5, 3, ["foundry", "ai"]),
                ("SMH", "ETF", 5, 3, ["semiconductor_etf"]),
            ],
            "AI & DATA CENTERS": [
                ("NVDA", "Semiconductors", 5, 4, ["ai", "data_centers"]),
                ("AMD", "Semiconductors", 5, 4, ["ai", "data_centers"]),
                ("AVGO", "Semiconductors", 5, 3, ["ai", "networking"]),
                ("SMCI", "Technology", 4, 5, ["servers", "high_beta"]),
                ("VRT", "Industrials", 4, 4, ["data_centers", "power"]),
                ("ANET", "Technology", 4, 3, ["networking", "data_centers"]),
                ("DELL", "Technology", 4, 3, ["servers", "ai"]),
                ("ORCL", "Technology", 4, 3, ["cloud", "ai"]),
                ("TSM", "Semiconductors", 5, 3, ["foundry", "ai"]),
            ],
            "FINANCIALS": [
                ("JPM", "Financials", 5, 2, ["banks", "quality"]),
                ("BAC", "Financials", 5, 2, ["banks"]),
                ("WFC", "Financials", 5, 2, ["banks"]),
                ("GS", "Financials", 5, 3, ["investment_banking"]),
                ("MS", "Financials", 5, 3, ["investment_banking"]),
                ("BX", "Financials", 4, 3, ["alternatives"]),
                ("XLF", "ETF", 5, 2, ["financials_etf"]),
            ],
            "ENERGY": [
                ("XOM", "Energy", 5, 2, ["oil_major"]),
                ("CVX", "Energy", 5, 2, ["oil_major"]),
                ("COP", "Energy", 4, 3, ["e_and_p"]),
                ("OXY", "Energy", 4, 4, ["e_and_p"]),
                ("SLB", "Energy", 4, 4, ["oil_services"]),
                ("HAL", "Energy", 4, 4, ["oil_services"]),
                ("XLE", "ETF", 5, 3, ["energy_etf"]),
            ],
            "OIL PULSE": [
                ("USO", "Oil", 5, 4, ["oil_etf", "wti"]),
                ("BNO", "Oil", 4, 4, ["oil_etf", "brent"]),
                ("XLE", "Energy", 5, 3, ["energy_etf"]),
                ("XOM", "Energy", 5, 2, ["oil_major"]),
                ("CVX", "Energy", 5, 2, ["oil_major"]),
                ("COP", "Energy", 4, 3, ["e_and_p"]),
                ("OXY", "Energy", 4, 4, ["e_and_p"]),
                ("SLB", "Energy", 4, 4, ["oil_services"]),
                ("HAL", "Energy", 4, 4, ["oil_services"]),
            ],
            "GOLD PULSE": [
                ("GLD", "Gold", 5, 2, ["gold_etf"]),
                ("IAU", "Gold", 5, 2, ["gold_etf"]),
                ("GDX", "Gold Miners", 5, 4, ["miners"]),
                ("GDXJ", "Gold Miners", 4, 5, ["junior_miners"]),
                ("NEM", "Gold Miners", 4, 4, ["miner"]),
                ("AEM", "Gold Miners", 4, 4, ["miner"]),
                ("WPM", "Gold Miners", 4, 3, ["streamer"]),
            ],
            "CRYPTO PULSE": [
                ("IBIT", "Crypto ETF", 5, 5, ["bitcoin_etf"]),
                ("FBTC", "Crypto ETF", 5, 5, ["bitcoin_etf"]),
                ("ETHE", "Crypto ETF", 4, 5, ["ethereum_etf"]),
                ("COIN", "Crypto", 4, 5, ["exchange", "high_beta"]),
                ("MSTR", "Crypto", 4, 5, ["bitcoin_proxy", "high_beta"]),
                ("MARA", "Crypto Miners", 4, 5, ["miner", "high_beta"]),
                ("RIOT", "Crypto Miners", 4, 5, ["miner", "high_beta"]),
            ],
            "FOREX PULSE": [
                ("EURUSD=X", "Major FX Pair", 5, 3, ["forex", "eur", "usd"], "EUR/USD"),
                ("GBPUSD=X", "Major FX Pair", 5, 3, ["forex", "gbp", "usd"], "GBP/USD"),
                ("USDJPY=X", "Major FX Pair", 5, 3, ["forex", "usd", "jpy"], "USD/JPY"),
                ("USDCHF=X", "Major FX Pair", 4, 3, ["forex", "usd", "chf"], "USD/CHF"),
                ("AUDUSD=X", "Major FX Pair", 4, 3, ["forex", "aud", "usd"], "AUD/USD"),
                ("NZDUSD=X", "Major FX Pair", 4, 3, ["forex", "nzd", "usd"], "NZD/USD"),
                ("USDCAD=X", "Major FX Pair", 4, 3, ["forex", "usd", "cad"], "USD/CAD"),
                ("EURJPY=X", "FX Cross Pair", 4, 4, ["forex", "eur", "jpy"], "EUR/JPY"),
                ("EURGBP=X", "FX Cross Pair", 4, 3, ["forex", "eur", "gbp"], "EUR/GBP"),
                ("GBPJPY=X", "FX Cross Pair", 4, 4, ["forex", "gbp", "jpy"], "GBP/JPY"),
                ("AUDJPY=X", "FX Cross Pair", 4, 4, ["forex", "aud", "jpy"], "AUD/JPY"),
                ("CADJPY=X", "FX Cross Pair", 4, 4, ["forex", "cad", "jpy"], "CAD/JPY"),
            ],
            "CURRENCY ETFs": [
                ("UUP", "Currency ETF", 4, 2, ["usd", "dollar_etf"]),
                ("FXE", "Currency ETF", 3, 2, ["eur", "euro_etf"]),
                ("FXY", "Currency ETF", 3, 3, ["jpy", "yen_etf"]),
                ("FXB", "Currency ETF", 3, 2, ["gbp", "pound_etf"]),
                ("FXC", "Currency ETF", 3, 2, ["cad", "canadian_dollar_etf"]),
                ("CYB", "Currency ETF", 3, 3, ["cny", "yuan_etf"]),
            ],
            "HEALTHCARE": [
                ("LLY", "Healthcare", 5, 3, ["pharma", "momentum"]),
                ("NVO", "Healthcare", 4, 3, ["pharma", "glp1"]),
                ("UNH", "Healthcare", 5, 2, ["managed_care"]),
                ("JNJ", "Healthcare", 5, 2, ["defensive"]),
                ("ABBV", "Healthcare", 5, 2, ["pharma"]),
                ("ISRG", "Healthcare", 4, 3, ["medtech"]),
                ("XLV", "ETF", 5, 2, ["healthcare_etf"]),
            ],
            "INDUSTRIALS": [
                ("CAT", "Industrials", 5, 3, ["machinery"]),
                ("DE", "Industrials", 4, 3, ["machinery"]),
                ("GE", "Industrials", 5, 3, ["aerospace"]),
                ("HON", "Industrials", 4, 2, ["industrial_quality"]),
                ("UNP", "Industrials", 4, 2, ["rails"]),
                ("ETN", "Industrials", 4, 3, ["electrification"]),
                ("XLI", "ETF", 5, 2, ["industrials_etf"]),
            ],
            "CANADA": [
                ("RY.TO", "Canada Financials", 4, 2, ["canada", "bank"]),
                ("TD.TO", "Canada Financials", 4, 2, ["canada", "bank"]),
                ("BNS.TO", "Canada Financials", 4, 2, ["canada", "bank"]),
                ("ENB.TO", "Canada Energy", 4, 2, ["canada", "pipeline", "dividend"]),
                ("CNQ.TO", "Canada Energy", 4, 3, ["canada", "oil"]),
                ("SU.TO", "Canada Energy", 4, 3, ["canada", "oil"]),
                ("SHOP.TO", "Canada Technology", 4, 4, ["canada", "growth"]),
                ("CNR.TO", "Canada Industrials", 4, 2, ["canada", "rail"]),
            ],
            "DIVIDENDS": [
                ("SCHD", "Dividend ETF", 5, 2, ["dividend", "quality"]),
                ("VIG", "Dividend ETF", 5, 2, ["dividend_growth"]),
                ("VDY.TO", "Canada Dividend ETF", 4, 2, ["canada", "dividend"]),
                ("CDZ.TO", "Canada Dividend ETF", 4, 2, ["canada", "dividend_growth"]),
                ("ZEB.TO", "Canada Financials ETF", 4, 2, ["canada", "banks"]),
                ("XEI.TO", "Canada Dividend ETF", 4, 2, ["canada", "income"]),
            ],
            "ETF MOMENTUM": [
                ("SPY", "ETF", 5, 2, ["benchmark"]),
                ("QQQ", "ETF", 5, 3, ["growth"]),
                ("SMH", "ETF", 5, 3, ["semiconductors"]),
                ("XLK", "ETF", 5, 2, ["technology"]),
                ("XLF", "ETF", 5, 2, ["financials"]),
                ("XLE", "ETF", 5, 3, ["energy"]),
                ("XLV", "ETF", 5, 2, ["healthcare"]),
                ("IWM", "ETF", 4, 3, ["small_caps"]),
            ],
            "HIGH BETA": [
                ("TSLA", "Consumer Discretionary", 5, 5, ["high_beta"]),
                ("COIN", "Crypto", 4, 5, ["high_beta"]),
                ("MSTR", "Crypto", 4, 5, ["high_beta"]),
                ("PLTR", "Technology", 5, 5, ["ai", "high_beta"]),
                ("SMCI", "Technology", 4, 5, ["ai", "high_beta"]),
                ("ARM", "Semiconductors", 4, 5, ["high_beta"]),
                ("TQQQ", "ETF", 4, 5, ["leveraged_momentum"]),
            ],
        }

        rows = presets.get(mode, [])

        universe: Dict[str, Dict[str, Any]] = {}

        for row in rows:
            if len(row) == 6:
                symbol, sector, liquidity, volatility, regime, display_symbol = row
            else:
                symbol, sector, liquidity, volatility, regime = row
                display_symbol = symbol

            symbol = str(symbol).upper().strip()

            universe[symbol] = {
                "sector": sector,
                "liquidity": liquidity,
                "volatility": volatility,
                "regime": regime,
                "data_symbol": symbol,
                "display_symbol": display_symbol,
            }

        return universe

    # =====================================================
    # UNIVERSE SELECTION STATE
    # =====================================================

    universe_options = [
        "JFBP",
        "FALLBACK",

        # Market index universe
        "INDEXES",

        # Futures universes
        "INDEX FUTURES",
        "COMMODITY FUTURES",
        "FX FUTURES",
        "RATES FUTURES",
        "FUTURES DASHBOARD",

        # Trader presets
        "MOMENTUM",
        "SWING TRADING",
        "BREAKOUTS",
        "DEFENSIVE",
        "DIVIDEND INCOME",
        "AI LEADERS",
        "CANADA",
        "EARNINGS WATCH",

        # Sector and theme universes
        "MAG 7",
        "SEMICONDUCTORS",
        "AI & DATA CENTERS",
        "FINANCIALS",
        "ENERGY",
        "HEALTHCARE",
        "INDUSTRIALS",

        # Pulse universes
        "OIL PULSE",
        "GOLD PULSE",
        "CRYPTO PULSE",
        "FOREX PULSE",
        "CURRENCY ETFs",

        # Portfolio and tactical universes
        "DIVIDENDS",
        "ETF MOMENTUM",
        "HIGH BETA",

        "CUSTOM BATCH",
    ]

    universe_mode = st.session_state.get(
        "scanner_universe_mode",
        "JFBP",
    )

    if universe_mode not in universe_options:
        universe_mode = "JFBP"
        st.session_state["scanner_universe_mode"] = universe_mode

    if universe_mode == "CUSTOM BATCH":

        active_universe = build_custom_batch_universe(
            st.session_state.get(
                "scanner_custom_batch_symbols",
                "",
            )
        )

    elif universe_mode == "FALLBACK":

        active_universe = fallback_universe()

    elif universe_mode == "JFBP":

        active_universe = (
            JFBP_UNIVERSE
            if isinstance(JFBP_UNIVERSE, dict)
            and JFBP_UNIVERSE
            else fallback_universe()
        )

    else:

        active_universe = scanner_preset_universe(universe_mode)

        if not active_universe:
            active_universe = fallback_universe()

    st.session_state["universe"] = active_universe

    # =====================================================
    # LOCAL HELPERS
    # =====================================================

    def now():
        return datetime.now(timezone.utc).isoformat()

    def clear_scanner_warning():
        st.session_state["scanner_last_error"] = ""

    def safe_snapshot(obj):
        if obj and hasattr(obj, "snapshot"):
            try:
                snap = obj.snapshot()
                return snap if isinstance(snap, dict) else {}
            except Exception as exc:
                st.session_state["scanner_last_error"] = f"snapshot failed: {exc}"
                return {}
        return {}

    def normalize_action(value: Any) -> str:
        action = str(value or "").upper().strip()

        action_map = {
            "LONG": "BUY",
            "BUY_LONG": "BUY",
            "ENTER_LONG": "BUY",
            "OPEN_LONG": "BUY",
            "BULLISH": "BUY",

            "SHORT": "SELL",
            "SELL_SHORT": "SELL",
            "ENTER_SHORT": "SELL",
            "OPEN_SHORT": "SELL",
            "BEARISH": "SELL",

            "NO TRADE": "HOLD",
            "NO_TRADE": "HOLD",
            "NONE": "HOLD",
            "FLAT": "HOLD",
            "NEUTRAL": "HOLD",
            "": "HOLD",
        }

        return action_map.get(action, action)

    def safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def safe_qty(value: Any, default: float = 1.0) -> float:
        qty = safe_float(value, default)
        if qty <= 0:
            return default
        return abs(qty)

    def calculate_equal_weight_qty(
        price: Any,
        action: str = "BUY",
        existing_qty: float = 0.0,
    ) -> float:
        """
        Target-weight sizing.

        BUY:
        - Buy only the delta needed to reach the target position value.
        - If already at or above target, return 0.

        SELL:
        - Sell the existing long position only.
        """

        price = safe_float(price, 0.0)
        action = normalize_action(action)
        existing_qty = safe_float(existing_qty, 0.0)

        if price <= 0:
            return 0.0

        current_position_value = max(0.0, existing_qty * price)

        if action == "SELL":
            return float(max(0.0, existing_qty))

        if action != "BUY":
            return 0.0

        delta_value = scanner_target_position_value() - current_position_value

        if delta_value <= 0:
            return 0.0

        qty = floor(delta_value / price)

        return float(max(0.0, qty))

    def apply_equal_weight_position_sizing(
        row: Dict[str, Any],
        existing_qty: float = 0.0,
    ) -> Dict[str, Any]:
        row = row if isinstance(row, dict) else {}

        action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        price = safe_float(row.get("price"), 0.0)
        existing_qty = safe_float(existing_qty, 0.0)

        current_position_value = max(0.0, existing_qty * price)
        delta_to_target_value = max(
            0.0,
            scanner_target_position_value() - current_position_value,
        )

        sized_qty = calculate_equal_weight_qty(
            price=price,
            action=action,
            existing_qty=existing_qty,
        )

        sizing_status = "SIZED_TO_TARGET"

        if action == "BUY" and sized_qty <= 0:
            sizing_status = "AT_OR_ABOVE_TARGET"
        elif action == "SELL":
            sizing_status = "SELL_EXISTING_LONG_ONLY"
        elif action not in ("BUY", "SELL"):
            sizing_status = "NO_TRADE_NO_SIZE"

        return {
            **row,
            "qty": sized_qty,
            "sizing_model": "TARGET_WEIGHT_5PCT_ACCOUNT_EQUITY",
            "sizing_status": sizing_status,
            "sizing_portfolio_value": scanner_account_equity(),
            "sizing_target_pct": SCANNER_TARGET_POSITION_PCT,
            "sizing_target_value": scanner_target_position_value(),
            "sizing_existing_qty": existing_qty,
            "sizing_current_value": round(current_position_value, 4),
            "sizing_delta_value": round(delta_to_target_value, 4),
        }

    def first_session_value(keys: List[str], default: Any = None) -> Any:
        for key in keys:
            if key in st.session_state:
                value = st.session_state.get(key)
                if value is not None:
                    return value
        return default

    def open_research_stock_from_scanner(symbol: str) -> None:
        """Handoff Scanner symbol to Research Stock and trigger app sidebar navigation."""

        symbol = str(symbol or "").upper().strip()

        if not symbol:
            st.warning("Select a symbol before opening Research Stock.")
            return

        # Ticker handoff keys used by different Research Stock builds.
        # Keep this broad because older Research Stock builds used different
        # session-state names for the active ticker.
        for key in (
            "research_ticker",
            "research_ticker_input",
            "research_symbol",
            "research_symbol_input",
            "selected_research_ticker",
            "research_stock_ticker",
            "research_stock_symbol",
            "research_stock_selected_symbol",
            "research_prefill_symbol",
            "research_requested_symbol",
            "selected_stock",
            "selected_symbol",
            "ticker",
            "ticker_input",
            "symbol_input",
        ):
            st.session_state[key] = symbol

        st.session_state["research_last_analyze"] = True
        st.session_state["research_autorun"] = True
        st.session_state["scanner_last_status"] = (
            f"SENT_{symbol}_TO_RESEARCH_STOCK"
        )

        # Router handoff keys used by app-level sidebar/router builds.
        # The main JFBP router uses jfbp_main_navigation; keep the aliases
        # for backward compatibility with older app.py builds.
        for key in (
            "jfbp_main_navigation",
            "jfbp_active_page",
            "active_page",
            "current_page",
            "selected_page",
            "selected_sidebar_page",
            "nav_page",
            "sidebar_page",
            "app_page",
            "page",
            "menu",
            "navigation",
        ):
            st.session_state[key] = "Research Stock"

        # Do not call st.switch_page here. In this app it can open a blank
        # Streamlit route because Research Stock is loaded by the custom router.
        st.session_state["scanner_click_research_stock_nav"] = True
        st.session_state["scanner_click_research_stock_symbol"] = symbol
        st.rerun()

    def render_research_stock_autonav() -> None:
        """Best-effort browser click of the existing sidebar Research Stock nav item."""

        if not st.session_state.get("scanner_click_research_stock_nav", False):
            return

        symbol = str(
            st.session_state.get("scanner_click_research_stock_symbol", "")
            or ""
        ).upper().strip()

        st.session_state["scanner_click_research_stock_nav"] = False

        st.components.v1.html(
            f"""
            <script>
            const targetText = "Research Stock";
            const symbol = {symbol!r};

            function clickResearchStock() {{
                const doc = window.parent.document;
                const candidates = Array.from(
                    doc.querySelectorAll('button, a, [role="button"], [data-testid="stSidebar"] *')
                );

                const target = candidates.find(el => {{
                    const text = (el.innerText || el.textContent || '').trim();
                    return text === targetText || text.includes(targetText);
                }});

                if (target) {{
                    target.click();
                }}
            }}

            setTimeout(clickResearchStock, 150);
            setTimeout(clickResearchStock, 450);
            setTimeout(clickResearchStock, 900);
            </script>
            """,
            height=0,
        )

        st.success(
            f"{symbol or 'Selected symbol'} is loaded for Research Stock. "
            "Opening Research Stock..."
        )


    # =====================================================
    # MULTI-ASSET SIGNAL BUS v1.0
    # =====================================================

    def multi_asset_signal_bus() -> Dict[str, Any]:
        bus = st.session_state.get("multi_asset_signal_bus", {})
        return bus if isinstance(bus, dict) else {}

    def infer_signal_asset_class(row: Dict[str, Any]) -> str:
        row = row if isinstance(row, dict) else {}
        symbol = str(row.get("symbol") or "").upper().strip()
        sector = str(row.get("sector") or "").upper().strip()
        regime = str(row.get("regime") or "").upper().strip()
        combined = f"{sector} {regime} {symbol}"

        if symbol.endswith("=X") or "FOREX" in combined or "FX " in combined or "CURRENCY" in combined:
            return "forex"

        if symbol.endswith("-USD") or symbol in {"IBIT", "FBTC", "ETHE", "COIN", "MSTR", "MARA", "RIOT"} or "CRYPTO" in combined or "BITCOIN" in combined or "ETHEREUM" in combined:
            return "crypto"

        if symbol in {"GC=F", "SI=F", "GLD", "IAU", "GDX", "GDXJ", "NEM", "GOLD", "AEM", "FNV", "WPM", "SLV", "SIL"} or "GOLD" in combined or "MINER" in combined or "SILVER" in combined:
            return "gold"

        if symbol in {"CL=F", "BZ=F", "USO", "BNO", "XLE", "XOP", "OIH", "XOM", "CVX", "COP", "EOG", "OXY", "SLB", "HAL", "BKR", "MPC", "PSX", "VLO"} or "OIL" in combined or "ENERGY" in combined or "CRUDE" in combined:
            return "oil"

        return "stocks"

    def pulse_bus_row(asset_class: str) -> Dict[str, Any]:
        asset_class = str(asset_class or "").lower().strip()
        bus = multi_asset_signal_bus()

        if asset_class in bus and isinstance(bus.get(asset_class), dict):
            return bus.get(asset_class, {})

        # Backward-compatible fallback for existing Pulse session exports.
        if asset_class in ("crypto", "forex", "gold", "oil"):
            allowed_key = "buy_allowed" if asset_class == "crypto" else "trade_allowed"
            return {
                "asset_class": asset_class,
                "regime": st.session_state.get(f"{asset_class}_pulse_regime", "UNKNOWN"),
                "stress_score": safe_float(st.session_state.get(f"{asset_class}_pulse_stress_score"), 0.0),
                "stress_label": st.session_state.get(f"{asset_class}_pulse_stress_label", ""),
                "breadth_score": safe_float(st.session_state.get(f"{asset_class}_pulse_breadth_score"), 0.0),
                "breadth_state": st.session_state.get(f"{asset_class}_pulse_breadth_state", ""),
                "trade_allowed": bool(st.session_state.get(f"{asset_class}_pulse_{allowed_key}", True)),
                "execution_multiplier": safe_float(st.session_state.get(f"{asset_class}_pulse_execution_multiplier"), 1.0),
                "market_cycle": st.session_state.get(f"{asset_class}_pulse_market_cycle", ""),
                "source": f"{asset_class}_pulse_legacy_session_exports",
            }

        return {}

    def apply_multi_asset_signal_bus_overlay(row: Dict[str, Any]) -> Dict[str, Any]:
        row = row if isinstance(row, dict) else {}
        asset_class = infer_signal_asset_class(row)
        bus_row = pulse_bus_row(asset_class)

        if not bus_row:
            return {
                **row,
                "pulse_asset_class": asset_class,
                "pulse_overlay": "NO_PULSE_BUS_DATA",
            }

        scanner_action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        qty = safe_float(row.get("qty"), 0.0)
        multiplier = safe_float(bus_row.get("execution_multiplier"), 1.0)
        stress_score = safe_float(bus_row.get("stress_score"), 0.0)
        trade_allowed = bool(bus_row.get("trade_allowed", True))
        regime = str(bus_row.get("regime") or "UNKNOWN")
        best_symbol = str(bus_row.get("best_symbol") or "").upper().strip()

        overlay = "PULSE_MONITOR_ONLY"

        if asset_class in ("crypto", "forex", "gold", "oil"):
            if scanner_action == "BUY" and (not trade_allowed or stress_score >= 70):
                scanner_action = "HOLD"
                qty = 0.0
                overlay = f"{asset_class.upper()}_PULSE_BUY_BLOCKED"
            elif scanner_action == "BUY":
                qty = round(max(0.0, qty * multiplier), 4)
                overlay = f"{asset_class.upper()}_PULSE_BUY_ALLOWED_{multiplier:.2f}X"
            elif scanner_action == "SELL":
                overlay = f"{asset_class.upper()}_PULSE_SELL_ALLOWED_RISK_REDUCTION"
            else:
                scanner_action = "HOLD"
                qty = 0.0
                overlay = f"{asset_class.upper()}_PULSE_HOLD"

        return {
            **row,
            "scanner_action": scanner_action,
            "action": scanner_action,
            "side": scanner_action,
            "qty": qty,
            "pulse_asset_class": asset_class,
            "pulse_regime": regime,
            "pulse_stress_score": stress_score,
            "pulse_breadth_score": safe_float(bus_row.get("breadth_score"), 0.0),
            "pulse_trade_allowed": trade_allowed,
            "pulse_execution_multiplier": multiplier,
            "pulse_market_cycle": bus_row.get("market_cycle"),
            "pulse_best_symbol": best_symbol,
            "pulse_overlay": overlay,
        }

    def market_reaction_context() -> Dict[str, Any]:
        raw_score = first_session_value(
            [
                "market_reaction_score",
                "reaction_score",
                "market_score",
                "market_event_score",
            ],
            None,
        )

        raw_confidence = first_session_value(
            [
                "market_reaction_confidence",
                "risk_confidence",
                "event_confidence",
            ],
            None,
        )

        raw_event = first_session_value(
            [
                "market_reaction_event",
                "market_event",
                "event_type",
                "market_regime",
                "reaction_regime",
            ],
            "",
        )

        raw_playbook = first_session_value(
            [
                "market_reaction_playbook",
                "playbook",
                "market_playbook",
            ],
            "",
        )

        score = safe_float(raw_score, 0.0)
        confidence = safe_float(raw_confidence, 0.0)

        event = str(raw_event or "").upper().strip()
        playbook = str(raw_playbook or "").upper().strip()

        risk_off_terms = [
            "RISK OFF",
            "RISK-OFF",
            "INSTITUTIONAL RISK OFF",
            "PANIC",
            "LIQUIDATION",
            "CRASH",
            "SELL-OFF",
            "SEVERE STRESS",
        ]

        risk_on_terms = [
            "RISK ON",
            "RISK-ON",
            "EXPANSION",
            "ACCUMULATION",
            "BULLISH",
        ]

        combined = f"{event} {playbook}"

        risk_off = any(term in combined for term in risk_off_terms)
        risk_on = any(term in combined for term in risk_on_terms)

        if not risk_off and score >= 85 and confidence >= 70:
            risk_off = True

        if risk_off:
            execution_multiplier = 0.50
            buy_allowed = False
            sell_allowed = True
            regime_label = "RISK_OFF"
        elif risk_on:
            execution_multiplier = 1.00
            buy_allowed = True
            sell_allowed = True
            regime_label = "RISK_ON"
        else:
            execution_multiplier = 1.00
            buy_allowed = True
            sell_allowed = True
            regime_label = "NEUTRAL"

        return {
            "score": score,
            "confidence": confidence,
            "event": raw_event or "",
            "playbook": raw_playbook or "",
            "risk_off": risk_off,
            "risk_on": risk_on,
            "regime_label": regime_label,
            "execution_multiplier": execution_multiplier,
            "buy_allowed": buy_allowed,
            "sell_allowed": sell_allowed,
        }

    def economic_calendar_context() -> Dict[str, Any]:
        """
        Economic calendar risk context.

        Current v1 source uses sample/manual events from engines.economic_calendar.
        Enforcement is OFF by default so sample/demo events cannot silently block
        scanner trades unless the user explicitly enables the overlay.
        """

        try:
            if (
                analyze_economic_calendar is None
                or get_calendar_events is None
            ):
                return {
                    "score": 0,
                    "label": "NONE",
                    "highest_event": "",
                    "source": "UNAVAILABLE",
                    "enforcement_enabled": False,
                }

            result = analyze_economic_calendar(
                get_calendar_events()
            )

            highest_event = result.get(
                "highest_risk_event",
            )

            event_name = ""

            if isinstance(highest_event, dict):
                event_name = str(
                    highest_event.get("name", "") or ""
                )

            score = int(
                safe_float(
                    result.get("economic_risk_score", 0),
                    0.0,
                )
            )

            label = str(
                result.get(
                    "economic_risk_label",
                    "NONE",
                )
                or "NONE"
            ).upper().strip()

            source = str(
                result.get(
                    "source",
                    result.get("calendar_source", "UNKNOWN"),
                )
                or "UNKNOWN"
            ).upper().strip()

            return {
                "score": score,
                "label": label,
                "highest_event": event_name,
                "source": source,
                "enforcement_enabled": bool(
                    st.session_state.get(
                        "scanner_economic_enforcement_enabled",
                        False,
                    )
                ),
            }

        except Exception as exc:
            st.session_state["scanner_last_error"] = (
                f"economic calendar context failed: {exc}"
            )

            return {
                "score": 0,
                "label": "NONE",
                "highest_event": "",
                "source": "ERROR",
                "enforcement_enabled": False,
            }

    def apply_economic_calendar_overlay(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optional economic-event risk overlay.

        Default behavior:
        - Monitor-only.
        - Adds economic risk fields to each scanner row.
        - Does not block or resize trades unless enforcement is enabled.

        Enforcement behavior:
        - EXTREME/HIGH: blocks new BUY signals.
        - MEDIUM: reduces BUY quantity by 25%.
        - SELL signals remain allowed because they may reduce risk.
        """

        row = row if isinstance(row, dict) else {}
        ctx = economic_calendar_context()

        scanner_action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        qty = safe_float(row.get("qty"), 0.0)
        overlay_reason = "ECONOMIC_CALENDAR_MONITOR_ONLY"

        if ctx["enforcement_enabled"]:

            if scanner_action == "BUY":

                if ctx["score"] >= 60:
                    scanner_action = "HOLD"
                    qty = 0.0
                    overlay_reason = (
                        "ECONOMIC_CALENDAR_HIGH_RISK_BUY_BLOCKED"
                    )

                elif ctx["score"] >= 35:
                    qty = round(qty * 0.75, 4)
                    overlay_reason = (
                        "ECONOMIC_CALENDAR_MEDIUM_RISK_SIZE_REDUCED"
                    )

                else:
                    overlay_reason = (
                        "ECONOMIC_CALENDAR_LOW_RISK_BUY_ALLOWED"
                    )

            elif scanner_action == "SELL":
                overlay_reason = (
                    "ECONOMIC_CALENDAR_SELL_ALLOWED_RISK_REDUCTION"
                )

            else:
                scanner_action = "HOLD"
                qty = 0.0
                overlay_reason = "ECONOMIC_CALENDAR_HOLD"

        return {
            **row,
            "scanner_action": scanner_action,
            "action": scanner_action,
            "side": scanner_action,
            "qty": qty,
            "economic_risk_score": ctx["score"],
            "economic_risk_label": ctx["label"],
            "economic_risk_highest_event": ctx["highest_event"],
            "economic_risk_source": ctx["source"],
            "economic_enforcement_enabled": ctx["enforcement_enabled"],
            "economic_calendar_overlay": overlay_reason,
        }

    def earnings_universe_context() -> Dict[str, Any]:
        symbols = list(active_universe.keys()) if isinstance(active_universe, dict) else []
        symbols = [str(symbol or "").upper().strip() for symbol in symbols]
        symbols = [symbol for symbol in symbols if symbol]

        # Keep scanner page responsive. Full earnings page can scan more symbols.
        symbols = symbols[:25]

        # Forex pairs and futures do not have corporate earnings.
        if symbols and all(symbol.endswith("=X") or symbol.endswith("=F") for symbol in symbols):
            return {
                "score": 0,
                "label": "NONE",
                "highest_symbol": "",
                "highest_date": None,
                "highest_days": None,
                "source": "ASSET_CLASS_SKIP",
                "symbol_count": len(symbols),
                "events": [],
                "enforcement_enabled": False,
            }

        try:
            result = cached_universe_earnings_context(tuple(symbols))

            highest_event = result.get("highest_risk_event")
            highest_symbol = ""
            highest_date = None
            highest_days = None

            if isinstance(highest_event, dict):
                highest_symbol = str(highest_event.get("symbol") or "")
                highest_date = highest_event.get("earnings_date")
                highest_days = highest_event.get("days_until")

            score = int(
                safe_float(
                    result.get("earnings_risk_score", 0),
                    0.0,
                )
            )

            label = str(
                result.get(
                    "earnings_risk_label",
                    "NONE",
                )
                or "NONE"
            ).upper().strip()

            return {
                "score": score,
                "label": label,
                "highest_symbol": highest_symbol,
                "highest_date": highest_date,
                "highest_days": highest_days,
                "source": str(result.get("source") or "YFINANCE"),
                "symbol_count": int(
                    safe_float(
                        result.get("symbol_count", len(symbols)),
                        len(symbols),
                    )
                ),
                "events": result.get("events", []),
                "enforcement_enabled": bool(
                    st.session_state.get(
                        "scanner_earnings_enforcement_enabled",
                        False,
                    )
                ),
            }

        except Exception as exc:
            st.session_state["scanner_last_error"] = (
                f"earnings universe context failed: {exc}"
            )

            return {
                "score": 0,
                "label": "NONE",
                "highest_symbol": "",
                "highest_date": None,
                "highest_days": None,
                "source": "ERROR",
                "symbol_count": 0,
                "events": [],
                "enforcement_enabled": False,
            }

    def earnings_symbol_context(symbol: str) -> Dict[str, Any]:
        symbol = str(symbol or "").upper().strip()

        # Forex pairs and futures do not have corporate earnings.
        if symbol.endswith("=X") or symbol.endswith("=F"):
            return {
                "symbol": symbol,
                "earnings_date": None,
                "days_until": None,
                "risk_score": 0,
                "risk_label": "NONE",
                "status": "NOT_APPLICABLE",
                "source": "ASSET_CLASS_SKIP",
                "reason": "Forex/futures symbols do not have earnings events.",
                "enforcement_enabled": False,
            }

        try:
            ctx = cached_symbol_earnings_context(symbol)
            ctx["enforcement_enabled"] = bool(
                st.session_state.get(
                    "scanner_earnings_enforcement_enabled",
                    False,
                )
            )
            return ctx

        except Exception as exc:
            st.session_state["scanner_last_error"] = (
                f"earnings symbol context failed for {symbol}: {exc}"
            )

            return {
                "symbol": symbol,
                "earnings_date": None,
                "days_until": None,
                "risk_score": 0,
                "risk_label": "NONE",
                "status": "ERROR",
                "source": "ERROR",
                "reason": str(exc),
                "enforcement_enabled": False,
            }

    def apply_earnings_risk_overlay(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optional earnings-risk overlay.

        Default behavior:
        - Monitor only.
        - Adds earnings risk fields to each scanner row.
        - Does not block or resize trades unless enforcement is enabled.

        Enforcement behavior:
        - EXTREME: blocks new BUY signals.
        - HIGH: reduces BUY quantity by 50%.
        - MEDIUM: warning only.
        - SELL signals remain allowed because they may reduce risk.
        """

        row = row if isinstance(row, dict) else {}
        symbol = str(row.get("symbol") or "").upper().strip()
        ctx = earnings_symbol_context(symbol)

        scanner_action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        qty = safe_float(row.get("qty"), 0.0)
        overlay_reason = "EARNINGS_RISK_MONITOR_ONLY"

        if ctx.get("enforcement_enabled"):

            if scanner_action == "BUY":

                days_until = ctx.get("days_until")

                try:
                    days_until = int(days_until)
                except Exception:
                    days_until = None

                if days_until is not None:

                    if days_until <= 3:
                        scanner_action = "HOLD"
                        qty = 0.0
                        overlay_reason = "EARNINGS_IMMINENT_BUY_BLOCKED"

                    elif days_until <= 7:
                        qty = max(
                            0.0,
                            round(qty * 0.50, 4),
                        )
                        overlay_reason = "EARNINGS_APPROACHING_SIZE_REDUCED"

                    else:
                        overlay_reason = "EARNINGS_LOW_RISK_BUY_ALLOWED"

                else:
                    overlay_reason = "EARNINGS_DATE_UNKNOWN"

            elif scanner_action == "SELL":
                overlay_reason = "EARNINGS_RISK_SELL_ALLOWED_RISK_REDUCTION"

            else:
                scanner_action = "HOLD"
                qty = 0.0
                overlay_reason = "EARNINGS_RISK_HOLD"

        return {
            **row,
            "scanner_action": scanner_action,
            "action": scanner_action,
            "side": scanner_action,
            "qty": qty,
            "earnings_risk_score": int(ctx.get("risk_score") or 0),
            "earnings_risk_label": ctx.get("risk_label", "NONE"),
            "earnings_date": ctx.get("earnings_date"),
            "earnings_days_until": ctx.get("days_until"),
            "earnings_status": ctx.get("status"),
            "earnings_source": ctx.get("source"),
            "earnings_reason": ctx.get("reason"),
            "earnings_enforcement_enabled": bool(
                ctx.get("enforcement_enabled", False)
            ),
            "earnings_risk_overlay": overlay_reason,
        }

    def apply_market_reaction_overlay(row: Dict[str, Any]) -> Dict[str, Any]:
        row = row if isinstance(row, dict) else {}
        ctx = market_reaction_context()

        scanner_action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        original_qty = safe_qty(row.get("qty"), 1.0)
        adjusted_qty = max(
            1.0,
            round(original_qty * ctx["execution_multiplier"], 4),
        )

        overlay_reason = ""

        if ctx["risk_off"]:

            if scanner_action == "BUY":
                scanner_action = "HOLD"
                adjusted_qty = 0.0
                overlay_reason = "MARKET_REACTION_RISK_OFF_BUY_BLOCKED"

            elif scanner_action == "SELL":
                overlay_reason = "MARKET_REACTION_RISK_OFF_SELL_ALLOWED"

            else:
                scanner_action = "HOLD"
                adjusted_qty = 0.0
                overlay_reason = "MARKET_REACTION_RISK_OFF_MONITOR_ONLY"

        elif ctx["risk_on"]:

            if scanner_action == "BUY":
                overlay_reason = "MARKET_REACTION_RISK_ON_BUY_ALLOWED"

            elif scanner_action == "SELL":
                overlay_reason = "MARKET_REACTION_RISK_ON_SELL_ALLOWED"

            else:
                scanner_action = "HOLD"
                adjusted_qty = 0.0
                overlay_reason = "MARKET_REACTION_RISK_ON_HOLD"

        else:

            if scanner_action in ("BUY", "SELL"):
                overlay_reason = "MARKET_REACTION_NEUTRAL_TRADE_ALLOWED"

            else:
                scanner_action = "HOLD"
                adjusted_qty = 0.0
                overlay_reason = "MARKET_REACTION_NEUTRAL_HOLD"

        return {
            **row,
            "scanner_action": scanner_action,
            "market_reaction_regime": ctx["regime_label"],
            "market_reaction_score": ctx["score"],
            "market_reaction_confidence": ctx["confidence"],
            "market_reaction_event": ctx["event"],
            "market_reaction_playbook": ctx["playbook"],
            "market_reaction_overlay": overlay_reason,
            "qty": adjusted_qty,
        }

    def get_price(symbol: str) -> float:
        symbol = str(symbol or "").upper().strip()

        try:
            if market and hasattr(market, "get_price"):
                price = market.get_price(symbol)
                if price:
                    return float(price)
        except Exception:
            pass

        try:
            if market and hasattr(market, "snapshot"):
                snap = market.snapshot()
                if isinstance(snap, dict):
                    row = snap.get(symbol)
                    price = row.get("price") if isinstance(row, dict) else row
                    if price:
                        return float(price)
        except Exception:
            pass

        return 100.0

    def normalize_meta(symbol: str, meta: Any) -> Dict[str, Any]:
        symbol = str(symbol or "").upper().strip()

        if not isinstance(meta, dict):
            meta = {}

        regime = meta.get("regime", [])

        raw_data_symbol = meta.get("data_symbol")
        raw_data_symbols = meta.get("data_symbols", [])

        if raw_data_symbols is None:
            raw_data_symbols = []

        if isinstance(raw_data_symbols, str):
            raw_data_symbols = [raw_data_symbols]

        if not isinstance(raw_data_symbols, (list, tuple)):
            raw_data_symbols = []

        data_symbols = []

        if raw_data_symbol:
            data_symbols.append(raw_data_symbol)

        for item in raw_data_symbols:
            data_symbols.append(item)

        data_symbols.append(symbol)

        cleaned_data_symbols = []

        for item in data_symbols:
            item = str(item or "").upper().strip()

            if item and item not in cleaned_data_symbols:
                cleaned_data_symbols.append(item)

        data_symbol = cleaned_data_symbols[0] if cleaned_data_symbols else symbol

        return {
            "symbol": symbol,
            "display_symbol": meta.get("display_symbol", symbol),
            "data_symbol": data_symbol,
            "data_symbols": cleaned_data_symbols,
            "sector": meta.get("sector", "Unknown"),
            "liquidity": int(meta.get("liquidity", 3) or 3),
            "volatility": int(meta.get("volatility", 3) or 3),
            "regime": ",".join(regime) if isinstance(regime, list) else str(regime),
        }
    
    # =====================================================
    # RESEARCH MODEL ENGINE
    # =====================================================

    @st.cache_data(ttl=300)
    def load_symbol_data(symbol: str):
        return yf.download(
            symbol,
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

    @st.cache_data(ttl=300)
    def load_benchmark_data():
        return yf.download(
            "SPY",
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

    def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
        frame = frame.copy()

        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = [
                "_".join([str(i) for i in col if i])
                for col in frame.columns
            ]

        return frame

    def find_col(frame: pd.DataFrame, name: str):
        exact = [
            c for c in frame.columns
            if str(c).lower() == name.lower()
        ]

        if exact:
            return exact[0]

        matches = [
            c for c in frame.columns
            if name.lower() in str(c).lower()
        ]

        return matches[0] if matches else None

    def resolve_data_symbols(symbol: str, meta: Dict[str, Any]) -> list:
        candidates = []

        data_symbols = meta.get("data_symbols")

        if isinstance(data_symbols, (list, tuple)):
            candidates.extend(data_symbols)

        data_symbol = meta.get("data_symbol")

        if data_symbol:
            candidates.append(data_symbol)

        candidates.append(symbol)

        cleaned = []

        for item in candidates:
            item = str(item or "").upper().strip()

            if item and item not in cleaned:
                cleaned.append(item)

        return cleaned

    def load_first_valid_symbol(
        display_symbol: str,
        meta: Dict[str, Any],
    ):
        attempted_symbols = []
        last_error = None

        for data_symbol in resolve_data_symbols(display_symbol, meta):
            attempted_symbols.append(data_symbol)

            try:
                df = load_symbol_data(data_symbol)

                if df is not None and not df.empty:
                    return data_symbol, df, attempted_symbols

                last_error = "No stock data"

            except Exception as exc:
                last_error = str(exc)

        raise RuntimeError(last_error or "No stock data")

    def research_model_signal(symbol: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        symbol = str(symbol or "").upper().strip()
        meta = normalize_meta(symbol, meta)

        data_symbol = meta.get("data_symbol", symbol)
        attempted_symbols = []

        try:
            data_symbol, df, attempted_symbols = load_first_valid_symbol(
                symbol,
                meta,
            )

            benchmark = load_benchmark_data()

            if df is None or df.empty:
                raise RuntimeError("No stock data")

            if benchmark is None or benchmark.empty:
                raise RuntimeError("No benchmark data")

            df = normalize_columns(df)
            benchmark = normalize_columns(benchmark)

            close_col = find_col(df, "Close")
            high_col = find_col(df, "High")
            low_col = find_col(df, "Low")
            open_col = find_col(df, "Open")
            bench_close_col = find_col(benchmark, "Close")

            if close_col is None:
                raise RuntimeError("Missing required close column")

            if bench_close_col is None:
                raise RuntimeError("Missing benchmark close column")

            df["Open"] = pd.to_numeric(
                df[open_col] if open_col else df[close_col],
                errors="coerce",
            )
            df["High"] = pd.to_numeric(
                df[high_col] if high_col else df[close_col],
                errors="coerce",
            )
            df["Low"] = pd.to_numeric(
                df[low_col] if low_col else df[close_col],
                errors="coerce",
            )
            df["Close"] = pd.to_numeric(
                df[close_col],
                errors="coerce",
            )

            benchmark["Benchmark"] = pd.to_numeric(
                benchmark[bench_close_col],
                errors="coerce",
            )

            df = df.sort_index()
            benchmark = benchmark.sort_index()

            df = df[~df.index.duplicated(keep="last")]
            benchmark = benchmark[~benchmark.index.duplicated(keep="last")]

            df = df.join(benchmark[["Benchmark"]], how="left")
            df["Benchmark"] = df["Benchmark"].ffill().bfill()

            df = df.dropna(
                subset=[
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Benchmark",
                ]
            )

            if len(df) < 30:
                raise RuntimeError("Not enough historical data")

            df["MA20"] = df["Close"].rolling(20).mean()

            if len(df) >= 50:
                df["MA50"] = df["Close"].rolling(50).mean()
            else:
                df["MA50"] = df["MA20"]

            df["RS"] = df["Close"] / df["Benchmark"]
            df["RS_MA20"] = df["RS"].rolling(20).mean()
            df["RS_SCORE"] = df["RS"] / df["RS_MA20"]

            prev_close = df["Close"].shift(1)

            tr1 = df["High"] - df["Low"]
            tr2 = (df["High"] - prev_close).abs()
            tr3 = (df["Low"] - prev_close).abs()

            df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df["ATR"] = df["TR"].rolling(14).mean()

            df["20D_HIGH"] = df["High"].rolling(20).max()
            df["20D_LOW"] = df["Low"].rolling(20).min()

            df = df.dropna(
                subset=[
                    "Close",
                    "MA20",
                    "MA50",
                    "RS_SCORE",
                    "ATR",
                    "20D_HIGH",
                    "20D_LOW",
                ]
            )

            if df.empty:
                raise RuntimeError("Not enough clean indicator data")

            if len(df) < 2:
                raise RuntimeError("Not enough clean rows for previous close")

            latest_close = round(float(df["Close"].iloc[-1]), 2)
            previous_close = round(float(df["Close"].iloc[-2]), 2)
            latest_ma20 = round(float(df["MA20"].iloc[-1]), 2)
            latest_ma50 = round(float(df["MA50"].iloc[-1]), 2)
            latest_rs_score = round(float(df["RS_SCORE"].iloc[-1]), 4)
            latest_atr = round(float(df["ATR"].iloc[-1]), 4)
            latest_20d_high = round(float(df["20D_HIGH"].iloc[-1]), 2)
            latest_20d_low = round(float(df["20D_LOW"].iloc[-1]), 2)

            above_ma20 = latest_close > latest_ma20
            above_ma50 = latest_close > latest_ma50
            improving_today = latest_close > previous_close
            strong_rs = latest_rs_score >= 1.05
            near_high = latest_close >= latest_20d_high * 0.98

            weak_rs = latest_rs_score <= 0.97
            below_ma20 = latest_close < latest_ma20
            below_ma50 = latest_close < latest_ma50
            falling_today = latest_close < previous_close

            model_score = 0

            if above_ma20:
                model_score += 1
            if above_ma50:
                model_score += 1
            if improving_today:
                model_score += 1
            if strong_rs:
                model_score += 1
            if near_high:
                model_score += 1

            if (
                above_ma20
                and above_ma50
                and improving_today
                and strong_rs
                and near_high
            ):
                signal = "BUY"
            elif (
                below_ma20
                and below_ma50
                and falling_today
                and weak_rs
            ):
                signal = "SELL"
            else:
                signal = "NO TRADE"

            scanner_action = normalize_action(signal)
            trend = "BULLISH" if above_ma20 and above_ma50 else "BEARISH"

            return {
                "timestamp": now(),
                "symbol": symbol,
                "display_symbol": meta.get("display_symbol", symbol),
                "data_symbol": data_symbol,
                "sector": meta["sector"],
                "liquidity": meta["liquidity"],
                "volatility": meta["volatility"],
                "regime": meta["regime"],
                "signal": signal,
                "scanner_action": scanner_action,
                "action": scanner_action,
                "side": scanner_action,
                "qty": 1,
                "price": latest_close,
                "model_score": model_score,
                "score": model_score,
                "trend": trend,
                "ma20": latest_ma20,
                "ma50": latest_ma50,
                "rs_score": latest_rs_score,
                "atr": latest_atr,
                "support": latest_20d_low,
                "resistance": latest_20d_high,
                "prev_close": previous_close,
                "attempted_symbols": ", ".join(attempted_symbols),
                "source": "research_model_scanner_v35_3",
                "mode": st.session_state.get("mode", "SIM"),
                "reason": None,
            }

        except Exception as exc:
            price = get_price(data_symbol or symbol)

            return {
                "timestamp": now(),
                "symbol": symbol,
                "display_symbol": meta.get("display_symbol", symbol),
                "data_symbol": data_symbol,
                "sector": meta["sector"],
                "liquidity": meta["liquidity"],
                "volatility": meta["volatility"],
                "regime": meta["regime"],
                "signal": "NO TRADE",
                "scanner_action": "HOLD",
                "action": "HOLD",
                "side": "HOLD",
                "qty": 1,
                "price": price,
                "model_score": 0,
                "score": 0,
                "trend": "UNKNOWN",
                "ma20": None,
                "ma50": None,
                "rs_score": None,
                "atr": None,
                "support": None,
                "resistance": None,
                "prev_close": None,
                "attempted_symbols": ", ".join(attempted_symbols),
                "reason": str(exc),
                "source": "research_model_scanner_v35_3_error_safe",
                "mode": st.session_state.get("mode", "SIM"),
            }

    # =====================================================
    # PORTFOLIO / RISK SYNC
    # =====================================================

    def coerce_position_row(symbol: str, row: Any) -> Dict[str, Any]:
        symbol = str(symbol or "").upper().strip()

        if isinstance(row, dict):
            contract = row.get("contract")

            if not symbol and contract is not None:
                symbol = str(
                    getattr(contract, "symbol", "") or ""
                ).upper().strip()

            signed_qty = (
                row.get("signed_qty")
                or row.get("position")
                or row.get("qty")
                or row.get("quantity")
                or row.get("shares")
                or 0
            )

            side = str(row.get("side", "") or "").upper()
            signed_qty = safe_float(signed_qty, 0.0)

            if "signed_qty" not in row and side == "SHORT":
                signed_qty = -abs(signed_qty)

            avg_price = (
                row.get("avg_price")
                or row.get("avg_cost")
                or row.get("avgCost")
                or row.get("average_cost")
                or row.get("averageCost")
                or row.get("price")
                or 0
            )

            last_price = (
                row.get("last_price")
                or row.get("market_price")
                or row.get("marketPrice")
                or row.get("last")
                or row.get("price")
                or 0
            )

            market_value = (
                row.get("position_value")
                or row.get("market_value")
                or row.get("marketValue")
                or 0
            )

            realized_pnl = (
                row.get("realized_pnl")
                or row.get("realized")
                or 0
            )

            unrealized_pnl = (
                row.get("unrealized_pnl")
                or row.get("unrealized")
                or 0
            )

            total_pnl = (
                row.get("total_pnl")
                or row.get("pnl")
                or 0
            )

        else:
            contract = getattr(row, "contract", None)

            if not symbol and contract is not None:
                symbol = str(
                    getattr(contract, "symbol", "") or ""
                ).upper().strip()

            signed_qty = (
                getattr(row, "signed_qty", None)
                or getattr(row, "position", None)
                or getattr(row, "qty", None)
                or getattr(row, "quantity", None)
                or getattr(row, "shares", None)
                or 0
            )

            signed_qty = safe_float(signed_qty, 0.0)

            avg_price = (
                getattr(row, "avg_price", None)
                or getattr(row, "avg_cost", None)
                or getattr(row, "avgCost", None)
                or getattr(row, "average_cost", None)
                or getattr(row, "averageCost", None)
                or 0
            )

            last_price = (
                getattr(row, "last_price", None)
                or getattr(row, "market_price", None)
                or getattr(row, "marketPrice", None)
                or getattr(row, "last", None)
                or 0
            )

            market_value = (
                getattr(row, "position_value", None)
                or getattr(row, "market_value", None)
                or getattr(row, "marketValue", None)
                or 0
            )

            realized_pnl = (
                getattr(row, "realized_pnl", None)
                or getattr(row, "realized", None)
                or 0
            )

            unrealized_pnl = (
                getattr(row, "unrealized_pnl", None)
                or getattr(row, "unrealized", None)
                or 0
            )

            total_pnl = (
                getattr(row, "total_pnl", None)
                or getattr(row, "pnl", None)
                or 0
            )

        avg_price = safe_float(avg_price, 0.0)
        last_price = safe_float(last_price, 0.0)
        market_value = safe_float(market_value, 0.0)
        realized_pnl = safe_float(realized_pnl, 0.0)
        unrealized_pnl = safe_float(unrealized_pnl, 0.0)
        total_pnl = safe_float(total_pnl, 0.0)

        if last_price <= 0 and market_value > 0 and abs(signed_qty) > 0:
            last_price = abs(market_value / signed_qty)

        if last_price <= 0 and avg_price > 0:
            last_price = avg_price

        if last_price <= 0:
            last_price = get_price(symbol)

        position_value = abs(signed_qty) * last_price

        if market_value > 0:
            position_value = abs(market_value)

        if unrealized_pnl == 0.0 and avg_price > 0 and last_price > 0:
            cost_basis = abs(signed_qty) * avg_price

            if signed_qty > 0:
                unrealized_pnl = position_value - cost_basis
            elif signed_qty < 0:
                unrealized_pnl = cost_basis - position_value

        if total_pnl == 0.0:
            total_pnl = realized_pnl + unrealized_pnl

        return {
            "symbol": symbol,
            "side": (
                "LONG"
                if signed_qty > 0
                else "SHORT"
                if signed_qty < 0
                else "FLAT"
            ),
            "qty": abs(signed_qty),
            "signed_qty": signed_qty,
            "avg_price": avg_price,
            "last_price": last_price,
            "position_value": position_value,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "total_pnl": total_pnl,
        }

    def get_portfolio_positions() -> Dict[str, Dict[str, Any]]:
        rows = {}

        live_mode = (
            str(st.session_state.get("mode", "SIM"))
            .upper()
            .strip()
            == "LIVE"
        )

        if live_mode:

            if gateway is None:
                st.session_state["scanner_position_source"] = (
                    "IBKR_GATEWAY_MISSING"
                )
                return rows

            for method_name in (
                "positions_snapshot",
                "get_positions",
                "positions",
                "broker_positions",
                "broker_positions_snapshot",
                "positions_cache",
            ):

                try:
                    if not hasattr(gateway, method_name):
                        continue

                    candidate = getattr(gateway, method_name)

                    if callable(candidate):
                        candidate = candidate()

                    if isinstance(candidate, dict):
                        candidate = list(candidate.values())

                    elif candidate is None:
                        candidate = []

                    for pos in list(candidate):

                        if isinstance(pos, dict):
                            contract = pos.get("contract")

                            symbol = (
                                pos.get("symbol")
                                or pos.get("ticker")
                                or pos.get("contract_symbol")
                                or ""
                            )

                            if not symbol and contract is not None:
                                symbol = getattr(
                                    contract,
                                    "symbol",
                                    "",
                                )

                        else:
                            contract = getattr(
                                pos,
                                "contract",
                                None,
                            )

                            symbol = (
                                getattr(pos, "symbol", "")
                                or getattr(contract, "symbol", "")
                                or ""
                            )

                        symbol = str(symbol or "").upper().strip()

                        if not symbol:
                            continue

                        row = coerce_position_row(symbol, pos)

                        if safe_float(row.get("signed_qty"), 0.0) != 0.0:
                            rows[row["symbol"]] = row

                    if rows:

                        st.session_state["scanner_position_source"] = (
                            f"IBKR_GATEWAY:{method_name}"
                        )

                        return rows

                except Exception as exc:
                    st.session_state["scanner_last_error"] = (
                        f"gateway.{method_name} positions failed: {exc}"
                    )

            st.session_state["scanner_position_source"] = (
                "IBKR_GATEWAY_EMPTY"
            )

            return rows

        if portfolio_engine is None:
            st.session_state["scanner_position_source"] = (
                "PORTFOLIO_ENGINE_MISSING"
            )
            return rows

        try:
            if hasattr(portfolio_engine, "snapshot"):
                snap = portfolio_engine.snapshot()

                if isinstance(snap, dict):
                    for symbol, value in snap.items():
                        row = coerce_position_row(symbol, value)

                        if (
                            abs(row["signed_qty"]) > 1e-9
                            or abs(row["realized_pnl"]) > 1e-9
                        ):
                            rows[row["symbol"]] = row

        except Exception as exc:
            st.session_state["scanner_last_error"] = (
                f"portfolio.snapshot failed: {exc}"
            )

        if rows:
            st.session_state["scanner_position_source"] = (
                "PORTFOLIO_ENGINE:snapshot"
            )
            return rows

        try:
            if hasattr(portfolio_engine, "risk_positions"):
                risk_positions = portfolio_engine.risk_positions()

                if isinstance(risk_positions, dict):
                    for symbol, signed_qty in risk_positions.items():
                        signed_qty = safe_float(signed_qty, 0.0)

                        if abs(signed_qty) <= 1e-9:
                            continue

                        symbol = str(symbol).upper().strip()
                        price = get_price(symbol)

                        rows[symbol] = {
                            "symbol": symbol,
                            "side": (
                                "LONG"
                                if signed_qty > 0
                                else "SHORT"
                            ),
                            "qty": abs(signed_qty),
                            "signed_qty": signed_qty,
                            "avg_price": price,
                            "last_price": price,
                            "position_value": abs(signed_qty) * price,
                            "unrealized_pnl": 0.0,
                            "realized_pnl": 0.0,
                            "total_pnl": 0.0,
                        }

        except Exception as exc:
            st.session_state["scanner_last_error"] = (
                f"portfolio.risk_positions failed: {exc}"
            )

        if rows:
            st.session_state["scanner_position_source"] = (
                "PORTFOLIO_ENGINE:risk_positions"
            )
        else:
            st.session_state["scanner_position_source"] = (
                "PORTFOLIO_ENGINE_EMPTY"
            )

        return rows


    def sync_market_reaction_to_risk_engine():
        try:
            if not risk_engine:
                return False

            if not hasattr(risk_engine, "update_market_reaction"):
                return False

            ctx = market_reaction_context()

            risk_engine.update_market_reaction(
                regime=ctx.get("regime_label", "NEUTRAL"),
                score=ctx.get("score", 0.0),
                confidence=ctx.get("confidence", 0.0),
            )

            return True

        except Exception as exc:
            st.session_state["scanner_last_error"] = (
                f"market reaction risk sync failed: {exc}"
            )
            return False

    def sync_risk():
        try:
            sync_market_reaction_to_risk_engine()

            if portfolio_engine and risk_engine and hasattr(risk_engine, "sync_positions"):
                positions = get_portfolio_positions()
                try:
                    risk_engine.sync_positions(positions, historical=True)
                except TypeError:
                    risk_engine.sync_positions(positions)

                sync_market_reaction_to_risk_engine()
                return True

        except Exception as exc:
            st.session_state["scanner_last_error"] = f"sync_risk failed: {exc}"

        return False


    # =====================================================
    # SCANNER OPPORTUNITY RANKING HELPERS
    # =====================================================

    def leadership_tier_from_percentile(percentile: Any) -> str:
        pct = safe_float(percentile, 0.0)

        if pct >= 90:
            return "ELITE"
        if pct >= 75:
            return "LEADER"
        if pct >= 50:
            return "STRONG"
        if pct >= 25:
            return "AVERAGE"
        return "WEAK"

    def rating_from_score_pct(score_pct: Any) -> str:
        pct = safe_float(score_pct, 0.0)

        if pct >= 90:
            return "A+"
        if pct >= 80:
            return "A"
        if pct >= 70:
            return "A-"
        if pct >= 60:
            return "B"
        if pct >= 50:
            return "C"
        if pct >= 35:
            return "D"
        return "F"

    def sector_leadership_map(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        sector_groups: Dict[str, List[Dict[str, Any]]] = {}

        for row in rows:
            if not isinstance(row, dict):
                continue

            symbol = str(row.get("symbol") or "").upper().strip()
            sector = str(row.get("sector") or "Unknown").strip()
            rs_score = safe_float(row.get("rs_score"), 0.0)

            if not symbol:
                continue

            sector_groups.setdefault(sector, []).append({
                "symbol": symbol,
                "sector": sector,
                "rs_score": rs_score,
                "model_score": safe_float(row.get("model_score"), 0.0),
            })

        leadership: Dict[str, Dict[str, Any]] = {}

        for sector, members in sector_groups.items():
            members = sorted(
                members,
                key=lambda item: (
                    safe_float(item.get("rs_score"), 0.0),
                    safe_float(item.get("model_score"), 0.0),
                ),
                reverse=True,
            )

            count = len(members)
            sector_leader = members[0]["symbol"] if members else ""

            for idx, item in enumerate(members, start=1):
                percentile = 100.0 if count <= 1 else round(
                    ((count - idx) / (count - 1)) * 100.0,
                    1,
                )

                symbol = item["symbol"]

                leadership[symbol] = {
                    "sector_rank": idx,
                    "sector_count": count,
                    "sector_percentile": percentile,
                    "leadership_tier": leadership_tier_from_percentile(percentile),
                    "sector_leader": sector_leader,
                }

        return leadership

    def scanner_trade_recommendation(
        row: Dict[str, Any],
        score_pct: float,
        rating: str,
    ) -> str:
        action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        trend = str(row.get("trend") or "").upper().strip()

        event_risk_label = str(
            row.get("combined_event_risk_label")
            or row.get("earnings_risk_label")
            or "NONE"
        ).upper().strip()

        days_until = row.get("earnings_days_until")

        try:
            days_until = int(days_until)
        except Exception:
            days_until = None

        high_event_risk = (
            event_risk_label in ("HIGH", "EXTREME")
            or (days_until is not None and days_until <= 7)
        )

        if action == "SELL":
            return "SELL"

        if action == "BUY":
            if score_pct >= 80 and not high_event_risk:
                return "STRONG BUY"
            if score_pct >= 60:
                return "WATCH" if high_event_risk else "BUY"
            return "WATCH"

        if trend == "BULLISH" and score_pct >= 50:
            return "WATCH"

        if trend == "BEARISH" and score_pct < 35:
            return "AVOID"

        return "WATCH"

    def apply_scanner_quality_overlay(row: Dict[str, Any]) -> Dict[str, Any]:
        row = row if isinstance(row, dict) else {}
        symbol = str(row.get("symbol") or "").upper().strip()

        leadership = st.session_state.get("scanner_sector_leadership_map", {})
        leadership_row = leadership.get(symbol, {}) if isinstance(leadership, dict) else {}

        if not leadership_row:
            leadership_row = {
                "sector_rank": None,
                "sector_count": None,
                "sector_percentile": 0.0,
                "leadership_tier": "UNKNOWN",
                "sector_leader": "",
            }

        market_ctx = market_reaction_context()
        economic_ctx = economic_calendar_context()
        earnings_ctx = earnings_symbol_context(symbol)

        trend = str(row.get("trend") or "").upper().strip()

        action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        model_score = safe_float(row.get("model_score"), 0.0)
        rs_score = safe_float(row.get("rs_score"), 0.0)
        sector_pct = safe_float(leadership_row.get("sector_percentile"), 0.0)

        earnings_label = str(
            row.get("earnings_risk_label")
            or earnings_ctx.get("risk_label")
            or "NONE"
        ).upper().strip()

        earnings_days = (
            row.get("earnings_days_until")
            if row.get("earnings_days_until") is not None
            else earnings_ctx.get("days_until")
        )

        try:
            earnings_days_int = int(earnings_days)
        except Exception:
            earnings_days_int = None

        economic_label = str(
            row.get("economic_risk_label")
            or economic_ctx.get("label")
            or "NONE"
        ).upper().strip()

        economic_score = int(
            safe_float(
                row.get("economic_risk_score")
                if row.get("economic_risk_score") is not None
                else economic_ctx.get("score", 0),
                0.0,
            )
        )

        market_regime = str(
            row.get("market_reaction_regime")
            or market_ctx.get("regime_label")
            or "NEUTRAL"
        ).upper().strip()

        market_buy_allowed = bool(market_ctx.get("buy_allowed", True))

        pulse_asset_class = row.get("pulse_asset_class") or infer_signal_asset_class(row)
        pulse_ctx = pulse_bus_row(pulse_asset_class)

        pulse_trade_allowed = bool(pulse_ctx.get("trade_allowed", True)) if pulse_ctx else True
        pulse_stress_score = safe_float(pulse_ctx.get("stress_score"), 0.0) if pulse_ctx else 0.0
        pulse_breadth_score = safe_float(pulse_ctx.get("breadth_score"), 0.0) if pulse_ctx else 0.0
        pulse_best_symbol = str(pulse_ctx.get("best_symbol") or "").upper().strip() if pulse_ctx else ""

        score = 0
        max_score = 10
        score_reasons = []

        if trend == "BULLISH":
            score += 1
            score_reasons.append("bullish trend")

        if rs_score >= 1.05:
            score += 1
            score_reasons.append("strong relative strength")

        if sector_pct >= 75:
            score += 1
            score_reasons.append("sector leader")

        if model_score >= 4:
            score += 1
            score_reasons.append("strong model score")

        if action == "BUY" or (trend == "BULLISH" and model_score >= 3):
            score += 1
            score_reasons.append("buyable setup")

        earnings_clear = not (
            earnings_label in ("HIGH", "EXTREME")
            or (earnings_days_int is not None and earnings_days_int <= 7)
        )

        if earnings_clear:
            score += 1
            score_reasons.append("earnings clear")

        economic_clear = not (
            economic_label in ("HIGH", "EXTREME")
            or economic_score >= 60
        )

        if economic_clear:
            score += 1
            score_reasons.append("economic risk acceptable")

        if market_regime != "RISK_OFF" and market_buy_allowed:
            score += 1
            score_reasons.append("market allows buys")

        if pulse_trade_allowed and pulse_stress_score < 70:
            score += 1
            score_reasons.append("asset stress acceptable")

        if pulse_asset_class in ("crypto", "forex", "gold", "oil"):
            if pulse_best_symbol and symbol == pulse_best_symbol:
                score += 1
                score_reasons.append("pulse best symbol")
            elif pulse_breadth_score >= 60:
                score += 1
                score_reasons.append("pulse breadth supportive")
        else:
            if market_regime != "RISK_OFF" and market_buy_allowed:
                score += 1
                score_reasons.append("stock-market context supportive")

        score_pct = round((score / max_score) * 100.0, 1)
        rating = rating_from_score_pct(score_pct)

        combined_event_risk_score = max(
            int(safe_float(earnings_ctx.get("risk_score"), 0.0)),
            economic_score,
        )

        if combined_event_risk_score >= 80:
            combined_event_risk_label = "EXTREME"
        elif combined_event_risk_score >= 60:
            combined_event_risk_label = "HIGH"
        elif combined_event_risk_score >= 35:
            combined_event_risk_label = "MEDIUM"
        elif combined_event_risk_score > 0:
            combined_event_risk_label = "LOW"
        else:
            combined_event_risk_label = "NONE"

        enriched = {
            **row,
            "sector_rank": leadership_row.get("sector_rank"),
            "sector_count": leadership_row.get("sector_count"),
            "sector_percentile": sector_pct,
            "leadership_tier": leadership_row.get("leadership_tier"),
            "sector_leader": leadership_row.get("sector_leader"),
            "earnings_risk_label": earnings_label,
            "earnings_risk_score": int(safe_float(earnings_ctx.get("risk_score"), 0.0)),
            "earnings_date": (
                row.get("earnings_date")
                if row.get("earnings_date") is not None
                else earnings_ctx.get("earnings_date")
            ),
            "earnings_days_until": earnings_days_int,
            "economic_risk_label": economic_label,
            "economic_risk_score": economic_score,
            "market_reaction_regime": market_regime,
            "market_buy_allowed": market_buy_allowed,
            "pulse_asset_class": pulse_asset_class,
            "pulse_regime": pulse_ctx.get("regime") if pulse_ctx else row.get("pulse_regime"),
            "pulse_stress_score": pulse_stress_score,
            "pulse_breadth_score": pulse_breadth_score,
            "pulse_best_symbol": pulse_best_symbol,
            "pulse_trade_allowed": pulse_trade_allowed,
            "combined_event_risk_score": combined_event_risk_score,
            "combined_event_risk_label": combined_event_risk_label,
            "opportunity_score": score,
            "opportunity_max_score": max_score,
            "opportunity_score_pct": score_pct,
            "overall_rating": rating,
            "score_reasons": " • ".join(score_reasons),
        }

        enriched["trade_recommendation"] = scanner_trade_recommendation(
            enriched,
            score_pct,
            rating,
        )

        return enriched

    def enrich_scanner_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = [row for row in rows if isinstance(row, dict)]

        leadership = sector_leadership_map(rows)
        st.session_state["scanner_sector_leadership_map"] = leadership

        enriched_rows = [
            apply_scanner_quality_overlay(row)
            for row in rows
        ]

        return sorted(
            enriched_rows,
            key=lambda row: (
                safe_float(row.get("opportunity_score_pct"), 0.0),
                safe_float(row.get("model_score"), 0.0),
                safe_float(row.get("rs_score"), 0.0),
            ),
            reverse=True,
        )
    
    # =====================================================
    # SIGNAL GENERATION / NORMALIZATION
    # =====================================================

    def generate_signals() -> List[Dict[str, Any]]:
        clear_scanner_warning()

        universe_mode = st.session_state.get(
            "scanner_universe_mode",
            "JFBP",
        )

        universe = st.session_state.get("universe")

        if not isinstance(universe, dict) or not universe:

            if universe_mode == "CUSTOM BATCH":

                universe = build_custom_batch_universe(
                    st.session_state.get(
                        "scanner_custom_batch_symbols",
                        "",
                    )
                )

                if not universe:
                    st.session_state["scanner_last_raw_signals"] = []
                    st.session_state["scanner_last_status"] = "CUSTOM_BATCH_EMPTY"
                    st.session_state["scanner_last_error"] = (
                        "Enter one or more ticker symbols in Custom Batch mode."
                    )
                    return []

            elif universe_mode == "FALLBACK":

                universe = fallback_universe()

            elif universe_mode == "JFBP":

                universe = (
                    JFBP_UNIVERSE
                    if isinstance(JFBP_UNIVERSE, dict)
                    and JFBP_UNIVERSE
                    else fallback_universe()
                )

            else:

                universe = scanner_preset_universe(universe_mode)
                if not universe:
                    universe = fallback_universe()

            st.session_state["universe"] = universe

        rows = []

        for symbol, meta in universe.items():

            symbol = str(symbol).upper().strip()

            if not symbol:
                continue

            row = research_model_signal(
                symbol=symbol,
                meta=meta if isinstance(meta, dict) else {},
            )

            rows.append(row)

        rows = enrich_scanner_rows(rows)

        st.session_state["scanner_last_raw_signals"] = rows
        st.session_state["scanner_last_status"] = (
            f"GENERATED_{len(rows)}_RESEARCH_MODEL_SIGNALS"
        )

        return rows

    def normalize_signal(row: Dict[str, Any]) -> Dict[str, Any]:
        row = row if isinstance(row, dict) else {}
        row = apply_market_reaction_overlay(row)

        symbol = str(row.get("symbol") or "").upper().strip()

        scanner_action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        price = safe_float(row.get("price"), get_price(symbol))

        portfolio_positions = get_portfolio_positions()
        existing_qty = 0.0

        if isinstance(portfolio_positions, dict):
            position_row = portfolio_positions.get(symbol, {})
            if isinstance(position_row, dict):
                existing_qty = safe_float(
                    position_row.get("signed_qty", position_row.get("qty", 0.0)),
                    0.0,
                )

        row = apply_equal_weight_position_sizing(
            row=row,
            existing_qty=existing_qty,
        )

        row = apply_economic_calendar_overlay(row)
        row = apply_earnings_risk_overlay(row)
        row = apply_multi_asset_signal_bus_overlay(row)

        scanner_action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        qty = safe_float(row.get("qty"), 0.0)

        if qty < 0:
            qty = abs(qty)

        execution_action = (
            scanner_action
            if scanner_action in ("BUY", "SELL")
            else "HOLD"
        )

        row = apply_scanner_quality_overlay(row)

        return {
            **row,
            "timestamp": row.get("timestamp") or now(),
            "symbol": symbol,
            "display_symbol": row.get("display_symbol", symbol),
            "scanner_action": scanner_action,
            "risk_action": execution_action,
            "execution_action": execution_action,
            "action": execution_action,
            "side": execution_action,
            "qty": qty,
            "price": price,
            "source": row.get("source") or "research_model_scanner_v35_3",
            "mode": st.session_state.get("mode", "SIM"),
        }

    def make_hold_row(signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = normalize_signal(signal)

        return {
            **signal,
            "risk_status": "IGNORED",
            "risk_approved": False,
            "risk_reason": "NON_EXECUTABLE_RESEARCH_MODEL_SIGNAL",
            "risk_reducing": False,
            "position_action": "NO_TRADE",
            "position_before": 0.0,
            "position_after": 0.0,
            "gross_before": 0.0,
            "gross_after": 0.0,
            "executable": False,
        }

    def coerce_batch_rows(batch_rows: Any) -> List[Dict[str, Any]]:
        if batch_rows is None:
            return []

        if isinstance(batch_rows, dict):
            return [batch_rows]

        if isinstance(batch_rows, list):
            return [row for row in batch_rows if isinstance(row, dict)]

        try:
            return [row for row in list(batch_rows) if isinstance(row, dict)]
        except Exception:
            return []

    def scanner_status_label(
        plan: List[Dict[str, Any]],
        hold_rows: List[Dict[str, Any]],
    ) -> str:
        plan = plan if isinstance(plan, list) else []
        hold_rows = hold_rows if isinstance(hold_rows, list) else []

        executable_count = len([
            row for row in plan
            if bool(row.get("executable"))
        ])

        blocked_short_count = len([
            row for row in hold_rows
            if row.get("position_action") == "BLOCKED_OPEN_SHORT"
        ])

        at_target_count = len([
            row for row in hold_rows
            if row.get("position_action") == "AT_TARGET_WEIGHT"
        ])

        risk_off_hold_count = len([
            row for row in hold_rows
            if row.get("market_reaction_overlay") == "MARKET_REACTION_RISK_OFF_HOLD"
        ])

        market_ctx = market_reaction_context()
        regime = str(
            market_ctx.get("regime_label", "NEUTRAL")
        ).upper().strip()

        if st.session_state.get("risk_kill_switch", False):
            return "KILL_SWITCH_ACTIVE"

        if regime == "RISK_OFF":
            return "DEFENSIVE_RISK_OFF"

        if regime == "RISK_ON" and executable_count > 0:
            return "RISK_ON_PLAN_READY"

        if executable_count <= 0:
            if blocked_short_count:
                return "NO_TRADES_LONG_ONLY_FILTER"

            if at_target_count:
                return "NO_TRADES_AT_TARGET"

            if risk_off_hold_count:
                return "NO_TRADES_RISK_OFF"

            return "NO_EXECUTABLE_TRADES"

        return "BATCH_PLAN_READY"

    def check_single_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = normalize_signal(signal)

        if st.session_state.get("risk_kill_switch", False):
            return {
                **signal,
                "risk_status": "BLOCKED",
                "risk_approved": False,
                "risk_reason": "KILL_SWITCH_ACTIVE",
                "risk_reducing": False,
                "position_action": "KILL_SWITCH",
                "position_before": None,
                "position_after": None,
                "gross_before": None,
                "gross_after": None,
                "executable": False,
            }

        approved = False
        reason = "RISK_ENGINE_MISSING"

        try:
            if risk_engine and hasattr(risk_engine, "check"):
                sync_market_reaction_to_risk_engine()
                check_result = risk_engine.check(signal)

                if isinstance(check_result, tuple):
                    approved = bool(check_result[0])
                    reason = check_result[1] if len(check_result) > 1 else ""

                elif isinstance(check_result, dict):
                    approved = bool(
                        check_result.get("approved")
                        or check_result.get("risk_approved")
                    )
                    reason = (
                        check_result.get("reason")
                        or check_result.get("risk_reason")
                        or ""
                    )

                else:
                    approved = bool(check_result)
                    reason = "APPROVED" if approved else "BLOCKED"

        except Exception as exc:
            approved = False
            reason = str(exc)

        risk_snapshot = safe_snapshot(risk_engine)

        last_check = (
            risk_snapshot.get("last_check", {})
            if isinstance(risk_snapshot, dict)
            else {}
        )

        execution_action = normalize_action(signal.get("execution_action"))

        executable = (
            bool(approved)
            and execution_action in ("BUY", "SELL")
        )

        return {
            **signal,
            "risk_status": "APPROVED" if approved else "BLOCKED",
            "risk_approved": bool(approved),
            "risk_reason": reason,
            "risk_reducing": bool(last_check.get("risk_reducing", False)),
            "position_action": last_check.get("position_action"),
            "position_before": last_check.get("position_before"),
            "position_after": last_check.get("position_after"),
            "gross_before": last_check.get("gross_before"),
            "gross_after": last_check.get("gross_after"),
            "executable": executable,
        }

    def build_risk_plan(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clear_scanner_warning()

        if not signals:
            signals = generate_signals()

        sync_market_reaction_to_risk_engine()
        sync_risk()

        normalized = [
            normalize_signal(signal)
            for signal in signals
        ]

        # =================================================
        # PORTFOLIO-AWARE LONG-ONLY + TARGET-WEIGHT FILTER
        # =================================================
        # Scanner is long-only.
        #
        # SELL:
        #   Allowed only when the portfolio already holds a long position.
        #
        # BUY:
        #   Allowed only when sizing says there is still room to buy.
        #   If qty <= 0, the position is already at/above target weight.
        #
        # This prevents:
        #   SELL + position 0 -> BLOCKED_OPEN_SHORT
        #   BUY repeatedly -> position keeps growing above target

        portfolio_positions = get_portfolio_positions()

        def portfolio_signed_qty(symbol: str) -> float:
            symbol = str(symbol or "").upper().strip()
            row = portfolio_positions.get(symbol, {})

            if isinstance(row, dict):
                return safe_float(
                    row.get("signed_qty", row.get("qty", 0.0)),
                    0.0,
                )

            return 0.0

        portfolio_filtered_rows = []
        trade_candidates = []

        for signal in normalized:
            signal = normalize_signal(signal)

            execution_action = normalize_action(
                signal.get("execution_action")
                or signal.get("action")
                or signal.get("side")
                or signal.get("scanner_action")
            )

            symbol = str(signal.get("symbol") or "").upper().strip()
            position_before = portfolio_signed_qty(symbol)
            planned_qty = safe_float(signal.get("qty"), 0.0)

            signal = {
                **signal,
                "symbol": symbol,
                "execution_action": execution_action,
                "action": execution_action,
                "side": execution_action,
                "qty": planned_qty,
                "position_before": position_before,
            }

            if execution_action == "BUY" and planned_qty <= 0:
                portfolio_filtered_rows.append({
                    **signal,
                    "scanner_action": "BUY",
                    "risk_action": "HOLD",
                    "execution_action": "HOLD",
                    "action": "HOLD",
                    "side": "HOLD",
                    "qty": 0.0,
                    "risk_status": "IGNORED",
                    "risk_approved": False,
                    "risk_reason": "AT_OR_ABOVE_TARGET_WEIGHT",
                    "risk_reducing": False,
                    "position_action": "AT_TARGET_WEIGHT",
                    "position_before": position_before,
                    "position_after": position_before,
                    "gross_before": None,
                    "gross_after": None,
                    "executable": False,
                    "portfolio_filter": True,
                })
                continue

            if execution_action == "SELL" and position_before <= 0:
                portfolio_filtered_rows.append({
                    **signal,
                    "scanner_action": "SELL",
                    "risk_action": "HOLD",
                    "execution_action": "HOLD",
                    "action": "HOLD",
                    "side": "HOLD",
                    "qty": 0.0,
                    "risk_status": "IGNORED",
                    "risk_approved": False,
                    "risk_reason": "PORTFOLIO_FILTER_NO_LONG_POSITION",
                    "risk_reducing": False,
                    "position_action": "BLOCKED_OPEN_SHORT",
                    "position_before": position_before,
                    "position_after": position_before,
                    "gross_before": None,
                    "gross_after": None,
                    "executable": False,
                    "portfolio_filter": True,
                })
                continue

            trade_candidates.append(signal)

        executable_signals = []

        for signal in trade_candidates:
            execution_action = normalize_action(
                signal.get("execution_action")
                or signal.get("action")
                or signal.get("side")
            )

            planned_qty = safe_float(signal.get("qty"), 0.0)

            if execution_action in ("BUY", "SELL") and planned_qty > 0:
                executable_signals.append({
                    **signal,
                    "execution_action": execution_action,
                    "action": execution_action,
                    "side": execution_action,
                    "qty": planned_qty,
                })

        hold_rows = [
            make_hold_row(signal)
            for signal in trade_candidates
            if (
                normalize_action(
                    signal.get("execution_action")
                    or signal.get("action")
                    or signal.get("side")
                ) not in ("BUY", "SELL")
                or safe_float(signal.get("qty"), 0.0) <= 0
            )
        ]

        hold_rows.extend(portfolio_filtered_rows)

        if st.session_state.get("risk_kill_switch", False):

            plan = [
                {
                    **signal,
                    "risk_status": "BLOCKED",
                    "risk_approved": False,
                    "risk_reason": "KILL_SWITCH_ACTIVE",
                    "risk_reducing": False,
                    "position_action": "KILL_SWITCH",
                    "position_before": signal.get("position_before"),
                    "position_after": signal.get("position_before"),
                    "gross_before": None,
                    "gross_after": None,
                    "executable": False,
                }
                for signal in executable_signals
            ]

            st.session_state["scanner_last_risk_plan"] = plan
            st.session_state["scanner_last_hold_rows"] = hold_rows
            st.session_state["scanner_last_status"] = scanner_status_label(
                plan,
                hold_rows,
            )

            return plan

        plan = []

        if (
            risk_engine
            and hasattr(risk_engine, "check_batch")
            and executable_signals
        ):

            try:
                sync_market_reaction_to_risk_engine()
                raw_batch_rows = risk_engine.check_batch(executable_signals)
                batch_rows = coerce_batch_rows(raw_batch_rows)

                if not batch_rows:
                    raise RuntimeError("check_batch returned no usable rows")

                for row in batch_rows:
                    row = normalize_signal(row)

                    approved = bool(
                        row.get("approved")
                        or row.get("risk_approved")
                    )

                    execution_action = normalize_action(
                        row.get("execution_action")
                        or row.get("risk_action")
                        or row.get("action")
                        or row.get("side")
                    )

                    planned_qty = safe_float(row.get("qty"), 0.0)

                    executable = (
                        approved
                        and execution_action in ("BUY", "SELL")
                        and planned_qty > 0
                    )

                    plan.append({
                        **row,
                        "scanner_action": row.get("scanner_action"),
                        "risk_action": execution_action,
                        "execution_action": execution_action,
                        "action": execution_action,
                        "side": execution_action,
                        "qty": planned_qty,
                        "risk_status": "APPROVED" if approved else "BLOCKED",
                        "risk_approved": approved,
                        "risk_reason": row.get("reason") or row.get("risk_reason"),
                        "risk_reducing": bool(row.get("risk_reducing")),
                        "position_action": row.get("position_action"),
                        "position_before": row.get("position_before"),
                        "position_after": row.get("position_after"),
                        "gross_before": row.get("gross_before"),
                        "gross_after": row.get("gross_after"),
                        "executable": executable,
                    })

            except Exception as exc:
                st.session_state["scanner_last_error"] = (
                    f"risk_engine.check_batch failed: {exc}"
                )

                plan = [
                    check_single_signal(signal)
                    for signal in executable_signals
                ]

        else:

            plan = [
                check_single_signal(signal)
                for signal in executable_signals
            ]

        st.session_state["scanner_last_risk_plan"] = plan
        st.session_state["scanner_last_hold_rows"] = hold_rows
        st.session_state["scanner_last_status"] = scanner_status_label(
            plan,
            hold_rows,
        )

        return plan
        
    # =====================================================
    # EXECUTION ENGINE
    # =====================================================

    def execute_plan(plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clear_scanner_warning()

        plan = [
            row for row in plan
            if isinstance(row, dict)
        ] if isinstance(plan, list) else []

        if st.session_state.get("risk_kill_switch", False):
            blocked_count = len(plan)

            results = [{
                "timestamp": now(),
                "status": "BLOCKED",
                "reason": "KILL_SWITCH_ACTIVE",
                "blocked_count": blocked_count,
                "source": "scanner_execute_v35_3",
            }]

            st.session_state["scanner_last_execution_results"] = results
            st.session_state["scanner_last_status"] = (
                f"EXECUTION_BLOCKED_KILL_SWITCH_{blocked_count}_ROWS"
            )

            st.error("🛑 KILL SWITCH ACTIVE — scanner execution blocked.")
            return results

        if not plan:
            st.session_state["scanner_last_execution_results"] = []
            st.session_state["scanner_last_status"] = (
                "EXECUTION_SKIPPED_NO_APPROVED_ROWS"
            )
            return []

        sync_market_reaction_to_risk_engine()
        sync_risk()

        executable_rows = []

        for row in plan:
            execution_action = normalize_action(
                row.get("execution_action")
                or row.get("action")
                or row.get("side")
            )

            risk_approved = bool(row.get("risk_approved"))
            executable = bool(row.get("executable"))

            qty = safe_float(row.get("qty"), 0.0)
            price = safe_float(row.get("price"), 0.0)

            if (
                risk_approved
                and executable
                and execution_action in ("BUY", "SELL")
                and qty > 0
                and price > 0
            ):
                executable_rows.append({
                    **row,
                    "execution_action": execution_action,
                    "action": execution_action,
                    "side": execution_action,
                    "qty": qty,
                    "price": price,
                })

        if not executable_rows:
            results = [{
                "timestamp": now(),
                "status": "SKIPPED",
                "reason": "NO_EXECUTABLE_APPROVED_ROWS",
                "rows_received": len(plan),
                "source": "scanner_execute_v35_3",
            }]

            st.session_state["scanner_last_execution_results"] = results
            st.session_state["scanner_last_status"] = (
                "EXECUTION_SKIPPED_NO_EXECUTABLE_ROWS"
            )

            return results

        results = []

        if pipeline is None or not hasattr(pipeline, "execute"):
            results = [{
                "timestamp": now(),
                "status": "PIPELINE_MISSING",
                "reason": "pipeline.execute unavailable",
                "rows_received": len(plan),
                "executable_rows": len(executable_rows),
                "source": "scanner_execute_v35_3",
            }]

            st.session_state["scanner_last_execution_results"] = results
            st.session_state["scanner_last_status"] = (
                "EXECUTION_FAILED_PIPELINE_MISSING"
            )

            return results

        executed = 0
        skipped = 0
        failed = 0

        for row in executable_rows:
            execution_action = normalize_action(
                row.get("execution_action")
                or row.get("action")
                or row.get("side")
            )

            risk_approved = bool(row.get("risk_approved"))
            executable = bool(row.get("executable"))
            qty = safe_float(row.get("qty"), 0.0)
            price = safe_float(row.get("price"), 0.0)

            if not (
                risk_approved
                and executable
                and execution_action in ("BUY", "SELL")
                and qty > 0
                and price > 0
            ):
                skipped += 1

                results.append({
                    "timestamp": now(),
                    "symbol": row.get("symbol"),
                    "scanner_action": row.get("scanner_action"),
                    "risk_action": row.get("risk_action"),
                    "execution_action": execution_action,
                    "action": execution_action,
                    "qty": qty,
                    "price": price,
                    "status": "SKIPPED",
                    "reason": row.get("risk_reason") or "NOT_EXECUTABLE",
                    "risk_approved": risk_approved,
                    "position_action": row.get("position_action"),
                    "position_before": row.get("position_before"),
                    "position_after_expected": row.get("position_after"),
                    "source": row.get("source"),
                })
                continue

            signal = {
                "symbol": row.get("symbol"),
                "action": execution_action,
                "side": execution_action,
                "qty": qty,
                "price": price,
                "risk_approved": True,
                "scanner_action": row.get("scanner_action"),
                "risk_action": row.get("risk_action"),
                "execution_action": execution_action,
                "position_action": row.get("position_action"),
                "position_before": row.get("position_before"),
                "position_after": row.get("position_after"),
                "mode": st.session_state.get("mode", "SIM"),
                "source": "scanner_execute_v35_3",
            }

            try:
                raw_result = pipeline.execute(signal)

                normalized = normalize_execution_result(
                    raw_result,
                    {
                        **row,
                        "execution_action": execution_action,
                        "qty": qty,
                        "price": price,
                    },
                )

                status = str(
                    normalized.get("status", "")
                ).upper().strip()

                if status in (
                    "ERROR",
                    "REJECTED",
                    "BLOCKED",
                    "NO_RESULT",
                    "PIPELINE_MISSING",
                    "TIMEOUT",
                ):
                    failed += 1
                elif status == "SKIPPED":
                    skipped += 1
                else:
                    executed += 1

                results.append(normalized)

            except Exception as exc:
                failed += 1

                results.append({
                    "timestamp": now(),
                    "symbol": row.get("symbol"),
                    "scanner_action": row.get("scanner_action"),
                    "risk_action": row.get("risk_action"),
                    "execution_action": execution_action,
                    "action": execution_action,
                    "qty": qty,
                    "price": price,
                    "status": "ERROR",
                    "reason": str(exc),
                    "risk_approved": risk_approved,
                    "position_action": row.get("position_action"),
                    "position_before": row.get("position_before"),
                    "position_after_expected": row.get("position_after"),
                    "source": row.get("source"),
                })

        st.session_state["scanner_last_execution_results"] = results
        st.session_state["scanner_last_status"] = (
            f"EXECUTED_{executed}_SKIPPED_{skipped}_FAILED_{failed}"
        )

        sync_market_reaction_to_risk_engine()
        sync_risk()

        return results

    def normalize_execution_result(
        raw_result: Any,
        source_row: Dict[str, Any],
    ) -> Dict[str, Any]:
        source_row = source_row if isinstance(source_row, dict) else {}

        base = {
            "timestamp": now(),
            "symbol": source_row.get("symbol"),
            "scanner_action": source_row.get("scanner_action"),
            "risk_action": source_row.get("risk_action"),
            "execution_action": source_row.get("execution_action"),
            "action": source_row.get("execution_action"),
            "qty": source_row.get("qty"),
            "price": source_row.get("price"),
            "risk_approved": source_row.get("risk_approved"),
            "position_action": source_row.get("position_action"),
            "position_before": source_row.get("position_before"),
            "position_after_expected": source_row.get("position_after"),
            "source": source_row.get("source"),
        }

        if raw_result is None:
            return {
                **base,
                "status": "NO_RESULT",
                "reason": "pipeline.execute returned None",
            }

        if isinstance(raw_result, dict):
            status = str(
                raw_result.get("status")
                or raw_result.get("state")
                or raw_result.get("result")
                or "SUBMITTED"
            ).upper().strip()

            return {
                **base,
                **raw_result,
                "timestamp": raw_result.get("timestamp") or base["timestamp"],
                "symbol": raw_result.get("symbol") or base["symbol"],
                "scanner_action": (
                    raw_result.get("scanner_action")
                    or base["scanner_action"]
                ),
                "risk_action": (
                    raw_result.get("risk_action")
                    or base["risk_action"]
                ),
                "execution_action": (
                    raw_result.get("execution_action")
                    or raw_result.get("action")
                    or base["execution_action"]
                ),
                "action": raw_result.get("action") or base["action"],
                "qty": raw_result.get("qty") or base["qty"],
                "price": raw_result.get("price") or base["price"],
                "fill_price": (
                    raw_result.get("fill_price")
                    or raw_result.get("avg_fill_price")
                ),
                "status": status,
                "reason": (
                    raw_result.get("reason")
                    or raw_result.get("message")
                ),
                "risk_approved": raw_result.get(
                    "risk_approved",
                    base["risk_approved"],
                ),
                "position_action": (
                    raw_result.get("position_action")
                    or base["position_action"]
                ),
                "position_before": raw_result.get(
                    "position_before",
                    base["position_before"],
                ),
                "position_after_expected": raw_result.get(
                    "position_after_expected",
                    base["position_after_expected"],
                ),
                "lifecycle_stage": raw_result.get("lifecycle_stage"),
                "realized_delta": raw_result.get("realized_delta"),
                "order_id": raw_result.get("order_id"),
                "fill_id": raw_result.get("fill_id"),
                "source": raw_result.get("source") or base["source"],
            }

        return {
            **base,
            "status": "SUBMITTED",
            "reason": str(raw_result),
        }

    # =====================================================
    # TABLE CLEANERS
    # =====================================================

    def clean_plan_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{
            "timestamp": row.get("timestamp"),
            "symbol": row.get("symbol"),
            "display_symbol": row.get("display_symbol"),
            "scanner_action": row.get("scanner_action"),
            "risk_action": row.get("risk_action"),
            "execution_action": row.get("execution_action"),
            "qty": row.get("qty"),
            "price": row.get("price"),
            "model_score": row.get("model_score"),
            "trend": row.get("trend"),
            "rs_score": row.get("rs_score"),
            "opportunity_score": row.get("opportunity_score"),
            "opportunity_score_pct": row.get("opportunity_score_pct"),
            "overall_rating": row.get("overall_rating"),
            "trade_recommendation": row.get("trade_recommendation"),
            "sector_rank": row.get("sector_rank"),
            "sector_count": row.get("sector_count"),
            "sector_percentile": row.get("sector_percentile"),
            "leadership_tier": row.get("leadership_tier"),
            "sector_leader": row.get("sector_leader"),
            "combined_event_risk_label": row.get("combined_event_risk_label"),
            "combined_event_risk_score": row.get("combined_event_risk_score"),
            "sizing_model": row.get("sizing_model"),
            "sizing_target_value": row.get("sizing_target_value"),
            "market_reaction_regime": row.get("market_reaction_regime"),
            "market_reaction_score": row.get("market_reaction_score"),
            "market_reaction_confidence": row.get("market_reaction_confidence"),
            "market_reaction_overlay": row.get("market_reaction_overlay"),
            "economic_risk_label": row.get("economic_risk_label"),
            "economic_risk_score": row.get("economic_risk_score"),
            "economic_risk_highest_event": row.get("economic_risk_highest_event"),
            "economic_calendar_overlay": row.get("economic_calendar_overlay"),
            "economic_enforcement_enabled": row.get("economic_enforcement_enabled"),
            "earnings_risk_label": row.get("earnings_risk_label"),
            "earnings_risk_score": row.get("earnings_risk_score"),
            "earnings_date": row.get("earnings_date"),
            "earnings_days_until": row.get("earnings_days_until"),
            "earnings_status": row.get("earnings_status"),
            "earnings_risk_overlay": row.get("earnings_risk_overlay"),
            "earnings_enforcement_enabled": row.get("earnings_enforcement_enabled"),
            "risk_status": row.get("risk_status"),
            "risk_reason": row.get("risk_reason"),
            "risk_reducing": row.get("risk_reducing"),
            "position_action": row.get("position_action"),
            "position_before": row.get("position_before"),
            "position_after": row.get("position_after"),
            "gross_before": row.get("gross_before"),
            "gross_after": row.get("gross_after"),
            "executable": row.get("executable"),
            "source": row.get("source"),
        } for row in rows]

    def clean_result_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cleaned = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            cleaned.append({
                "timestamp": row.get("timestamp"),
                "symbol": row.get("symbol"),
                "scanner_action": row.get("scanner_action"),
                "risk_action": row.get("risk_action"),
                "execution_action": row.get("execution_action"),
                "qty": row.get("qty"),
                "price": row.get("price"),
                "fill_price": row.get("fill_price"),
                "status": row.get("status"),
                "reason": row.get("reason"),
                "risk_approved": row.get("risk_approved"),
                "position_action": row.get("position_action"),
                "position_before": row.get("position_before"),
                "position_after_expected": row.get("position_after_expected"),
                "lifecycle_stage": row.get("lifecycle_stage"),
                "realized_delta": row.get("realized_delta"),
                "order_id": row.get("order_id"),
                "fill_id": row.get("fill_id"),
                "source": row.get("source"),
            })

        return cleaned


    # =====================================================
    # v73 DISPLAY BADGES / VISUAL HELPERS
    # =====================================================

    def sector_strength_label(score: Any) -> str:
        score = safe_float(score, 0.0)

        if score >= 60:
            return "🟢 STRONG"

        if score >= 45:
            return "🟡 AVERAGE"

        return "🔴 WEAK"

    def leadership_badge(tier: Any) -> str:
        tier = str(tier or "").upper().strip()

        if tier == "ELITE":
            return "🟢 ELITE"

        if tier == "LEADER":
            return "🟡 LEADER"

        if tier == "STRONG":
            return "🟡 STRONG"

        if tier == "AVERAGE":
            return "⚪ AVERAGE"

        if tier == "WEAK":
            return "🔴 WEAK"

        return tier or "N/A"

    def highlight_top_opportunity(row):
        if row.name == 0:
            return ["background-color: #ecfdf3"] * len(row)

        return [""] * len(row)

    def scanner_compact_card(
        label: str,
        value: Any,
        tone: str = "blue",
    ) -> None:
        palette = {
            "blue": ("#f3f8ff", "#cfe2ff", "#1f2937"),
            "green": ("#ecfdf3", "#bbebca", "#087a2f"),
            "yellow": ("#fff8e6", "#ffe2a8", "#92400e"),
            "red": ("#fff1f2", "#fecdd3", "#9f1239"),
            "neutral": ("#f8fafc", "#dbe3ef", "#1f2937"),
        }

        background, border, color = palette.get(
            tone,
            palette["blue"],
        )

        card_html = (
            '<div style="'
            f'background:{background};'
            f'border:1px solid {border};'
            'border-radius:14px;'
            'padding:0.78rem 0.86rem;'
            'min-height:82px;'
            'margin-bottom:0.55rem;'
            'overflow-wrap:anywhere;'
            '">'
            '<div style="font-size:0.70rem;font-weight:850;color:#52677d;'
            'text-transform:uppercase;letter-spacing:0.04em;line-height:1.15;'
            'margin-bottom:0.35rem;">'
            f'{str(label)}'
            '</div>'
            f'<div style="font-size:1.02rem;font-weight:850;color:{color};'
            'line-height:1.15;white-space:normal;overflow-wrap:anywhere;">'
            f'{str(value)}'
            '</div></div>'
        )

        st.markdown(card_html, unsafe_allow_html=True)

    def scanner_tip(text: str) -> None:
        """Small user-facing explanation helper for Scanner sections."""

        st.caption(f"💡 {text}")

    def scanner_help_expander(title: str, body: str) -> None:
        """Compact explanatory expander used across the Scanner page."""

        with st.expander(f"ℹ️ {title}", expanded=False):
            st.markdown(body)


    # =====================================================
    # PAGE RENDER
    # =====================================================

    sync_market_reaction_to_risk_engine()
    sync_risk()
    sync_market_reaction_to_risk_engine()

    positions = get_portfolio_positions()
    risk_snapshot = safe_snapshot(risk_engine)

    if str(st.session_state.get("mode", "SIM")).upper().strip() == "LIVE":
        st.caption(
            "LIVE broker-truth mode: Scanner positions are read from "
            "IBKR gateway only. Old SIM/test portfolio positions are ignored."
        )

    def display_scanner_status(raw_status: Any) -> str:
        status = str(raw_status or "READY").upper().strip()

        if status.startswith("DEFENSIVE_RISK_OFF"):
            return "Risk-Off"

        if status.startswith("KILL_SWITCH"):
            return "Kill Switch"

        if status.startswith("EXECUTION_BLOCKED"):
            return "Execution Blocked"

        if status.startswith("EXECUTION_SKIPPED"):
            return "No Trades"

        if status.startswith("EXECUTED_"):
            return "Executed"

        if status.startswith("GENERATED_"):
            return "Signals Generated"

        if status.startswith("NO_TRADES_LONG_ONLY"):
            return "LONG ONLY"

        if status.startswith("NO_TRADES_AT_TARGET"):
            return "AT TARGET"

        if status.startswith("NO_TRADES_RISK_OFF"):
            return "RISK OFF"

        if status.startswith("NO_EXECUTABLE"):
            return "No Trades"

        if status.startswith("BATCH_PLAN_READY"):
            return "Plan Ready"

        if status.startswith("CLEARED"):
            return "Cleared"

        if status.startswith("REFRESHED"):
            return "Refreshed"

        return status.title().replace("_", " ")

    def safe_gateway_account_values() -> Dict[str, Any]:
        try:
            if gateway and hasattr(gateway, "account_values"):
                values = gateway.account_values()
                return values if isinstance(values, dict) else {}
        except Exception as exc:
            st.session_state["scanner_last_error"] = (
                f"gateway.account_values failed: {exc}"
            )

        return {}

    def safe_gateway_account_snapshot() -> Dict[str, Any]:
        try:
            if gateway and hasattr(gateway, "account_snapshot"):
                snap = gateway.account_snapshot()
                return snap if isinstance(snap, dict) else {}
        except Exception as exc:
            st.session_state["scanner_last_error"] = (
                f"gateway.account_snapshot failed: {exc}"
            )

        return {}

    def safe_gateway_account_summary() -> List[Dict[str, Any]]:
        try:
            if gateway and hasattr(gateway, "account_summary"):
                rows = gateway.account_summary()

                if isinstance(rows, list):
                    return [
                        row for row in rows
                        if isinstance(row, dict)
                    ]

        except Exception as exc:
            st.session_state["scanner_last_error"] = (
                f"gateway.account_summary failed: {exc}"
            )

        return []

    scanner_status_raw = st.session_state.get(
        "scanner_last_status",
        "READY",
    )

    scanner_status_display = display_scanner_status(
        scanner_status_raw
    )

    market_ctx = market_reaction_context()

    account_values = safe_gateway_account_values()
    account_snapshot = safe_gateway_account_snapshot()
    account_summary_rows = safe_gateway_account_summary()


    # =====================================================
    # SCANNER v85.1 WORKBENCH RESPONSIVE THEME
    # Market Pulse width standard + responsive scanner layout
    # =====================================================

    st.markdown(
        """
        <style>
            /* =====================================================
               JFBP GLOBAL CONTENT WIDTH STANDARD
               Matches Market Pulse visual rhythm
               ===================================================== */

            .block-container {
                padding-top: 1.4rem !important;
                padding-bottom: 2.5rem !important;

                max-width: 1700px !important;

                padding-left: 3rem !important;
                padding-right: 3rem !important;

                margin-left: auto !important;
                margin-right: auto !important;
            }

            h1 {
                font-size: clamp(1.85rem, 3.5vw, 2.4rem) !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
                line-height: 1.12 !important;
            }

            h2, h3 {
                font-size: clamp(1.10rem, 2.2vw, 1.45rem) !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
                line-height: 1.18 !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.85rem;
                align-items: stretch;
            }

            div[data-testid="stHorizontalBlock"] > div {
                min-width: 0 !important;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                overflow-wrap: anywhere;
                word-break: normal;
            }

            div[data-testid="stMetric"] {
                background: #f7fbff;
                border: 1px solid #d9e8ff;
                border-radius: 14px;
                padding: 14px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }

            div[data-testid="stMetricLabel"] {
                font-size: 0.85rem !important;
                font-weight: 800 !important;
                color: #48617a !important;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }

            div[data-testid="stMetricValue"] {
                font-size: 1.25rem !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
            }

            div[data-testid="stDataFrame"] {
                font-size: 0.92rem !important;
                border-radius: 12px !important;
                overflow-x: auto !important;
                max-width: 100% !important;
            }

            div[data-testid="stDataFrame"] * {
                white-space: normal !important;
                overflow-wrap: anywhere !important;
            }

            .stButton > button {
                border-radius: 10px;
                font-weight: 750;
                min-height: 38px;
                border: 1px solid #d7e3f5;
            }

            .scanner-section-card {
                border-radius: 16px;
                padding: 12px 14px;
                margin: 6px 0 10px 0;
            }

            .scanner-section-blue {
                background: #eef6ff;
                border: 1px solid #cfe2ff;
            }

            .scanner-section-green {
                background: #ecfdf3;
                border: 1px solid #bbebca;
            }

            .scanner-section-yellow {
                background: #fff8e6;
                border: 1px solid #ffe2a8;
            }

            .scanner-section-title {
                font-size: 0.76rem;
                font-weight: 850;
                color: #52677d;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                margin-bottom: 4px;
            }

            .scanner-section-value {
                font-size: 1.2rem;
                font-weight: 850;
                color: #1f2937;
                line-height: 1.15;
            }

            .scanner-section-note {
                font-size: 0.9rem;
                color: #52677d;
                margin-top: 4px;
            }

            .scanner-inline-note {
                font-size: 0.84rem;
                color: #52677d;
                line-height: 1.35;
            }

            /* Prevent metric/card rows from clipping long labels. */
            [data-testid="stMetricLabel"],
            [data-testid="stMetricValue"] {
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
                overflow-wrap: anywhere !important;
            }

            /* Medium screens: keep Market Pulse spacing but reduce pressure. */
            @media (max-width: 1500px) {
                .block-container {
                    max-width: 1550px !important;
                    padding-left: 2.25rem !important;
                    padding-right: 2.25rem !important;
                }

                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                }

                div[data-testid="stHorizontalBlock"] > div {
                    min-width: min(100%, 360px) !important;
                }
            }

            /* Tablet / small laptop. */
            @media (max-width: 1180px) {
                .block-container {
                    max-width: 100% !important;
                    padding-left: 1.5rem !important;
                    padding-right: 1.5rem !important;
                }

                div[data-testid="stHorizontalBlock"] > div {
                    min-width: 100% !important;
                    flex: 1 1 100% !important;
                }

                div[data-testid="stMetric"] {
                    padding: 10px 11px;
                }

                div[data-testid="stMetricValue"] {
                    font-size: 1.05rem !important;
                }

                div[data-testid="stMetricLabel"] {
                    font-size: 0.74rem !important;
                }
            }

            /* Mobile. */
            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem !important;
                    padding-right: 0.9rem !important;
                }

                div[data-testid="stDataFrame"] {
                    font-size: 0.82rem !important;
                }

                .scanner-section-card {
                    padding: 11px 12px;
                }
            }

        </style>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # SCANNER COMMAND ROW
    # =====================================================

    render_research_stock_autonav()

    st.title("📡 Scanner")
    st.caption(
        "Research-model opportunity scanner with trader presets, index/futures universes, responsive layout, and optional custom batch symbols."
    )

    scanner_help_expander(
        "How to use this page",
        """
        **1. Pick a universe or Trader Preset.** Use **INDEXES** for broad market ETFs, **FUTURES DASHBOARD** or the Futures universes for E-mini, commodity, FX, and rates futures, **Trader Presets** for Momentum / Swing Trading / Breakouts / Defensive / Dividend Income / AI Leaders / Canada / Earnings Watch, **Pulse universes** for Oil/Gold/Crypto/Forex, **CURRENCY ETFs** for macro currency ETF proxies, **JFBP** for the saved app universe, **FALLBACK** for the safe built-in list, or **CUSTOM BATCH** to paste your own symbols.

        **2. For Gold / Oil / Forex / Crypto, open the matching Pulse page first.** The Pulse page reads the asset-class regime, stress, breadth, execution bias, and best opportunity. Then return to **Scanner**, select the matching universe, and run the scan.

        - **Gold:** Open **Gold Pulse** → return to **Scanner** → select **GOLD PULSE** → **Run Scanner**.
        - **Oil:** Open **Oil Pulse** → return to **Scanner** → select **OIL PULSE** → **Run Scanner**.
        - **Forex:** Open **Forex Pulse** → return to **Scanner** → select **FOREX PULSE** → **Run Scanner**.
        - **Crypto:** Open **Crypto Pulse** → return to **Scanner** → select **CRYPTO PULSE** → **Run Scanner**.

        **3. Run Scanner.** This ranks symbols by trend, relative strength, sector leadership, earnings risk, economic risk, Market Pulse context, and Pulse regime context when available.

        **4. Build Risk-Aware Plan.** This does not blindly trade. It checks the risk engine, existing positions, target sizing, long-only rules, and event-risk overlays first.

        **5. Execute only after review.** Execution still requires confirmation and only approved BUY/SELL rows are routed.
        """,
    )


    # =====================================================
    # MULTI-ASSET SIGNAL BUS DASHBOARD
    # =====================================================

    bus_snapshot = multi_asset_signal_bus()
    if bus_snapshot:
        with st.expander("🌍 Multi-Asset Signal Bus", expanded=False):
            st.caption(
                "Pulse pages publish regime, stress, breadth, execution multiplier, and best opportunity here. "
                "Scanner reads this bus when scoring and building risk-aware plans."
            )
            bus_rows = []
            for asset_key in ("crypto", "forex", "gold", "oil"):
                row = bus_snapshot.get(asset_key, {})
                if not isinstance(row, dict) or not row:
                    continue
                bus_rows.append({
                    "Asset": str(row.get("label") or asset_key.title()),
                    "Regime": row.get("regime", "UNKNOWN"),
                    "Stress": row.get("stress_score", ""),
                    "Breadth": row.get("breadth_score", ""),
                    "Allowed": "YES" if row.get("trade_allowed", True) else "NO",
                    "Multiplier": f"{safe_float(row.get('execution_multiplier'), 1.0):.2f}x",
                    "Best": row.get("best_symbol", ""),
                    "Best Score": row.get("best_score", ""),
                    "Updated": row.get("timestamp", ""),
                })
            if bus_rows:
                st.dataframe(pd.DataFrame(bus_rows), width="stretch", hide_index=True)
            else:
                st.info("No Pulse bus rows have been published yet. Open a Pulse page first, then return to Scanner.")
    

    # =====================================================
    # SCANNER v84 TRADING DESK COMMAND STRIP
    # =====================================================
    # Compact one-row control layer. The trader should see decision
    # and opportunity information first; setup controls stay available
    # without consuming the full first screen.

    with st.container(border=True):
        strip_cols = responsive_columns([1.55, 1.0, 1.15, 0.85, 1.05, 0.9])

        with strip_cols[0]:
            selected_universe_mode = st.selectbox(
                "Universe",
                universe_options,
                index=universe_options.index(universe_mode),
                key="scanner_universe_mode_selector",
            )

            if selected_universe_mode != universe_mode:
                st.session_state["scanner_universe_mode"] = selected_universe_mode
                st.session_state["scanner_last_status"] = "REFRESHED"
                st.rerun()

            st.caption(
                f"{universe_mode} • {len(active_universe)} symbols"
            )

        with strip_cols[1]:
            st.caption("Scanner")
            run_scan_btn = st.button(
                "Run Scanner",
                width="stretch",
                key="scanner_run_v36_1",
            )

        with strip_cols[2]:
            st.caption("Risk Engine")
            build_plan_btn = st.button(
                "Build Plan",
                width="stretch",
                key="scanner_plan_v36_1",
            )

        with strip_cols[3]:
            st.caption("Data")
            refresh_btn = st.button(
                "Refresh",
                width="stretch",
                key="scanner_refresh_v36_1",
            )

        with strip_cols[4]:
            st.caption("Workspace")
            clear_btn = st.button(
                "Clear View",
                width="stretch",
                key="scanner_clear_v36_1",
            )

        with strip_cols[5]:
            st.caption("Controls")
            with st.popover("Settings ⚙️", use_container_width=True):
                st.markdown("#### Scanner Settings & Overlays")
                scanner_tip(
                    "Settings stay compact in v84 so the opportunity engine remains above the fold."
                )

                with st.expander("Account Sizing", expanded=False):

                    current_equity = scanner_account_equity()
                    manual_equity = safe_float(
                        st.session_state.get("scanner_account_equity_override"),
                        0.0,
                    )

                    st.caption(
                        "Scanner position sizing uses account equity when available. "
                        "If no live account equity is found, it falls back safely to $50,000."
                    )

                    sizing_col1, sizing_col2, sizing_col3 = responsive_columns(3)

                    with sizing_col1:
                        st.metric(
                            "Account Equity Used",
                            f"${current_equity:,.2f}",
                        )

                    with sizing_col2:
                        st.metric(
                            "Target Position %",
                            f"{SCANNER_TARGET_POSITION_PCT * 100:.1f}%",
                        )

                    with sizing_col3:
                        st.metric(
                            "Target Position Value",
                            f"${scanner_target_position_value():,.2f}",
                        )

                    new_manual_equity = st.number_input(
                        "Manual account equity override",
                        min_value=0.0,
                        value=float(manual_equity),
                        step=1000.0,
                        help=(
                            "Use 0 to allow automatic account equity detection. "
                            "Set a value to size scanner positions from a specific account size."
                        ),
                        key="scanner_account_equity_override_input",
                    )

                    if abs(new_manual_equity - manual_equity) > 1e-9:
                        st.session_state["scanner_account_equity_override"] = float(
                            new_manual_equity
                        )
                        st.session_state["scanner_last_status"] = "REFRESHED"
                        st.rerun()

                    if manual_equity > 0:
                        if st.button(
                            "Clear manual equity override",
                            width="stretch",
                            key="scanner_clear_equity_override_v36_1",
                        ):
                            st.session_state["scanner_account_equity_override"] = 0.0
                            st.session_state["scanner_last_status"] = "REFRESHED"
                            st.rerun()

                with st.expander("Economic Calendar Risk Overlay", expanded=False):

                    economic_ctx = economic_calendar_context()

                    ec1, ec2 = responsive_columns(2)

                    ec1.metric(
                        "Economic Risk",
                        economic_ctx["label"],
                    )

                    ec2.metric(
                        "Risk Score",
                        economic_ctx["score"],
                    )

                    st.caption(
                        f"Highest event: {economic_ctx['highest_event'] or 'None'} • "
                        f"Source: {economic_ctx['source']}"
                    )

                    current_economic_enforcement = bool(
                        st.session_state.get(
                            "scanner_economic_enforcement_enabled",
                            False,
                        )
                    )

                    new_economic_enforcement = st.checkbox(
                        "Enable Economic Calendar enforcement in Scanner",
                        value=current_economic_enforcement,
                        key="scanner_economic_enforcement_enabled_input",
                        help=(
                            "OFF = monitor only. ON = high-risk economic events can block "
                            "new BUY signals and medium-risk events can reduce BUY sizing."
                        ),
                    )

                    if new_economic_enforcement != current_economic_enforcement:
                        st.session_state[
                            "scanner_economic_enforcement_enabled"
                        ] = bool(new_economic_enforcement)
                        st.session_state["scanner_last_status"] = "REFRESHED"
                        st.rerun()

                    if current_economic_enforcement:
                        if economic_ctx["score"] >= 60:
                            st.warning(
                                "Economic Calendar enforcement is ON. "
                                "HIGH/EXTREME event risk will block new BUY signals."
                            )
                        elif economic_ctx["score"] >= 35:
                            st.info(
                                "Economic Calendar enforcement is ON. "
                                "MEDIUM event risk will reduce BUY sizing."
                            )
                        else:
                            st.success(
                                "Economic Calendar enforcement is ON, but event risk is low."
                            )
                    else:
                        st.info(
                            "Economic Calendar enforcement is OFF. Scanner monitors "
                            "economic risk but does not change trades."
                        )

                with st.expander("Earnings Risk Overlay", expanded=False):

                    earnings_ctx = earnings_universe_context()

                    er1, er2 = responsive_columns(2)

                    er1.metric(
                        "Earnings Risk",
                        earnings_ctx["label"],
                    )

                    er2.metric(
                        "Risk Score",
                        earnings_ctx["score"],
                    )

                    st.caption(
                        f"Highest symbol: {earnings_ctx['highest_symbol'] or 'None'} • "
                        f"Days: {earnings_ctx['highest_days'] if earnings_ctx['highest_days'] is not None else 'None'} • "
                        f"Source: {earnings_ctx['source']}"
                    )

                    current_earnings_enforcement = bool(
                        st.session_state.get(
                            "scanner_earnings_enforcement_enabled",
                            False,
                        )
                    )

                    new_earnings_enforcement = st.checkbox(
                        "Enable Earnings Risk enforcement in Scanner",
                        value=current_earnings_enforcement,
                        key="scanner_earnings_enforcement_enabled_input",
                        help=(
                            "OFF = monitor only. ON = BUY signals are blocked within "
                            "3 days of earnings and reduced 50% within 7 days."
                        ),
                    )

                    if new_earnings_enforcement != current_earnings_enforcement:
                        st.session_state[
                            "scanner_earnings_enforcement_enabled"
                        ] = bool(new_earnings_enforcement)
                        st.session_state["scanner_last_status"] = "REFRESHED"
                        st.rerun()

                    events = earnings_ctx.get("events", [])

                    if events:
                        earnings_df = pd.DataFrame(events)

                        display_cols = [
                            "symbol",
                            "earnings_date",
                            "days_until",
                            "risk_label",
                            "risk_score",
                            "status",
                            "source",
                            "reason",
                        ]

                        display_cols = [
                            col for col in display_cols
                            if col in earnings_df.columns
                        ]

                        st.dataframe(
                            earnings_df[display_cols],
                            width="stretch",
                            hide_index=True,
                        )

                    if current_earnings_enforcement:
                        highest_days = earnings_ctx.get("highest_days")

                        try:
                            highest_days = int(highest_days)
                        except Exception:
                            highest_days = None

                        if highest_days is not None and highest_days <= 3:
                            st.warning(
                                "Earnings enforcement is ON. "
                                "BUY signals within 3 days of earnings are blocked."
                            )

                        elif highest_days is not None and highest_days <= 7:
                            st.info(
                                "Earnings enforcement is ON. "
                                "BUY signals within 7 days of earnings are reduced 50%."
                            )

                        else:
                            st.success(
                                "Earnings enforcement is ON, but no near-term earnings risk exists."
                            )
                    else:
                        st.info(
                            "Earnings enforcement is OFF. Scanner monitors earnings "
                            "risk but does not change trades."
                        )

    with st.expander("🎯 Trader Presets", expanded=False):
        preset_cols = responsive_columns(3)
        preset_groups = [
            ("Momentum", "Fastest relative-strength names", "MOMENTUM"),
            ("Swing Trading", "Liquid names for multi-day setups", "SWING TRADING"),
            ("Breakouts", "High-RS breakout candidates", "BREAKOUTS"),
            ("Defensive", "Lower-beta defensive watchlist", "DEFENSIVE"),
            ("Dividend Income", "Income and dividend-growth ETFs", "DIVIDEND INCOME"),
            ("AI Leaders", "AI and data-center leaders", "AI LEADERS"),
            ("Canada", "Canadian banks, energy, rails, growth", "CANADA"),
            ("Earnings Watch", "Large caps to monitor around earnings", "EARNINGS WATCH"),
            ("Indexes", "SPY, QQQ, IWM, RSP, VTI, global ETFs", "INDEXES"),
            ("Futures Dashboard", "E-mini, crude, gold, FX, and rates futures", "FUTURES DASHBOARD"),
            ("Index Futures", "ES, NQ, YM, RTY E-mini contracts", "INDEX FUTURES"),
            ("Commodity Futures", "Crude, Brent, gold, silver, gas, copper", "COMMODITY FUTURES"),
            ("Forex Pulse", "EUR/USD, GBP/USD, USD/JPY and major FX crosses", "FOREX PULSE"),
            ("Currency ETFs", "UUP, FXE, FXB, FXY, FXC, CYB macro proxies", "CURRENCY ETFs"),
            ("FX Futures", "Euro, yen, pound, CAD, dollar index", "FX FUTURES"),
            ("Rates Futures", "2Y, 5Y, 10Y, 30Y Treasury futures", "RATES FUTURES"),
        ]

        for i, (label, note, preset_key) in enumerate(preset_groups):
            with preset_cols[i % 3]:
                st.markdown(f"**{label}**")
                st.caption(note)
                if st.button(
                    f"Load {label}",
                    width="stretch",
                    key=f"scanner_load_preset_{preset_key.lower().replace(' ', '_')}_v86",
                ):
                    st.session_state["scanner_universe_mode"] = preset_key
                    st.session_state["scanner_universe_mode_selector"] = preset_key
                    st.session_state["universe"] = scanner_preset_universe(preset_key)
                    st.session_state["scanner_last_status"] = "REFRESHED"
                    st.rerun()

    if selected_universe_mode == "CUSTOM BATCH":
        with st.expander("Custom Batch Symbols", expanded=True):
            custom_symbols_input = st.text_area(
                "Paste ticker symbols",
                value=st.session_state.get(
                    "scanner_custom_batch_symbols",
                    "AAPL, MSFT, NVDA, AMZN, META, GOOGL, AVGO",
                ),
                height=96,
                key="scanner_custom_batch_symbols_input",
                help=(
                    "Paste tickers separated by commas, spaces, or new lines. "
                    "Example: AAPL, MSFT, NVDA, SHOP.TO, RY.TO"
                ),
            )

            parsed_custom_symbols = parse_custom_batch_symbols(
                custom_symbols_input
            )

            if (
                custom_symbols_input
                != st.session_state.get("scanner_custom_batch_symbols", "")
            ):
                st.session_state["scanner_custom_batch_symbols"] = (
                    custom_symbols_input
                )
                st.session_state["universe"] = build_custom_batch_universe(
                    custom_symbols_input
                )
                st.session_state["scanner_last_status"] = "REFRESHED"

            st.caption(
                f"Parsed symbols: {len(parsed_custom_symbols)} • "
                f"{', '.join(parsed_custom_symbols[:15])}"
                f"{' ...' if len(parsed_custom_symbols) > 15 else ''}"
            )

    if run_scan_btn:
        signals = generate_signals()
        build_risk_plan(signals)
        st.rerun()

    if build_plan_btn:
        signals = st.session_state.get("scanner_last_raw_signals", [])
        build_risk_plan(signals)
        st.rerun()

    if refresh_btn:
        sync_market_reaction_to_risk_engine()
        sync_risk()
        st.session_state["scanner_last_status"] = "REFRESHED"
        clear_scanner_warning()
        st.rerun()

    if clear_btn:
        st.session_state["scanner_last_raw_signals"] = []
        st.session_state["scanner_last_risk_plan"] = []
        st.session_state["scanner_last_hold_rows"] = []
        st.session_state["scanner_last_execution_results"] = []
        st.session_state["scanner_last_status"] = "CLEARED"
        clear_scanner_warning()
        st.rerun()

    st.divider()

    dashboard_left, dashboard_right = responsive_columns([1.30, 0.90], gap="medium")

    ranking_df = pd.DataFrame()
    sector_summary_df = pd.DataFrame()
    elite_df = pd.DataFrame()

    with dashboard_left:

        # =====================================================
        # SCANNER CONFIDENCE + INTELLIGENCE BRIEF
        # Executive decision card aligned with Market Pulse.
        # =====================================================

        raw_signals_for_confidence = st.session_state.get(
            "scanner_last_raw_signals",
            [],
        )

        raw_signals_for_confidence = [
            row for row in raw_signals_for_confidence
            if isinstance(row, dict)
        ] if isinstance(raw_signals_for_confidence, list) else []

        risk_plan_for_confidence = st.session_state.get(
            "scanner_last_risk_plan",
            [],
        )

        risk_plan_for_confidence = [
            row for row in risk_plan_for_confidence
            if isinstance(row, dict)
        ] if isinstance(risk_plan_for_confidence, list) else []

        economic_ctx = economic_calendar_context()
        earnings_ctx = earnings_universe_context()
        market_ctx = market_reaction_context()

        executable_count = len([
            row for row in risk_plan_for_confidence
            if bool(row.get("executable"))
        ])

        avg_opportunity_score = 0.0

        if raw_signals_for_confidence:
            avg_opportunity_score = sum(
                safe_float(row.get("opportunity_score_pct"), 0.0)
                for row in raw_signals_for_confidence
            ) / len(raw_signals_for_confidence)

        market_regime = str(
            market_ctx.get("regime_label", "NEUTRAL") or "NEUTRAL"
        ).upper().strip()

        economic_label = str(
            economic_ctx.get("label", "NONE") or "NONE"
        ).upper().strip()

        earnings_label = str(
            earnings_ctx.get("label", "NONE") or "NONE"
        ).upper().strip()

        scanner_confidence = 50

        if market_regime == "RISK_ON":
            scanner_confidence += 20
        elif market_regime == "RISK_OFF":
            scanner_confidence -= 25

        scanner_confidence += int(avg_opportunity_score / 8)

        if executable_count >= 5:
            scanner_confidence += 10
        elif executable_count >= 2:
            scanner_confidence += 5
        elif executable_count == 0:
            scanner_confidence -= 10

        scanner_confidence -= int(
            safe_float(economic_ctx.get("score", 0), 0.0) / 8
        )

        scanner_confidence -= int(
            safe_float(earnings_ctx.get("score", 0), 0.0) / 10
        )

        scanner_confidence = max(
            0,
            min(100, scanner_confidence),
        )

        if scanner_confidence >= 90:
            confidence_label = "🟢 HIGH CONVICTION"
            confidence_tone = "green"
        elif scanner_confidence >= 75:
            confidence_label = "🟢 FAVORABLE"
            confidence_tone = "green"
        elif scanner_confidence >= 60:
            confidence_label = "🟡 SELECTIVE"
            confidence_tone = "yellow"
        elif scanner_confidence >= 40:
            confidence_label = "🟠 DEFENSIVE"
            confidence_tone = "yellow"
        else:
            confidence_label = "🔴 CAPITAL PRESERVATION"
            confidence_tone = "red"

        brief_parts = []

        if market_regime == "RISK_ON":
            brief_parts.append(
                "Market regime is supportive for selective long exposure."
            )
        elif market_regime == "RISK_OFF":
            brief_parts.append(
                "Market regime is defensive. New long exposure should be approached cautiously."
            )
        else:
            brief_parts.append(
                "Market regime is neutral. Scanner quality and risk filters should drive selectivity."
            )

        if avg_opportunity_score >= 80:
            brief_parts.append(
                "Opportunity quality is strong across the current scan."
            )
        elif avg_opportunity_score >= 60:
            brief_parts.append(
                "Opportunity quality is acceptable but selective."
            )
        else:
            brief_parts.append(
                "Opportunity quality is weak, so forcing trades is not recommended."
            )

        if economic_label in ("HIGH", "EXTREME"):
            brief_parts.append(
                f"Economic risk is elevated at {economic_label}."
            )
        else:
            brief_parts.append(
                f"Economic risk is {economic_label}."
            )

        if earnings_label in ("HIGH", "EXTREME"):
            brief_parts.append(
                f"Earnings risk is elevated at {earnings_label}."
            )
        else:
            brief_parts.append(
                f"Earnings risk is {earnings_label}."
            )

        if executable_count > 0:
            brief_parts.append(
                f"{executable_count} executable trade(s) are currently approved by the risk engine."
            )
        else:
            brief_parts.append(
                "No executable trades are currently approved by the risk engine."
            )

        st.subheader("🧠 Scanner Confidence")

        with st.container(border=True):

            scanner_tip(
                "This combines market regime, opportunity quality, event risk, and executable trade readiness into one decision score."
            )

            confidence_left, confidence_right = responsive_columns([1.2, 4.8])

            with confidence_left:
                scanner_compact_card(
                    "Confidence",
                    f"{scanner_confidence}/100",
                    tone=confidence_tone,
                )

            with confidence_right:
                scanner_compact_card(
                    "Reading",
                    confidence_label,
                    tone=confidence_tone,
                )

            st.markdown("#### 🧠 Scanner Intelligence Brief")

            st.write(
                " ".join(brief_parts)
            )
            
        # =====================================================
        # SCANNER OPPORTUNITY RANKING
        # =====================================================
        
        st.subheader("Scanner Opportunity Dashboard")
        scanner_tip(
            "This is the main ranking area. It shows the strongest current opportunities first, not a guaranteed buy list."
        )
        
        raw_signals = st.session_state.get(
            "scanner_last_raw_signals",
            [],
        )
        
        raw_signals = [
            row for row in raw_signals
            if isinstance(row, dict)
        ] if isinstance(raw_signals, list) else []
        
        if raw_signals:
        
            ranking_df = pd.DataFrame(
                enrich_scanner_rows(raw_signals)
            )
        
            # =================================================
            # BEST CURRENT OPPORTUNITY
            # =================================================
        
            if not ranking_df.empty:
                best_df = ranking_df.copy()
        
                sort_cols = [
                    col for col in [
                        "opportunity_score_pct",
                        "model_score",
                        "rs_score",
                    ]
                    if col in best_df.columns
                ]
        
                if sort_cols:
                    best_df = best_df.sort_values(
                        by=sort_cols,
                        ascending=False,
                    )
        
                best_row = best_df.iloc[0].to_dict()
                best_symbol = str(best_row.get("display_symbol") or best_row.get("symbol", "") or "")
        
                best_recommendation = str(
                    best_row.get("trade_recommendation", "WATCH") or "WATCH"
                ).upper().strip()
        
                best_research_signal = str(
                    best_row.get(
                        "research_signal",
                        best_row.get(
                            "signal",
                            best_row.get("setup_status", "N/A"),
                        ),
                    )
                    or "N/A"
                ).upper().strip()
        
                best_score = safe_float(
                    best_row.get("opportunity_score_pct"),
                    0.0,
                )
        
                best_rating = str(best_row.get("overall_rating", "") or "")
                best_sector = str(best_row.get("sector", "") or "")
                best_sector_rank = best_row.get("sector_rank")
                best_sector_count = best_row.get("sector_count")
        
                best_leadership = str(
                    best_row.get("leadership_tier", "") or ""
                ).upper().strip()
        
                best_rs = safe_float(best_row.get("rs_score"), 0.0)
        
                best_earnings = str(
                    best_row.get("earnings_risk_label", "NONE") or "NONE"
                ).upper().strip()
        
                rank_text = ""
        
                if best_sector_rank is not None and best_sector_count is not None:
                    rank_text = f"{best_sector_rank}/{best_sector_count}"
        
                best_recommendation_icon = {
                    "STRONG BUY": "🟢 STRONG BUY",
                    "BUY": "🟢 BUY",
                    "WATCH": "🟡 WATCH",
                    "NO TRADE": "🟡 WATCH",
                    "HOLD": "⚪ HOLD",
                    "AVOID": "🔴 AVOID",
                    "SELL": "🔴 SELL",
                }.get(best_recommendation, best_recommendation)
        
                best_research_icon = {
                    "STRONG BUY": "🟢 STRONG BUY",
                    "BUY": "🟢 BUY",
                    "WATCH": "🟡 WATCH",
                    "NO TRADE": "🟡 WATCH",
                    "HOLD": "⚪ HOLD",
                    "AVOID": "🔴 AVOID",
                    "SELL": "🔴 SELL",
                }.get(best_research_signal, best_research_signal)
        
                with st.container(border=True):
                    st.markdown("#### 🏆 Best Current Opportunity")
                    scanner_tip(
                        "This is the highest-ranked symbol right now based on the scanner score, sector rank, relative strength, and event-risk checks."
                    )
        
                    hero_left, hero_right = responsive_columns([1.45, 5.55])
        
                    with hero_left:
                        st.markdown(
                            f"""
                            <div style="font-size:clamp(1.65rem, 3.2vw, 2.3rem); font-weight:800; line-height:1.05; white-space:nowrap; word-break:keep-all; overflow-wrap:normal;">
                                {best_symbol or "N/A"}
                            </div>
                            <div style="font-size:0.85rem; opacity:0.75; margin-top:0.25rem;">
                                {best_sector or "N/A"}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
        
                    with hero_right:
                        hero_row_1 = responsive_columns(3)
                        hero_row_2 = responsive_columns(3)

                        with hero_row_1[0]:
                            scanner_compact_card(
                                "Research Signal",
                                best_research_icon,
                                tone="green" if "BUY" in best_research_icon else "yellow",
                            )

                        with hero_row_1[1]:
                            scanner_compact_card(
                                "Risk-Adjusted",
                                best_recommendation_icon,
                                tone="green" if "BUY" in best_recommendation_icon else "yellow",
                            )

                        with hero_row_1[2]:
                            scanner_compact_card(
                                "Score",
                                f"{best_score:.1f}",
                                tone="blue",
                            )

                        with hero_row_2[0]:
                            scanner_compact_card(
                                "Rating",
                                best_rating or "N/A",
                                tone="blue",
                            )

                        with hero_row_2[1]:
                            scanner_compact_card(
                                "Peer Rank",
                                rank_text or "N/A",
                                tone="blue",
                            )

                        with hero_row_2[2]:
                            scanner_compact_card(
                                "Leadership",
                                best_leadership or "N/A",
                                tone="green" if best_leadership == "ELITE" else "yellow",
                            )
        
                    concise_rank = rank_text or "N/A"
                    concise_earnings = (
                        "Earnings Clear"
                        if best_earnings in ("NONE", "LOW", "")
                        else f"{best_earnings} Earnings Risk"
                    )

                    st.success(
                        f"{best_symbol or 'N/A'} • {best_sector or 'N/A'} #{concise_rank} • "
                        f"RS {best_rs:.2f} • {best_leadership or 'N/A'} • "
                        f"{concise_earnings} • {best_research_signal} → {best_recommendation}"
                    )
                
            # =================================================
            # SIMPLIFIED TOP OPPORTUNITIES
            # =================================================
        
            st.markdown("#### Top Opportunities")
        
            ranking_display_df = ranking_df.copy()
        
            if "trade_recommendation" in ranking_display_df.columns:
                recommendation_map = {
                    "STRONG BUY": "🟢 STRONG BUY",
                    "BUY": "🟢 BUY",
                    "WATCH": "🟡 WATCH",
                    "HOLD": "⚪ HOLD",
                    "AVOID": "🔴 AVOID",
                    "SELL": "🔴 SELL",
                }
        
                ranking_display_df["recommendation"] = (
                    ranking_display_df["trade_recommendation"]
                    .astype(str)
                    .str.upper()
                    .map(recommendation_map)
                    .fillna(ranking_display_df["trade_recommendation"])
                )
        
            ranking_cols = [
                "display_symbol",
                "symbol",
                "recommendation",
                "opportunity_score_pct",
                "overall_rating",
                "sector",
                "sector_rank",
                "leadership_tier",
                "trend",
                "rs_score",
                "earnings_risk_label",
                "price",
            ]
        
            ranking_cols = [
                col for col in ranking_cols
                if col in ranking_display_df.columns
            ]
        
            top_opportunities_df = ranking_display_df[ranking_cols].head(25).copy()

            if "leadership_tier" in top_opportunities_df.columns:
                top_opportunities_df["leadership_tier"] = top_opportunities_df[
                    "leadership_tier"
                ].apply(leadership_badge)

            st.dataframe(
                top_opportunities_df.style.apply(
                    highlight_top_opportunity,
                    axis=1,
                ),
                width="stretch",
                hide_index=True,
                height=320,
            )

        # =====================================================
        # IGNORED / NON-EXECUTABLE ROWS + RAW SIGNALS
        # =====================================================

        if raw_signals and not ranking_df.empty:

            left_hold_rows = st.session_state.get(
                "scanner_last_hold_rows",
                [],
            )

            left_hold_df = (
                pd.DataFrame(clean_plan_rows(left_hold_rows))
                if left_hold_rows
                else pd.DataFrame()
            )

            if not left_hold_df.empty:
                with st.expander(
                    "Ignored / Non-Executable Scanner Rows",
                    expanded=False,
                ):
                    st.markdown(
                        """
                        <div class="scanner-section-card scanner-section-yellow">
                            <div class="scanner-section-title">Ignored / Non-Executable</div>
                            <div class="scanner-section-value">Signals filtered by risk, sizing, or long-only rules</div>
                            <div class="scanner-section-note">Useful for diagnostics, but not current execution candidates.</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.dataframe(
                        left_hold_df,
                        width="stretch",
                        height=320,
                    )

            with st.expander(
                "Full Raw Scanner Signals",
                expanded=False,
            ):
                st.markdown(
                    """
                    <div class="scanner-section-card scanner-section-blue">
                        <div class="scanner-section-title">Raw Scanner Signals</div>
                        <div class="scanner-section-value">Full model output</div>
                        <div class="scanner-section-note">Complete scanner table for audit and troubleshooting.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.dataframe(
                    ranking_df,
                    width="stretch",
                    hide_index=True,
                    height=320,
                )

        # =====================================================

        # =====================================================
        # PORTFOLIO POSITIONS
        # =====================================================

        positions = get_portfolio_positions()

        if positions:

            positions_df = pd.DataFrame(positions).T

            for col in positions_df.columns:
                if positions_df[col].dtype == "object":
                    positions_df[col] = (
                        positions_df[col]
                        .astype(str)
                    )

            with st.expander(
                f"Portfolio Positions ({len(positions_df)})",
                expanded=False,
            ):
                scanner_tip(
                    "The scanner uses current positions to avoid opening shorts and to avoid adding beyond the target position size."
                )
                st.dataframe(
                    positions_df,
                    width="stretch",
                    height=220,
                )

        else:
            st.info("No portfolio positions.")

    with dashboard_right:
        st.subheader("System Status")
        scanner_tip(
            "This panel summarizes the current market regime, risk state, exposure, positions, and event-risk background."
        )

        # =====================================================
        # SCANNER REGIME BANNER (v73)
        # =====================================================

        scanner_regime = str(
            first_session_value(
                [
                    "market_reaction_scanner_regime",
                    "scanner_regime",
                    "market_regime",
                    "market_reaction_regime",
                ],
                market_ctx.get("regime_label", "SELECTIVE"),
            )
            or "SELECTIVE"
        ).upper().strip()

        if scanner_regime in ("RISK_ON", "RISK-ON"):
            st.success(
                "🟢 RISK-ON MARKET • Leadership expanding • Full participation"
            )

        elif scanner_regime in ("DEFENSIVE", "RISK_OFF", "RISK-OFF"):
            st.error(
                "🔴 DEFENSIVE MARKET • Reduce exposure • Smaller position sizes"
            )

        else:
            st.warning(
                "🟡 SELECTIVE MARKET • Leadership concentrated • Focus on strongest sectors"
            )

        economic_ctx = economic_calendar_context()
        earnings_ctx = earnings_universe_context()

        compact_risk_state = str(
            risk_snapshot.get("risk_state", "UNKNOWN")
        )

        compact_gross_exposure = safe_float(
            risk_snapshot.get("gross_exposure"),
            0.0,
        )

        compact_open_positions = risk_snapshot.get(
            "open_positions",
            0,
        )

        compact_max_positions = risk_snapshot.get(
            "max_open_positions",
            0,
        )

        compact_pipeline_status = (
            "READY"
            if pipeline
            else "MISSING"
        )

        with st.container(border=True):

            status_cards = [
                ("Scanner", scanner_status_display),
                ("Pipeline", compact_pipeline_status),
                ("Risk", compact_risk_state),
                ("Exposure", f"${compact_gross_exposure:,.0f}"),
            ]

            for index in range(0, len(status_cards), 2):
                status_cols = responsive_columns(2)

                for status_col, (status_label, status_value) in zip(
                    status_cols,
                    status_cards[index:index + 2],
                ):
                    with status_col:
                        status_label_text = str(status_label)
                        status_value_text = str(status_value)

                        st.markdown(
                            f"""
                            <div class="scanner-section-card scanner-section-blue" style="min-height:64px;">
                                <div class="scanner-section-title">{status_label_text}</div>
                                <div class="scanner-section-value" style="font-size:1rem; overflow-wrap:anywhere;">
                                    {status_value_text}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

        with st.popover("Diagnostics"):
            st.write(
                {
                    "Economic Calendar": economic_ctx,
                    "Earnings Risk": earnings_ctx,
                    "Market Reaction": {
                        "Regime": market_ctx["regime_label"],
                        "Score": market_ctx["score"],
                        "Confidence": market_ctx["confidence"],
                        "Event": market_ctx["event"],
                        "Playbook": market_ctx["playbook"],
                        "BUY Allowed": market_ctx["buy_allowed"],
                        "SELL Allowed": market_ctx["sell_allowed"],
                        "Execution Multiplier": market_ctx["execution_multiplier"],
                    },
                    "Position Sizing": {
                        "Sizing Model": "Equal Weight / Cash + Positions",
                        "Position Source": st.session_state.get(
                            "scanner_position_source",
                            "UNKNOWN",
                        ),
                        "Cash Value": scanner_cash_value(),
                        "Positions Value": scanner_positions_value(),
                        "Trading Equity Used": scanner_account_equity(),
                        "Fallback Portfolio Value": SCANNER_FALLBACK_PORTFOLIO_VALUE,
                        "Target Position %": SCANNER_TARGET_POSITION_PCT,
                        "Target Position Value": scanner_target_position_value(),
                        "Minimum Quantity": SCANNER_MIN_QTY,
                    },
                    "Compact Status Details": {
                        "Positions": f"{compact_open_positions}/{compact_max_positions}",
                        "Portfolio Position Rows": len(positions),
                        "Economic": f"{economic_ctx['label']} • {economic_ctx['score']}",
                        "Earnings": f"{earnings_ctx['label']} • {earnings_ctx['score']}",
                    },
                    "Risk Snapshot": risk_snapshot,
                    "IBKR Account Snapshot": account_snapshot,
                    "IBKR Account Values": account_values,
                    "IBKR Account Summary Row Count": len(account_summary_rows),
                    "IBKR Account Summary Preview": account_summary_rows[:10],
                    "Raw Scanner Status": scanner_status_raw,
                }
            )

        last_error = st.session_state.get(
            "scanner_last_error",
            "",
        )

        if last_error:
            st.warning(
                f"Scanner warning: {last_error}"
            )

        # =====================================================
        # RIGHT-RAIL LEADERSHIP WORKBENCH
        # Keeps the right column active instead of leaving a blank field.
        # =====================================================

        if raw_signals and not ranking_df.empty:
            # =================================================
            # SECTOR LEADERSHIP SNAPSHOT
            # =================================================
        
            sector_summary_df = pd.DataFrame()
        
            if not ranking_df.empty and "sector" in ranking_df.columns:
                sector_rows = []
        
                for sector, group in ranking_df.groupby("sector", dropna=False):
                    group = group.copy()
                    sector_name = str(sector or "Unknown")
        
                    avg_score = round(
                        safe_float(
                            group.get("opportunity_score_pct", pd.Series(dtype=float))
                            .mean(),
                            0.0,
                        ),
                        1,
                    )
        
                    elite_count = int(
                        (
                            group.get("leadership_tier", pd.Series(dtype=str))
                            .astype(str)
                            .str.upper()
                            == "ELITE"
                        ).sum()
                    )
        
                    leader = ""
        
                    if "symbol" in group.columns:
                        leader = str(
                            group.sort_values(
                                by=[
                                    "opportunity_score_pct",
                                    "model_score",
                                    "rs_score",
                                ],
                                ascending=False,
                            )
                            .iloc[0]
                            .get("symbol", "")
                        )
        
                    sector_rows.append({
                        "sector": sector_name,
                        "sector_score": avg_score,
                        "symbols": len(group),
                        "elite_count": elite_count,
                        "sector_leader": leader,
                    })
        
                sector_summary_df = pd.DataFrame(sector_rows)
        
                if not sector_summary_df.empty:
                    sector_summary_df = sector_summary_df.sort_values(
                        by=["sector_score", "elite_count", "symbols"],
                        ascending=False,
                    )
        
            if not sector_summary_df.empty:
                if universe_mode == "FOREX PULSE":
                    st.markdown("#### 📊 Currency Pair Leadership")
                    scanner_tip(
                        "This ranks the strongest FX pairs in the selected Forex universe. Forex has currency-pair groups instead of stock sectors."
                    )
                elif universe_mode == "CURRENCY ETFs":
                    st.markdown("#### 📊 Currency ETF Leadership")
                    scanner_tip(
                        "This ranks macro currency ETF proxies such as UUP, FXE, FXB, FXY, FXC, and CYB."
                    )
                else:
                    st.markdown("#### 📊 Sector Leadership")
                    scanner_tip(
                        "Strong sectors help confirm whether leadership is broad and healthy or concentrated in only a few names."
                    )
        
                sector_display_df = sector_summary_df.copy()
                sector_display_df["strength"] = sector_display_df[
                    "sector_score"
                ].apply(sector_strength_label)
        
                sector_display_cols = [
                    "sector",
                    "strength",
                    "sector_score",
                    "symbols",
                    "elite_count",
                    "sector_leader",
                ]
        
                st.dataframe(
                    sector_display_df[sector_display_cols],
                    width="stretch",
                    hide_index=True,
                    height=220,
                )
            # =================================================
            # ELITE CANDIDATES
            # =================================================
        
            elite_df = ranking_df.copy()
        
            if not elite_df.empty:
                elite_df = elite_df[
                    (
                        elite_df.get("overall_rating", pd.Series(dtype=str))
                        .astype(str)
                        .isin(["A+", "A", "A-"])
                    )
                    & (
                        elite_df.get("leadership_tier", pd.Series(dtype=str))
                        .astype(str)
                        .str.upper()
                        .isin(["ELITE", "LEADER"])
                    )
                ]
        
            if not elite_df.empty:
                st.markdown("#### ⭐ Elite Candidates")
                scanner_tip(
                    "These are high-quality candidates with strong ratings and leadership. They still need risk-plan approval before execution."
                )
        
                elite_cols = [
                    "display_symbol",
                    "symbol",
                    "trade_recommendation",
                    "opportunity_score_pct",
                    "overall_rating",
                    "sector",
                    "sector_rank",
                    "leadership_tier",
                    "earnings_risk_label",
                    "price",
                ]
        
                elite_cols = [
                    col for col in elite_cols
                    if col in elite_df.columns
                ]
        
                elite_display_df = elite_df[elite_cols].head(12).copy()

                if "leadership_tier" in elite_display_df.columns:
                    elite_display_df["leadership_tier"] = elite_display_df[
                        "leadership_tier"
                    ].apply(leadership_badge)

                st.dataframe(
                    elite_display_df,
                    width="stretch",
                    hide_index=True,
                    height=260,
                )
        
                quick_symbols = [
                    str(symbol or "").upper().strip()
                    for symbol in elite_df["symbol"].head(12).tolist()
                    if str(symbol or "").strip()
                ] if "symbol" in elite_df.columns else []
        
                if quick_symbols:
                    q1, q2 = responsive_columns([2, 1])
        
                    with q1:
                        selected_research_symbol = st.selectbox(
                            "Send elite candidate to Research Stock",
                            quick_symbols,
                            key="scanner_elite_research_symbol_v37_1",
                        )
        
                    with q2:
                        st.write("")
                        st.write("")
        
                        if st.button(
                            "Open Research Stock",
                            width="stretch",
                            key="scanner_open_research_stock_v37_4",
                        ):
                            open_research_stock_from_scanner(
                                selected_research_symbol
                            )
        
            else:
                st.info(
                    "No elite candidates yet. Run Scanner again or wait for stronger "
                    "technical confirmation."
                )
        

        # =====================================================
        # RIGHT-COLUMN ANALYSIS PANELS
        # =====================================================

        with st.expander("Ranking Diagnostics", expanded=False):
            if raw_signals and not ranking_df.empty:

                # =================================================
                # WHY IT RANKED HERE
                # =================================================
        
                if not ranking_df.empty:
                    st.markdown("#### 🔎 Why It Ranked Here")
                    scanner_tip(
                        "This explains the main reasons behind the ranking so you can see whether the score is driven by trend, sector leadership, or event risk."
                    )
        
                    why_rows = []
        
                    for _, row in ranking_df.head(5).iterrows():
                        symbol = str(row.get("symbol", "") or "")
                        sector = str(row.get("sector", "") or "")
                        recommendation = str(
                            row.get("trade_recommendation", "WATCH") or "WATCH"
                        ).upper().strip()
                        rating = str(row.get("overall_rating", "") or "")
                        leadership = str(
                            row.get("leadership_tier", "") or ""
                        ).upper().strip()
                        sector_rank = row.get("sector_rank")
                        sector_count = row.get("sector_count")
                        trend = str(row.get("trend", "") or "").upper().strip()
                        rs_score = safe_float(row.get("rs_score"), 0.0)
                        earnings = str(
                            row.get("earnings_risk_label", "NONE") or "NONE"
                        ).upper().strip()
                        earnings_days = row.get("earnings_days_until")
        
                        leadership_badge = {
                            "ELITE": "🟢 ELITE",
                            "LEADER": "🟢 LEADER",
                            "STRONG": "🟡 STRONG",
                            "AVERAGE": "⚪ AVERAGE",
                            "WEAK": "🔴 WEAK",
                        }.get(leadership, leadership or "N/A")
        
                        earnings_badge = {
                            "NONE": "🟢 CLEAR",
                            "LOW": "🟢 LOW",
                            "MEDIUM": "🟡 MEDIUM",
                            "HIGH": "🟠 HIGH",
                            "EXTREME": "🔴 EXTREME",
                        }.get(earnings, earnings or "N/A")
        
                        recommendation_badge = {
                            "STRONG BUY": "🟢 STRONG BUY",
                            "BUY": "🟢 BUY",
                            "WATCH": "🟡 WATCH",
                            "HOLD": "⚪ HOLD",
                            "AVOID": "🔴 AVOID",
                            "SELL": "🔴 SELL",
                        }.get(recommendation, recommendation or "N/A")
        
                        rank_text = ""
                        if sector_rank is not None and sector_count is not None:
                            rank_text = f"#{sector_rank}/{sector_count} {sector}"
        
                        reason_parts = []
        
                        if rank_text:
                            reason_parts.append(rank_text)
        
                        if leadership:
                            reason_parts.append(leadership_badge)
        
                        if trend == "BULLISH":
                            reason_parts.append("bullish trend")
                        elif trend == "BEARISH":
                            reason_parts.append("bearish trend")
        
                        if rs_score > 0:
                            reason_parts.append(f"RS {rs_score:.4f}")
        
                        if earnings in ("NONE", "LOW", ""):
                            reason_parts.append("earnings clear")
                        else:
                            try:
                                days_text = int(earnings_days)
                                reason_parts.append(f"earnings in {days_text} day(s)")
                            except Exception:
                                reason_parts.append(f"{earnings.lower()} earnings risk")
        
                        why_rows.append({
                            "symbol": symbol,
                            "recommendation": recommendation_badge,
                            "rating": rating,
                            "why_it_ranked_here": " • ".join(reason_parts),
                        })
        
                    if why_rows:
                        st.dataframe(
                            pd.DataFrame(why_rows),
                            width="stretch",
                            hide_index=True,
                            height=260,
                        )
        



            if raw_signals and not ranking_df.empty:

                # =================================================
                # OPPORTUNITY DIAGNOSTICS
                # =================================================

                st.markdown("#### 🏆 Opportunity Diagnostics")
                scanner_tip(
                    "How the score was built from trend, relative strength, sector leadership, event risk, and market regime."
                )

                thesis_rows = []

                for _, row in ranking_df.head(6).iterrows():
                    symbol = str(row.get("symbol", ""))
                    recommendation = str(row.get("trade_recommendation", ""))
                    rating = str(row.get("overall_rating", ""))
                    sector = str(row.get("sector", ""))
                    leadership = str(row.get("leadership_tier", ""))
                    trend = str(row.get("trend", ""))
                    rs_score = safe_float(row.get("rs_score"), 0.0)
                    earnings = str(row.get("earnings_risk_label", "NONE"))
                    sector_rank = row.get("sector_rank")
                    sector_count = row.get("sector_count")

                    thesis_parts = []

                    if trend.upper() == "BULLISH":
                        thesis_parts.append("bullish trend")
                    elif trend.upper() == "BEARISH":
                        thesis_parts.append("bearish trend")

                    if rs_score >= 1.05:
                        thesis_parts.append("strong relative strength")

                    if leadership.upper() in ("ELITE", "LEADER"):
                        thesis_parts.append(
                            f"{leadership.lower()} sector leadership"
                        )

                    if earnings.upper() not in ("NONE", "LOW", ""):
                        thesis_parts.append(f"{earnings.lower()} earnings risk")

                    thesis = "; ".join(thesis_parts) or "mixed/neutral setup"

                    thesis_rows.append({
                        "symbol": symbol,
                        "recommendation": recommendation,
                        "rating": rating,
                        "sector": sector,
                        "rank": (
                            f"{sector_rank}/{sector_count}"
                            if sector_rank is not None and sector_count is not None
                            else ""
                        ),
                        "leadership": leadership,
                        "thesis": thesis,
                    })

                if thesis_rows:
                    st.dataframe(
                        pd.DataFrame(thesis_rows),
                        width="stretch",
                        hide_index=True,
                        height=255,
                    )

                diagnostic_cols = [
                    "display_symbol",
                    "symbol",
                    "signal",
                    "scanner_action",
                    "action",
                    "opportunity_score",
                    "opportunity_score_pct",
                    "overall_rating",
                    "sector",
                    "sector_rank",
                    "sector_count",
                    "leadership_tier",
                    "model_score",
                    "trend",
                    "rs_score",
                    "earnings_risk_label",
                    "economic_risk_label",
                    "market_reaction_regime",
                    "combined_event_risk_label",
                    "price",
                ]

                diagnostic_cols = [
                    col for col in diagnostic_cols
                    if col in ranking_df.columns
                ]

                st.dataframe(
                    ranking_df[diagnostic_cols].head(12),
                    width="stretch",
                    hide_index=True,
                    height=305,
                )

    st.divider()

    # RISK-AWARE EXECUTION PLAN
    # =====================================================

    st.subheader("Risk-Aware Execution Plan")
    scanner_tip(
        "This is the safety layer. A symbol can rank well but still be ignored if it fails sizing, portfolio, market, or risk-engine checks."
    )

    plan = st.session_state.get("scanner_last_risk_plan", [])
    hold_rows = st.session_state.get("scanner_last_hold_rows", [])

    plan_df = (
        pd.DataFrame(clean_plan_rows(plan))
        if plan
        else pd.DataFrame()
    )

    hold_df = (
        pd.DataFrame(clean_plan_rows(hold_rows))
        if hold_rows
        else pd.DataFrame()
    )

    executable_count = (
        int(plan_df["executable"].fillna(False).sum())
        if not plan_df.empty and "executable" in plan_df
        else 0
    )

    planned_count = len(plan_df)
    blocked_count = planned_count - executable_count
    hold_count = len(hold_df)

    blocked_open_short_count = 0
    at_target_count = 0
    risk_off_hold_count = 0

    if not hold_df.empty:

        if "position_action" in hold_df:
            blocked_open_short_count = int(
                (hold_df["position_action"] == "BLOCKED_OPEN_SHORT").sum()
            )
            at_target_count = int(
                (hold_df["position_action"] == "AT_TARGET_WEIGHT").sum()
            )

        if "market_reaction_overlay" in hold_df:
            risk_off_hold_count = int(
                (
                    hold_df["market_reaction_overlay"]
                    == "MARKET_REACTION_RISK_OFF_HOLD"
                ).sum()
            )

    p1, p2, p3, p4, p5 = responsive_columns(5)
    p1.metric("Executable", executable_count)
    p2.metric("Planned", planned_count)
    p3.metric("Hold / Ignored", hold_count)
    p4.metric("Blocked Shorts", blocked_open_short_count)
    p5.metric("Risk-Off Holds", risk_off_hold_count)

    if executable_count > 0:
        st.success(
            f"{executable_count} executable trade(s) approved by the risk engine."
        )

    elif hold_count > 0 or blocked_count > 0:
        st.info(
            "No executable trades generated. "
            f"{hold_count} row(s) were HOLD / ignored, "
            f"{blocked_open_short_count} SELL row(s) were blocked by long-only rules, "
            f"{at_target_count} BUY row(s) were already at target weight, "
            f"and {risk_off_hold_count} row(s) were held due to Risk-Off conditions."
        )

    else:
        st.info("No scanner plan built yet. Run Scanner, then Build Risk-Aware Plan.")

    if not plan_df.empty:
        with st.expander("Risk Engine Plan Details", expanded=False):
            st.dataframe(plan_df, width="stretch")

            if blocked_count:
                st.markdown("#### Blocked Risk Engine Rows")
                blocked_df = (
                    plan_df[plan_df["executable"] == False]
                    if "executable" in plan_df
                    else plan_df
                )
                st.dataframe(blocked_df, width="stretch")

    st.divider()

    # =====================================================
    # EXECUTION CONTROLS
    # =====================================================

    current_mode = str(st.session_state.get("mode", "SIM")).upper().strip()
    is_live_mode = current_mode == "LIVE"

    plan = st.session_state.get("scanner_last_risk_plan", [])

    has_executable_rows = any(
        bool(row.get("executable"))
        and normalize_action(row.get("execution_action")) in ("BUY", "SELL")
        for row in plan
        if isinstance(row, dict)
    )

    if has_executable_rows:

        st.subheader("Execution Controls")

        scanner_tip(
            "Execution is intentionally separated from scanning. "
            "Only approved executable rows can be sent, and confirmation is required."
        )

        executable_rows_count = sum(
            1
            for row in plan
            if isinstance(row, dict)
            and bool(row.get("executable"))
            and normalize_action(row.get("execution_action")) in ("BUY", "SELL")
        )

        approved_rows_count = sum(
            1
            for row in plan
            if isinstance(row, dict)
            and bool(row.get("risk_approved"))
        )

        if is_live_mode:
            st.error("🚨 LIVE TRADING MODE — REAL ORDERS CAN BE SENT")

        with st.container(border=True):

            exec_cols = responsive_columns(
                [1.0, 1.05, 1.2, 1.35, 1.55, 0.95]
            )

            with exec_cols[0]:
                st.caption("Mode")

                mode_tone = (
                    "red"
                    if is_live_mode
                    else "blue"
                )

                scanner_compact_card(
                    "Execution",
                    "LIVE" if is_live_mode else "SIM",
                    tone=mode_tone,
                )

            with exec_cols[1]:
                st.caption("Approved")

                scanner_compact_card(
                    "Executable",
                    executable_rows_count,
                    tone=(
                        "green"
                        if executable_rows_count
                        else "yellow"
                    ),
                )

            with exec_cols[2]:
                st.caption("Confirmation")

                confirm_execute = st.checkbox(
                    "Arm execution",
                    key="scanner_confirm_execute_v35_3",
                )

            live_ack = True
            live_phrase_ok = True

            with exec_cols[3]:
                st.caption("Safety")

                if is_live_mode:

                    with st.popover(
                        "Live Safety",
                        use_container_width=True,
                    ):

                        st.warning(
                            "LIVE mode requires confirmation and the exact typed phrase before routing broker orders."
                        )

                        live_ack = st.checkbox(
                            "I understand this sends LIVE broker orders",
                            key="scanner_live_ack_v35_3",
                        )

                        live_phrase = st.text_input(
                            "Type EXECUTE LIVE ORDERS to arm live execution",
                            key="scanner_live_phrase_v35_3",
                        )

                        live_phrase_ok = (
                            live_phrase.strip().upper()
                            == "EXECUTE LIVE ORDERS"
                        )

                        if (
                            confirm_execute
                            and live_ack
                            and live_phrase_ok
                        ):
                            st.error(
                                "🚨 LIVE TRADING ARMED"
                            )
                        else:
                            st.warning(
                                "LIVE execution is locked."
                            )

                else:

                    scanner_compact_card(
                        "Routing",
                        "Simulated Orders",
                        tone="blue",
                    )

            execution_unlocked = (
                confirm_execute
                and live_ack
                and live_phrase_ok
            )

            with exec_cols[4]:
                st.caption("Action")

                execute_btn = st.button(
                    "Execute Approved Signals Only",
                    width="stretch",
                    disabled=not execution_unlocked,
                    key="scanner_execute_v35_3",
                )

            with exec_cols[5]:
                st.caption("Details")

                with st.popover(
                    "Rules",
                    use_container_width=True,
                ):

                    st.caption(
                        "Only rows with risk_approved=True and execution_action BUY/SELL are routed to pipeline."
                    )

                    st.metric(
                        "Approved Rows",
                        approved_rows_count,
                    )

                    st.metric(
                        "Executable Rows",
                        executable_rows_count,
                    )

                    if is_live_mode:

                        st.warning(
                            "LIVE mode requires checkbox confirmation and the exact typed phrase before routing orders."
                        )

                    else:

                        st.info(
                            "SIM mode active. Orders are simulated unless pipeline mode says otherwise."
                        )

        if execute_btn:

            if (
                is_live_mode
                and not execution_unlocked
            ):
                st.error(
                    "LIVE execution blocked. Required confirmations missing."
                )
                st.stop()

            results = execute_plan(
                st.session_state.get(
                    "scanner_last_risk_plan",
                    [],
                )
            )

            st.session_state[
                "scanner_last_execution_results"
            ] = results

            st.success(
                f"Scanner execution complete. Rows processed: {len(results)}"
            )
    # =====================================================
    # EXECUTION RESULTS
    # =====================================================

    results = st.session_state.get(
        "scanner_last_execution_results",
        [],
    )

    results = [
        row for row in results
        if isinstance(row, dict)
    ] if isinstance(results, list) else []

    if results:

        st.subheader("Last Execution Results")

        result_df = pd.DataFrame(
            clean_result_rows(results)
        )

        status_counts = {}

        if "status" in result_df:
            status_counts = (
                result_df["status"]
                .astype(str)
                .str.upper()
                .value_counts()
                .to_dict()
            )

        complete_count = status_counts.get("COMPLETE", 0)
        partial_count = status_counts.get("PARTIAL", 0)
        skipped_count = status_counts.get("SKIPPED", 0)
        blocked_count = status_counts.get("BLOCKED", 0)
        rejected_count = status_counts.get("REJECTED", 0)
        error_count = status_counts.get("ERROR", 0)
        timeout_count = status_counts.get("TIMEOUT", 0)

        failed_count = (
            rejected_count
            + error_count
            + timeout_count
        )

        r1, r2, r3, r4, r5 = responsive_columns(5)
        r1.metric("Complete", complete_count)
        r2.metric("Partial", partial_count)
        r3.metric("Skipped", skipped_count)
        r4.metric("Blocked", blocked_count)
        r5.metric("Failed", failed_count)

        if complete_count or partial_count:
            st.success(
                f"{complete_count + partial_count} order result(s) completed."
            )

        elif skipped_count or blocked_count:
            st.info(
                f"{skipped_count + blocked_count} execution row(s) were skipped or blocked."
            )

        elif failed_count:
            st.error(
                f"{failed_count} execution row(s) failed."
            )

        st.markdown("#### Execution Result Details")
        st.dataframe(
            result_df,
            width="stretch",
        )

        st.divider()

    # =====================================================
    # RISK SNAPSHOT
    # =====================================================

    with st.expander(
        "Risk Snapshot",
        expanded=False,
    ):

        sync_market_reaction_to_risk_engine()
        risk_snapshot = safe_snapshot(risk_engine)

        if risk_snapshot:

            risk_state = str(
                risk_snapshot.get("risk_state", "UNKNOWN")
            )

            risk_reason = str(
                risk_snapshot.get("risk_state_reason", "")
            )

            market_regime = str(
                risk_snapshot.get("market_reaction_regime", "UNKNOWN")
            )

            market_score = safe_float(
                risk_snapshot.get("market_reaction_score"),
                0.0,
            )

            market_confidence = safe_float(
                risk_snapshot.get("market_reaction_confidence"),
                0.0,
            )

            gross_exposure = safe_float(
                risk_snapshot.get("gross_exposure"),
                0.0,
            )

            open_positions = int(
                safe_float(
                    risk_snapshot.get("open_positions"),
                    0.0,
                )
            )

            max_open_positions = int(
                safe_float(
                    risk_snapshot.get("max_open_positions"),
                    0.0,
                )
            )

            daily_trades = int(
                safe_float(
                    risk_snapshot.get("daily_trades"),
                    0.0,
                )
            )

            max_daily_trades = int(
                safe_float(
                    risk_snapshot.get("max_daily_trades"),
                    0.0,
                )
            )

            r1, r2, r3, r4, r5, r6 = responsive_columns(6)

            r1.metric("Risk State", risk_state)
            r2.metric("Regime", market_regime)
            r3.metric("Exposure", f"${gross_exposure:,.0f}")
            r4.metric(
                "Positions",
                f"{open_positions}/{max_open_positions}",
            )
            r5.metric("Score", f"{market_score:.0f}")
            r6.metric("Confidence", f"{market_confidence:.0f}")

            st.caption(
                (
                    f"Reason: {risk_reason} · "
                    f"Daily Trades: {daily_trades}/{max_daily_trades}"
                )
                if risk_reason
                else f"Daily Trades: {daily_trades}/{max_daily_trades}"
            )

            diagnostics_available = any(
                key in risk_snapshot
                for key in (
                    "positions",
                    "last_prices",
                    "last_check",
                    "last_sync",
                    "last_batch_check",
                )
            )

            if diagnostics_available:
                with st.popover("Diagnostics"):
                    diagnostic_keys = [
                        "positions",
                        "last_prices",
                        "last_check",
                        "last_sync",
                        "last_batch_check",
                    ]

                    diagnostics = {
                        key: risk_snapshot.get(key)
                        for key in diagnostic_keys
                        if key in risk_snapshot
                    }

                    st.json(diagnostics)

        else:
            st.info("No risk snapshot available.")

