from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import streamlit as st

PREFERENCES_KEY = "trading_preferences"
PREFERENCES_VERSION = 1
PREFERENCES_FILE = Path(__file__).resolve().parents[1] / "runtime_state" / "trading_preferences.json"

PROFILE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "Conservative": {
        "risk_per_trade_pct": 0.5,
        "max_portfolio_risk_pct": 4.0,
        "max_open_trades": 8,
        "max_position_size_pct": 6.0,
        "portfolio_overlap_warning_threshold": 0.85,
        "tp1_allocation": 50.0,
        "tp2_allocation": 35.0,
        "tp3_allocation": 15.0,
        "move_stop_to_breakeven": True,
        "trailing_stop_enabled": False,
        "trailing_stop_method": "ATR",
        "atr_trailing_multiple": 2.0,
        "time_stop_enabled": True,
        "time_stop_days": 12,
        "exit_before_earnings": True,
        "avoid_holding_over_weekend": True,
    },
    "Balanced": {
        "risk_per_trade_pct": 1.0,
        "max_portfolio_risk_pct": 6.0,
        "max_open_trades": 12,
        "max_position_size_pct": 8.0,
        "portfolio_overlap_warning_threshold": 0.85,
        "tp1_allocation": 50.0,
        "tp2_allocation": 40.0,
        "tp3_allocation": 10.0,
        "move_stop_to_breakeven": True,
        "trailing_stop_enabled": False,
        "trailing_stop_method": "ATR",
        "atr_trailing_multiple": 2.0,
        "time_stop_enabled": True,
        "time_stop_days": 10,
        "exit_before_earnings": True,
        "avoid_holding_over_weekend": False,
    },
    "Aggressive": {
        "risk_per_trade_pct": 1.5,
        "max_portfolio_risk_pct": 8.0,
        "max_open_trades": 16,
        "max_position_size_pct": 12.0,
        "portfolio_overlap_warning_threshold": 0.85,
        "tp1_allocation": 40.0,
        "tp2_allocation": 40.0,
        "tp3_allocation": 20.0,
        "move_stop_to_breakeven": True,
        "trailing_stop_enabled": True,
        "trailing_stop_method": "ATR",
        "atr_trailing_multiple": 2.0,
        "time_stop_enabled": True,
        "time_stop_days": 8,
        "exit_before_earnings": False,
        "avoid_holding_over_weekend": False,
    },
}

BASE_DEFAULTS: Dict[str, Any] = {
    "version": PREFERENCES_VERSION,
    "account_size": 100000.0,
    "risk_profile": "Balanced",
    "custom": deepcopy(PROFILE_DEFAULTS["Balanced"]),
}


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


def _account_size_bucket(account_size: float) -> str:
    if account_size < 50000:
        return "small"
    if account_size < 250000:
        return "standard"
    return "large"


def _apply_account_size_scaling(values: Dict[str, Any], account_size: float) -> Dict[str, Any]:
    scaled = deepcopy(values)
    bucket = _account_size_bucket(account_size)
    if bucket == "small":
        scaled["risk_per_trade_pct"] = max(0.25, _safe_float(values.get("risk_per_trade_pct"), 1.0) * 0.85)
        scaled["max_portfolio_risk_pct"] = max(2.0, _safe_float(values.get("max_portfolio_risk_pct"), 6.0) * 0.9)
        scaled["max_open_trades"] = max(3, _safe_int(values.get("max_open_trades"), 10) - 2)
        scaled["max_position_size_pct"] = max(2.0, _safe_float(values.get("max_position_size_pct"), 8.0) * 0.85)
    elif bucket == "large":
        scaled["risk_per_trade_pct"] = min(3.0, _safe_float(values.get("risk_per_trade_pct"), 1.0) * 1.1)
        scaled["max_portfolio_risk_pct"] = min(12.0, _safe_float(values.get("max_portfolio_risk_pct"), 6.0) * 1.1)
        scaled["max_open_trades"] = min(30, _safe_int(values.get("max_open_trades"), 10) + 3)
        scaled["max_position_size_pct"] = min(25.0, _safe_float(values.get("max_position_size_pct"), 8.0) * 1.15)
    return scaled


def _effective_profile_values(profile: str, custom: Dict[str, Any], account_size: float) -> Dict[str, Any]:
    profile_name = str(profile or "Balanced")
    if profile_name == "Custom":
        base = deepcopy(PROFILE_DEFAULTS["Balanced"])
        base.update(custom or {})
        return base
    base = deepcopy(PROFILE_DEFAULTS.get(profile_name, PROFILE_DEFAULTS["Balanced"]))
    return _apply_account_size_scaling(base, account_size)


def build_profile_defaults(account_size: float, profile: str) -> Dict[str, Any]:
    return _effective_profile_values(profile, {}, account_size)


def _normalize_preferences(raw: Dict[str, Any] | None) -> Dict[str, Any]:
    payload = deepcopy(BASE_DEFAULTS)
    if isinstance(raw, dict):
        payload.update({k: v for k, v in raw.items() if k in {"version", "account_size", "risk_profile", "custom"}})

    payload["version"] = PREFERENCES_VERSION
    payload["account_size"] = max(1000.0, _safe_float(payload.get("account_size"), 100000.0))
    payload["risk_profile"] = str(payload.get("risk_profile") or "Balanced")
    if payload["risk_profile"] not in {"Conservative", "Balanced", "Aggressive", "Custom"}:
        payload["risk_profile"] = "Balanced"

    custom = payload.get("custom") if isinstance(payload.get("custom"), dict) else {}
    merged_custom = deepcopy(PROFILE_DEFAULTS["Balanced"])
    merged_custom.update(custom)
    payload["custom"] = merged_custom

    payload["effective"] = _effective_profile_values(payload["risk_profile"], payload["custom"], payload["account_size"])
    return payload


