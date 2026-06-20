# =========================================================
# JFBP QUANT DESK — AUTOMATION CONTROL CENTER
# v2.2 Responsive Institutional Freeze Candidate — How-To + Mobile Dashboard Fix
# Phase 1: SIM-only automation control layer
# =========================================================

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any
import json
import os
import signal
import subprocess
import sys
import time

import pandas as pd
import streamlit as st


# =========================================================
# PAGE CONFIG HELPERS
# =========================================================

PAGE_TITLE = "Automation Control Center"
PAGE_ICON = "🤖"
PAGE_VERSION = "v3.4 Quant Executor v1.1 — Time Exit"
PAGE_STATUS = "SIMULATION ONLY"


# =========================================================
# SESSION STATE
# =========================================================

def _seed_queue() -> List[Dict[str, object]]:
    """Demo scanner-approved queue. Replace with Scanner output later."""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return [
        {
            "id": "SIG-001",
            "time": now,
            "symbol": "NVDA",
            "side": "BUY",
            "score": 91,
            "regime": "RISK-ON",
            "sector": "Technology",
            "setup": "Momentum Breakout",
            "status": "WAITING",
            "reason": "Scanner approved. Strong score and leadership confirmation.",
        },
        {
            "id": "SIG-002",
            "time": now,
            "symbol": "MSFT",
            "side": "BUY",
            "score": 83,
            "regime": "SELECTIVE",
            "sector": "Technology",
            "setup": "Pullback Continuation",
            "status": "WAITING",
            "reason": "Scanner approved. Score above minimum threshold.",
        },
        {
            "id": "SIG-003",
            "time": now,
            "symbol": "TSLA",
            "side": "BUY",
            "score": 79,
            "regime": "SELECTIVE",
            "sector": "Consumer Discretionary",
            "setup": "High Beta Reversal",
            "status": "WAITING",
            "reason": "Scanner approved, but symbol may be blocked by automation rules.",
        },
        {
            "id": "SIG-004",
            "time": now,
            "symbol": "AVGO",
            "side": "BUY",
            "score": 87,
            "regime": "RISK-ON",
            "sector": "Technology",
            "setup": "Relative Strength Continuation",
            "status": "WAITING",
            "reason": "Scanner approved. Sector leadership remains constructive.",
        },
    ]


