from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

import streamlit as st

from core.trading_preferences import (
    PROFILE_DEFAULTS,
    build_profile_defaults,
    get_trading_preferences,
    save_trading_preferences,
)


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _ensure_widget_default(key: str, default: Any) -> Any:
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def _profile_readout(values: Dict[str, Any]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Risk Per Trade", f"{_safe_float(values.get('risk_per_trade_pct'), 1.0):.2f}%")
    with c2:
        st.metric("Max Portfolio Risk", f"{_safe_float(values.get('max_portfolio_risk_pct'), 6.0):.2f}%")
    with c3:
        st.metric("Max Open Trades", f"{_safe_int(values.get('max_open_trades'), 12)}")
    with c4:
        st.metric("Max Position Size", f"{_safe_float(values.get('max_position_size_pct'), 8.0):.2f}%")
    st.caption(f"Portfolio Overlap Warning Level: {_safe_float(values.get('portfolio_overlap_warning_threshold'), 0.85):.2f}")


st.title("Trading Preferences")
st.caption("Account-wide policy settings used by Trade Management Plan.")

prefs = get_trading_preferences()
current_profile = str(prefs.get("risk_profile") or "Balanced")
account_size = _safe_float(prefs.get("account_size"), 100000.0)
current_custom = deepcopy(prefs.get("custom") or PROFILE_DEFAULTS["Balanced"])

_ensure_widget_default("tpref_account_size", account_size)
_ensure_widget_default("tpref_risk_profile", current_profile)
_ensure_widget_default("tpref_custom_risk_per_trade", _safe_float(current_custom.get("risk_per_trade_pct"), 1.0))
_ensure_widget_default("tpref_custom_max_portfolio_risk", _safe_float(current_custom.get("max_portfolio_risk_pct"), 6.0))
_ensure_widget_default("tpref_custom_max_open_trades", _safe_int(current_custom.get("max_open_trades"), 12))
_ensure_widget_default("tpref_custom_max_position_size", _safe_float(current_custom.get("max_position_size_pct"), 8.0))
_ensure_widget_default("tpref_tp1", _safe_float(current_custom.get("tp1_allocation"), 50.0))
_ensure_widget_default("tpref_tp2", _safe_float(current_custom.get("tp2_allocation"), 40.0))
_ensure_widget_default("tpref_tp3", _safe_float(current_custom.get("tp3_allocation"), 10.0))
_ensure_widget_default("tpref_move_be", bool(current_custom.get("move_stop_to_breakeven", True)))
_ensure_widget_default("tpref_trailing", bool(current_custom.get("trailing_stop_enabled", False)))
_ensure_widget_default("tpref_trailing_method", str(current_custom.get("trailing_stop_method") or "ATR"))
_ensure_widget_default("tpref_atr_multiple", _safe_float(current_custom.get("atr_trailing_multiple"), 2.0))
_ensure_widget_default("tpref_time_stop_enabled", bool(current_custom.get("time_stop_enabled", True)))
_ensure_widget_default("tpref_time_stop_days", _safe_int(current_custom.get("time_stop_days"), 10))
_ensure_widget_default("tpref_exit_earnings", bool(current_custom.get("exit_before_earnings", True)))
_ensure_widget_default("tpref_avoid_weekend", bool(current_custom.get("avoid_holding_over_weekend", False)))
_ensure_widget_default("tpref_overlap_warning_level", _safe_float(current_custom.get("portfolio_overlap_warning_threshold"), 0.85))

with st.container(border=True):
    st.subheader("1) Account Policy")
    c1, c2 = st.columns(2)
    with c1:
        account_size = st.number_input("Account Size", min_value=1000.0, max_value=25000000.0, step=1000.0, key="tpref_account_size")
    with c2:
        risk_profile = st.selectbox(
            "Risk Profile",
            options=["Conservative", "Balanced", "Aggressive", "Custom"],
            index=["Conservative", "Balanced", "Aggressive", "Custom"].index(current_profile)
            if current_profile in {"Conservative", "Balanced", "Aggressive", "Custom"}
            else 1,
            key="tpref_risk_profile",
        )

    if risk_profile != "Custom":
        st.caption("Profile defaults are automatically scaled by account size.")
        _profile_readout(build_profile_defaults(account_size, risk_profile))
    else:
        st.caption("Custom profile unlocked: edit account-wide risk limits directly.")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            current_custom["risk_per_trade_pct"] = st.number_input("Risk Per Trade %", min_value=0.05, max_value=10.0, step=0.05, key="tpref_custom_risk_per_trade")
        with c2:
            current_custom["max_portfolio_risk_pct"] = st.number_input("Max Portfolio Risk %", min_value=0.5, max_value=50.0, step=0.1, key="tpref_custom_max_portfolio_risk")
        with c3:
            current_custom["max_open_trades"] = st.number_input("Max Open Trades", min_value=1, max_value=100, step=1, key="tpref_custom_max_open_trades")
        with c4:
            current_custom["max_position_size_pct"] = st.number_input("Max Position Size %", min_value=0.1, max_value=100.0, step=0.5, key="tpref_custom_max_position_size")

with st.container(border=True):
    st.subheader("2) Trade Management Defaults")
    source = prefs.get("effective", {})
    if risk_profile == "Custom":
        source = current_custom

    c1, c2, c3 = st.columns(3)
    with c1:
        current_custom["tp1_allocation"] = st.number_input("TP1 Allocation %", min_value=0.0, max_value=100.0, step=1.0, disabled=risk_profile != "Custom", key="tpref_tp1")
    with c2:
        current_custom["tp2_allocation"] = st.number_input("TP2 Allocation %", min_value=0.0, max_value=100.0, step=1.0, disabled=risk_profile != "Custom", key="tpref_tp2")
    with c3:
        current_custom["tp3_allocation"] = st.number_input("TP3 Allocation %", min_value=0.0, max_value=100.0, step=1.0, disabled=risk_profile != "Custom", key="tpref_tp3")

    total_tp = (
        _safe_float(current_custom.get("tp1_allocation"), 0.0)
        + _safe_float(current_custom.get("tp2_allocation"), 0.0)
        + _safe_float(current_custom.get("tp3_allocation"), 0.0)
    )
    if abs(total_tp - 100.0) > 0.001:
        st.warning(f"TP allocation total is {total_tp:.1f}%. Institutional workflow expects 100%.")

    c4, c5, c6 = st.columns(3)
    with c4:
        current_custom["move_stop_to_breakeven"] = st.checkbox("Move Stop To Breakeven", disabled=risk_profile != "Custom", key="tpref_move_be")
        current_custom["trailing_stop_enabled"] = st.checkbox("Enable Trailing Stop", disabled=risk_profile != "Custom", key="tpref_trailing")
        current_custom["trailing_stop_method"] = st.selectbox(
            "Trailing Stop Method",
            options=["ATR", "Percentage", "Swing Low", "EMA 21", "EMA 50"],
            index=["ATR", "Percentage", "Swing Low", "EMA 21", "EMA 50"].index(str(current_custom.get("trailing_stop_method") or "ATR"))
            if str(current_custom.get("trailing_stop_method") or "ATR") in {"ATR", "Percentage", "Swing Low", "EMA 21", "EMA 50"}
            else 0,
            disabled=risk_profile != "Custom",
            key="tpref_trailing_method",
        )
        current_custom["atr_trailing_multiple"] = st.number_input(
            "ATR Multiplier",
            min_value=0.1,
            max_value=20.0,
            step=0.1,
            disabled=risk_profile != "Custom",
            key="tpref_atr_multiple",
        )
        st.caption("ATR is the default trailing method used in Trade Management Plan.")
    with c5:
        current_custom["time_stop_enabled"] = st.checkbox("Enable Time Stop", disabled=risk_profile != "Custom", key="tpref_time_stop_enabled")
        current_custom["time_stop_days"] = st.number_input("Time Stop Days", min_value=1, max_value=252, step=1, disabled=risk_profile != "Custom", key="tpref_time_stop_days")
    with c6:
        current_custom["exit_before_earnings"] = st.checkbox("Exit Before Earnings", disabled=risk_profile != "Custom", key="tpref_exit_earnings")
        current_custom["avoid_holding_over_weekend"] = st.checkbox("Avoid Weekend Holds", disabled=risk_profile != "Custom", key="tpref_avoid_weekend")

with st.container(border=True):
    st.subheader("3) Diversification Warning Defaults")
    if risk_profile == "Custom":
        current_custom["portfolio_overlap_warning_threshold"] = st.number_input("Portfolio Overlap Warning Level", min_value=0.10, max_value=1.00, step=0.01, key="tpref_overlap_warning_level")
        st.caption("Higher values make overlap warnings less sensitive. Default institutional setting is 0.85.")
    else:
        st.metric("Portfolio Overlap Warning Level", f"{_safe_float(source.get('portfolio_overlap_warning_threshold'), 0.85):.2f}")
        st.caption("Only Custom Risk Profile can change this account-wide overlap warning level.")

st.caption("Changes here become the source of truth for account-wide risk controls used in Trade Management Plan.")

if st.button("Save Trading Preferences", type="primary", width="stretch"):
    payload = {
        "account_size": account_size,
        "risk_profile": risk_profile,
        "custom": current_custom,
    }
    updated = save_trading_preferences(payload)
    st.success("Trading Preferences saved.")
    st.json({
        "risk_profile": updated.get("risk_profile"),
        "account_size": updated.get("account_size"),
        "effective": updated.get("effective"),
    })