def _migrate_from_session() -> Dict[str, Any]:
    base = deepcopy(BASE_DEFAULTS)
    base["account_size"] = max(1000.0, _safe_float(st.session_state.get("tcc_account_size"), 100000.0))

    risk_profile = str(st.session_state.get("trading_risk_profile") or "Balanced")
    if risk_profile not in {"Conservative", "Balanced", "Aggressive", "Custom"}:
        risk_profile = "Balanced"
    base["risk_profile"] = risk_profile

    custom = deepcopy(PROFILE_DEFAULTS["Balanced"])
    custom.update(
        {
            "risk_per_trade_pct": max(0.05, _safe_float(st.session_state.get("tcc_risk_pct"), 1.0)),
            "max_portfolio_risk_pct": max(0.5, _safe_float(st.session_state.get("tcc_max_portfolio_risk_pct"), 6.0)),
            "max_open_trades": max(1, _safe_int(st.session_state.get("tcc_max_open_trades"), 12)),
            "max_position_size_pct": max(0.1, _safe_float(st.session_state.get("tcc_max_position_pct"), 8.0)),
            "portfolio_overlap_warning_threshold": min(1.0, max(0.1, _safe_float(st.session_state.get("tcc_correlation_warning_threshold"), 0.85))),
            "tp1_allocation": max(0.0, _safe_float(st.session_state.get("tcc_tp1_allocation_default"), 50.0)),
            "tp2_allocation": max(0.0, _safe_float(st.session_state.get("tcc_tp2_allocation_default"), 40.0)),
            "tp3_allocation": max(0.0, _safe_float(st.session_state.get("tcc_tp3_allocation_default"), 10.0)),
            "move_stop_to_breakeven": bool(st.session_state.get("tcc_move_to_be_default", True)),
            "trailing_stop_enabled": bool(st.session_state.get("tcc_trailing_enabled_default", False)),
            "trailing_stop_method": str(st.session_state.get("tcc_trailing_method_default") or "ATR"),
            "atr_trailing_multiple": max(0.1, _safe_float(st.session_state.get("tcc_atr_multiple_default"), 2.0)),
            "time_stop_enabled": bool(st.session_state.get("tcc_time_stop_enabled_default", True)),
            "time_stop_days": max(1, _safe_int(st.session_state.get("tcc_time_stop_days_default"), 10)),
            "exit_before_earnings": bool(st.session_state.get("tcc_exit_before_earnings_default", True)),
            "avoid_holding_over_weekend": bool(st.session_state.get("tcc_avoid_weekend_default", False)),
        }
    )
    base["custom"] = custom
    return _normalize_preferences(base)


def _load_from_disk() -> Dict[str, Any] | None:
    if not PREFERENCES_FILE.exists():
        return None
    try:
        payload = json.loads(PREFERENCES_FILE.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return _normalize_preferences(payload)
    except Exception:
        return None
    return None


def _save_to_disk(preferences: Dict[str, Any]) -> None:
    PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": PREFERENCES_VERSION,
        "account_size": preferences.get("account_size"),
        "risk_profile": preferences.get("risk_profile"),
        "custom": preferences.get("custom"),
    }
    PREFERENCES_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def apply_preferences_to_session(preferences: Dict[str, Any]) -> Dict[str, Any]:
    prefs = _normalize_preferences(preferences)
    effective = prefs["effective"]

    st.session_state[PREFERENCES_KEY] = prefs
    st.session_state["trading_risk_profile"] = prefs["risk_profile"]

    st.session_state["tcc_account_size"] = prefs["account_size"]
    st.session_state["tcc_risk_pct"] = effective["risk_per_trade_pct"]
    st.session_state["tcc_max_portfolio_risk_pct"] = effective["max_portfolio_risk_pct"]
    st.session_state["tcc_max_open_trades"] = int(effective["max_open_trades"])
    st.session_state["tcc_max_position_pct"] = effective["max_position_size_pct"]
    st.session_state["tcc_correlation_warning_threshold"] = float(effective.get("portfolio_overlap_warning_threshold", 0.85))

    st.session_state["tcc_tp1_allocation_default"] = effective["tp1_allocation"]
    st.session_state["tcc_tp2_allocation_default"] = effective["tp2_allocation"]
    st.session_state["tcc_tp3_allocation_default"] = effective["tp3_allocation"]
    st.session_state["tcc_move_to_be_default"] = bool(effective["move_stop_to_breakeven"])
    st.session_state["tcc_trailing_enabled_default"] = bool(effective["trailing_stop_enabled"])
    st.session_state["tcc_trailing_method_default"] = str(effective.get("trailing_stop_method") or "ATR")
    st.session_state["tcc_atr_multiple_default"] = float(effective.get("atr_trailing_multiple", 2.0))
    st.session_state["tcc_time_stop_enabled_default"] = bool(effective["time_stop_enabled"])
    st.session_state["tcc_time_stop_days_default"] = int(effective["time_stop_days"])
    st.session_state["tcc_exit_before_earnings_default"] = bool(effective["exit_before_earnings"])
    st.session_state["tcc_avoid_weekend_default"] = bool(effective["avoid_holding_over_weekend"])

    return prefs


def get_trading_preferences() -> Dict[str, Any]:
    existing = st.session_state.get(PREFERENCES_KEY)
    if isinstance(existing, dict):
        return apply_preferences_to_session(existing)

    loaded = _load_from_disk()
    if loaded is None:
        loaded = _migrate_from_session()
        _save_to_disk(loaded)

    return apply_preferences_to_session(loaded)


def save_trading_preferences(preferences: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_preferences(preferences)
    _save_to_disk(normalized)
    return apply_preferences_to_session(normalized)