def _init_state() -> None:
    """Initialize local page state safely."""

    defaults = {
        "acc_mode": "OFF",
        "acc_kill_switch": False,
        "acc_market_pulse_allowed": True,
        "acc_scanner_active": True,
        "acc_data_feed_healthy": True,
        "acc_oms_reconciled": False,
        "acc_ibkr_connected": False,
        "acc_risk_controls_active": True,
        "acc_audit_logging_active": True,
        "acc_telegram_connected": True,
        "acc_telegram_alerts_enabled": True,
        "acc_notify_approved": True,
        "acc_notify_rejected": True,
        "acc_notify_held": True,
        "acc_notify_removed": False,
        "acc_notify_gate_failure": True,
        "acc_notify_kill_switch": True,
        "acc_notify_live_event": True,
        "acc_live_armed": False,
        "acc_auto_live_phrase_ok": False,
        "acc_min_score": 75,
        "acc_max_trades_day": 5,
        "acc_max_position_pct": 5.0,
        "acc_max_daily_risk_pct": 1.0,
        "acc_max_daily_loss": 1000.0,
        "acc_current_drawdown": 250.0,
        "acc_exposure_utilization": 38,
        "acc_allowed_symbols": "AAPL, MSFT, NVDA, AMD, AVGO, META, GOOGL, AMZN, SPY, QQQ, EURUSD=X, GBPUSD=X, USDJPY=X, USDCHF=X, AUDUSD=X, NZDUSD=X, USDCAD=X, EURJPY=X, GBPJPY=X, BTC-USD, ETH-USD, GC=F, SI=F, CL=F, BZ=F, ES=F, NQ=F, RTY=F",
        "acc_blocked_symbols": "TSLA, GME, AMC",
        "acc_regime_filter": ["RISK-ON", "SELECTIVE"],
        "acc_asset_class_allow": ["Stocks", "ETFs", "Forex", "Crypto", "Gold", "Oil", "Futures"],
        "acc_sector_allow": ["Technology", "Financials", "Healthcare", "Industrials", "Energy"],
        "acc_sector_block": [],
        "acc_queue": _seed_queue(),
        "acc_audit": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# =========================================================
# STYLE
# =========================================================

def _inject_css() -> None:
    st.markdown(
        """
        <style>
            .acc-hero {
                padding: 1.25rem 1.35rem;
                border-radius: 20px;
                border: 1px solid rgba(37, 99, 235, 0.22);
                background:
                    radial-gradient(circle at top left, rgba(37, 99, 235, 0.16), transparent 34%),
                    linear-gradient(135deg, rgba(15, 23, 42, 0.055), rgba(100, 116, 139, 0.045));
                margin-bottom: 1rem;
            }

            .acc-hero-title {
                font-size: 2rem;
                font-weight: 900;
                letter-spacing: -0.03em;
                margin-bottom: 0.15rem;
            }

            .acc-hero-subtitle {
                font-size: 1rem;
                color: #475569;
                line-height: 1.45;
                max-width: 980px;
            }

            .acc-version-pill {
                display: inline-block;
                margin-top: 0.75rem;
                padding: 0.28rem 0.65rem;
                border-radius: 999px;
                border: 1px solid rgba(37, 99, 235, 0.28);
                background: rgba(37, 99, 235, 0.08);
                color: #1e40af;
                font-size: 0.76rem;
                font-weight: 900;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }

            .acc-workflow {
                padding: 0.85rem 1rem;
                border-radius: 16px;
                border: 1px solid rgba(148, 163, 184, 0.30);
                background: rgba(248, 250, 252, 0.72);
                margin-bottom: 1rem;
                font-weight: 800;
                text-align: center;
                line-height: 1.55;
            }

            .acc-card {
                padding: 1rem;
                border-radius: 16px;
                border: 1px solid rgba(148, 163, 184, 0.30);
                background: rgba(248, 250, 252, 0.68);
                height: 100%;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.035);
            }

            .acc-card-strong {
                padding: 1.1rem;
                border-radius: 18px;
                border: 1px solid rgba(37, 99, 235, 0.24);
                background: linear-gradient(135deg, rgba(37, 99, 235, 0.09), rgba(37, 99, 235, 0.025));
                height: 100%;
            }

            .acc-small {
                font-size: 0.88rem;
                opacity: 0.80;
                line-height: 1.45;
            }

            .acc-label {
                font-size: 0.76rem;
                font-weight: 900;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: #64748b;
                margin-bottom: 0.25rem;
            }

            .acc-big {
                font-size: 1.75rem;
                font-weight: 900;
                letter-spacing: -0.035em;
                color: #0f172a;
                margin-bottom: 0.10rem;
            }

            .acc-good {
                color: #15803d;
                font-weight: 900;
            }

            .acc-bad {
                color: #dc2626;
                font-weight: 900;
            }

            .acc-warn {
                color: #b45309;
                font-weight: 900;
            }

            .acc-lock {
                padding: 1rem;
                border-radius: 16px;
                border: 1px solid rgba(220, 38, 38, 0.32);
                background: rgba(254, 226, 226, 0.58);
            }

            .acc-vault {
                padding: 1.15rem;
                border-radius: 18px;
                border: 1px solid rgba(220, 38, 38, 0.30);
                background:
                    repeating-linear-gradient(
                        135deg,
                        rgba(220, 38, 38, 0.055),
                        rgba(220, 38, 38, 0.055) 10px,
                        rgba(254, 242, 242, 0.45) 10px,
                        rgba(254, 242, 242, 0.45) 20px
                    );
            }

            .acc-step {
                padding: 0.85rem 0.9rem;
                border-radius: 14px;
                border: 1px solid rgba(148, 163, 184, 0.28);
                background: rgba(248, 250, 252, 0.74);
                text-align: center;
                font-weight: 900;
                min-height: 4.25rem;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .acc-arrow {
                text-align: center;
                font-weight: 900;
                color: #64748b;
                font-size: 1.2rem;
                margin: 0.20rem 0;
            }


            .acc-howto {
                padding: 1rem 1.05rem;
                border-radius: 18px;
                border: 1px solid rgba(37, 99, 235, 0.22);
                background: linear-gradient(135deg, rgba(37, 99, 235, 0.065), rgba(248, 250, 252, 0.78));
                margin-bottom: 1rem;
            }

            .acc-howto-step {
                padding: 0.85rem 0.9rem;
                border-radius: 14px;
                border: 1px solid rgba(148, 163, 184, 0.28);
                background: rgba(255, 255, 255, 0.58);
                height: 100%;
            }

            .acc-howto-num {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 1.55rem;
                height: 1.55rem;
                border-radius: 999px;
                background: rgba(37, 99, 235, 0.12);
                color: #1e40af;
                font-weight: 900;
                margin-right: 0.35rem;
            }

            .acc-sidebar-help {
                padding: 0.75rem 0.8rem;
                border-radius: 14px;
                border: 1px solid rgba(37, 99, 235, 0.22);
                background: rgba(37, 99, 235, 0.07);
                font-size: 0.82rem;
                line-height: 1.45;
                margin-bottom: 0.85rem;
            }


            .acc-dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
                gap: 0.9rem;
                margin-bottom: 0.95rem;
            }

            .acc-dashboard-card {
                padding: 1rem 1.05rem;
                border-radius: 18px;
                border: 1px solid rgba(148, 163, 184, 0.30);
                background: rgba(248, 250, 252, 0.72);
                min-height: 8.4rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.035);
                overflow: hidden;
            }

            .acc-dashboard-card-strong {
                border-color: rgba(37, 99, 235, 0.24);
                background: linear-gradient(135deg, rgba(37, 99, 235, 0.09), rgba(37, 99, 235, 0.025));
            }

            .acc-dashboard-title {
                font-size: clamp(0.78rem, 1.2vw, 0.95rem);
                font-weight: 800;
                color: #334155;
                margin-bottom: 0.85rem;
                white-space: normal;
                overflow-wrap: anywhere;
                line-height: 1.2;
            }

            .acc-dashboard-value {
                font-size: clamp(1.55rem, 3.5vw, 2.75rem);
                line-height: 1.0;
                font-weight: 850;
                letter-spacing: -0.045em;
                color: #111827;
                white-space: normal;
                overflow-wrap: anywhere;
            }

            .acc-dashboard-value-small {
                font-size: clamp(1.2rem, 2.2vw, 2.05rem);
                letter-spacing: -0.03em;
            }

            .acc-dashboard-status {
                margin-top: 0.75rem;
                font-size: clamp(0.82rem, 1.2vw, 0.95rem);
                font-weight: 900;
                letter-spacing: 0.02em;
                white-space: normal;
                overflow-wrap: anywhere;
            }

            .acc-tabs-note {
                font-size: 0.82rem;
                color: #64748b;
                margin-top: -0.2rem;
                margin-bottom: 0.35rem;
            }

            .acc-footer {
                margin-top: 1.25rem;
                padding: 0.9rem 1rem;
                border-radius: 16px;
                border: 1px solid rgba(148, 163, 184, 0.28);
                background: rgba(248, 250, 252, 0.72);
                color: #475569;
                font-size: 0.86rem;
                line-height: 1.45;
            }

            div[data-testid="stMetric"] {
                border: 1px solid rgba(148, 163, 184, 0.26);
                border-radius: 15px;
                padding: 0.58rem 0.66rem;
                background: rgba(248, 250, 252, 0.66);
                min-width: 0 !important;
                overflow: hidden;
            }

            div[data-testid="stMetricLabel"],
            div[data-testid="stMetricValue"],
            div[data-testid="stMetricDelta"] {
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
                overflow-wrap: anywhere !important;
                word-break: normal !important;
                line-height: 1.15 !important;
            }

            div[data-testid="stMetricValue"] {
                font-size: clamp(1.0rem, 1.55vw, 1.55rem) !important;
            }

            div[data-testid="stMetricLabel"] {
                font-size: clamp(0.66rem, 0.86vw, 0.78rem) !important;
            }

            @media (max-width: 768px) {
                .acc-hero { padding: 0.95rem; }
                .acc-hero-title { font-size: 1.55rem; }
                .acc-card, .acc-card-strong, .acc-vault { padding: 0.85rem; }
                .acc-big { font-size: 1.35rem; }
                .acc-workflow { font-size: 0.88rem; }
            }

            div[data-testid="stTabs"] [role="tablist"] {
                gap: 0.15rem;
                overflow-x: auto;
                overflow-y: hidden;
                white-space: nowrap;
                padding-bottom: 0.15rem;
            }

            div[data-testid="stTabs"] [role="tab"] {
                min-width: fit-content;
                padding-left: 0.55rem;
                padding-right: 0.55rem;
            }

            @media (max-width: 1100px) {
                .acc-dashboard-grid {
                    grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
                    gap: 0.7rem;
                }

                .acc-dashboard-card {
                    min-height: 7.5rem;
                    padding: 0.85rem 0.9rem;
                }
            }

            @media (max-width: 640px) {
                .acc-dashboard-grid {
                    grid-template-columns: 1fr 1fr;
                    gap: 0.65rem;
                }

                .acc-dashboard-card {
                    min-height: 6.7rem;
                    border-radius: 15px;
                    padding: 0.78rem;
                }
            }

            @media (max-width: 430px) {
                .acc-dashboard-grid {
                    grid-template-columns: 1fr;
                }
            }


            .acc-watch-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
                gap: 0.62rem;
                margin-top: 0.85rem;
                margin-bottom: 1rem;
            }

            .acc-watch-card {
                border-radius: 16px;
                border: 1px solid rgba(148, 163, 184, 0.32);
                background: rgba(248, 250, 252, 0.72);
                padding: 0.62rem 0.72rem;
                min-height: 4.75rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.035);
                overflow: hidden;
            }

            .acc-watch-label {
                font-size: clamp(0.66rem, 0.82vw, 0.78rem);
                font-weight: 850;
                color: #475569;
                margin-bottom: 0.24rem;
                line-height: 1.18;
                overflow-wrap: anywhere;
            }

            .acc-watch-value {
                font-size: clamp(0.98rem, 1.45vw, 1.38rem);
                font-weight: 850;
                letter-spacing: -0.025em;
                color: #111827;
                line-height: 1.04;
                white-space: normal;
                overflow-wrap: anywhere;
                word-break: break-word;
                hyphens: auto;
            }

            .acc-watch-note {
                margin-top: 0.28rem;
                font-size: 0.66rem;
                color: #64748b;
                line-height: 1.25;
                overflow-wrap: anywhere;
            }

            .acc-watch-good {
                border-color: rgba(22, 163, 74, 0.28);
                background: rgba(236, 253, 245, 0.74);
            }

            .acc-watch-bad {
                border-color: rgba(220, 38, 38, 0.28);
                background: rgba(254, 242, 242, 0.74);
            }

            .acc-watch-warn {
                border-color: rgba(217, 119, 6, 0.28);
                background: rgba(255, 251, 235, 0.76);
            }

            .acc-watch-blue {
                border-color: rgba(37, 99, 235, 0.24);
                background: rgba(239, 246, 255, 0.76);
            }

            @media (max-width: 1100px) {
                .acc-watch-grid {
                    grid-template-columns: 1fr 1fr;
                    gap: 0.62rem;
                }

                .acc-watch-card {
                    min-height: 4.65rem;
                    padding: 0.58rem 0.66rem;
                    border-radius: 14px;
                }

                .acc-watch-value {
                    font-size: clamp(0.92rem, 1.45vw, 1.25rem);
                    letter-spacing: -0.015em;
                }
            }

            @media (max-width: 640px) {
                .acc-watch-grid {
                    grid-template-columns: 1fr;
                }
            }


            /* Signal Watcher v2.5.1 polish: reduce visual weight and prevent oversized cards. */
            .acc-watch-compact .acc-watch-card {
                min-height: 4.45rem;
            }

            .acc-watch-compact .acc-watch-value {
                font-size: clamp(0.92rem, 1.35vw, 1.25rem);
                letter-spacing: -0.015em;
            }

            .acc-watch-version .acc-watch-value {
                font-size: clamp(0.88rem, 1.20vw, 1.10rem);
                line-height: 1.05;
            }


            /* v2.5.3: iPad watcher control polish. */
            @media (max-width: 1180px) {
                div[data-testid="stMetric"] {
                    min-height: 4.1rem !important;
                    padding: 0.62rem 0.70rem !important;
                }

                div[data-testid="stMetricValue"] {
                    font-size: clamp(1.05rem, 1.7vw, 1.55rem) !important;
                    line-height: 1.08 !important;
                }

                div[data-testid="stMetricLabel"] {
                    font-size: 0.72rem !important;
                }

                div[data-testid="column"] .stButton > button {
                    min-height: 2.25rem;
                    font-size: 0.78rem;
                    padding: 0.25rem 0.45rem;
                }
            }

            @media (max-width: 1100px) {
                div[data-testid="column"] .stButton > button {
                    min-height: 2.35rem;
                    padding-left: 0.35rem;
                    padding-right: 0.35rem;
                    font-size: 0.82rem;
                    white-space: normal;
                    word-break: normal;
                }
            }

        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# UTILS
# =========================================================

def _csv_to_set(raw: str) -> set[str]:
    return {x.strip().upper() for x in str(raw).split(",") if x.strip()}


def _asset_class_for_signal(signal: Dict[str, object]) -> str:
    """Classify a scanner/automation signal into a broad asset class."""

    symbol = str(signal.get("symbol", "") or "").upper().strip()
    sector = str(signal.get("sector", "") or "").upper().strip()

    if symbol.endswith("=X") or sector.startswith("FX ") or "FOREX" in sector:
        return "Forex"

    if symbol.endswith("-USD") or "CRYPTO" in sector:
        return "Crypto"

    if symbol in {"GC=F", "SI=F"} or "GOLD" in sector or "SILVER" in sector:
        return "Gold"

    if symbol in {"CL=F", "BZ=F", "NG=F", "HG=F"} or "OIL" in sector or "COMMODITY FUTURES" in sector:
        return "Oil" if symbol in {"CL=F", "BZ=F"} or "OIL" in sector else "Futures"

    if symbol.endswith("=F") or "FUTURES" in sector:
        return "Futures"

    if "ETF" in sector or symbol in {"SPY", "QQQ", "DIA", "IWM", "RSP", "VTI", "TLT", "GLD", "USO", "IBIT", "FBTC"}:
        return "ETFs"

    return "Stocks"


def _approved_count_today() -> int:
    return sum(
        1
        for row in st.session_state.acc_audit
        if row.get("Action") == "APPROVED_SIM"
    )


def _waiting_count() -> int:
    return sum(1 for row in st.session_state.acc_queue if row.get("status") == "WAITING")


def _telegram_ready() -> bool:
    return bool(
        st.session_state.get("acc_telegram_connected", False)
        and st.session_state.get("acc_telegram_alerts_enabled", False)
    )


def _telegram_notifier():
    for key in (
        "telegram_notifier",
        "telegram_alerts",
        "telegram_client",
        "notifier",
    ):
        obj = st.session_state.get(key)
        if obj is not None:
            return obj
    return None


def _send_telegram_alert(title: str, message: str) -> bool:
    """Best-effort Telegram alert.

    If a notifier object exists in session state, this calls it. If the app is
    running without a notifier object, the function records a UI-level simulated
    send so the control center can still be tested safely.
    """

    if not _telegram_ready():
        return False

    text = f"{title}\n\n{message}"
    notifier = _telegram_notifier()

    if notifier is None:
        st.session_state["acc_last_telegram_alert"] = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": title,
            "message": message,
            "status": "SIMULATED_NO_NOTIFIER",
        }
        return True

    for method_name in ("send", "send_message", "notify", "alert"):
        if hasattr(notifier, method_name):
            try:
                getattr(notifier, method_name)(text)
                st.session_state["acc_last_telegram_alert"] = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": title,
                    "message": message,
                    "status": "SENT",
                }
                return True
            except Exception as exc:
                st.session_state["acc_last_telegram_alert"] = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": title,
                    "message": message,
                    "status": f"ERROR: {exc}",
                }
                return False

    st.session_state["acc_last_telegram_alert"] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": title,
        "message": message,
        "status": "NO_SUPPORTED_METHOD",
    }
    return False


def _should_notify(action: str) -> bool:
    mapping = {
        "APPROVED_SIM": "acc_notify_approved",
        "REJECTED": "acc_notify_rejected",
        "HELD": "acc_notify_held",
        "REMOVED": "acc_notify_removed",
    }
    key = mapping.get(str(action).upper())
    return bool(st.session_state.get(key, False)) if key else False


def _audit(action: str, signal: Dict[str, object], note: str) -> None:
    telegram_sent = False

    if _should_notify(action):
        telegram_sent = _send_telegram_alert(
            "🤖 JFBP Automation Alert",
            "\n".join(
                [
                    f"Action: {action}",
                    f"Ticker: {signal.get('symbol', '')}",
                    f"Side: {signal.get('side', '')}",
                    f"Score: {signal.get('score', '')}",
                    f"Regime: {signal.get('regime', '')}",
                    f"Mode: {st.session_state.acc_mode}",
                    f"Note: {note}",
                ]
            ),
        )

    st.session_state.acc_audit.insert(
        0,
        {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Action": action,
            "Signal ID": signal.get("id", ""),
            "Symbol": signal.get("symbol", ""),
            "Side": signal.get("side", ""),
            "Score": signal.get("score", ""),
            "Regime": signal.get("regime", ""),
            "Sector": signal.get("sector", ""),
            "Asset Class": _asset_class_for_signal(signal),
            "Mode": st.session_state.acc_mode,
            "Telegram Sent": "YES" if telegram_sent else "NO",
            "Note": note,
        },
    )


def _gate_status() -> Dict[str, bool]:
    return {
        "Market Pulse risk approved": bool(st.session_state.acc_market_pulse_allowed),
        "Scanner active": bool(st.session_state.acc_scanner_active),
        "Data feed healthy": bool(st.session_state.acc_data_feed_healthy),
        "OMS reconciled": bool(st.session_state.acc_oms_reconciled),
        "Live IBKR connected": bool(st.session_state.acc_ibkr_connected),
        "Risk controls active": bool(st.session_state.acc_risk_controls_active),
        "Kill switch OFF": not bool(st.session_state.acc_kill_switch),
        "Audit logging active": bool(st.session_state.acc_audit_logging_active),
        "Telegram connected": bool(st.session_state.acc_telegram_connected),
        "LIVE trading armed": bool(st.session_state.acc_live_armed),
        "AUTO LIVE phrase confirmed": bool(st.session_state.acc_auto_live_phrase_ok),
    }


def _sim_gate_status() -> Dict[str, bool]:
    return {
        "Market Pulse risk approved": bool(st.session_state.acc_market_pulse_allowed),
        "Scanner active": bool(st.session_state.acc_scanner_active),
        "Data feed healthy": bool(st.session_state.acc_data_feed_healthy),
        "OMS reconciled": bool(st.session_state.acc_oms_reconciled),
        "Risk controls active": bool(st.session_state.acc_risk_controls_active),
        "Kill switch OFF": not bool(st.session_state.acc_kill_switch),
        "Audit logging active": bool(st.session_state.acc_audit_logging_active),
        "Telegram connected": bool(st.session_state.acc_telegram_connected),
    }


def _readiness_score() -> tuple[int, str]:
    scoring = [
        (15, bool(st.session_state.acc_market_pulse_allowed)),
        (15, bool(st.session_state.acc_scanner_active)),
        (15, bool(st.session_state.acc_oms_reconciled)),
        (15, bool(st.session_state.acc_ibkr_connected)),
        (15, bool(st.session_state.acc_risk_controls_active)),
        (15, not bool(st.session_state.acc_kill_switch)),
        (10, bool(st.session_state.acc_audit_logging_active)),
        (10, bool(st.session_state.acc_telegram_connected)),
    ]

    score = sum(points for points, ok in scoring if ok)

    if st.session_state.acc_mode == "SIM AUTO" and all(_sim_gate_status().values()):
        label = "SIMULATION READY"
    elif st.session_state.acc_mode == "OFF":
        label = "OFFLINE"
    elif score >= 75:
        label = "PARTIAL READY"
    else:
        label = "BLOCKED"

    return score, label


def _evaluate_signal(signal: Dict[str, object]) -> tuple[bool, str]:
    symbol = str(signal.get("symbol", "")).upper()
    score = int(signal.get("score", 0))
    regime = str(signal.get("regime", ""))
    sector = str(signal.get("sector", ""))
    asset_class = _asset_class_for_signal(signal)

    allowed = _csv_to_set(st.session_state.acc_allowed_symbols)
    blocked = _csv_to_set(st.session_state.acc_blocked_symbols)

    if st.session_state.acc_mode == "OFF":
        return False, "Automation mode is OFF. Manual approval/rejection only."

    if st.session_state.acc_mode == "LIVE AUTO LOCKED":
        return False, "LIVE AUTO is locked in Phase 1. Use SIM AUTO only."

    if symbol in blocked:
        return False, f"{symbol} is blocked by automation rules."

    if allowed and symbol not in allowed:
        return False, f"{symbol} is not in the allowed symbols list."

    allowed_asset_classes = st.session_state.get("acc_asset_class_allow", [])
    if allowed_asset_classes and asset_class not in allowed_asset_classes:
        return False, f"{asset_class} is not enabled in the allowed asset classes filter."

    if score < int(st.session_state.acc_min_score):
        return False, f"Score {score} is below the minimum score threshold."

    if regime not in st.session_state.acc_regime_filter:
        return False, f"Regime {regime} is not allowed by the market regime filter."

    if asset_class in ("Stocks", "ETFs"):
        if st.session_state.acc_sector_allow and sector not in st.session_state.acc_sector_allow:
            return False, f"Sector {sector} is not in the sector allow list."

        if sector in st.session_state.acc_sector_block:
            return False, f"Sector {sector} is blocked."

    if _approved_count_today() >= int(st.session_state.acc_max_trades_day):
        return False, "Maximum automated trades per day has been reached."

    sim_gates = _sim_gate_status()
    failed_gates = [name for name, ok in sim_gates.items() if not ok]
    if failed_gates:
        return False, "SIM safety gate failed: " + ", ".join(failed_gates)

    return True, "Signal passes Phase 1 SIM automation controls."



# =========================================================
# SIGNAL WATCHER MONITORING HELPERS
# =========================================================

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data"
SIGNAL_WATCHER_STATE_FILE = DATA_DIR / "signal_watcher_state.json"
SIGNAL_WATCHER_SCAN_LOG_FILE = DATA_DIR / "signal_watcher_scans.csv"
SIGNAL_WATCHER_ALERT_LOG_FILE = DATA_DIR / "signal_watcher_alerts.csv"
SIGNAL_WATCHER_SIGNAL_LOG_FILE = DATA_DIR / "signal_watcher_signal_log.csv"
SIGNAL_WATCHER_PROCESS_FILE = DATA_DIR / "signal_watcher_process.json"
SIGNAL_WATCHER_STDOUT_LOG_FILE = DATA_DIR / "signal_watcher_process_stdout.log"
SIGNAL_WATCHER_STDERR_LOG_FILE = DATA_DIR / "signal_watcher_process_stderr.log"
SIGNAL_WATCHER_SCRIPT = APP_ROOT / "core" / "Signal_Watcher_v3_Analytics.py"

# Quant Executor files (internal Quant Executor v1 Paper engine filenames retained for stability)
AUTO_TRADER_SCRIPT = APP_ROOT / "core" / "Auto_Trader_v1_Paper.py"
AUTO_TRADER_PROCESS_FILE = DATA_DIR / "auto_trader_paper_process.json"
AUTO_TRADER_CONFIG_FILE = DATA_DIR / "auto_trader_paper_config.json"
AUTO_TRADER_STATE_FILE = DATA_DIR / "auto_trader_paper_state.json"
AUTO_TRADER_ORDER_LOG_FILE = DATA_DIR / "auto_trader_paper_orders.csv"
AUTO_TRADER_FILL_LOG_FILE = DATA_DIR / "auto_trader_paper_fills.csv"
AUTO_TRADER_POSITION_FILE = DATA_DIR / "auto_trader_paper_positions.json"
AUTO_TRADER_EVENT_LOG_FILE = DATA_DIR / "auto_trader_paper_events.csv"
AUTO_TRADER_CLOSED_TRADES_FILE = DATA_DIR / "auto_trader_paper_closed_trades.csv"
AUTO_TRADER_STDOUT_LOG_FILE = DATA_DIR / "auto_trader_paper_process_stdout.log"
AUTO_TRADER_STDERR_LOG_FILE = DATA_DIR / "auto_trader_paper_process_stderr.log"


def _read_json_file(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_csv_file(path: Path, max_rows: int = 50) -> pd.DataFrame:
    try:
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_csv(path)
        if df.empty:
            return df
        return df.tail(max_rows).copy()
    except Exception:
        return pd.DataFrame()


def _parse_watcher_time(value: Any):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        # Watcher writes ISO timestamps with timezone info.
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def _watcher_health_snapshot() -> Dict[str, Any]:
    state = _read_json_file(SIGNAL_WATCHER_STATE_FILE)
    stats = state.get("stats", {}) if isinstance(state.get("stats"), dict) else {}

    interval_minutes = int(float(stats.get("last_scan_interval_minutes") or 5))
    last_finished = _parse_watcher_time(stats.get("last_scan_finished"))

    now_utc = datetime.now(timezone.utc)
    seconds_since_scan = None
    running = False

    if last_finished is not None:
        if last_finished.tzinfo is None:
            last_finished = last_finished.replace(tzinfo=timezone.utc)
        seconds_since_scan = max(0, int((now_utc - last_finished).total_seconds()))
        running = seconds_since_scan <= max(180, (interval_minutes * 60 * 2) + 60)

    alert_df = _read_csv_file(SIGNAL_WATCHER_ALERT_LOG_FILE, max_rows=100)
    scan_df = _read_csv_file(SIGNAL_WATCHER_SCAN_LOG_FILE, max_rows=500)
    signal_df = _read_csv_file(SIGNAL_WATCHER_SIGNAL_LOG_FILE, max_rows=5000)

    today = datetime.now().strftime("%Y-%m-%d")
    alerts_today = 0
    last_alert_symbol = "None"
    last_alert_time = "Never"

    if not alert_df.empty:
        if "timestamp" in alert_df.columns:
            alert_df["timestamp_text"] = alert_df["timestamp"].astype(str)
            alerts_today = int(alert_df[alert_df["timestamp_text"].str.startswith(today)].shape[0])
        else:
            alerts_today = int(alert_df.shape[0])

        last_alert = alert_df.tail(1).iloc[0].to_dict()
        last_alert_symbol = str(last_alert.get("symbol") or "None")
        last_alert_time = str(last_alert.get("timestamp") or "Never")

    return {
        "state": state,
        "stats": stats,
        "scan_df": scan_df,
        "alert_df": alert_df,
        "signal_df": signal_df,
        "running": running,
        "seconds_since_scan": seconds_since_scan,
        "alerts_today": alerts_today,
        "last_alert_symbol": last_alert_symbol,
        "last_alert_time": last_alert_time,
        "state_file_exists": SIGNAL_WATCHER_STATE_FILE.exists(),
        "scan_log_exists": SIGNAL_WATCHER_SCAN_LOG_FILE.exists(),
        "alert_log_exists": SIGNAL_WATCHER_ALERT_LOG_FILE.exists(),
        "signal_log_exists": SIGNAL_WATCHER_SIGNAL_LOG_FILE.exists(),
    }


def _format_seconds_ago(seconds: Any) -> str:
    if seconds is None:
        return "Never"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m ago"


# =========================================================
# SIGNAL WATCHER PROCESS CONTROL HELPERS
# =========================================================

def _pid_is_running(pid: Any) -> bool:
    """Return True when an operating-system process ID appears alive."""

    try:
        pid = int(pid)
    except Exception:
        return False

    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def _read_process_record() -> Dict[str, Any]:
    return _read_json_file(SIGNAL_WATCHER_PROCESS_FILE)


def _write_process_record(record: Dict[str, Any]) -> None:
    try:
        SIGNAL_WATCHER_PROCESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SIGNAL_WATCHER_PROCESS_FILE.write_text(
            json.dumps(record, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except Exception as exc:
        st.session_state["acc_signal_watcher_process_error"] = str(exc)


def _clear_process_record() -> None:
    try:
        if SIGNAL_WATCHER_PROCESS_FILE.exists():
            SIGNAL_WATCHER_PROCESS_FILE.unlink()
    except Exception as exc:
        st.session_state["acc_signal_watcher_process_error"] = str(exc)


def _process_status() -> Dict[str, Any]:
    record = _read_process_record()
    pid = record.get("pid")
    running = _pid_is_running(pid)

    if record and not running:
        record = {
            **record,
            "status": "STALE_PID",
            "stale_checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    return {
        "record": record,
        "pid": pid,
        "running": running,
        "process_file_exists": SIGNAL_WATCHER_PROCESS_FILE.exists(),
        "script_exists": SIGNAL_WATCHER_SCRIPT.exists(),
        "stdout_log": SIGNAL_WATCHER_STDOUT_LOG_FILE,
        "stderr_log": SIGNAL_WATCHER_STDERR_LOG_FILE,
    }


def _start_signal_watcher_process() -> tuple[bool, str]:
    """Start Signal Watcher as a detached background Python process."""

    current = _process_status()

    if current["running"]:
        return False, f"Signal Watcher is already running with PID {current['pid']}."

    if not SIGNAL_WATCHER_SCRIPT.exists():
        return False, f"Watcher script not found: {SIGNAL_WATCHER_SCRIPT}"

    token_present = bool(
        os.getenv("JFBP_TELEGRAM_BOT_TOKEN")
        or os.getenv("TELEGRAM_BOT_TOKEN")
    )
    chat_present = bool(
        os.getenv("JFBP_TELEGRAM_CHAT_ID")
        or os.getenv("TELEGRAM_CHAT_ID")
    )

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    try:
        SIGNAL_WATCHER_STDOUT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        stdout_handle = SIGNAL_WATCHER_STDOUT_LOG_FILE.open("a", encoding="utf-8")
        stderr_handle = SIGNAL_WATCHER_STDERR_LOG_FILE.open("a", encoding="utf-8")

        popen_kwargs = {
            "cwd": str(APP_ROOT),
            "env": env,
            "stdout": stdout_handle,
            "stderr": stderr_handle,
        }

        # On macOS/Linux this detaches the watcher from Streamlit reruns.
        if hasattr(os, "setsid"):
            popen_kwargs["preexec_fn"] = os.setsid

        proc = subprocess.Popen(
            [sys.executable, str(SIGNAL_WATCHER_SCRIPT)],
            **popen_kwargs,
        )

        record = {
            "pid": proc.pid,
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "python": sys.executable,
            "script": str(SIGNAL_WATCHER_SCRIPT),
            "cwd": str(APP_ROOT),
            "stdout_log": str(SIGNAL_WATCHER_STDOUT_LOG_FILE),
            "stderr_log": str(SIGNAL_WATCHER_STDERR_LOG_FILE),
            "telegram_token_visible_to_streamlit": token_present,
            "telegram_chat_visible_to_streamlit": chat_present,
            "status": "STARTED",
        }
        _write_process_record(record)

        if not token_present or not chat_present:
            return True, (
                f"Started PID {proc.pid}, but Telegram environment variables are not visible "
                "to Streamlit. Alerts may fail until TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID "
                "are exported before launching Streamlit."
            )

        return True, f"Signal Watcher started with PID {proc.pid}."

    except Exception as exc:
        return False, f"Failed to start Signal Watcher: {exc}"


def _stop_signal_watcher_process() -> tuple[bool, str]:
    """Stop Signal Watcher using the stored PID."""

    status = _process_status()
    pid = status.get("pid")

    try:
        pid_int = int(pid)
    except Exception:
        _clear_process_record()
        return False, "No valid Signal Watcher PID was found. Process record cleared."

    if not status["running"]:
        _clear_process_record()
        return False, "Signal Watcher was not running. Stale process record cleared."

    try:
        if hasattr(os, "killpg"):
            try:
                os.killpg(os.getpgid(pid_int), signal.SIGTERM)
            except Exception:
                os.kill(pid_int, signal.SIGTERM)
        else:
            os.kill(pid_int, signal.SIGTERM)

        for _ in range(20):
            if not _pid_is_running(pid_int):
                _clear_process_record()
                return True, f"Signal Watcher stopped. PID {pid_int} terminated."
            time.sleep(0.15)

        if hasattr(os, "killpg"):
            try:
                os.killpg(os.getpgid(pid_int), signal.SIGKILL)
            except Exception:
                os.kill(pid_int, signal.SIGKILL)
        else:
            os.kill(pid_int, signal.SIGKILL)

        _clear_process_record()
        return True, f"Signal Watcher forced stopped. PID {pid_int} killed."

    except Exception as exc:
        return False, f"Failed to stop Signal Watcher PID {pid_int}: {exc}"


def _tail_text_file(path: Path, lines: int = 80) -> str:
    try:
        if not path.exists():
            return ""
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(content[-lines:])
    except Exception as exc:
        return f"Could not read log: {exc}"



# =========================================================
# QUANT EXECUTOR HELPERS
# =========================================================

def _default_auto_trader_config() -> Dict[str, Any]:
    return {
        "enabled": True,
        "poll_interval_seconds": 10,
        "paper_account_value": 100000.0,
        "buy_allocation_dollars": 5000.0,
        "strong_buy_allocation_dollars": 10000.0,
        "max_open_positions": 10,
        "max_daily_trades": 5,
        "max_position_dollars": 10000.0,
        "min_score": 60.0,
        "allow_pyramiding": False,
        "telegram_enabled": True,
        "dry_run": False,
        "stop_loss_pct": 8.0,
        "take_profit_pct": 15.0,
        "trailing_activation_pct": 10.0,
        "trailing_stop_pct": 10.0,
        "signal_exit_enabled": True,
        "time_exit_enabled": True,
        "max_holding_days": 20,
        "allowed_asset_classes": ["Stocks", "ETFs", "Forex", "Crypto", "Gold", "Oil", "Futures"],
        "allowed_symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "AVGO", "META", "GOOGL", "AMZN", "SPY", "QQQ",
            "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", "NZDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X",
            "BTC-USD", "ETH-USD",
            "GC=F", "SI=F", "CL=F", "BZ=F", "ES=F", "NQ=F", "RTY=F",
        ],
    }


def _read_auto_trader_config() -> Dict[str, Any]:
    config = _default_auto_trader_config()
    stored = _read_json_file(AUTO_TRADER_CONFIG_FILE)
    if isinstance(stored, dict):
        config.update(stored)
    return config


def _write_auto_trader_config(config: Dict[str, Any]) -> None:
    AUTO_TRADER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTO_TRADER_CONFIG_FILE.write_text(
        json.dumps(config, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _read_auto_trader_process_record() -> Dict[str, Any]:
    return _read_json_file(AUTO_TRADER_PROCESS_FILE)


def _write_auto_trader_process_record(record: Dict[str, Any]) -> None:
    AUTO_TRADER_PROCESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTO_TRADER_PROCESS_FILE.write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _clear_auto_trader_process_record() -> None:
    try:
        if AUTO_TRADER_PROCESS_FILE.exists():
            AUTO_TRADER_PROCESS_FILE.unlink()
    except Exception as exc:
        st.session_state["acc_auto_trader_process_error"] = str(exc)


def _auto_trader_process_status() -> Dict[str, Any]:
    record = _read_auto_trader_process_record()
    pid = record.get("pid")
    running = _pid_is_running(pid)
    if record and not running:
        record = {
            **record,
            "status": "STALE_PID",
            "stale_checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    return {
        "record": record,
        "pid": pid,
        "running": running,
        "process_file_exists": AUTO_TRADER_PROCESS_FILE.exists(),
        "script_exists": AUTO_TRADER_SCRIPT.exists(),
        "stdout_log": AUTO_TRADER_STDOUT_LOG_FILE,
        "stderr_log": AUTO_TRADER_STDERR_LOG_FILE,
    }


def _start_auto_trader_process() -> tuple[bool, str]:
    current = _auto_trader_process_status()
    if current["running"]:
        return False, f"Quant Executor is already running with PID {current['pid']}."
    if not AUTO_TRADER_SCRIPT.exists():
        return False, f"Quant Executor script not found: {AUTO_TRADER_SCRIPT}"

    config = _read_auto_trader_config()
    _write_auto_trader_config(config)

    token_present = bool(os.getenv("JFBP_TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN"))
    chat_present = bool(os.getenv("JFBP_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID"))

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    try:
        AUTO_TRADER_STDOUT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        stdout_handle = AUTO_TRADER_STDOUT_LOG_FILE.open("a", encoding="utf-8")
        stderr_handle = AUTO_TRADER_STDERR_LOG_FILE.open("a", encoding="utf-8")
        popen_kwargs = {
            "cwd": str(APP_ROOT),
            "env": env,
            "stdout": stdout_handle,
            "stderr": stderr_handle,
        }
        if hasattr(os, "setsid"):
            popen_kwargs["preexec_fn"] = os.setsid
        proc = subprocess.Popen([sys.executable, str(AUTO_TRADER_SCRIPT)], **popen_kwargs)
        record = {
            "pid": proc.pid,
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "python": sys.executable,
            "script": str(AUTO_TRADER_SCRIPT),
            "cwd": str(APP_ROOT),
            "stdout_log": str(AUTO_TRADER_STDOUT_LOG_FILE),
            "stderr_log": str(AUTO_TRADER_STDERR_LOG_FILE),
            "telegram_token_visible_to_streamlit": token_present,
            "telegram_chat_visible_to_streamlit": chat_present,
            "status": "STARTED",
            "mode": "PAPER_ONLY",
        }
        _write_auto_trader_process_record(record)
        if not token_present or not chat_present:
            return True, (
                f"Quant Executor started with PID {proc.pid}, but Telegram environment variables "
                "are not visible to Streamlit. Paper fills will still be logged."
            )
        return True, f"Quant Executor started with PID {proc.pid}."
    except Exception as exc:
        return False, f"Failed to start Quant Executor: {exc}"


def _stop_auto_trader_process() -> tuple[bool, str]:
    status = _auto_trader_process_status()
    pid = status.get("pid")
    try:
        pid_int = int(pid)
    except Exception:
        _clear_auto_trader_process_record()
        return False, "No valid Quant Executor PID was found. Process record cleared."
    if not status["running"]:
        _clear_auto_trader_process_record()
        return False, "Quant Executor was not running. Stale process record cleared."
    try:
        if hasattr(os, "killpg"):
            try:
                os.killpg(os.getpgid(pid_int), signal.SIGTERM)
            except Exception:
                os.kill(pid_int, signal.SIGTERM)
        else:
            os.kill(pid_int, signal.SIGTERM)
        for _ in range(20):
            if not _pid_is_running(pid_int):
                _clear_auto_trader_process_record()
                return True, f"Quant Executor stopped. PID {pid_int} terminated."
            time.sleep(0.15)
        if hasattr(os, "killpg"):
            try:
                os.killpg(os.getpgid(pid_int), signal.SIGKILL)
            except Exception:
                os.kill(pid_int, signal.SIGKILL)
        else:
            os.kill(pid_int, signal.SIGKILL)
        _clear_auto_trader_process_record()
        return True, f"Quant Executor forced stopped. PID {pid_int} killed."
    except Exception as exc:
        return False, f"Failed to stop Quant Executor PID {pid_int}: {exc}"


def _clear_auto_trader_paper_book() -> tuple[bool, str]:
    status = _auto_trader_process_status()
    if status.get("running"):
        return False, "Stop Quant Executor before clearing the local paper book."
    targets = [
        AUTO_TRADER_STATE_FILE,
        AUTO_TRADER_ORDER_LOG_FILE,
        AUTO_TRADER_FILL_LOG_FILE,
        AUTO_TRADER_POSITION_FILE,
        AUTO_TRADER_EVENT_LOG_FILE,
        AUTO_TRADER_CLOSED_TRADES_FILE,
    ]
    removed = 0
    for path in targets:
        try:
            if path.exists():
                path.unlink()
                removed += 1
        except Exception as exc:
            return False, f"Could not clear {path.name}: {exc}"
    return True, f"Local paper book cleared. Files removed: {removed}."


def _auto_trader_snapshot() -> Dict[str, Any]:
    state = _read_json_file(AUTO_TRADER_STATE_FILE)
    stats = state.get("stats", {}) if isinstance(state.get("stats"), dict) else {}
    config = _read_auto_trader_config()
    process = _auto_trader_process_status()
    fills_df = _read_csv_file(AUTO_TRADER_FILL_LOG_FILE, max_rows=250)
    orders_df = _read_csv_file(AUTO_TRADER_ORDER_LOG_FILE, max_rows=250)
    events_df = _read_csv_file(AUTO_TRADER_EVENT_LOG_FILE, max_rows=250)
    closed_df = _read_csv_file(AUTO_TRADER_CLOSED_TRADES_FILE, max_rows=250)
    positions = _read_json_file(AUTO_TRADER_POSITION_FILE)
    if not isinstance(positions, dict):
        positions = {}

    last_finished = _parse_watcher_time(stats.get("last_scan_finished"))
    seconds_since_scan = None
    if last_finished is not None:
        if last_finished.tzinfo is None:
            last_finished = last_finished.replace(tzinfo=timezone.utc)
        seconds_since_scan = max(0, int((datetime.now(timezone.utc) - last_finished).total_seconds()))

    today = datetime.now().strftime("%Y-%m-%d")
    fills_today = 0
    if not fills_df.empty and "timestamp" in fills_df.columns:
        fills_today = int(fills_df[fills_df["timestamp"].astype(str).str.startswith(today)].shape[0])

    return {
        "state": state,
        "stats": stats,
        "config": config,
        "process": process,
        "fills_df": fills_df,
        "orders_df": orders_df,
        "events_df": events_df,
        "closed_df": closed_df,
        "positions": positions,
        "seconds_since_scan": seconds_since_scan,
        "fills_today": fills_today,
        "state_file_exists": AUTO_TRADER_STATE_FILE.exists(),
        "fill_log_exists": AUTO_TRADER_FILL_LOG_FILE.exists(),
        "order_log_exists": AUTO_TRADER_ORDER_LOG_FILE.exists(),
        "position_file_exists": AUTO_TRADER_POSITION_FILE.exists(),
        "closed_trades_file_exists": AUTO_TRADER_CLOSED_TRADES_FILE.exists(),
    }


def _auto_trader_panel() -> None:
    st.subheader("🧠 Quant Executor")
    st.caption(
        "What it means: this is the PAPER-only automated executor. It reads Signal Watcher BUY alerts, "
        "opens local simulated paper positions, manages exits, and records statistics. It does not send live IBKR orders."
    )

    snap = _auto_trader_snapshot()
    process = snap["process"]
    stats = snap["stats"]
    config = snap["config"]

    st.warning(
        "Current mode: PAPER. Positions shown here are local Quant Executor paper positions only. "
        "They will not appear in IBKR unless we later build and enable OMS/IBKR paper routing."
    )

    with st.expander("📘 How to use Quant Executor", expanded=True):
        st.markdown(
            """
            **Purpose**

            Quant Executor is the automated paper-testing engine for JFBP Quant Desk.

            **What it does now**

            1. Reads Signal Watcher BUY / STRONG BUY alerts across approved asset classes.
            2. Creates a local PAPER entry.
            3. Tracks the position in `auto_trader_paper_positions.json`.
            4. Monitors exits every cycle.
            5. Sends Telegram paper entry and exit alerts.
            6. Writes paper fills, closed trades, and performance statistics.

            **Important**

            The Paper Positions table below is **not your IBKR account**. It is a local paper book used to test the logic before broker routing. If JPM appears here and not in IBKR, that is correct.

            **Exit priority**

            Stop Loss → Trailing Stop → Take Profit → Time Exit → Signal Exit
            """
        )

    st.markdown("#### Quant Executor Control")
    status_cols = st.columns(4)
    with status_cols[0]:
        st.metric("Process", "RUNNING" if process["running"] else "STOPPED", f"PID {process.get('pid') or 'None'}")
    with status_cols[1]:
        st.metric("Mode", "PAPER", "Local only")
    with status_cols[2]:
        st.metric("Script", "FOUND" if process["script_exists"] else "MISSING")
    with status_cols[3]:
        st.metric("Heartbeat", "FRESH" if snap["seconds_since_scan"] is not None and snap["seconds_since_scan"] < 90 else "WAITING", _format_seconds_ago(snap["seconds_since_scan"]))

    config_cols = st.columns(4)
    with config_cols[0]:
        config["enabled"] = st.toggle("Enable Quant Executor", value=bool(config.get("enabled", True)))
        config["telegram_enabled"] = st.toggle("Telegram Executor Alerts", value=bool(config.get("telegram_enabled", True)))
        config["signal_exit_enabled"] = st.toggle("Signal Exit Enabled", value=bool(config.get("signal_exit_enabled", True)))
    with config_cols[1]:
        config["buy_allocation_dollars"] = st.number_input("BUY Allocation $", min_value=100.0, max_value=100000.0, step=100.0, value=float(config.get("buy_allocation_dollars", 5000.0)))
        config["strong_buy_allocation_dollars"] = st.number_input("STRONG BUY Allocation $", min_value=100.0, max_value=100000.0, step=100.0, value=float(config.get("strong_buy_allocation_dollars", 10000.0)))
    with config_cols[2]:
        config["max_open_positions"] = st.number_input("Max Open Positions", min_value=1, max_value=100, step=1, value=int(config.get("max_open_positions", 10)))
        config["max_daily_trades"] = st.number_input("Max Daily Trades", min_value=1, max_value=100, step=1, value=int(config.get("max_daily_trades", 5)))
    with config_cols[3]:
        config["min_score"] = st.number_input("Minimum Score", min_value=0.0, max_value=100.0, step=1.0, value=float(config.get("min_score", 60.0)))
        config["allow_pyramiding"] = st.toggle("Allow Pyramiding", value=bool(config.get("allow_pyramiding", False)))

    with st.expander("🌐 Multi-Asset Universe Settings", expanded=False):
        st.caption(
            "These settings prepare Quant Executor for Scanner and Pulse-page signals across stocks, ETFs, forex, crypto, gold, oil, and futures."
        )

        current_asset_classes = config.get(
            "allowed_asset_classes",
            ["Stocks", "ETFs", "Forex", "Crypto", "Gold", "Oil", "Futures"],
        )

        if not isinstance(current_asset_classes, list):
            current_asset_classes = ["Stocks", "ETFs"]

        config["allowed_asset_classes"] = st.multiselect(
            "Executor Allowed Asset Classes",
            options=["Stocks", "ETFs", "Forex", "Crypto", "Gold", "Oil", "Futures"],
            default=[
                item for item in current_asset_classes
                if item in ["Stocks", "ETFs", "Forex", "Crypto", "Gold", "Oil", "Futures"]
            ],
            key="acc_qe_allowed_asset_classes_v33",
        )

        current_symbols = config.get("allowed_symbols", [])

        if isinstance(current_symbols, list):
            current_symbols_text = ", ".join(str(item) for item in current_symbols)
        else:
            current_symbols_text = str(current_symbols or "")

        allowed_symbols_text = st.text_area(
            "Executor Allowed Symbols",
            value=current_symbols_text,
            height=110,
            key="acc_qe_allowed_symbols_v33",
            help="Comma-separated. Examples: EURUSD=X, GBPUSD=X, BTC-USD, GC=F, CL=F, ES=F, NQ=F.",
        )

        config["allowed_symbols"] = [
            symbol.strip().upper()
            for symbol in allowed_symbols_text.replace("\n", ",").split(",")
            if symbol.strip()
        ]

    with st.expander("🚪 Exit Engine Settings", expanded=True):
        st.caption(
            "Quant Executor v1.1 exit stack: Stop Loss → Trailing Stop → Take Profit → "
            "Time Exit → Signal Exit. Time Exit prevents stale positions from sitting forever."
        )

        e1, e2, e3, e4 = st.columns(4)
        with e1:
            config["stop_loss_pct"] = st.number_input(
                "Stop Loss %",
                min_value=0.1,
                max_value=50.0,
                step=0.5,
                value=float(config.get("stop_loss_pct", 8.0)),
                key="acc_qe_stop_loss_pct_v11",
            )
        with e2:
            config["take_profit_pct"] = st.number_input(
                "Take Profit %",
                min_value=0.1,
                max_value=100.0,
                step=0.5,
                value=float(config.get("take_profit_pct", 15.0)),
                key="acc_qe_take_profit_pct_v11",
            )
        with e3:
            config["trailing_activation_pct"] = st.number_input(
                "Trail Activates After Gain %",
                min_value=0.1,
                max_value=100.0,
                step=0.5,
                value=float(config.get("trailing_activation_pct", 10.0)),
                key="acc_qe_trailing_activation_pct_v11",
            )
        with e4:
            config["trailing_stop_pct"] = st.number_input(
                "Trailing Stop %",
                min_value=0.1,
                max_value=50.0,
                step=0.5,
                value=float(config.get("trailing_stop_pct", 10.0)),
                key="acc_qe_trailing_stop_pct_v11",
            )

        t1, t2, t3 = st.columns([1, 1, 2])
        with t1:
            config["time_exit_enabled"] = st.toggle(
                "Time Exit Enabled",
                value=bool(config.get("time_exit_enabled", True)),
                key="acc_qe_time_exit_enabled_v11",
                help="When enabled, Quant Executor exits positions that exceed the maximum holding period.",
            )
        with t2:
            config["max_holding_days"] = st.number_input(
                "Max Holding Days",
                min_value=1,
                max_value=252,
                step=1,
                value=int(config.get("max_holding_days", 20)),
                key="acc_qe_max_holding_days_v11",
                help="Maximum calendar days a paper position may remain open before the Time Exit triggers.",
            )
        with t3:
            st.info(
                """
TIME EXIT EXAMPLE

Entry Date .............. Day 0
Max Holding Days ........ 20
No stop/target hit ...... Position still open

Exit Trigger ............ SELL on Day 20
"""
            )

        st.info(
            """
TRAILING STOP EXAMPLE

Entry Price ............. $100
Activation Level ........ $110 (+10%)
Highest Price ........... $120
Trailing Stop ........... $108 (-10% from high)

Exit Trigger ............ SELL at $108
"""
        )

    ctl_cols = st.columns(4)
    with ctl_cols[0]:
        save_clicked = st.button("💾 Save Executor Settings", width="stretch", key="acc_save_auto_trader_config_v11")
    with ctl_cols[1]:
        start_clicked = st.button("▶ Start Quant Executor", width="stretch", disabled=bool(process["running"]), key="acc_start_auto_trader_v11")
    with ctl_cols[2]:
        stop_clicked = st.button("⏹ Stop Quant Executor", width="stretch", disabled=not bool(process["running"]), key="acc_stop_auto_trader_v11")
    with ctl_cols[3]:
        refresh_clicked = st.button("🔄 Refresh", width="stretch", key="acc_refresh_auto_trader_v11")

    if save_clicked:
        _write_auto_trader_config(config)
        st.success("Quant Executor settings saved.")
        st.rerun()
    if start_clicked:
        _write_auto_trader_config(config)
        ok, msg = _start_auto_trader_process()
        st.success(msg) if ok else st.error(msg)
        st.rerun()
    if stop_clicked:
        ok, msg = _stop_auto_trader_process()
        st.success(msg) if ok else st.warning(msg)
        st.rerun()
    if refresh_clicked:
        st.rerun()

    if process["record"]:
        with st.expander("Quant Executor process details", expanded=False):
            st.json(process["record"])
            log_cols = st.columns(2)
            with log_cols[0]:
                st.markdown("**stdout log**")
                st.code(_tail_text_file(AUTO_TRADER_STDOUT_LOG_FILE, lines=60) or "No stdout log yet.")
            with log_cols[1]:
                st.markdown("**stderr log**")
                st.code(_tail_text_file(AUTO_TRADER_STDERR_LOG_FILE, lines=60) or "No stderr log yet.")

    st.divider()

    st.success("🟢 Quant Executor engine is running.") if process["running"] else st.error("🔴 Quant Executor engine is stopped.")

    _watcher_card_grid([
        {"label": "Quant Executor", "value": "RUNNING" if process["running"] else "STOPPED", "note": "Execution process", "tone": "good" if process["running"] else "bad"},
        {"label": "Open Positions", "value": stats.get("open_positions", len(snap["positions"])), "note": "Local paper book only", "tone": "blue"},
        {"label": "Closed Positions", "value": stats.get("closed_positions", 0), "note": "Completed paper exits", "tone": "blue"},
        {"label": "Last Trade", "value": stats.get("last_symbol", "None"), "note": stats.get("last_trade_time", "Never"), "tone": "blue"},
    ])

    _watcher_card_grid([
        {"label": "Realized P&L", "value": f"${float(stats.get('realized_pnl', 0) or 0):,.2f}", "note": "Closed paper trades", "tone": "good" if float(stats.get('realized_pnl', 0) or 0) >= 0 else "bad"},
        {"label": "Unrealized P&L", "value": f"${float(stats.get('unrealized_pnl', 0) or 0):,.2f}", "note": "Open paper positions", "tone": "good" if float(stats.get('unrealized_pnl', 0) or 0) >= 0 else "bad"},
        {"label": "Win Rate", "value": f"{float(stats.get('win_rate_pct', 0) or 0):,.1f}%", "note": "Closed trades only", "tone": "blue"},
        {"label": "Profit Factor", "value": f"{float(stats.get('profit_factor', 0) or 0):,.2f}", "note": "Gross profit / gross loss", "tone": "blue"},
    ])

    _watcher_card_grid([
        {"label": "Average Win", "value": f"${float(stats.get('average_win', 0) or 0):,.2f}", "note": "Winning exits", "tone": "good"},
        {"label": "Average Loss", "value": f"${float(stats.get('average_loss', 0) or 0):,.2f}", "note": "Losing exits", "tone": "bad" if float(stats.get('average_loss', 0) or 0) < 0 else "neutral"},
        {"label": "Max Drawdown", "value": f"${float(stats.get('max_drawdown', 0) or 0):,.2f}", "note": "Closed-trade equity curve", "tone": "warn"},
        {"label": "Last Status", "value": stats.get("last_status", "UNKNOWN"), "note": stats.get("last_message", "Quant Executor cycle result"), "tone": "good" if str(stats.get("last_status", "")).upper() in ("OK", "FILLED", "EXIT_FILLED") else "warn"},
    ])

    positions = snap["positions"]
    if positions:
        st.markdown("#### Paper Positions — Local Simulator Only")
        st.caption("These positions are saved in the Quant Executor local paper book. They are not IBKR positions.")
        position_df = pd.DataFrame.from_dict(positions, orient="index")
        preferred_cols = [c for c in ["symbol", "qty", "entry_price", "avg_price", "last_price", "highest_price", "stop_loss_price", "take_profit_price", "trailing_active", "trailing_stop_price", "days_held", "max_holding_days", "time_exit_enabled", "market_value", "unrealized_pnl", "unrealized_pnl_pct", "entry_time", "last_update"] if c in position_df.columns]
        st.dataframe(position_df[preferred_cols] if preferred_cols else position_df, width="stretch")
    else:
        st.info("No paper positions yet.")

    closed_df = snap["closed_df"]
    if not closed_df.empty:
        st.markdown("#### Closed Paper Trades")
        display_cols = [c for c in ["exit_time", "symbol", "qty", "entry_price", "exit_price", "pnl_dollars", "pnl_pct", "exit_reason"] if c in closed_df.columns]
        st.dataframe(closed_df[display_cols].tail(25).iloc[::-1], width="stretch", hide_index=True)

    fills_df = snap["fills_df"]
    if not fills_df.empty:
        st.markdown("#### Recent Paper Fills")
        display_cols = [c for c in ["timestamp", "symbol", "action", "qty", "fill_price", "notional", "trade_recommendation", "exit_reason", "pnl_dollars", "pnl_pct", "opportunity_score_pct", "telegram_sent", "source"] if c in fills_df.columns]
        st.dataframe(fills_df[display_cols].tail(25).iloc[::-1], width="stretch", hide_index=True)
    else:
        st.info("No paper fills logged yet.")

    with st.expander("🧹 Paper book maintenance", expanded=False):
        st.warning("Use this only when you want to reset the local Quant Executor paper test. It does not touch IBKR.")
        confirm_clear = st.checkbox("I understand this clears only the local Quant Executor paper book", key="acc_confirm_clear_qe_paper_book")
        if st.button("Clear Local Paper Book", disabled=not confirm_clear or bool(process["running"]), width="stretch"):
            ok, msg = _clear_auto_trader_paper_book()
            st.success(msg) if ok else st.error(msg)
            st.rerun()
        if process["running"]:
            st.caption("Stop Quant Executor before clearing the local paper book.")

    with st.expander("Quant Executor files", expanded=False):
        st.write({
            "config": str(AUTO_TRADER_CONFIG_FILE),
            "state": str(AUTO_TRADER_STATE_FILE),
            "orders": str(AUTO_TRADER_ORDER_LOG_FILE),
            "fills": str(AUTO_TRADER_FILL_LOG_FILE),
            "positions": str(AUTO_TRADER_POSITION_FILE),
            "closed_trades": str(AUTO_TRADER_CLOSED_TRADES_FILE),
            "events": str(AUTO_TRADER_EVENT_LOG_FILE),
        })


# =========================================================
# SECTIONS
# =========================================================

def _header() -> None:
    st.markdown(
        f"""
        <div class="acc-hero">
            <div class="acc-hero-title">🤖 Automation Control Center</div>
            <div class="acc-hero-subtitle">
                <b>Institutional Signal Governance Layer.</b><br>
                All scanner-approved signals pass through this control page before OMS routing.
                Phase 1 is SIM-only: signals can be reviewed, approved, rejected, simulated, and audited,
                but no live automated orders are transmitted.
            </div>
            <div class="acc-version-pill">{PAGE_VERSION} · {PAGE_STATUS}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="acc-workflow">
            📈 Market Pulse → 🔎 Scanner → Research Stock / Forex / Crypto / Gold / Oil Pulse → 🤖 Automation Control Center → ⚙ OMS Execution → 🔌 Live IBKR → 💼 Portfolio → 📝 Journal
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "What it means: this page governs signal automation. It does not generate signals and it does not bypass OMS."
    )



def _sidebar_how_to() -> None:
    """Compact page guide shown in the Streamlit sidebar."""

    st.sidebar.markdown(
        """
        <div class="acc-sidebar-help">
            <b>🤖 Automation Control Center</b><br><br>
            <b>Purpose:</b><br>
            Govern scanner signals before execution.<br><br>
            <b>Workflow:</b><br>
            1. Market Pulse / Pulse pages<br>
            2. Scanner multi-asset signals<br>
            3. Verify Safety Gates<br>
            4. Approve / Reject / Hold<br>
            5. Check Audit Trail<br><br>
            <b>Status:</b> SIMULATION ONLY<br>
            <b>Telegram:</b> Safety alerts enabled
        </div>
        """,
        unsafe_allow_html=True,
    )


def _how_to_use_page() -> None:
    """Onboarding guide so the page is self-explanatory for future use."""

    st.subheader("🤖 How to Use This Page")

    st.markdown(
        """
        <div class="acc-howto">
            <b>Purpose:</b> This page is the institutional control layer between Scanner, the Pulse pages,
            and OMS Execution. It reviews stock, ETF, forex, crypto, gold, oil, and futures opportunities,
            applies automation rules, verifies safety gates,
            simulates routing decisions, and records every decision in the audit trail.
            <br><br>
            <b>Important:</b> No live automated orders are sent from this page. Current status is
            <b>SIMULATION ONLY</b>. Telegram alerts should be active before automation testing so safety events are visible immediately.
        </div>
        """,
        unsafe_allow_html=True,
    )

    s1, s2, s3 = st.columns(3)

    with s1:
        st.markdown(
            """
            <div class="acc-howto-step">
                <span class="acc-howto-num">1</span><b>Start with Market Pulse</b><br>
                Confirm the market regime and make sure risk is allowed before automation is considered.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with s2:
        st.markdown(
            """
            <div class="acc-howto-step">
                <span class="acc-howto-num">2</span><b>Run Scanner / Pulse Pages</b><br>
                Scanner, Forex Pulse, Crypto Pulse, Gold Pulse, and Oil Pulse candidates can feed the automation queue.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with s3:
        st.markdown(
            """
            <div class="acc-howto-step">
                <span class="acc-howto-num">3</span><b>Check Readiness</b><br>
                Review Automation Readiness, Safety Gates, trade capacity, and current mode.
            </div>
            """,
            unsafe_allow_html=True,
        )

    s4, s5, s6 = st.columns(3)

    with s4:
        st.markdown(
            """
            <div class="acc-howto-step">
                <span class="acc-howto-num">4</span><b>Verify Safety Gates</b><br>
                Required SIM gates include Market Pulse risk approval, Scanner active, OMS reconciled,
                risk controls active, kill switch OFF, and audit logging active.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with s5:
        st.markdown(
            """
            <div class="acc-howto-step">
                <span class="acc-howto-num">5</span><b>Review Signal Queue</b><br>
                Inspect score, regime, sector, setup, and rules compliance. Then Approve SIM, Reject, or Hold.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with s6:
        st.markdown(
            """
            <div class="acc-howto-step">
                <span class="acc-howto-num">6</span><b>Review Simulator & Audit</b><br>
                Confirm the simulated route through OMS, risk check, IBKR simulation, Journal, and Portfolio impact.
                Then confirm the action appears in the audit trail.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("🔒 Live automation status", expanded=False):
        st.warning(
            "LIVE automation is disabled in this build. Phase 3 would require ARM OMS LIVE, "
            "ARM AUTO LIVE, Live IBKR connected, Kill Switch OFF, Daily Loss Limit configured, "
            "Risk Controls active, and Audit Logging enabled."
        )

        st.markdown(
            """
            **Normal daily workflow**

            Market Pulse  
            ↓  
            Scanner  
            ↓  
            Research Stock / Forex Pulse / Crypto Pulse / Gold Pulse / Oil Pulse  
            ↓  
            Automation Control Center  
            ↓  
            OMS Execution  
            ↓  
            Live IBKR  
            ↓  
            Portfolio  
            ↓  
            Journal
            """
        )



def _dashboard_card(title: str, value: object, status: str = "", status_class: str = "", strong: bool = False) -> str:
    """Return a responsive dashboard card as HTML."""

    card_class = "acc-dashboard-card acc-dashboard-card-strong" if strong else "acc-dashboard-card"
    value_class = "acc-dashboard-value"

    if len(str(value)) > 10:
        value_class += " acc-dashboard-value-small"

    status_html = ""
    if status:
        status_html = f'<div class="acc-dashboard-status {status_class}">{status}</div>'

    return f"""
        <div class="{card_class}">
            <div class="acc-dashboard-title">{title}</div>
            <div class="{value_class}">{value}</div>
            {status_html}
        </div>
    """


def _readiness_dashboard() -> None:
    """Command dashboard using native Streamlit cards.

    This version intentionally avoids custom dashboard HTML so Streamlit does
    not display raw <div> markup on some deployments. The layout uses two
    short metric rows and compact values to stay readable on desktop, tablet,
    and mobile.
    """

    score, label = _readiness_score()
    sim_ready = all(_sim_gate_status().values()) and st.session_state.acc_mode == "SIM AUTO"
    safety_label = "PASS" if sim_ready else "FAIL"

    st.subheader("📊 Automation Status Dashboard")
    st.caption("What it means: this is the command-level view of automation readiness and system activity.")

    if label == "SIMULATION READY":
        st.success(f"Automation Readiness: {score} / 100 — {label}")
    elif label == "OFFLINE":
        st.error(f"Automation Readiness: {score} / 100 — {label}")
    elif score >= 75:
        st.warning(f"Automation Readiness: {score} / 100 — {label}")
    else:
        st.error(f"Automation Readiness: {score} / 100 — {label}")

    row1 = st.columns(4)

    with row1[0]:
        st.metric(
            "Automation Readiness",
            f"{score}/100",
            label,
        )

    with row1[1]:
        st.metric(
            "Automation Mode",
            st.session_state.acc_mode,
        )

    with row1[2]:
        st.metric(
            "Safety Gates",
            safety_label,
            "SIM gates only",
        )

    with row1[3]:
        st.metric(
            "Signals Waiting",
            _waiting_count(),
        )

    row2 = st.columns(3)

    with row2[0]:
        st.metric(
            "SIM Approvals Today",
            _approved_count_today(),
        )

    with row2[1]:
        st.metric(
            "Max Trades / Day",
            int(st.session_state.acc_max_trades_day),
        )

    with row2[2]:
        st.metric(
            "Kill Switch",
            "ON" if st.session_state.acc_kill_switch else "OFF",
        )

    row3 = st.columns(2)

    with row3[0]:
        st.metric(
            "Telegram Alerts",
            "ON" if _telegram_ready() else "OFF",
        )

    with row3[1]:
        st.metric(
            "Build Status",
            "v3.0",
            "watcher analytics",
        )

    st.caption(
        "Responsive fix: dashboard uses native Streamlit metric cards. Telegram status is part of automation safety visibility."
    )


def _telegram_controls() -> None:
    st.subheader("📲 Telegram Alerts")
    st.caption("What it means: Telegram provides immediate operator visibility when automation approves, rejects, holds, or blocks signals.")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.toggle("Telegram Connected", key="acc_telegram_connected")
        st.toggle("Telegram Alerts Enabled", key="acc_telegram_alerts_enabled")

    with c2:
        st.toggle("Notify Signal Approved", key="acc_notify_approved")
        st.toggle("Notify Signal Rejected", key="acc_notify_rejected")
        st.toggle("Notify Signal Held", key="acc_notify_held")

    with c3:
        st.toggle("Notify Safety Gate Failure", key="acc_notify_gate_failure")
        st.toggle("Notify Kill Switch", key="acc_notify_kill_switch")
        st.toggle("Notify LIVE Auto Event", key="acc_notify_live_event")

    status = "ACTIVE" if _telegram_ready() else "OFFLINE"
    st.metric("Telegram Alert Status", status)

    if st.button("Send Telegram Test Alert", width="stretch"):
        ok = _send_telegram_alert(
            "🤖 JFBP Automation Test",
            "Telegram alerts are connected to Automation Control Center.",
        )
        if ok:
            st.success("Telegram test alert recorded/sent.")
        else:
            st.warning("Telegram test alert was not sent. Check connection/settings.")

    last_alert = st.session_state.get("acc_last_telegram_alert", {})
    if last_alert:
        with st.expander("Last Telegram alert detail", expanded=False):
            st.json(last_alert)

def _mode_controls() -> None:
    st.subheader("⚙️ Automation Mode")
    st.caption("What it means: controls whether scanner-approved signals are ignored, processed in SIM, or locked for future live automation.")

    c1, c2, c3 = st.columns([1.2, 1, 1])

    with c1:
        st.radio(
            "Mode",
            options=["OFF", "SIM AUTO", "LIVE AUTO LOCKED"],
            key="acc_mode",
            horizontal=False,
            help="LIVE AUTO LOCKED is intentionally disabled in Phase 1.",
        )

    with c2:
        st.toggle("Emergency Kill Switch", key="acc_kill_switch")
        st.toggle("Market Pulse Allows Risk", key="acc_market_pulse_allowed")
        st.toggle("Scanner Active", key="acc_scanner_active")
        st.toggle("Data Feed Healthy", key="acc_data_feed_healthy")

    with c3:
        st.toggle("OMS Reconciled", key="acc_oms_reconciled")
        st.toggle("Risk Controls Active", key="acc_risk_controls_active")
        st.toggle("Live IBKR Connected", key="acc_ibkr_connected")
        st.toggle("LIVE Trading Armed", key="acc_live_armed")

        phrase = st.text_input(
            "Future LIVE phrase",
            type="password",
            placeholder="ARM AUTO LIVE",
            help="Reserved for Phase 3. Does not unlock live routing in Phase 1.",
        )
        st.session_state.acc_auto_live_phrase_ok = phrase.strip().upper() == "ARM AUTO LIVE"

    if st.session_state.acc_mode == "LIVE AUTO LOCKED":
        st.markdown(
            """
            <div class="acc-lock">
                🔒 <b>LIVE AUTO is locked.</b><br>
                Phase 1 does not route live automated orders. This page is limited to OFF and SIM-only control.
            </div>
            """,
            unsafe_allow_html=True,
        )


def _rules() -> None:
    st.subheader("📋 Automation Rules Engine")
    st.caption("What it means: only scanner signals meeting all automation criteria are eligible for SIM approval.")

    with st.expander("📋 Automation Rules Engine", expanded=True):
        r1, r2, r3 = st.columns(3)

        with r1:
            st.number_input("Minimum Opportunity Score", min_value=0, max_value=100, key="acc_min_score")
            st.number_input("Maximum Trades Per Day", min_value=1, max_value=50, key="acc_max_trades_day")
            st.number_input("Maximum Daily Loss ($)", min_value=0.0, max_value=100000.0, step=100.0, key="acc_max_daily_loss")

        with r2:
            st.number_input("Max Position Size (%)", min_value=0.1, max_value=100.0, step=0.5, key="acc_max_position_pct")
            st.number_input("Maximum Daily Risk (%)", min_value=0.1, max_value=25.0, step=0.1, key="acc_max_daily_risk_pct")
            st.multiselect(
                "Allowed Market Regimes",
                options=["RISK-ON", "SELECTIVE", "DEFENSIVE", "RISK-OFF"],
                key="acc_regime_filter",
            )
            st.multiselect(
                "Allowed Asset Classes",
                options=["Stocks", "ETFs", "Forex", "Crypto", "Gold", "Oil", "Futures"],
                key="acc_asset_class_allow",
                help="Multi-asset safety filter for Scanner, Pulse pages, Signal Watcher, and Quant Executor testing.",
            )

        with r3:
            st.text_area("Allowed Symbols", key="acc_allowed_symbols", height=94)
            st.text_area("Blocked Symbols", key="acc_blocked_symbols", height=94)

        s1, s2 = st.columns(2)

        with s1:
            st.multiselect(
                "Sector Allow List",
                options=[
                    "Technology",
                    "Financials",
                    "Healthcare",
                    "Industrials",
                    "Energy",
                    "Consumer Discretionary",
                    "Consumer Staples",
                    "Utilities",
                    "Materials",
                    "Real Estate",
                    "Communication Services",
                ],
                key="acc_sector_allow",
            )

        with s2:
            st.multiselect(
                "Sector Block List",
                options=[
                    "Technology",
                    "Financials",
                    "Healthcare",
                    "Industrials",
                    "Energy",
                    "Consumer Discretionary",
                    "Consumer Staples",
                    "Utilities",
                    "Materials",
                    "Real Estate",
                    "Communication Services",
                ],
                key="acc_sector_block",
            )

    with st.expander("📲 Notification Rules", expanded=False):
        st.caption(
            "These settings are controlled in the Telegram Alerts panel above. "
            "This summary is read-only to avoid duplicate Streamlit widget keys."
        )

        n1, n2, n3 = st.columns(3)

        with n1:
            st.write(f"Approved signals: {'ON' if st.session_state.get('acc_notify_approved') else 'OFF'}")
            st.write(f"Rejected signals: {'ON' if st.session_state.get('acc_notify_rejected') else 'OFF'}")
            st.write(f"Held signals: {'ON' if st.session_state.get('acc_notify_held') else 'OFF'}")

        with n2:
            st.write(f"Removed signals: {'ON' if st.session_state.get('acc_notify_removed') else 'OFF'}")
            st.write(f"Safety gate failure: {'ON' if st.session_state.get('acc_notify_gate_failure') else 'OFF'}")
            st.write(f"Kill switch activated: {'ON' if st.session_state.get('acc_notify_kill_switch') else 'OFF'}")

        with n3:
            st.write(f"LIVE auto event: {'ON' if st.session_state.get('acc_notify_live_event') else 'OFF'}")
            st.metric("Telegram", "ACTIVE" if _telegram_ready() else "OFFLINE")


def _safety_gates() -> None:
    st.subheader("🛡 Safety Gate Monitor")
    st.caption("What it means: every required gate must pass before automation can process signals.")

    gates = _gate_status()
    gcols = st.columns(3)

    for i, (name, ok) in enumerate(gates.items()):
        with gcols[i % 3]:
            st.markdown(
                f"""
                <div class="acc-card">
                    {'✅' if ok else '❌'} <b>{name}</b><br>
                    <span class="{'acc-good' if ok else 'acc-bad'}">{'PASS' if ok else 'BLOCKED'}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    sim_ready = all(_sim_gate_status().values()) and st.session_state.acc_mode == "SIM AUTO"
    live_ready = all(gates.values()) and st.session_state.acc_mode == "LIVE AUTO LOCKED"

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("SIM Automation", "READY" if sim_ready else "BLOCKED")
    with m2:
        st.metric("LIVE Automation", "LOCKED" if not live_ready else "GATED")
    with m3:
        st.metric("Kill Switch", "ON" if st.session_state.acc_kill_switch else "OFF")
    with m4:
        st.metric("Audit Logging", "ACTIVE" if st.session_state.acc_audit_logging_active else "OFF")


def _signal_queue() -> None:
    st.subheader("📥 Scanner Signal Queue")
    st.caption("What it means: this is the operating queue for scanner-approved candidates awaiting SIM approval, rejection, or hold.")

    if not st.session_state.acc_queue:
        st.info("No scanner signals are currently waiting in the automation queue.")
        return

    queue_df = pd.DataFrame(st.session_state.acc_queue)
    if not queue_df.empty:
        queue_df["asset_class"] = queue_df.apply(
            lambda row: _asset_class_for_signal(row.to_dict()),
            axis=1,
        )
    display_cols = ["time", "symbol", "side", "score", "regime", "asset_class", "sector", "setup", "status"]
    st.dataframe(queue_df[display_cols], width="stretch", hide_index=True)

    st.divider()

    for signal in list(st.session_state.acc_queue):
        with st.expander(
            f"{signal['symbol']} — {signal['side']} — Score {signal['score']} — {signal['status']}",
            expanded=False,
        ):
            ok, note = _evaluate_signal(signal)

            c1, c2 = st.columns([2, 1])

            with c1:
                st.write(f"**Setup:** {signal['setup']}")
                st.write(f"**Regime:** {signal['regime']}")
                st.write(f"**Asset Class:** {_asset_class_for_signal(signal)}")
                st.write(f"**Sector:** {signal['sector']}")
                st.write(f"**Reason:** {signal['reason']}")
                if ok:
                    st.success(note)
                else:
                    st.warning(note)

            with c2:
                approve_disabled = not ok or signal["status"] != "WAITING"
                action_disabled = signal["status"] != "WAITING"

                if st.button("Approve SIM", key=f"approve_{signal['id']}", disabled=approve_disabled, width="stretch"):
                    signal["status"] = "APPROVED_SIM"
                    _audit("APPROVED_SIM", signal, note)
                    st.rerun()

                if st.button("Reject", key=f"reject_{signal['id']}", disabled=action_disabled, width="stretch"):
                    signal["status"] = "REJECTED"
                    _audit("REJECTED", signal, "Rejected manually by operator.")
                    st.rerun()

                if st.button("Hold", key=f"hold_{signal['id']}", disabled=action_disabled, width="stretch"):
                    signal["status"] = "HELD"
                    _audit("HELD", signal, "Held for further review.")
                    st.rerun()

                if st.button("Remove", key=f"remove_{signal['id']}", width="stretch"):
                    _audit("REMOVED", signal, "Removed from signal queue.")
                    st.session_state.acc_queue = [
                        x for x in st.session_state.acc_queue
                        if x["id"] != signal["id"]
                    ]
                    st.rerun()


def _routing_simulator() -> None:
    st.subheader("⚙ Routing Simulator")
    st.caption("What it means: this shows how a qualifying signal would move through the JFBP stack. No live orders are transmitted.")

    steps = [
        "Scanner Signal Accepted",
        "Automation Rules Passed",
        "OMS Ticket Simulated",
        "Risk Check Passed",
        "IBKR Route Simulated",
        "Journal Record Prepared",
        "Portfolio Impact Estimated",
    ]

    for idx, step in enumerate(steps):
        st.markdown(f'<div class="acc-step">{step}</div>', unsafe_allow_html=True)
        if idx < len(steps) - 1:
            st.markdown('<div class="acc-arrow">↓</div>', unsafe_allow_html=True)

    st.info("SIM-only: this simulator documents the future route. It does not create live IBKR orders.")


def _daily_risk_controls() -> None:
    st.subheader("🚨 Daily Risk Controls")
    st.caption("What it means: automation must remain inside predefined daily loss, trade count, position size, and exposure limits.")

    trade_count = _approved_count_today()
    remaining = max(0, int(st.session_state.acc_max_trades_day) - trade_count)

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric("Max Daily Loss", f"${float(st.session_state.acc_max_daily_loss):,.0f}")
    with c2:
        st.metric("Current Drawdown", f"${float(st.session_state.acc_current_drawdown):,.0f}")
    with c3:
        st.metric("Trade Count", f"{trade_count} / {int(st.session_state.acc_max_trades_day)}")
    with c4:
        st.metric("Remaining Capacity", remaining)
    with c5:
        st.metric("Exposure Utilization", f"{int(st.session_state.acc_exposure_utilization)}%")


def _audit_trail() -> None:
    st.subheader("📜 Automation Audit Trail")
    st.caption("What it means: every accepted, rejected, held, or removed automated signal is recorded for accountability and review.")

    if not st.session_state.acc_audit:
        st.info("No automation decisions have been recorded yet.")
        return

    audit_df = pd.DataFrame(st.session_state.acc_audit)
    st.dataframe(audit_df, width="stretch", hide_index=True)

    csv = audit_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Audit CSV",
        data=csv,
        file_name="automation_control_audit.csv",
        mime="text/csv",
    )


def _live_vault() -> None:
    st.subheader("🔒 LIVE Automation Vault")
    st.caption("What it means: live automation is future functionality and remains locked in the current build.")

    requirements = [
        ("ARM OMS LIVE", st.session_state.acc_live_armed),
        ("ARM AUTO LIVE", st.session_state.acc_auto_live_phrase_ok),
        ("Live IBKR Connected", st.session_state.acc_ibkr_connected),
        ("Kill Switch OFF", not st.session_state.acc_kill_switch),
        ("Daily Loss Limit Configured", st.session_state.acc_max_daily_loss > 0),
        ("Risk Controls Active", st.session_state.acc_risk_controls_active),
        ("Audit Logging Enabled", st.session_state.acc_audit_logging_active),
        ("Telegram Connected", st.session_state.acc_telegram_connected),
    ]

    st.markdown(
        """
        <div class="acc-vault">
            <b>LIVE Automation Not Available In Current Build</b><br>
            This vault shows the future requirements for Phase 3 only.
            The current page remains SIMULATION ONLY.
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for idx, (name, ok) in enumerate(requirements):
        with cols[idx % 2]:
            st.markdown(
                f"""
                <div class="acc-card">
                    {'✅' if ok else '🔒'} <b>{name}</b><br>
                    <span class="{'acc-good' if ok else 'acc-bad'}">{'READY' if ok else 'LOCKED'}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )




def _watcher_card_grid(cards: List[Dict[str, object]]) -> None:
    """Responsive Signal Watcher cards without raw HTML rendering."""

    pieces = ['<div class="acc-watch-grid">']

    for card in cards:
        label = str(card.get("label", ""))
        value = str(card.get("value", ""))
        note = str(card.get("note", ""))
        tone = str(card.get("tone", "neutral"))

        tone_class = {
            "good": "acc-watch-good",
            "bad": "acc-watch-bad",
            "warn": "acc-watch-warn",
            "blue": "acc-watch-blue",
            "neutral": "acc-watch-neutral",
        }.get(tone, "acc-watch-neutral")

        note_html = f'<div class="acc-watch-note">{note}</div>' if note else ""

        # Keep each card on one line. Indented multiline HTML can be interpreted
        # as a code block by Streamlit/Markdown on some deployments.
        pieces.append(
            f'<div class="acc-watch-card {tone_class}">'
            f'<div class="acc-watch-label">{label}</div>'
            f'<div class="acc-watch-value">{value}</div>'
            f'{note_html}'
            f'</div>'
        )

    pieces.append('</div>')
    st.markdown("".join(pieces), unsafe_allow_html=True)



def _today_filter(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Return rows whose timestamp starts with today's local date."""

    if df is None or df.empty or timestamp_col not in df.columns:
        return pd.DataFrame()

    today = datetime.now().strftime("%Y-%m-%d")
    work = df.copy()
    work["_timestamp_text"] = work[timestamp_col].astype(str)
    return work[work["_timestamp_text"].str.startswith(today)].copy()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def _safe_mean(series: Any) -> float:
    try:
        value = pd.to_numeric(series, errors="coerce").dropna().mean()
        if pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _signal_watcher_analytics(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Build operational analytics from Signal Watcher CSV logs."""

    scan_df = snapshot.get("scan_df", pd.DataFrame())
    alert_df = snapshot.get("alert_df", pd.DataFrame())
    signal_df = snapshot.get("signal_df", pd.DataFrame())
    stats = snapshot.get("stats", {}) if isinstance(snapshot.get("stats"), dict) else {}

    today_scans = _today_filter(scan_df)
    today_alerts = _today_filter(alert_df)
    today_signals = _today_filter(signal_df)

    scans_today = int(today_scans.shape[0]) if not today_scans.empty else 0
    alerts_today = int(today_alerts.shape[0]) if not today_alerts.empty else snapshot.get("alerts_today", 0)

    duplicates_today = 0
    errors_today = 0
    rows_today = 0

    if not today_scans.empty:
        if "duplicates_blocked" in today_scans.columns:
            duplicates_today = int(pd.to_numeric(today_scans["duplicates_blocked"], errors="coerce").fillna(0).sum())
        if "errors" in today_scans.columns:
            errors_today = int(pd.to_numeric(today_scans["errors"], errors="coerce").fillna(0).sum())
        if "rows" in today_scans.columns:
            rows_today = int(pd.to_numeric(today_scans["rows"], errors="coerce").fillna(0).sum())

    rec_counts = {}
    signal_counts = {}
    top_buy_rows = pd.DataFrame()
    top_sector_rows = pd.DataFrame()
    avg_score = 0.0

    if not today_signals.empty:
        if "trade_recommendation" in today_signals.columns:
            rec_counts = (
                today_signals["trade_recommendation"]
                .astype(str)
                .str.upper()
                .value_counts()
                .to_dict()
            )
        if "signal" in today_signals.columns:
            signal_counts = (
                today_signals["signal"]
                .astype(str)
                .str.upper()
                .value_counts()
                .to_dict()
            )
        if "opportunity_score_pct" in today_signals.columns:
            avg_score = _safe_mean(today_signals["opportunity_score_pct"])

        if "sector" in today_signals.columns:
            top_sector_rows = (
                today_signals.assign(sector=today_signals["sector"].astype(str))
                .groupby("sector", dropna=False)
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
                .head(8)
            )

        if "trade_recommendation" in today_signals.columns:
            buy_mask = today_signals["trade_recommendation"].astype(str).str.upper().isin(["BUY", "STRONG BUY"])
            top_buy_rows = today_signals[buy_mask].copy()
            if not top_buy_rows.empty and "opportunity_score_pct" in top_buy_rows.columns:
                top_buy_rows["_score_sort"] = pd.to_numeric(top_buy_rows["opportunity_score_pct"], errors="coerce").fillna(0)
                top_buy_rows = top_buy_rows.sort_values("_score_sort", ascending=False).drop(columns=["_score_sort"])
            top_buy_rows = top_buy_rows.head(12)

    else:
        # Backward compatibility before the v3 signal log exists.
        rec_counts = stats.get("last_scan_recommendation_counts", {}) if isinstance(stats.get("last_scan_recommendation_counts"), dict) else {}
        signal_counts = stats.get("last_scan_signal_counts", {}) if isinstance(stats.get("last_scan_signal_counts"), dict) else {}

    buy_count = _safe_int(rec_counts.get("BUY", 0))
    strong_buy_count = _safe_int(rec_counts.get("STRONG BUY", 0))
    watch_count = _safe_int(rec_counts.get("WATCH", 0))
    sell_count = _safe_int(rec_counts.get("SELL", 0))
    avoid_count = _safe_int(rec_counts.get("AVOID", 0))

    return {
        "scans_today": scans_today,
        "alerts_today": alerts_today,
        "duplicates_today": duplicates_today,
        "errors_today": errors_today,
        "rows_today": rows_today,
        "buy_count": buy_count,
        "strong_buy_count": strong_buy_count,
        "watch_count": watch_count,
        "sell_count": sell_count,
        "avoid_count": avoid_count,
        "avg_score": avg_score,
        "rec_counts": rec_counts,
        "signal_counts": signal_counts,
        "today_alerts": today_alerts,
        "today_signals": today_signals,
        "top_buy_rows": top_buy_rows,
        "top_sector_rows": top_sector_rows,
    }


def _signal_watcher_analytics_panel(snapshot: Dict[str, Any]) -> None:
    st.markdown("#### 📈 Signal Watcher Analytics")
    st.caption(
        "What it means: this shows what the watcher is doing today, not just whether it is alive."
    )

    analytics = _signal_watcher_analytics(snapshot)

    _watcher_card_grid([
        {
            "label": "Scans Today",
            "value": analytics["scans_today"],
            "note": "Watcher cycles logged today",
            "tone": "blue",
        },
        {
            "label": "Rows Today",
            "value": analytics["rows_today"],
            "note": "Total signal rows processed",
            "tone": "neutral",
        },
        {
            "label": "BUY Today",
            "value": analytics["buy_count"],
            "note": "BUY recommendations observed",
            "tone": "good" if analytics["buy_count"] else "neutral",
        },
        {
            "label": "Strong BUY Today",
            "value": analytics["strong_buy_count"],
            "note": "Highest-conviction BUY signals",
            "tone": "good" if analytics["strong_buy_count"] else "neutral",
        },
        {
            "label": "WATCH Today",
            "value": analytics["watch_count"],
            "note": "Watchlist-level candidates",
            "tone": "warn" if analytics["watch_count"] else "neutral",
        },
        {
            "label": "SELL / AVOID Today",
            "value": analytics["sell_count"] + analytics["avoid_count"],
            "note": "Risk-off or weak setups",
            "tone": "bad" if (analytics["sell_count"] + analytics["avoid_count"]) else "neutral",
        },
        {
            "label": "Duplicates Today",
            "value": analytics["duplicates_today"],
            "note": "Repeated alerts suppressed",
            "tone": "warn" if analytics["duplicates_today"] else "neutral",
        },
        {
            "label": "Errors Today",
            "value": analytics["errors_today"],
            "note": "Data/model errors",
            "tone": "bad" if analytics["errors_today"] else "good",
        },
    ])

    if not snapshot.get("signal_log_exists"):
        st.info(
            "Signal Watcher v3 analytics log has not been created yet. Start or restart the v3 watcher once; "
            "the BUY/WATCH/SELL counts will populate after the next scan."
        )

    top_buy_rows = analytics["top_buy_rows"]
    top_sector_rows = analytics["top_sector_rows"]
    today_alerts = analytics["today_alerts"]

    left, right = st.columns([1.35, 1.0])

    with left:
        st.markdown("##### Today's BUY / STRONG BUY candidates")
        if isinstance(top_buy_rows, pd.DataFrame) and not top_buy_rows.empty:
            display_cols = [
                col for col in [
                    "timestamp",
                    "symbol",
                    "trade_recommendation",
                    "price",
                    "model_score",
                    "opportunity_score_pct",
                    "sector",
                    "trend",
                    "rs_score",
                ]
                if col in top_buy_rows.columns
            ]
            st.dataframe(
                top_buy_rows[display_cols].head(12),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No BUY / STRONG BUY candidates logged today yet.")

    with right:
        st.markdown("##### Sector Activity")
        if isinstance(top_sector_rows, pd.DataFrame) and not top_sector_rows.empty:
            st.dataframe(
                top_sector_rows,
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Sector activity appears after v3 signal rows are logged.")

    st.markdown("##### Last 10 Telegram Alerts")
    if isinstance(today_alerts, pd.DataFrame) and not today_alerts.empty:
        display_cols = [
            col for col in [
                "timestamp",
                "symbol",
                "trade_recommendation",
                "price",
                "model_score",
                "opportunity_score_pct",
                "telegram_sent",
                "telegram_status",
            ]
            if col in today_alerts.columns
        ]
        st.dataframe(
            today_alerts[display_cols].tail(10).iloc[::-1],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No Telegram alerts logged today yet.")

def _signal_watcher_panel() -> None:
    st.subheader("🔔 Signal Watcher")
    st.caption(
        "What it means: this monitors the background BUY-signal alert engine. "
        "This panel does not send orders and does not start live trading."
    )

    snapshot = _watcher_health_snapshot()
    stats = snapshot["stats"]
    process = _process_status()

    st.markdown("#### Signal Watcher Control")

    # v2.5.3: keep iPad layout clean by separating status cards from buttons.
    status_cols = st.columns(3)

    with status_cols[0]:
        st.metric(
            "Process",
            "RUNNING" if process["running"] else "STOPPED",
            f"PID {process.get('pid') or 'None'}",
        )

    with status_cols[1]:
        st.metric(
            "Script",
            "FOUND" if process["script_exists"] else "MISSING",
        )

    with status_cols[2]:
        st.metric(
            "Heartbeat",
            "FRESH" if snapshot["running"] else "STALE",
            _format_seconds_ago(snapshot["seconds_since_scan"]),
        )

    st.caption("Control")
    button_cols = st.columns(3)

    with button_cols[0]:
        start_clicked = st.button(
            "▶ Start Watcher",
            width="stretch",
            disabled=bool(process["running"]),
            key="acc_start_signal_watcher_v25",
        )

    with button_cols[1]:
        stop_clicked = st.button(
            "⏹ Stop Watcher",
            width="stretch",
            disabled=not bool(process["running"]),
            key="acc_stop_signal_watcher_v25",
        )

    with button_cols[2]:
        refresh_clicked = st.button(
            "🔄 Refresh Status",
            width="stretch",
            key="acc_refresh_signal_watcher_v25",
        )

    if start_clicked:
        ok, message = _start_signal_watcher_process()
        if ok:
            st.success(message)
        else:
            st.error(message)
        st.rerun()

    if stop_clicked:
        ok, message = _stop_signal_watcher_process()
        if ok:
            st.success(message)
        else:
            st.warning(message)
        st.rerun()

    if refresh_clicked:
        st.rerun()

    if process["record"]:
        with st.expander("Signal Watcher process details", expanded=False):
            st.json(process["record"])

            log_cols = st.columns(2)
            with log_cols[0]:
                st.markdown("**stdout log**")
                st.code(_tail_text_file(SIGNAL_WATCHER_STDOUT_LOG_FILE, lines=60) or "No stdout log yet.")
            with log_cols[1]:
                st.markdown("**stderr log**")
                st.code(_tail_text_file(SIGNAL_WATCHER_STDERR_LOG_FILE, lines=60) or "No stderr log yet.")

    st.divider()

    if not snapshot["state_file_exists"]:
        st.warning(
            "Signal Watcher has not written a state file yet. Start the watcher once, "
            "then refresh this page."
        )
    elif snapshot["running"]:
        st.success("🟢 Signal Watcher appears to be running recently.")
    else:
        st.error("🔴 Signal Watcher appears stopped or stale.")

    status_label = "RUNNING" if snapshot["running"] else "STOPPED"
    status_note = "Fresh scan detected" if snapshot["running"] else "No recent scan / stale"
    last_scan_finished = str(stats.get("last_scan_finished") or "Never")
    last_scan_status = str(stats.get("last_scan_status") or "UNKNOWN")
    watcher_version = str(stats.get("watcher_version", "Unknown"))
    watcher_version_display = watcher_version
    watcher_version_note = "Background engine build"
    if watcher_version.lower().startswith("v2.0") and "scanner" in watcher_version.lower():
        watcher_version_display = "v2.0"
        watcher_version_note = "scanner-integrated build"

    _watcher_card_grid([
        {
            "label": "Watcher Status",
            "value": status_label,
            "note": status_note,
            "tone": "good" if snapshot["running"] else "bad",
        },
        {
            "label": "Last Scan",
            "value": _format_seconds_ago(snapshot["seconds_since_scan"]),
            "note": last_scan_finished,
            "tone": "blue",
        },
        {
            "label": "Alerts Today",
            "value": snapshot["alerts_today"],
            "note": "Telegram BUY alerts logged today",
            "tone": "blue",
        },
        {
            "label": "Last Alert",
            "value": snapshot["last_alert_symbol"],
            "note": snapshot["last_alert_time"],
            "tone": "blue",
        },
    ])

    _watcher_card_grid([
        {
            "label": "Scan Status",
            "value": last_scan_status,
            "note": "Last watcher cycle result",
            "tone": "good" if last_scan_status == "OK" else "warn",
        },
        {
            "label": "Symbols Scanned",
            "value": stats.get("last_scan_symbol_count", 0),
            "note": "Universe size used last scan",
            "tone": "neutral",
        },
        {
            "label": "Rows",
            "value": stats.get("last_scan_rows", 0),
            "note": "Signal rows generated",
            "tone": "neutral",
        },
        {
            "label": "Alerts Last Scan",
            "value": stats.get("last_scan_alerts_sent", 0),
            "note": "New alerts in last cycle",
            "tone": "blue",
        },
        {
            "label": "Duplicates Blocked",
            "value": stats.get("last_scan_duplicates_blocked", 0),
            "note": "Repeated BUY alerts suppressed",
            "tone": "warn" if int(stats.get("last_scan_duplicates_blocked", 0) or 0) else "neutral",
        },
        {
            "label": "Errors Last Scan",
            "value": stats.get("last_scan_errors", 0),
            "note": "Data/model errors",
            "tone": "bad" if int(stats.get("last_scan_errors", 0) or 0) else "good",
        },
        {
            "label": "Scan Interval",
            "value": f"{stats.get('last_scan_interval_minutes', 5)} min",
            "note": "Configured watcher frequency",
            "tone": "blue",
        },
        {
            "label": "Watcher Version",
            "value": watcher_version_display,
            "note": watcher_version_note,
            "tone": "neutral",
        },
    ])

    st.divider()
    _signal_watcher_analytics_panel(snapshot)

    st.info(
        "Start/Stop controls are active. Signal Watcher remains alerts-only: no OMS, no IBKR, no orders."
    )

    with st.expander("Watcher file status", expanded=False):
        st.write(
            {
                "state_file": str(SIGNAL_WATCHER_STATE_FILE),
                "state_file_exists": snapshot["state_file_exists"],
                "scan_log": str(SIGNAL_WATCHER_SCAN_LOG_FILE),
                "scan_log_exists": snapshot["scan_log_exists"],
                "alert_log": str(SIGNAL_WATCHER_ALERT_LOG_FILE),
                "alert_log_exists": snapshot["alert_log_exists"],
                "signal_log": str(SIGNAL_WATCHER_SIGNAL_LOG_FILE),
                "signal_log_exists": snapshot["signal_log_exists"],
                "last_scan_finished": last_scan_finished,
                "last_alert_time": snapshot["last_alert_time"],
            }
        )

    alert_df = snapshot["alert_df"]
    if not alert_df.empty:
        st.markdown("#### Recent Signal Watcher Alerts")
        display_cols = [
            col for col in [
                "timestamp",
                "symbol",
                "trade_recommendation",
                "price",
                "model_score",
                "opportunity_score_pct",
                "telegram_sent",
                "telegram_status",
            ]
            if col in alert_df.columns
        ]
        st.dataframe(
            alert_df[display_cols].tail(20).iloc[::-1],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No Signal Watcher alerts logged yet.")

    scan_df = snapshot["scan_df"]
    if not scan_df.empty:
        with st.expander("Recent Signal Watcher scans", expanded=False):
            st.dataframe(
                scan_df.tail(20).iloc[::-1],
                width="stretch",
                hide_index=True,
            )

def _future_phase_box() -> None:
    st.subheader("🧭 Future Roadmap")
    st.caption("What it means: these capabilities are intentionally staged so automation never outruns safety.")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div class="acc-card">
                <b>Phase 1 — Current</b><br>
                ✅ OFF / SIM only<br>
                ✅ Multi-asset signal queue<br>
                ✅ Approve / reject / hold<br>
                ✅ Routing simulator<br>
                ✅ Audit trail<br>
                ❌ No live routing
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div class="acc-card">
                <b>Phase 2 — SIM Routing</b><br>
                SIM auto-route to OMS<br>
                OMS paper validation<br>
                Multi-asset reconciliation checks<br>
                Journal integration<br>
                Portfolio impact preview
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            """
            <div class="acc-card">
                <b>Phase 3 — LIVE Automation</b><br>
                ARM OMS LIVE<br>
                ARM AUTO LIVE<br>
                Daily loss limit<br>
                Live IBKR connection<br>
                Hard kill switch<br>
                Full audit trail
            </div>
            """,
            unsafe_allow_html=True,
        )


def _footer() -> None:
    st.markdown(
        f"""
        <div class="acc-footer">
            <b>Automation Control Center {PAGE_VERSION}</b><br>
            Status: <b>{PAGE_STATUS}</b><br>
            Purpose: Institutional signal governance and automation oversight between Scanner and OMS Execution.
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# PUBLIC ENTRYPOINT
# =========================================================

def run_page() -> None:
    _init_state()
    _inject_css()

    _sidebar_how_to()
    _header()
    _how_to_use_page()
    _readiness_dashboard()

    st.markdown(
        '<div class="acc-tabs-note">Tip: on smaller screens, swipe the tab row sideways to see all sections.</div>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs([
        "Control",
        "Rules",
        "Safety Gates",
        "Signal Queue",
        "Simulator",
        "Risk",
        "Audit",
        "LIVE Vault",
        "Signal Watcher",
        "Quant Executor",
        "Roadmap",
    ])

    with tabs[0]:
        _mode_controls()
        st.divider()
        _telegram_controls()

    with tabs[1]:
        _rules()

    with tabs[2]:
        _safety_gates()

    with tabs[3]:
        _signal_queue()

    with tabs[4]:
        _routing_simulator()

    with tabs[5]:
        _daily_risk_controls()

    with tabs[6]:
        _audit_trail()

    with tabs[7]:
        _live_vault()

    with tabs[8]:
        _signal_watcher_panel()

    with tabs[9]:
        _auto_trader_panel()

    with tabs[10]:
        _future_phase_box()

    _footer()


if __name__ == "__main__":
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
    run_page()
