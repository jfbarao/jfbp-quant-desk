# =========================================================
# 📈 JFBP RESEARCH STOCK PAGE — v93 RESEARCH COMMAND CENTER
# =========================================================

import streamlit as st
import pandas as pd
import yfinance as yf

from core.responsive import inject_responsive_css, columns as responsive_columns
from core.ui_cards import inject_card_css

try:
    from pages.SaaS_Core import remember_active_page
except Exception:
    def remember_active_page(page_name: str):
        return None

try:
    from universe.jfbp_universe import JFBP_UNIVERSE
except Exception:
    JFBP_UNIVERSE = {}

try:
    from engines.earnings_risk import analyze_symbol_earnings_risk, earnings_exemption_type
except Exception:
    analyze_symbol_earnings_risk = None
    earnings_exemption_type = None

try:
    from engines.economic_calendar import (
        analyze_economic_calendar,
        sample_events,
    )
except Exception:
    analyze_economic_calendar = None
    sample_events = None



# =========================================================
# SECTOR BENCHMARK HELPERS
# =========================================================

def sector_benchmark_for_profile(ticker: str, profile: dict) -> dict:
    ticker = str(ticker or "").upper().strip()
    profile = profile if isinstance(profile, dict) else {}

    sector = str(profile.get("sector", "") or "").upper().strip()
    regime_raw = profile.get("regime", [])

    if isinstance(regime_raw, (list, tuple)):
        regime = " ".join(str(item) for item in regime_raw).upper()
    else:
        regime = str(regime_raw or "").upper()

    combined = f"{ticker} {sector} {regime}"

    if any(term in combined for term in ("SEMI", "CHIP", "NVDA", "AMD", "LRCX", "ASML", "ARM", "SMCI", "MU", "TSM")):
        return {"symbol": "SMH", "label": "Semiconductors", "source": "ETF"}

    if any(term in combined for term in ("TECH", "SOFTWARE", "CLOUD", "AI", "CYBER")):
        return {"symbol": "XLK", "label": "Technology", "source": "ETF"}

    if any(term in combined for term in ("FINANC", "BANK", "INSURANCE", "BROKER")):
        return {"symbol": "XLF", "label": "Financials", "source": "ETF"}

    if any(term in combined for term in ("ENERGY", "OIL", "GAS")):
        return {"symbol": "XLE", "label": "Energy", "source": "ETF"}

    if any(term in combined for term in ("HEALTH", "PHARMA", "BIOTECH", "MEDICAL")):
        return {"symbol": "XLV", "label": "Healthcare", "source": "ETF"}

    if any(term in combined for term in ("INDUSTRIAL", "AEROSPACE", "DEFENSE", "MACHINERY")):
        return {"symbol": "XLI", "label": "Industrials", "source": "ETF"}

    if any(term in combined for term in ("CONSUMER DEFENSIVE", "DEFENSIVE", "STAPLES", "GROCERY")):
        return {"symbol": "XLP", "label": "Consumer Staples", "source": "ETF"}

    if any(term in combined for term in ("CONSUMER", "RETAIL", "DISCRETIONARY", "ECOMMERCE")):
        return {"symbol": "XLY", "label": "Consumer Discretionary", "source": "ETF"}

    if any(term in combined for term in ("UTILITY", "UTILITIES")):
        return {"symbol": "XLU", "label": "Utilities", "source": "ETF"}

    if any(term in combined for term in ("REAL ESTATE", "REIT")):
        return {"symbol": "XLRE", "label": "Real Estate", "source": "ETF"}

    if any(term in combined for term in ("MATERIAL", "MINING", "CHEMICAL")):
        return {"symbol": "XLB", "label": "Materials", "source": "ETF"}

    if any(term in combined for term in ("COMMUNICATION", "MEDIA", "TELECOM")):
        return {"symbol": "XLC", "label": "Communication Services", "source": "ETF"}

    if ticker in {"SPY", "QQQ", "DIA", "IWM", "TQQQ", "UVXY"}:
        return {"symbol": "SPY", "label": "Broad Market", "source": "ETF"}

    return {"symbol": "SPY", "label": "Broad Market Fallback", "source": "FALLBACK"}


def relative_strength_label(value: float) -> str:
    try:
        value = float(value)
    except Exception:
        return "UNKNOWN"

    if value >= 1.05:
        return "STRONG"
    if value <= 0.97:
        return "WEAK"
    return "NEUTRAL"


def research_bias_from_context(trend: str, model_score: int, market_rs_label: str, sector_rs_label: str) -> str:
    trend = str(trend or "UNKNOWN").upper().strip()
    market_rs_label = str(market_rs_label or "UNKNOWN").upper().strip()
    sector_rs_label = str(sector_rs_label or "UNKNOWN").upper().strip()

    if trend == "BULLISH" and model_score >= 3 and market_rs_label == "STRONG":
        if sector_rs_label in ("STRONG", "NEUTRAL"):
            return "BULLISH"
        return "BULLISH BUT SECTOR-LAGGING"

    if trend == "BEARISH" and model_score <= 1:
        return "BEARISH"

    return "NEUTRAL"


def conditions_to_buy(
    signal: str,
    model_score: int,
    combined_label: str,
    days_until,
    sector_rs_label: str,
    sector_leadership_label_value: str = "UNKNOWN",
) -> list:
    signal = str(signal or "NO TRADE").upper().strip()
    combined_label = str(combined_label or "NONE").upper().strip()
    sector_rs_label = str(sector_rs_label or "UNKNOWN").upper().strip()
    sector_leadership_label_value = str(
        sector_leadership_label_value or "UNKNOWN"
    ).upper().strip()

    conditions = []

    if signal != "BUY":
        conditions.append("Research Score must generate a BUY signal.")

    if model_score < 4:
        conditions.append("Research Score should improve to at least 4/5.")

    try:
        days_int = int(float(days_until)) if days_until is not None else None
    except Exception:
        days_int = None

    if days_int is not None and days_int <= 7:
        conditions.append("Wait for earnings risk to clear or reduce after the release.")

    if combined_label in ("HIGH", "EXTREME"):
        conditions.append("Combined event risk should fall below HIGH.")

    if sector_rs_label == "WEAK":
        conditions.append("Sector-relative strength should improve versus the sector benchmark.")

    if sector_leadership_label_value in ("WEAK", "AVERAGE", "UNKNOWN"):
        conditions.append("Sector leadership rank should improve into the top half of the sector.")

    if not conditions:
        conditions.append("Current setup already meets research BUY conditions; apply portfolio and risk rules.")

    return conditions




# =========================================================
# SECTOR LEADERSHIP HELPERS
# =========================================================

def _normalize_yf_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()

    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [
            "_".join([str(i) for i in col if i])
            for col in frame.columns
        ]

    return frame


def _find_yf_col(frame: pd.DataFrame, name: str):
    exact = [
        col for col in frame.columns
        if str(col).lower() == name.lower()
    ]

    if exact:
        return exact[0]

    matches = [
        col for col in frame.columns
        if name.lower() in str(col).lower()
    ]

    return matches[0] if matches else None


@st.cache_data(ttl=900)
def cached_sector_leadership_context(
    ticker: str,
    sector: str,
    sector_benchmark_symbol: str,
) -> dict:
    ticker = str(ticker or "").upper().strip()
    sector = str(sector or "").strip()
    sector_benchmark_symbol = str(
        sector_benchmark_symbol or "SPY"
    ).upper().strip()

    if not ticker or not sector:
        return {
            "sector": sector or "UNKNOWN",
            "sector_benchmark": sector_benchmark_symbol,
            "target_symbol": ticker,
            "target_rank": None,
            "total_symbols": 0,
            "percentile": None,
            "leader_symbol": None,
            "rows": [],
            "status": "NO_SECTOR",
        }

    peers = [
        symbol for symbol, meta in JFBP_UNIVERSE.items()
        if isinstance(meta, dict)
        and str(meta.get("sector", "")).strip() == sector
        and str(symbol).upper().strip() not in {
            "SPY",
            "QQQ",
            "DIA",
            "IWM",
            "TQQQ",
            "UVXY",
        }
    ]

    if ticker not in peers:
        peers.append(ticker)

    peers = sorted(set(str(symbol).upper().strip() for symbol in peers if symbol))

    try:
        sector_df = yf.download(
            sector_benchmark_symbol,
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        sector_df = _normalize_yf_columns(sector_df)
        sector_close_col = _find_yf_col(sector_df, "Close")

        if sector_df is None or sector_df.empty or sector_close_col is None:
            raise RuntimeError("Missing sector benchmark data")

        sector_df = sector_df.sort_index()
        sector_df["Sector_Close"] = pd.to_numeric(
            sector_df[sector_close_col],
            errors="coerce",
        )

        sector_df = sector_df[["Sector_Close"]].dropna()

    except Exception as exc:
        return {
            "sector": sector,
            "sector_benchmark": sector_benchmark_symbol,
            "target_symbol": ticker,
            "target_rank": None,
            "total_symbols": len(peers),
            "percentile": None,
            "leader_symbol": None,
            "rows": [],
            "status": f"BENCHMARK_ERROR: {exc}",
        }

    rows = []

    for symbol in peers:
        try:
            df = yf.download(
                symbol,
                period="6mo",
                interval="1d",
                progress=False,
                auto_adjust=False,
                threads=False,
            )

            if df is None or df.empty:
                continue

            df = _normalize_yf_columns(df)
            close_col = _find_yf_col(df, "Close")

            if close_col is None:
                continue

            frame = pd.DataFrame(index=df.index)
            frame["Close"] = pd.to_numeric(
                df[close_col],
                errors="coerce",
            )

            frame = frame.join(sector_df, how="inner")
            frame = frame.dropna(subset=["Close", "Sector_Close"])

            if len(frame) < 30:
                continue

            frame["RS_SECTOR"] = frame["Close"] / frame["Sector_Close"]
            frame["RS_SECTOR_MA20"] = frame["RS_SECTOR"].rolling(20).mean()
            frame["RS_SECTOR_SCORE"] = frame["RS_SECTOR"] / frame["RS_SECTOR_MA20"]
            frame["MA20"] = frame["Close"].rolling(20).mean()
            frame["MA50"] = frame["Close"].rolling(50).mean()

            close_now = float(frame["Close"].iloc[-1])
            close_20 = float(frame["Close"].iloc[-21]) if len(frame) > 21 else close_now
            close_60 = float(frame["Close"].iloc[-61]) if len(frame) > 61 else float(frame["Close"].iloc[0])

            rs_score = float(frame["RS_SECTOR_SCORE"].iloc[-1])
            ma20 = float(frame["MA20"].iloc[-1])
            ma50 = float(frame["MA50"].iloc[-1])

            return_20d = (close_now / close_20 - 1.0) * 100.0 if close_20 else 0.0
            return_60d = (close_now / close_60 - 1.0) * 100.0 if close_60 else 0.0

            trend_score = 0

            if close_now > ma20:
                trend_score += 1
            if close_now > ma50:
                trend_score += 1
            if rs_score >= 1.05:
                trend_score += 1

            rows.append({
                "rank": None,
                "symbol": symbol,
                "sector": sector,
                "sector_benchmark": sector_benchmark_symbol,
                "last_price": round(close_now, 2),
                "rs_vs_sector": round(rs_score, 4),
                "rs_label": relative_strength_label(rs_score),
                "return_20d_pct": round(return_20d, 2),
                "return_60d_pct": round(return_60d, 2),
                "trend_score": trend_score,
                "leadership_score": round(
                    (rs_score * 100.0)
                    + (return_20d * 0.20)
                    + (return_60d * 0.10)
                    + (trend_score * 2.0),
                    4,
                ),
            })

        except Exception:
            continue

    rows = sorted(
        rows,
        key=lambda row: row.get("leadership_score", 0),
        reverse=True,
    )

    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    target_row = next(
        (row for row in rows if row.get("symbol") == ticker),
        None,
    )

    total = len(rows)
    target_rank = target_row.get("rank") if target_row else None

    percentile = None

    if target_rank is not None and total > 0:
        percentile = round(((total - target_rank + 1) / total) * 100.0, 1)

    leader_symbol = rows[0].get("symbol") if rows else None

    return {
        "sector": sector,
        "sector_benchmark": sector_benchmark_symbol,
        "target_symbol": ticker,
        "target_rank": target_rank,
        "target_row": target_row,
        "total_symbols": total,
        "percentile": percentile,
        "leader_symbol": leader_symbol,
        "rows": rows,
        "status": "OK" if rows else "NO_VALID_ROWS",
    }


def sector_leadership_label(percentile) -> str:
    try:
        value = float(percentile)
    except Exception:
        return "UNKNOWN"

    if value >= 90:
        return "ELITE"
    if value >= 75:
        return "LEADER"
    if value >= 50:
        return "STRONG"
    if value >= 25:
        return "AVERAGE"
    return "WEAK"


def sector_leadership_badge(label: str) -> str:
    label = str(label or "UNKNOWN").upper().strip()

    badges = {
        "ELITE": "🟢 ELITE",
        "LEADER": "🟢 LEADER",
        "STRONG": "🟡 STRONG",
        "AVERAGE": "🟠 AVERAGE",
        "WEAK": "🔴 WEAK",
        "UNKNOWN": "⚪ UNKNOWN",
    }

    return badges.get(label, label)


# =========================================================
# EVENT RISK HELPERS
# =========================================================

@st.cache_data(ttl=3600)
def research_earnings_context(symbol: str):
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
            earnings_date = earnings_date.isoformat()

        return {
            "symbol": symbol,
            "earnings_date": (
                "Not Applicable (ETF)"
                if str(row.get("status") or "").upper().strip() == "NOT_APPLICABLE_ETF"
                else earnings_date
            ),
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


def research_economic_context():
    if analyze_economic_calendar is None or sample_events is None:
        return {
            "risk_score": 0,
            "risk_label": "NONE",
            "highest_event": "None",
            "hours_until": None,
            "source": "UNAVAILABLE",
        }

    try:
        result = analyze_economic_calendar(sample_events())
        highest = result.get("highest_risk_event")

        highest_name = "None"
        hours = None
        source = "SAMPLE"

        if isinstance(highest, dict):
            highest_name = str(highest.get("name") or "None")
            hours = highest.get("hours_until")
            source = str(highest.get("source") or source).upper()

        return {
            "risk_score": int(float(result.get("economic_risk_score") or 0)),
            "risk_label": str(result.get("economic_risk_label") or "NONE").upper().strip(),
            "highest_event": highest_name,
            "hours_until": hours,
            "source": source,
        }

    except Exception as exc:
        return {
            "risk_score": 0,
            "risk_label": "NONE",
            "highest_event": "None",
            "hours_until": None,
            "source": f"ERROR: {exc}",
        }


def research_market_reaction_context():
    score = st.session_state.get(
        "market_reaction_score",
        st.session_state.get("reaction_score", 0),
    )

    confidence = st.session_state.get(
        "market_reaction_confidence",
        st.session_state.get("risk_confidence", 0),
    )

    event = st.session_state.get(
        "market_reaction_event",
        st.session_state.get("market_event", ""),
    )

    playbook = st.session_state.get(
        "market_reaction_playbook",
        st.session_state.get("playbook", ""),
    )

    try:
        score = float(score or 0)
    except Exception:
        score = 0.0

    try:
        confidence = float(confidence or 0)
    except Exception:
        confidence = 0.0

    combined = f"{event} {playbook}".upper()

    risk_off_terms = [
        "RISK OFF",
        "RISK-OFF",
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

    risk_off = any(term in combined for term in risk_off_terms)
    risk_on = any(term in combined for term in risk_on_terms)

    if not risk_off and score >= 85 and confidence >= 70:
        risk_off = True

    if risk_off:
        regime = "RISK_OFF"
    elif risk_on:
        regime = "RISK_ON"
    else:
        regime = "NEUTRAL"

    return {
        "regime": regime,
        "score": score,
        "confidence": confidence,
        "event": event or "None",
        "playbook": playbook or "None",
    }


def event_risk_label(score: int) -> str:
    if score >= 80:
        return "EXTREME"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "NONE"


def event_risk_badge(label: str) -> str:
    label = str(label or "NONE").upper().strip()

    badges = {
        "EXTREME": "🔴 EXTREME",
        "HIGH": "🟠 HIGH",
        "MEDIUM": "🟡 MEDIUM",
        "LOW": "🟢 LOW",
        "NONE": "🟢 NONE",
        "DEMO": "🔵 DEMO",
    }

    return badges.get(label, label)


def safe_int(value, default=None):
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def combined_research_event_context(
    signal: str,
    earnings_ctx: dict,
    economic_ctx: dict,
    market_ctx: dict,
    model_score: int = 0,
    trend: str = "UNKNOWN",
    rs_score: float = 0.0,
):
    earnings_score = int(float(earnings_ctx.get("risk_score") or 0))
    economic_score = int(float(economic_ctx.get("risk_score") or 0))
    market_score = int(float(market_ctx.get("score") or 0))

    market_component = 0

    if market_ctx.get("regime") == "RISK_OFF":
        market_component = min(40, market_score)
    elif market_ctx.get("regime") == "RISK_ON":
        market_component = 0
    else:
        market_component = min(20, market_score)

    combined_score = min(
        100,
        int(
            max(earnings_score, economic_score)
            + market_component * 0.5
        ),
    )

    combined_label = event_risk_label(combined_score)

    days_until_int = safe_int(
        earnings_ctx.get("days_until"),
        None,
    )

    signal = str(signal or "NO TRADE").upper().strip()
    trend = str(trend or "UNKNOWN").upper().strip()

    reasons = []

    if days_until_int is not None:
        if days_until_int <= 3:
            reasons.append(
                f"Earnings are in {days_until_int} day(s), creating elevated gap risk."
            )
        elif days_until_int <= 7:
            reasons.append(
                f"Earnings are in {days_until_int} day(s), so position sizing should be conservative."
            )

    if economic_ctx.get("risk_label") not in ("NONE", "LOW", "DEMO"):
        reasons.append(
            f"Economic calendar risk is {economic_ctx.get('risk_label')}."
        )

    if market_ctx.get("regime") == "RISK_OFF":
        reasons.append("Market reaction context is Risk-Off.")
    elif market_ctx.get("regime") == "RISK_ON":
        reasons.append("Market reaction context is Risk-On.")

    reasons.append(
        f"Research Score is {model_score}/5 with a {trend} trend."
    )

    if signal == "BUY" and days_until_int is not None and days_until_int <= 3:
        decision = "WAIT — EARNINGS IMMINENT"
        guidance = "Avoid initiating a new BUY until after earnings are released."
        severity = "WARNING"
    elif signal == "BUY" and days_until_int is not None and days_until_int <= 7:
        decision = "BUY SETUP — REDUCE SIZE"
        guidance = "A BUY setup exists, but use reduced size or wait for earnings confirmation."
        severity = "WARNING"
    elif signal == "BUY" and market_ctx.get("regime") == "RISK_OFF":
        decision = "WAIT — MARKET RISK OFF"
        guidance = "Avoid new long entries while market reaction context is Risk-Off."
        severity = "WARNING"
    elif signal == "BUY" and combined_score >= 60:
        decision = "BUY SETUP — EVENT RISK HIGH"
        guidance = "Technical setup is positive, but event risk is elevated. Consider waiting or reducing size."
        severity = "WARNING"
    elif signal == "BUY":
        decision = "BUY SETUP — EVENT RISK ACCEPTABLE"
        guidance = "Normal research conditions. A new BUY can be considered if portfolio and risk rules allow it."
        severity = "SUCCESS"
    elif signal == "SELL":
        decision = "SELL / RISK REDUCTION SETUP"
        guidance = (
    "Research model generated a SELL signal. "
    "Event risk does not block risk reduction."
)
        severity = "ERROR"
    else:
        decision = "NO TRADE"
        guidance = "No actionable BUY or SELL from the research model. Monitor only."
        severity = "INFO"

    summary = (
        f"{signal}. {guidance} "
        f"Combined event risk is {combined_label}."
    )

    return {
        "combined_score": combined_score,
        "combined_label": combined_label,
        "combined_badge": event_risk_badge(combined_label),
        "decision": decision,
        "guidance": guidance,
        "severity": severity,
        "reasons": reasons,
        "summary": summary,
    }


def open_trade_command_from_research(symbol: str) -> None:
    """Deterministic handoff from Research Stock to Trade Command Center."""

    symbol = str(symbol or "").upper().strip()

    if not symbol:
        st.warning("Enter a symbol before opening Trade Command Center.")
        return

    st.session_state["selected_symbol"] = symbol
    st.session_state["trade_command_symbol"] = symbol
    st.session_state["tcc_symbol"] = symbol
    st.session_state["jfbp_main_navigation"] = "Trade Command Center"

    remember_active_page("Trade Command Center")

    st.rerun()


def run_page():

    inject_responsive_css()
    inject_card_css()

    st.title("Research Stock")

    # =====================================================
    # RESPONSIVE UI LAYER (v89)
    # Browser-safe and mobile-friendly layout controls.
    # =====================================================

    st.markdown(
        """
<style>
/* General text safety across Chrome, Safari, Firefox, and mobile. */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    overflow-wrap: break-word !important;
    word-break: normal !important;
}

/* Keep Streamlit blocks from forcing horizontal overflow. */
div[data-testid="stHorizontalBlock"] {
    gap: 1.15rem !important;
}

/* Compact metric sizing for Research Stock. */
[data-testid="stMetricValue"] {
    font-size: 1.55rem !important;
    line-height: 1.2 !important;
    white-space: normal !important;
    overflow-wrap: break-word !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.85rem !important;
    white-space: normal !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
    white-space: normal !important;
}

/* Markdown and alert cards should wrap naturally. */
.stMarkdown, .stCaption, .stAlert, .stInfo, .stWarning, .stError, .stSuccess {
    overflow-wrap: break-word !important;
    word-break: normal !important;
}

/* Tables should scroll instead of breaking the layout. */
[data-testid="stDataFrame"] {
    overflow-x: auto !important;
}

/* Section headers: strong on desktop, controlled on narrow screens. */
h1 {
    line-height: 1.15 !important;
}

h2 {
    line-height: 1.20 !important;
}

/* Tablet and phone behavior: stack columns vertically. */
@media (max-width: 900px) {
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }

    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
    }

    h1 {
        font-size: 2.0rem !important;
    }

    h2 {
        font-size: 1.55rem !important;
    }

    h3 {
        font-size: 1.20rem !important;
    }
}

.research-flow {background:#eff6ff;border:1px solid #bfdbfe;border-radius:14px;padding:0.9rem 1rem;margin:0.75rem 0 0.85rem 0;color:#1e3a8a;line-height:1.45;}
.research-exec-card {background:#ffffff;border:1px solid #e5eaf3;border-radius:18px;padding:1rem 1.05rem;margin:0.75rem 0 1rem 0;box-shadow:0 1px 2px rgba(15,23,42,.04);}
.research-exec-title {font-size:1.08rem;font-weight:900;color:#1f2937;margin-bottom:.45rem;}
.research-exec-text {font-size:.94rem;line-height:1.5;color:#334155;}
.institutional-chapter {font-size:1.22rem;font-weight:900;letter-spacing:.01em;color:#0f172a;margin:1.35rem 0 .55rem 0;padding-top:.15rem;}
.pf-decision-card {background:#ffffff;border:1px solid #d6dce8;border-radius:18px;padding:.95rem .85rem;margin:.55rem 0 .85rem 0;box-shadow:0 1px 1px rgba(15,23,42,.03);}
.opportunity-scorecard,
.opportunity-scorecard * {word-break:normal !important;overflow-wrap:normal !important;hyphens:none !important;}
.scorecard-row {display:flex;align-items:stretch;}
.scorecard-cell {flex:1 1 0;padding:.3rem .55rem;min-width:0;display:flex;flex-direction:column;justify-content:center;}
.scorecard-divider {border-left:1px solid #d9dee8;}
.scorecard-heading {font-size:.9rem;line-height:1.25;font-weight:800;color:#1f2937;margin-bottom:.3rem;}
.scorecard-role-value {font-size:1.45rem;line-height:1.25;font-weight:800;display:flex;align-items:center;justify-content:center;text-align:center;width:100%;margin:.15rem 0;}
.scorecard-allocation-value {font-size:1.55rem;line-height:1.25;font-weight:800;text-align:center;margin:.15rem 0;}
.scorecard-review-value {font-size:1.15rem;line-height:1.25;font-weight:800;color:#2563eb;margin:.2rem 0;}
.scorecard-description {font-size:.9rem;line-height:1.4;color:#667085;}
.pf-role-value-bad {color:#dc2626;}
.pf-role-value-good {color:#0f9f6e;}
.pf-interpretation {background:#eff6ff;border:1px solid #bfdbfe;border-radius:14px;padding:.75rem .95rem;color:#1d4ed8;line-height:1.45;margin:0 0 .8rem 0;}

/* Small phones: reduce title and metric pressure further. */
@media (max-width: 520px) {
    [data-testid="stMetricValue"] {
        font-size: 1.20rem !important;
    }

    [data-testid="stMetricDelta"],
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
    }

    h1 {
        font-size: 1.70rem !important;
    }

    h2 {
        font-size: 1.35rem !important;
    }

    h3 {
        font-size: 1.10rem !important;
    }
}
</style>
""",
        unsafe_allow_html=True,
    )

    st.subheader("Institutional Security Analysis")
    st.caption(
        "Analyze a company the same way a professional portfolio manager would, from market regime to technicals, quality, risk, and final allocation decision."
    )

    st.markdown(
        """
        <div class="research-flow">
            <strong>Workflow:</strong><br>
            Scanner → Research Stock → Trade Command Center → OMS Execution → Position Command Center → Journal
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📖 How to Use Research Stock", expanded=False):
        st.markdown(
            """
            **1. Analyze a symbol**  
            Enter a ticker and click **Analyze**.

            **2. Read the Executive Summary**  
            Focus first on setup status, research score, relative strength, event risk, and trade bias.

            **3. Review the intelligence layer**  
            Confirm the Institutional Research Brief, Technical Analysis, Portfolio Fit recommendation, and Institutional Review.

            **4. Decide the next step**  
            BUY candidates move to **Trade Command Center**. WATCH candidates stay under review. SELL / AVOID means no new long action.

            **5. Complete the workflow**  
            Research Stock → Trade Command Center → OMS Execution → Position Command Center → Journal.
            """
        )

    ticker = st.text_input(
        "Enter Ticker",
        value=st.session_state.get("research_ticker", "ORCL"),
        key="research_ticker_input",
    ).upper()

    st.session_state["research_ticker"] = ticker

    profile = JFBP_UNIVERSE.get(ticker, {})

    colA, colB, colC, colD = responsive_columns(4)

    with colA:
        analyze = st.button(
            "Analyze",
            width="stretch",
            key="research_analyze_btn",
        )

    with colB:
        refresh = st.button(
            "Refresh + Clear Cache",
            width="stretch",
            key="research_refresh_btn",
        )

    with colC:
        clear = st.button(
            "Clear",
            width="stretch",
            key="research_clear_btn",
        )

    with colD:
        open_trade_command = st.button(
            "Open Trade Command Center",
            width="stretch",
            key="research_open_trade_command_btn",
        )

    if refresh:
        st.cache_data.clear()
        st.session_state["research_last_analyze"] = True
        st.rerun()

    if clear:
        st.session_state["research_ticker"] = "ORCL"
        st.session_state["research_last_analyze"] = False
        st.cache_data.clear()
        st.rerun()

    if open_trade_command:
        open_trade_command_from_research(ticker)

    if analyze:
        st.session_state["research_last_analyze"] = True

    if not st.session_state.get("research_last_analyze", False):
        st.info("Enter ticker and click Analyze")
        return

    @st.cache_data(ttl=300)
    def load_data(symbol):
        return yf.download(
            symbol,
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )

    @st.cache_data(ttl=300)
    def load_range_data(symbol):
        return yf.download(
            symbol,
            period="1y",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )

    @st.cache_data(ttl=300)
    def load_benchmark(symbol):
        return yf.download(
            symbol,
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )

    @st.cache_data(ttl=3600)
    def load_company_profile(symbol):
        symbol = str(symbol or "").upper().strip()

        result = {
            "name": symbol,
            "sector": "N/A",
            "industry": "N/A",
        }

        try:
            info = yf.Ticker(symbol).info or {}

            result["name"] = str(
                info.get("shortName")
                or info.get("longName")
                or symbol
            )

            result["sector"] = str(
                info.get("sector")
                or "N/A"
            )

            result["industry"] = str(
                info.get("industry")
                or "N/A"
            )

        except Exception:
            pass

        return result

    def clean_display_value(value, default="N/A"):
        value = str(value or "").strip()
        return value if value else default

    def signed_pct(value):
        try:
            return f"{float(value):+.2f}%"
        except Exception:
            return "N/A"

    def signed_price_delta(value, pct):
        try:
            return f"{float(value):+.2f} ({float(pct):+.2f}%)"
        except Exception:
            return "N/A"

    def format_earnings_label(earnings_ctx):
        earnings_date = earnings_ctx.get("earnings_date")
        days_until = safe_int(
            earnings_ctx.get("days_until"),
            None,
        )

        date_label = "Unknown"

        if earnings_date:
            try:
                date_label = pd.to_datetime(
                    earnings_date
                ).strftime("%b %d, %Y")
            except Exception:
                date_label = str(earnings_date)

        if days_until is None:
            return date_label

        return date_label

    sector_benchmark = sector_benchmark_for_profile(
        ticker,
        profile,
    )

    sector_benchmark_symbol = sector_benchmark.get(
        "symbol",
        "SPY",
    )

    sector_benchmark_label = sector_benchmark.get(
        "label",
        "Broad Market",
    )

    df = load_data(ticker)
    range_df = load_range_data(ticker)
    benchmark = load_benchmark("SPY")
    sector_df = load_benchmark(sector_benchmark_symbol)
    company_profile = load_company_profile(ticker)
    earnings_ctx = research_earnings_context(ticker)

    if df is None or df.empty:
        st.error("No stock data found.")
        return

    if benchmark is None or benchmark.empty:
        st.error("No benchmark data found.")
        return

    if sector_df is None or sector_df.empty:
        sector_df = benchmark.copy()
        sector_benchmark_symbol = "SPY"
        sector_benchmark_label = "Broad Market Fallback"

    def normalize_columns(frame):
        frame = frame.copy()

        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = [
                "_".join([str(i) for i in col if i])
                for col in frame.columns
            ]

        frame.index = pd.to_datetime(
            frame.index,
            errors="coerce",
        )

        try:
            frame.index = frame.index.tz_localize(None)
        except Exception:
            pass

        frame = frame[~frame.index.isna()]
        frame = frame.sort_index()

        return frame

    df = normalize_columns(df)
    benchmark = normalize_columns(benchmark)
    sector_df = normalize_columns(sector_df)

    if range_df is not None and not range_df.empty:
        range_df = normalize_columns(range_df)

    def find_col(frame, name):
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

    close_col = find_col(df, "Close")
    high_col = find_col(df, "High")
    low_col = find_col(df, "Low")
    open_col = find_col(df, "Open")
    volume_col = find_col(df, "Volume")
    bench_close_col = find_col(benchmark, "Close")
    sector_close_col = find_col(sector_df, "Close")

    if close_col is None or bench_close_col is None:
        st.error("Missing required Close column.")
        return

    df_clean = pd.DataFrame(index=df.index)

    df_clean["Open"] = pd.to_numeric(
        df[open_col] if open_col else df[close_col],
        errors="coerce",
    )

    df_clean["High"] = pd.to_numeric(
        df[high_col] if high_col else df[close_col],
        errors="coerce",
    )

    df_clean["Low"] = pd.to_numeric(
        df[low_col] if low_col else df[close_col],
        errors="coerce",
    )

    df_clean["Close"] = pd.to_numeric(
        df[close_col],
        errors="coerce",
    )

    if volume_col:
        df_clean["Volume"] = pd.to_numeric(
            df[volume_col],
            errors="coerce",
        )
    else:
        df_clean["Volume"] = 0.0

    benchmark_clean = pd.DataFrame(index=benchmark.index)
    benchmark_clean["Benchmark"] = pd.to_numeric(
        benchmark[bench_close_col],
        errors="coerce",
    )

    sector_clean = pd.DataFrame(index=sector_df.index)

    if sector_close_col is None:
        sector_clean["Sector_Benchmark"] = benchmark_clean[
            "Benchmark"
        ]
    else:
        sector_clean["Sector_Benchmark"] = pd.to_numeric(
            sector_df[sector_close_col],
            errors="coerce",
        )

    # Safer alignment: keep the stock's own dates as the base.
    # This prevents SPY/sector ETF date mismatches from shrinking
    # the stock dataframe and causing false "not enough data" warnings.
    df = df_clean.join(
        benchmark_clean,
        how="left",
    )

    df = df.join(
        sector_clean,
        how="left",
    )

    df["Benchmark"] = df["Benchmark"].ffill().bfill()
    df["Sector_Benchmark"] = df["Sector_Benchmark"].ffill().bfill()

    df = df.dropna(
        subset=[
            "Open",
            "High",
            "Low",
            "Close",
            "Benchmark",
            "Sector_Benchmark",
        ]
    )

    if len(df) < 60:
        st.warning(
            f"Not enough historical data after alignment. "
            f"Rows available: {len(df)}"
        )
        return

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    df["RS"] = df["Close"] / df["Benchmark"]
    df["RS_MA20"] = df["RS"].rolling(20).mean()
    df["RS_SCORE"] = df["RS"] / df["RS_MA20"]

    df["RS_SECTOR"] = df["Close"] / df["Sector_Benchmark"]
    df["RS_SECTOR_MA20"] = df["RS_SECTOR"].rolling(20).mean()
    df["RS_SECTOR_SCORE"] = (
        df["RS_SECTOR"] / df["RS_SECTOR_MA20"]
    )

    df["AVG_VOLUME_20D"] = df["Volume"].rolling(20).mean()

    prev_close = df["Close"].shift(1)

    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - prev_close).abs()
    tr3 = (df["Low"] - prev_close).abs()

    df["TR"] = pd.concat(
        [
            tr1,
            tr2,
            tr3,
        ],
        axis=1,
    ).max(axis=1)

    df["ATR"] = df["TR"].rolling(14).mean()

    df["20D_HIGH"] = df["High"].rolling(20).max()
    df["20D_LOW"] = df["Low"].rolling(20).min()

    df = df.dropna()

    if df.empty:
        st.warning("Not enough clean indicator data.")
        return

    latest_close = round(float(df["Close"].iloc[-1]), 2)
    previous_close = round(float(df["Close"].iloc[-2]), 2)

    latest_ma20 = round(float(df["MA20"].iloc[-1]), 2)
    latest_ma50 = round(float(df["MA50"].iloc[-1]), 2)

    latest_rs_score = round(float(df["RS_SCORE"].iloc[-1]), 4)

    latest_sector_rs_score = round(
        float(df["RS_SECTOR_SCORE"].iloc[-1]),
        4,
    )

    latest_atr = round(float(df["ATR"].iloc[-1]), 4)
    avg_volume_20d = float(df["AVG_VOLUME_20D"].iloc[-1] or 0.0)

    latest_20d_high = round(float(df["20D_HIGH"].iloc[-1]), 2)
    latest_20d_low = round(float(df["20D_LOW"].iloc[-1]), 2)

    support = latest_20d_low
    resistance = latest_20d_high

    daily_change = round(latest_close - previous_close, 2)

    if previous_close:
        daily_change_pct = round(
            ((latest_close - previous_close) / previous_close) * 100,
            2,
        )
    else:
        daily_change_pct = 0.0

    atr_pct = (
        latest_atr / latest_close
        if latest_close
        else 0.0
    )

    liquidity_pass = avg_volume_20d >= 1_000_000
    volatility_pass = atr_pct <= 0.08

    ma_structure_pass = (
        latest_close > latest_ma20
        and latest_ma20 > latest_ma50
    )

    low_52w = None
    high_52w = None
    range_position = 0.0

    try:
        if range_df is not None and not range_df.empty:
            range_high_col = find_col(range_df, "High")
            range_low_col = find_col(range_df, "Low")

            if range_high_col and range_low_col:
                range_high_series = pd.to_numeric(
                    range_df[range_high_col],
                    errors="coerce",
                )

                range_low_series = pd.to_numeric(
                    range_df[range_low_col],
                    errors="coerce",
                )

                high_52w = round(float(range_high_series.max()), 2)
                low_52w = round(float(range_low_series.min()), 2)

                if high_52w > low_52w:
                    range_position = (
                        (latest_close - low_52w)
                        / (high_52w - low_52w)
                    )

                    range_position = max(
                        0.0,
                        min(1.0, float(range_position)),
                    )

    except Exception:
        low_52w = None
        high_52w = None
        range_position = 0.0

    range_position_pass = range_position >= 0.70

    above_ma20 = latest_close > latest_ma20
    above_ma50 = latest_close > latest_ma50
    improving_today = latest_close > previous_close
    strong_rs = latest_rs_score >= 1.05
    near_high = latest_close >= latest_20d_high * 0.98

    weak_rs = latest_rs_score <= 0.97

    market_rs_label = relative_strength_label(
        latest_rs_score
    )

    sector_rs_label = relative_strength_label(
        latest_sector_rs_score
    )

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

    if above_ma20 and above_ma50:
        market_bias = "BULLISH"
    elif below_ma20 and below_ma50:
        market_bias = "BEARISH"
    else:
        market_bias = "NEUTRAL"

    trend = market_bias

    if trend == "BULLISH":
        trend_text = (
            f"{ticker} remains in a constructive bullish trend."
        )
    elif trend == "BEARISH":
        trend_text = (
            f"{ticker} remains under bearish pressure."
        )
    else:
        trend_text = (
            f"{ticker} remains in a neutral technical zone."
        )

    if latest_rs_score >= 1.05:
        momentum_text = "Relative strength is strong versus SPY."
    elif latest_rs_score <= 0.97:
        momentum_text = "Relative strength is weak versus SPY."
    else:
        momentum_text = (
            "Relative strength versus SPY remains neutral to constructive."
        )

    commentary = (
        f"{trend_text} "
        f"{momentum_text} "
        f"Key support is near \\${support:.2f}. "
        f"Resistance is located near \\${resistance:.2f}."
    )

    # =====================================================
    # STOCK IDENTITY + TRADER SNAPSHOT HEADER (v93 DECISION-FIRST)
    # =====================================================

    company_name = clean_display_value(
        company_profile.get("name"),
        ticker,
    )

    profile_sector = clean_display_value(
        profile.get("sector")
        or company_profile.get("sector"),
        "N/A",
    )

    profile_industry = clean_display_value(
        profile.get("industry")
        or company_profile.get("industry"),
        "N/A",
    )

    profile_regime = profile.get("regime", [])

    if isinstance(profile_regime, list):
        profile_regime = ", ".join(profile_regime)

    profile_regime = clean_display_value(
        profile_regime,
        "N/A",
    )

    def clean_event_date_only(value, default="Unknown"):
        if not value:
            return default

        value_text = str(value).strip()

        try:
            dt = pd.to_datetime(
                value_text,
                errors="coerce",
                utc=True,
            )

            if pd.notna(dt):
                return dt.strftime("%b %d").replace(" 0", " ")

        except Exception:
            pass

        if "T" in value_text:
            date_part = value_text.split("T")[0]

            try:
                dt = pd.to_datetime(
                    date_part,
                    errors="coerce",
                )

                if pd.notna(dt):
                    return dt.strftime("%b %d").replace(" 0", " ")

            except Exception:
                pass

            return date_part

        return value_text

    def normalize_event_time_label(value):
        if not value:
            return None

        value_text = str(value).strip()
        value_key = value_text.lower().replace("_", " ").replace("-", " ")

        if "T" in value_text or value_text[:4].isdigit():
            return None

        if value_key in (
            "bmo",
            "before market open",
            "before open",
            "pre market",
            "premarket",
            "am",
        ):
            return "8:30 AM ET"

        if value_key in (
            "amc",
            "after market close",
            "after close",
            "post market",
            "postmarket",
            "pm",
        ):
            return "4:05 PM ET"

        return value_text

    header_economic_ctx = research_economic_context()
    header_market_ctx = research_market_reaction_context()

    header_event_ctx = combined_research_event_context(
        signal=signal,
        earnings_ctx=earnings_ctx,
        economic_ctx=header_economic_ctx,
        market_ctx=header_market_ctx,
        model_score=model_score,
        trend=trend,
        rs_score=latest_rs_score,
    )

    header_economic_label = str(
        header_economic_ctx.get("risk_label", "NONE") or "NONE"
    ).upper().strip()

    header_combined_label = str(
        header_event_ctx.get("combined_label", "NONE") or "NONE"
    ).upper().strip()

    highest_event_label = str(
        header_economic_ctx.get("highest_event", "None") or "None"
    ).strip()

    highest_event_upper = highest_event_label.upper()

    economic_date_raw = (
        header_economic_ctx.get("event_date")
        or header_economic_ctx.get("highest_event_date")
        or header_economic_ctx.get("date")
        or header_economic_ctx.get("event_datetime")
        or header_economic_ctx.get("datetime")
        or header_economic_ctx.get("release_date")
    )

    economic_time_raw = (
        header_economic_ctx.get("event_time")
        or header_economic_ctx.get("time_label")
        or header_economic_ctx.get("release_time")
        or header_economic_ctx.get("time")
    )

    if not economic_date_raw and economic_time_raw:
        economic_time_text = str(economic_time_raw).strip()

        if "T" in economic_time_text or economic_time_text[:4].isdigit():
            economic_date_raw = economic_time_raw

    economic_clean_date = clean_event_date_only(
        economic_date_raw,
        default=None,
    )

    economic_clean_time = normalize_event_time_label(
        economic_time_raw
    )

    if highest_event_upper in (
        "CPI",
        "PPI",
        "NFP",
    ):
        economic_clean_time = "8:30 AM ET"

    elif "FOMC" in highest_event_upper:
        economic_clean_time = "2:00 PM ET"

    if economic_clean_date and economic_clean_time:
        economic_date_label = (
            f"{economic_clean_date} • {economic_clean_time}"
        )
    elif economic_clean_date:
        economic_date_label = economic_clean_date
    elif economic_clean_time:
        economic_date_label = economic_clean_time
    else:
        economic_date_label = "Time Unknown"

    try:
        spy_current = float(benchmark["Benchmark"].iloc[-1])
        spy_previous = float(benchmark["Benchmark"].iloc[-2])

        spy_daily_change_pct = (
            ((spy_current - spy_previous) / spy_previous) * 100
            if spy_previous
            else 0.0
        )

    except Exception:
        spy_daily_change_pct = 0.0

    relative_day_strength = daily_change_pct - spy_daily_change_pct

    display_signal = signal

    if signal == "NO TRADE":
        display_signal = "WATCH"

    research_score_pct = int(
        round((model_score / 5) * 100)
    )

    if model_score >= 5:
        research_score_label = "ELITE"
    elif model_score >= 4:
        research_score_label = "STRONG"
    elif model_score >= 3:
        research_score_label = "NEUTRAL"
    elif model_score >= 2:
        research_score_label = "CAUTION"
    elif model_score >= 1:
        research_score_label = "DEVELOPING"
    else:
        research_score_label = "AVOID"

    st.subheader(f"{ticker} — {company_name}")

    st.caption(
        f"{profile_sector} • "
        f"{profile_industry} • "
        f"{profile_regime} • "
        f"Benchmark: {sector_benchmark_symbol}"
    )

    top_row = responsive_columns(5)

    with top_row[0]:
        st.metric(
            "Last Price",
            f"${latest_close:.2f}",
            f"{daily_change_pct:+.2f}%",
        )

    with top_row[1]:
        st.metric(
            "Research Score",
            f"{research_score_pct}%",
            research_score_label,
            delta_color="off",
        )

    with top_row[2]:
        st.markdown("**Setup Status**")

        if display_signal == "STRONG BUY":
            st.markdown("#### 🟢 STRONG BUY")
        elif display_signal == "BUY":
            st.markdown("#### 🟢 BUY")
        elif display_signal == "WATCH":
            st.markdown("#### 🟡 WATCH")
        elif display_signal == "AVOID":
            st.markdown("#### 🔴 AVOID")
        elif display_signal == "SELL":
            st.markdown("#### 🔴 SELL")
        else:
            st.markdown(f"#### ⚪ {display_signal}")

    with top_row[3]:

        if market_rs_label == "STRONG":
            rs_display = "🟢 STRONG"

        elif market_rs_label == "WEAK":
            rs_display = "🔴 WEAK"

        else:
            rs_display = "🟡 NEUTRAL"

        st.metric(
            "Relative Strength",
            rs_display,
            f"RS {latest_rs_score:.2f}",
            delta_color="off",
        )
    
    with top_row[4]:
        st.metric(
            "Event Risk",
            header_combined_label,
        )

    st.caption("52-Week Range")
    st.caption("0% = near yearly low • 100% = near yearly high")

    if low_52w is not None and high_52w is not None:

        st.progress(range_position)

        range_cols = responsive_columns(3)

        with range_cols[0]:
            st.metric("52-Week Low", f"${low_52w:.2f}")

        with range_cols[1]:
            st.metric("Current", f"${latest_close:.2f}")

        with range_cols[2]:
            st.metric("52-Week High", f"${high_52w:.2f}")

    else:
        st.info("52-week range unavailable for this symbol.")

    earnings_days = earnings_ctx.get("days_until")
    earnings_date = earnings_ctx.get("earnings_date")

    earnings_time_raw = (
        earnings_ctx.get("earnings_time")
        or earnings_ctx.get("earnings_time_label")
        or earnings_ctx.get("report_time")
        or earnings_ctx.get("release_time")
        or earnings_ctx.get("time_label")
        or earnings_ctx.get("time")
        or earnings_ctx.get("when")
        or earnings_ctx.get("period")
    )

    earnings_time_label = normalize_event_time_label(
        earnings_time_raw
    )

    earnings_date_label = "Unknown"

    if str(earnings_ctx.get("status") or "").upper().strip() == "NOT_APPLICABLE_ETF":
        earnings_date_label = "Not Applicable (ETF)"

    elif earnings_date:
        earnings_date_label = clean_event_date_only(
            earnings_date
        )

    if not earnings_time_label:
        earnings_time_label = "Time Unknown"

    if str(earnings_ctx.get("status") or "").upper().strip() == "NOT_APPLICABLE_ETF":
        earnings_time_label = "N/A"

    earnings_ribbon_label = (
        f"Earnings: {earnings_date_label} • {earnings_time_label}"
    )

    if earnings_days is not None:
        try:
            earnings_days_int = int(float(earnings_days))
        except Exception:
            earnings_days_int = None

        if earnings_days_int == 0:
            earnings_ribbon_label += " • Today"
        elif earnings_days_int == 1:
            earnings_ribbon_label += " • Tomorrow"
        elif earnings_days_int is not None:
            earnings_ribbon_label += f" • {earnings_days_int} Days"

    economic_ribbon_label = (
        highest_event_label
        if highest_event_label
        and highest_event_upper != "NONE"
        else "Economic Event"
    )

    st.markdown(
        '<div class="institutional-chapter">Executive Research Verdict</div>',
        unsafe_allow_html=True,
    )
    st.subheader("🎯 Executive Summary")
    st.caption(
        "What it means: One compact research read before moving to Trade Command Center."
    )

    with st.container(border=True):
        summary_cols = responsive_columns(6)

        with summary_cols[0]:
            st.metric("Setup", display_signal)
        with summary_cols[1]:
            st.metric("Research", f"{research_score_pct}%", research_score_label, delta_color="off")
        with summary_cols[2]:
            st.metric("RS", market_rs_label, f"{latest_rs_score:.2f}", delta_color="off")
        with summary_cols[3]:
            st.metric("Event Risk", header_combined_label)
        with summary_cols[4]:
            st.metric("Earnings", earnings_date_label)
        with summary_cols[5]:
            st.metric("Trade Bias", trend)

        st.markdown("#### 📋 Quick Read")
        st.write(commentary)

        st.markdown("##### Event Risk Context")

    event_cols = responsive_columns(4)

    with event_cols[0]:
        st.info(
            f"**{earnings_ribbon_label}**  \n"
            f"{event_risk_badge(earnings_ctx.get('risk_label', 'NONE'))}"
        )

    with event_cols[1]:
        economic_header = (
            f"{economic_ribbon_label}: "
            f"{economic_date_label}"
        )

        st.info(
            f"**{economic_header}**  \n"
            f"{event_risk_badge(header_economic_label)}"
        )

    with event_cols[2]:
        st.info(
            f"**Combined Risk**  \n"
            f"{header_event_ctx.get('combined_badge', '🟢 NONE')}"
        )

    with event_cols[3]:
        st.info(
            f"**Market Regime**  \n"
            f"{header_market_ctx.get('regime', 'NEUTRAL')}"
        )
        
    # =====================================================
    # STOCK INTELLIGENCE BRIEF (v93 COMMAND CENTER RESPONSIVE)
    # Summary-first decision layer aligned with Scanner Intelligence.
    # =====================================================

    # These are calculated here so the Intelligence Brief can appear
    # before the chart and the detailed research sections.
    research_bias = research_bias_from_context(
        trend=trend,
        model_score=model_score,
        market_rs_label=market_rs_label,
        sector_rs_label=sector_rs_label,
    )

    sector_leadership_ctx = cached_sector_leadership_context(
        ticker=ticker,
        sector=str(
            profile.get("sector", "")
            or ""
        ),
        sector_benchmark_symbol=sector_benchmark_symbol,
    )

    sector_rank = sector_leadership_ctx.get(
        "target_rank"
    )

    sector_total = sector_leadership_ctx.get(
        "total_symbols"
    )

    sector_percentile = sector_leadership_ctx.get(
        "percentile"
    )

    sector_leadership_status = (
        sector_leadership_label(
            sector_percentile
        )
    )

    brief_combined_label = str(
        header_event_ctx.get("combined_label", "NONE") or "NONE"
    ).upper().strip()

    brief_market_regime = str(
        header_market_ctx.get("regime", "NEUTRAL") or "NEUTRAL"
    ).upper().strip()

    stock_confidence = 45
    stock_confidence += int((model_score / 5) * 25)

    if trend == "BULLISH":
        stock_confidence += 10
    elif trend == "BEARISH":
        stock_confidence -= 10

    if market_rs_label == "STRONG":
        stock_confidence += 10
    elif market_rs_label == "WEAK":
        stock_confidence -= 10

    if sector_rs_label == "STRONG":
        stock_confidence += 8
    elif sector_rs_label == "WEAK":
        stock_confidence -= 6

    if sector_leadership_status in ("ELITE", "LEADER"):
        stock_confidence += 10
    elif sector_leadership_status == "STRONG":
        stock_confidence += 5
    elif sector_leadership_status in ("WEAK", "UNKNOWN"):
        stock_confidence -= 6

    if brief_combined_label in ("HIGH", "EXTREME"):
        stock_confidence -= 18
    elif brief_combined_label in ("NONE", "LOW"):
        stock_confidence += 5

    if brief_market_regime == "RISK_ON":
        stock_confidence += 6
    elif brief_market_regime == "RISK_OFF":
        stock_confidence -= 15

    stock_confidence = max(
        0,
        min(100, int(stock_confidence)),
    )

    if stock_confidence >= 90:
        stock_confidence_label = "🟢 HIGH CONVICTION"
        stock_confidence_tone = "success"
    elif stock_confidence >= 75:
        stock_confidence_label = "🟢 FAVORABLE"
        stock_confidence_tone = "success"
    elif stock_confidence >= 60:
        stock_confidence_label = "🟡 SELECTIVE"
        stock_confidence_tone = "warning"
    elif stock_confidence >= 40:
        stock_confidence_label = "🟠 DEFENSIVE"
        stock_confidence_tone = "warning"
    else:
        stock_confidence_label = "🔴 AVOID / CAPITAL PRESERVATION"
        stock_confidence_tone = "error"

    brief_action_bias = display_signal

    if signal == "BUY" and brief_combined_label in ("HIGH", "EXTREME"):
        brief_action_bias = "WATCH"
    elif signal == "BUY" and brief_market_regime == "RISK_OFF":
        brief_action_bias = "WATCH"
    elif signal == "NO TRADE":
        brief_action_bias = "WATCH"

    leadership_rank_text = (
        f"{sector_rank}/{sector_total}"
        if sector_rank is not None and sector_total
        else "N/A"
    )

    st.divider()
    st.markdown(
        '<div class="institutional-chapter">Institutional Research Brief</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "What it means: A single institutional narrative for positioning, conviction, and risk framing."
    )

    brief_cols = responsive_columns(2)

    with brief_cols[0]:
        st.metric(
            "Overall Rating",
            research_score_label,
            f"Research {research_score_pct}%",
            delta_color="off",
        )
        st.metric(
            "Confidence",
            f"{stock_confidence}/100",
            stock_confidence_label,
            delta_color="off",
        )
        st.markdown("**Bull Case**")
        st.markdown(f"- Trend profile: {trend}.")
        st.markdown(f"- Relative strength versus SPY: {market_rs_label}.")
        st.markdown(f"- Sector leadership: {sector_leadership_status} ({leadership_rank_text}).")
        st.markdown("**Catalysts**")
        st.markdown(f"- Earnings window: {earnings_ribbon_label}.")
        st.markdown(f"- Highest macro event: {economic_ribbon_label} ({economic_date_label}).")

    with brief_cols[1]:
        st.markdown("**Bear Case**")
        st.markdown(f"- Combined event risk: {brief_combined_label}.")
        st.markdown(f"- Market regime: {brief_market_regime}.")
        st.markdown(f"- Sector-relative strength: {sector_rs_label}.")
        st.markdown("**Key Risks**")
        st.markdown(f"- Event-risk badge: {header_event_ctx.get('combined_badge', '🟢 NONE')}.")
        st.markdown(f"- Earnings risk label: {earnings_ctx.get('risk_label', 'NONE')}.")
        st.markdown("**Bottom Line**")
        st.info(
            f"{brief_action_bias} bias with {stock_confidence_label.lower()} conviction. "
            f"Current regime is {brief_market_regime}; event risk is {brief_combined_label}."
        )
        
    # =====================================================
    # BALANCED PRICE + LEVELS LAYOUT (v86 CLEAN LEVELS PANEL)
    # =====================================================

    chart_df = df[
        [
            "Close",
            "MA20",
            "MA50",
        ]
    ].copy()

    chart_left, chart_right = responsive_columns([2.3, 1.2])

    st.markdown(
        '<div class="institutional-chapter">Technical Analysis</div>',
        unsafe_allow_html=True,
    )

    with chart_left:

        st.subheader("Technical Snapshot")

        st.line_chart(
            chart_df,
            height=400,
            width="stretch",
        )

    with chart_right:

        st.subheader("Key Trading Levels")

        range_position_label = (
            f"{range_position * 100:.0f}%"
            if low_52w is not None
            and high_52w is not None
            else "N/A"
        )

    

        st.markdown(
            f"""
<div style="font-size:0.95rem; line-height:1.9;">

<div style="display:flex; justify-content:space-between;">
<span><strong>Support</strong></span>
<span>${support:.2f}</span>
</div>

<div style="display:flex; justify-content:space-between;">
<span><strong>Resistance</strong></span>
<span>${resistance:.2f}</span>
</div>

<div style="display:flex; justify-content:space-between;">
<span><strong>ATR</strong></span>
<span>{latest_atr:.2f}</span>
</div>

<div style="display:flex; justify-content:space-between;">
<span><strong>20-Day MA</strong></span>
<span>${latest_ma20:.2f}</span>
</div>

<div style="display:flex; justify-content:space-between;">
<span><strong>50-Day MA</strong></span>
<span>${latest_ma50:.2f}</span>
</div>

<div style="display:flex; justify-content:space-between;">
<span><strong>Position Within 52-Week Range</strong></span>
<span>{range_position_label}</span>
</div>

</div>
""",
            unsafe_allow_html=True,
        )

        st.caption(
            "Balanced technical view: price action on the left, "
            "key trading levels on the right."
        )

        st.caption(
            "52-week position: 0% = near the yearly low; "
            "100% = near the yearly high."
        )
        

    research_bias = research_bias_from_context(
        trend=trend,
        model_score=model_score,
        market_rs_label=market_rs_label,
        sector_rs_label=sector_rs_label,
    )

    sector_leadership_ctx = cached_sector_leadership_context(
        ticker=ticker,
        sector=str(
            profile.get("sector", "")
            or ""
        ),
        sector_benchmark_symbol=sector_benchmark_symbol,
    )

    sector_rank = sector_leadership_ctx.get(
        "target_rank"
    )

    sector_total = sector_leadership_ctx.get(
        "total_symbols"
    )

    sector_percentile = sector_leadership_ctx.get(
        "percentile"
    )

    sector_leadership_status = (
        sector_leadership_label(
            sector_percentile
        )
    )

    # =====================================================
    # RESEARCH DASHBOARD LAYOUT (v85 HEADER EVENT RISK CLEANUP)
    # =====================================================

    earnings_ctx = research_earnings_context(ticker)
    economic_ctx = research_economic_context()
    market_ctx = research_market_reaction_context()

    event_ctx = combined_research_event_context(
        signal=signal,
        earnings_ctx=earnings_ctx,
        economic_ctx=economic_ctx,
        market_ctx=market_ctx,
        model_score=model_score,
        trend=trend,
        rs_score=latest_rs_score,
    )

    combined_label = str(
        event_ctx.get("combined_label", "NONE") or "NONE"
    ).upper().strip()

    days_until = earnings_ctx.get("days_until")

    try:
        days_until_int = (
            int(float(days_until))
            if days_until is not None
            else None
        )
    except Exception:
        days_until_int = None

    event_risk_rows = [
        {
            "Factor": "Next Earnings",
            "Value": (
                "Not Applicable (ETF)"
                if str(earnings_ctx.get("status") or "").upper().strip() == "NOT_APPLICABLE_ETF"
                else earnings_ctx.get("earnings_date") or "None"
            ),
        },
        {
            "Factor": "Economic Risk",
            "Value": event_risk_badge(
                economic_ctx.get("risk_label", "NONE")
            ),
        },
        {
            "Factor": "Highest Economic Event",
            "Value": economic_ctx.get("highest_event", "None"),
        },
        {
            "Factor": "Market Regime",
            "Value": market_ctx.get("regime", "NEUTRAL"),
        },
    ]

    market_regime_for_recommendation = str(
        market_ctx.get("regime", "NEUTRAL") or "NEUTRAL"
    ).upper().strip()

    leadership_is_good = sector_leadership_status in (
        "ELITE",
        "LEADER",
        "STRONG",
    )

    event_risk_high = combined_label in (
        "HIGH",
        "EXTREME",
    )

    # =====================================================
    # RECOMMENDATION REASONS ENGINE (v87)
    # Dynamic explanation tied to the current recommendation.
    # =====================================================

    trade_reasons = []

    trade_reasons.append(
        f"Research Score: {model_score}/5."
    )

    trade_reasons.append(
        f"Trend: {trend}."
    )

    trade_reasons.append(
        f"RS vs SPY: {market_rs_label} ({latest_rs_score:.4f})."
    )

    trade_reasons.append(
        (
            f"RS vs {sector_benchmark_symbol}: "
            f"{sector_rs_label} ({latest_sector_rs_score:.4f})."
        )
    )

    if sector_rank is not None and sector_total:
        trade_reasons.append(
            (
                f"Sector Leadership: rank {sector_rank}/{sector_total} "
                f"({sector_leadership_status})."
            )
        )
    else:
        trade_reasons.append(
            "Sector Leadership: peer rank unavailable."
        )

    trade_reasons.append(
        f"Combined Event Risk: {combined_label}."
    )

    if days_until_int is not None:
        trade_reasons.append(
            f"Earnings timing: {days_until_int} day(s) until next earnings."
        )
    else:
        trade_reasons.append(
            "Earnings timing: no confirmed near-term earnings date."
        )

    trade_reasons.append(
        f"Market Regime: {market_regime_for_recommendation}."
    )

    trade_reasons.append(
        f"Research Bias: {research_bias}."
    )

    trade_recommendation = "WATCH"
    trade_guidance = "Monitor only until the setup becomes clearer."
    recommendation_severity = "INFO"

    if signal == "SELL":
        trade_recommendation = "SELL"
        trade_guidance = (
    "Research model generated a SELL signal. "
    "Risk-reduction actions are allowed "
    "even when event risk is elevated."
)
        recommendation_severity = "ERROR"

    elif signal == "BUY":

        if days_until_int is not None and days_until_int <= 3:
            trade_recommendation = "WATCH"
            trade_guidance = (
                "BUY setup exists, but earnings are imminent. "
                "Wait until after the earnings release before considering a new entry."
            )
            recommendation_severity = "WARNING"

        elif market_regime_for_recommendation == "RISK_OFF":
            trade_recommendation = "WATCH"
            trade_guidance = (
                "BUY setup exists, but market reaction context is Risk-Off. "
                "Wait for market conditions to stabilize."
            )
            recommendation_severity = "WARNING"

        elif event_risk_high:
            trade_recommendation = "WATCH"
            trade_guidance = (
                "BUY setup exists, but combined event risk is elevated. "
                "Wait or use reduced sizing."
            )
            recommendation_severity = "WARNING"

        elif (
            model_score >= 4
            and market_rs_label == "STRONG"
            and sector_rs_label == "STRONG"
            and leadership_is_good
        ):
            trade_recommendation = "STRONG BUY"
            trade_guidance = (
                "Technical, relative-strength, sector-leadership, "
                "and event-risk conditions are aligned."
            )
            recommendation_severity = "SUCCESS"

        else:
            trade_recommendation = "BUY"
            trade_guidance = (
                "BUY setup exists, but not all quality filters are ideal."
            )
            recommendation_severity = "SUCCESS"

    elif (
        research_bias == "BULLISH"
        and market_rs_label == "STRONG"
        and sector_rs_label == "STRONG"
        and leadership_is_good
    ):
        trade_recommendation = "WATCH"
        trade_guidance = (
            "High-quality bullish candidate, but the research model has not "
            "generated a BUY signal yet."
        )

    elif trend == "BEARISH" or market_rs_label == "WEAK":
        trade_recommendation = "AVOID"
        trade_guidance = (
            "Current setup lacks enough technical or relative-strength confirmation."
        )
        recommendation_severity = "WARNING"

    else:
        trade_recommendation = "WATCH"
        trade_guidance = (
            "No actionable BUY or SELL from the research model. Monitor only."
        )

    guidance = trade_guidance

    earnings_label = str(
        earnings_ctx.get("risk_label", "NONE") or "NONE"
    ).upper().strip()

    economic_label = str(
        economic_ctx.get("risk_label", "NONE") or "NONE"
    ).upper().strip()

    market_regime = str(
        market_ctx.get("regime", "NEUTRAL") or "NEUTRAL"
    ).upper().strip()

    scorecard_rows = []

    def add_scorecard_row(
        factor: str,
        score: int,
        max_score: int,
        status: str,
        note: str,
    ) -> None:
        scorecard_rows.append({
            "Factor": factor,
            "Score": score,
            "Max": max_score,
            "Status": status,
            "Note": note,
        })

    add_scorecard_row(
        "Trend",
        2 if trend == "BULLISH" else 0,
        2,
        "PASS" if trend == "BULLISH" else "FAIL",
        f"Trend is {trend}.",
    )

    add_scorecard_row(
        "MA Structure",
        1 if ma_structure_pass else 0,
        1,
        "PASS" if ma_structure_pass else "WATCH",
        (
            f"Close ${latest_close:.2f}, "
            f"MA20 ${latest_ma20:.2f}, "
            f"MA50 ${latest_ma50:.2f}."
        ),
    )

    add_scorecard_row(
        "Position Within 52-Week Range",
        1 if range_position_pass else 0,
        1,
        "PASS" if range_position_pass else "WATCH",
        f"{range_position * 100:.0f}% of 52-week range.",
    )

    add_scorecard_row(
        "Liquidity",
        1 if liquidity_pass else 0,
        1,
        "PASS" if liquidity_pass else "FAIL",
        f"20D average volume is {avg_volume_20d:,.0f}.",
    )

    add_scorecard_row(
        "Volatility",
        1 if volatility_pass else 0,
        1,
        "PASS" if volatility_pass else "WATCH",
        f"ATR is {atr_pct * 100:.1f}% of price.",
    )

    add_scorecard_row(
        "RS vs SPY",
        2 if market_rs_label == "STRONG" else 0,
        2,
        "PASS" if market_rs_label == "STRONG" else "WATCH",
        f"RS vs SPY is {latest_rs_score:.4f} ({market_rs_label}).",
    )

    add_scorecard_row(
        f"RS vs {sector_benchmark_symbol}",
        2 if sector_rs_label == "STRONG" else 0,
        2,
        "PASS" if sector_rs_label == "STRONG" else "WATCH",
        (
            f"Sector-relative strength is {latest_sector_rs_score:.4f} "
            f"({sector_rs_label})."
        ),
    )

    leadership_pass = sector_leadership_status in (
        "ELITE",
        "LEADER",
        "STRONG",
    )

    add_scorecard_row(
        "Sector Leadership",
        2 if leadership_pass else 0,
        2,
        "PASS" if leadership_pass else "WATCH",
        (
            f"Peer group rank is {sector_rank}/{sector_total} "
            f"({sector_leadership_status})."
            if sector_rank is not None and sector_total
            else "Peer group rank unavailable."
        ),
    )

    add_scorecard_row(
        "Research Bias",
        2 if research_bias == "BULLISH" else 0,
        2,
        "PASS" if research_bias == "BULLISH" else "WATCH",
        f"Research bias is {research_bias}.",
    )

    earnings_scorecard_score = 1
    earnings_status = "PASS"
    earnings_note = f"Earnings risk is {earnings_label}."

    if earnings_label in (
        "HIGH",
        "EXTREME",
    ):
        earnings_scorecard_score = 0
        earnings_status = "RISK"
        earnings_note = (
            f"Earnings risk is {earnings_label}; "
            f"next earnings are in {earnings_ctx.get('days_until')} day(s)."
        )

    add_scorecard_row(
        "Earnings Risk",
        earnings_scorecard_score,
        1,
        earnings_status,
        earnings_note,
    )

    economic_scorecard_score = 1
    economic_status = "PASS"

    if economic_label in (
        "HIGH",
        "EXTREME",
    ):
        economic_scorecard_score = 0
        economic_status = "RISK"
    elif economic_label == "DEMO":
        economic_scorecard_score = 0
        economic_status = "DEMO"

    add_scorecard_row(
        "Economic Risk",
        economic_scorecard_score,
        1,
        economic_status,
        f"Economic calendar risk is {economic_label}.",
    )

    market_scorecard_score = 2
    market_status = "PASS"

    if market_regime == "RISK_OFF":
        market_scorecard_score = 0
        market_status = "RISK"
    elif market_regime == "NEUTRAL":
        market_scorecard_score = 0
        market_status = "NEUTRAL"

    add_scorecard_row(
        "Market Regime",
        market_scorecard_score,
        2,
        market_status,
        f"Market regime is {market_regime}.",
    )

    opportunity_score = int(
        sum(row["Score"] for row in scorecard_rows)
    )

    opportunity_max = int(
        sum(row["Max"] for row in scorecard_rows)
    )

    opportunity_pct = (
        opportunity_score / opportunity_max
        if opportunity_max > 0
        else 0.0
    )

    if opportunity_pct >= 0.90:
        overall_rating = "A+"
    elif opportunity_pct >= 0.80:
        overall_rating = "A"
    elif opportunity_pct >= 0.70:
        overall_rating = "A-"
    elif opportunity_pct >= 0.60:
        overall_rating = "B"
    elif opportunity_pct >= 0.50:
        overall_rating = "C"
    else:
        overall_rating = "D"

    scorecard_df = pd.DataFrame(
        scorecard_rows
    )

    checklist_rows = [
        {
            "Requirement": "Research Score ≥ 4",
            "Passed": model_score >= 4,
            "Weight": 2,
        },
        {
            "Requirement": "Research BUY Signal",
            "Passed": signal == "BUY",
            "Weight": 2,
        },
        {
            "Requirement": "Earnings Cleared",
            "Passed": (
                earnings_ctx.get("days_until") is None
                or safe_int(
                    earnings_ctx.get("days_until"),
                    999,
                ) > 7
            ),
            "Weight": 2,
        },
        {
            "Requirement": "Combined Risk Below HIGH",
            "Passed": event_ctx.get(
                "combined_label",
                "NONE",
            ) not in (
                "HIGH",
                "EXTREME",
            ),
            "Weight": 2,
        },
        {
            "Requirement": "RS vs SPY Strong",
            "Passed": market_rs_label == "STRONG",
            "Weight": 1,
        },
        {
            "Requirement": f"RS vs {sector_benchmark_symbol} Strong",
            "Passed": sector_rs_label == "STRONG",
            "Weight": 1,
        },
        {
            "Requirement": "Sector Leadership Strong",
            "Passed": sector_leadership_status in (
                "ELITE",
                "LEADER",
                "STRONG",
            ),
            "Weight": 1,
        },
    ]

    passed_checks = sum(
        row["Weight"]
        for row in checklist_rows
        if row.get("Passed")
    )

    total_checks = sum(
        row["Weight"]
        for row in checklist_rows
    )

    readiness_pct = (
        passed_checks / total_checks
        if total_checks
        else 0.0
    )

    checklist_df = pd.DataFrame(
        checklist_rows
    )

    checklist_df["Status"] = checklist_df[
        "Passed"
    ].apply(
        lambda passed:
        "✅ PASS"
        if passed
        else "⬜ WAIT"
    )

    checklist_display = checklist_df[
        [
            "Status",
            "Requirement",
            "Weight",
        ]
    ]

    def factor_grade(status: str) -> str:

        status = str(status or "").upper().strip()

        if status == "PASS":
            return "🟢 A"

        if status in (
            "WATCH",
            "NEUTRAL",
        ):
            return "🟡 C"

        if status in (
            "RISK",
            "FAIL",
            "DEMO",
        ):
            return "🔴 F"

        return "⚪ N/A"

    grade_df = scorecard_df.copy()

    if "Status" in grade_df.columns:
        grade_df["Grade"] = grade_df["Status"].apply(
            factor_grade
        )

    grade_display_cols = [
        "Factor",
        "Grade",
        "Score",
        "Max",
        "Note",
    ]

    grade_display_cols = [
        col for col in grade_display_cols
        if col in grade_df.columns
    ]

    
    dashboard_left, dashboard_right = responsive_columns([2.3, 1.2])

    st.markdown(
        '<div class="institutional-chapter">Market Context</div>',
        unsafe_allow_html=True,
    )

    with dashboard_left:

        st.subheader("🏆 Relative Strength & Sector Leadership")
        st.caption(
            "What it means: Measures whether the stock is outperforming "
            "the market, its sector benchmark, and its peer group."
        )

        rs1, rs2, rs3, rs4 = responsive_columns(4)

        with rs1:
            st.metric(
                "RS vs SPY",
                latest_rs_score,
                market_rs_label,
                delta_color="off",
            )
            st.caption("RS > 1.00 means outperforming SPY.")

        with rs2:
            st.metric(
                f"RS vs {sector_benchmark_symbol}",
                latest_sector_rs_score,
                sector_rs_label,
                delta_color="off",
            )
            st.caption(
                f"RS > 1.00 means outperforming {sector_benchmark_symbol}."
            )

        with rs3:
            st.metric(
                "Sector Benchmark",
                sector_benchmark_symbol,
                sector_benchmark_label,
                delta_color="off",
            )
            st.caption("Sector ETF used for comparison.")

        with rs4:
            st.metric(
                "Research Bias",
                research_bias,
            )
            st.caption("Model view from trend and relative strength.")

        st.caption(
            "Relative strength guide: STRONG = outperforming, "
            "NEUTRAL = near benchmark, WEAK = underperforming."
        )

        if sector_rs_label == "STRONG":
            st.success(f"{ticker} is outperforming both SPY and its sector benchmark ({sector_benchmark_symbol}).")
        elif market_rs_label == "STRONG" and sector_rs_label == "WEAK":
            st.warning(f"{ticker} is outperforming SPY but lagging its sector benchmark ({sector_benchmark_symbol}).")
        elif market_rs_label == "WEAK":
            st.warning(f"{ticker} is weak versus SPY. Sector-relative score is {sector_rs_label}.")
        else:
            st.info(f"{ticker} has neutral relative strength versus SPY and {sector_benchmark_symbol}.")

        sl1, sl2, sl3, sl4 = responsive_columns(4)

        sl1.metric(
            "Peer Group Rank",
            (
                f"{sector_rank} / {sector_total}"
                if sector_rank is not None and sector_total
                else "N/A"
            ),
        )
        sl1.caption(
            "Rank among stocks in the same peer group; 1 is strongest."
        )

        sl2.metric(
            "Sector Percentile",
            f"{sector_percentile}%" if sector_percentile is not None else "N/A",
            sector_leadership_status,
            delta_color="off",
        )
        sl2.caption(
            "Percentile rank within the sector peer group."
        )

        sl3.metric(
            "Peer Group Leader",
            sector_leadership_ctx.get("leader_symbol") or "N/A",
        )
        sl3.caption(
            "Highest-scoring stock in this peer group right now."
        )

        sl4.metric(
            "Leadership Tier",
            sector_leadership_badge(sector_leadership_status),
        )
        sl4.caption(
            "Overall leadership classification versus peers."
        )

        if sector_leadership_status in ("ELITE", "LEADER"):
            st.success(f"{ticker} ranks among the strongest stocks in its {profile.get('sector', 'sector')} peer group.")
        elif sector_leadership_status == "STRONG":
            st.info(f"{ticker} ranks in the upper half of its {profile.get('sector', 'sector')} peer group.")
        elif sector_leadership_status == "AVERAGE":
            st.info(f"{ticker} is average versus its {profile.get('sector', 'sector')} peer group.")
        elif sector_leadership_status == "WEAK":
            st.warning(f"{ticker} is lagging its {profile.get('sector', 'sector')} peer group.")
        else:
            st.info("Sector leadership ranking is unavailable for this symbol.")

        leadership_rows = sector_leadership_ctx.get("rows", [])

        leadership_df = pd.DataFrame()
        display_cols = []

        if leadership_rows:
            leadership_df = pd.DataFrame(
                leadership_rows
            )

            display_cols = [
                "rank",
                "symbol",
                "rs_vs_sector",
                "rs_label",
                "return_20d_pct",
                "return_60d_pct",
                "trend_score",
                "leadership_score",
            ]

            display_cols = [
                col for col in display_cols
                if col in leadership_df.columns
            ]

        table_df = df[
            [
                "Open",
                "High",
                "Low",
                "Close",
                "Benchmark",
                "Sector_Benchmark",
                "RS",
                "RS_MA20",
                "RS_SCORE",
                "RS_SECTOR",
                "RS_SECTOR_MA20",
                "RS_SECTOR_SCORE",
                "MA20",
                "MA50",
                "ATR",
                "20D_HIGH",
                "20D_LOW",
            ]
        ].copy()

        table_df = table_df.reset_index()
        first_col = table_df.columns[0]
        table_df = table_df.rename(
            columns={
                first_col: "Date",
            }
        )

        table_df["Date"] = pd.to_datetime(
            table_df["Date"],
            errors="coerce",
        )

        table_df = table_df.sort_values(
            "Date",
            ascending=False,
        )

        compact_model_cols = [
            "Date",
            "Close",
            "RS_SCORE",
            "RS_SECTOR_SCORE",
            "MA20",
            "MA50",
            "ATR",
            "20D_HIGH",
            "20D_LOW",
        ]

        compact_model_cols = [
            col for col in compact_model_cols
            if col in table_df.columns
        ]

        st.divider()
        st.subheader("🏆 Peer Group Analysis")
        st.caption(
            "What it means: Compares the stock against similar companies "
            "to identify leadership, laggards, and relative momentum."
        )

        leaders_col, recent_col = responsive_columns(2)

        with leaders_col:

            st.markdown("### Top Peer Group Leaders")

            if not leadership_df.empty and display_cols:
                st.dataframe(
                    leadership_df[display_cols].head(10),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info(
                    "Sector leadership table unavailable for this symbol."
                )

        with recent_col:

            st.markdown("### Recent Model Table")

            st.dataframe(
                table_df[compact_model_cols].head(10),
                width="stretch",
                hide_index=True,
            )

            with st.expander(
                "Full Model Diagnostics",
                expanded=False,
            ):
                st.dataframe(
                    table_df.head(10),
                    width="stretch",
                    hide_index=True,
                )

        st.divider()
        st.markdown(
            '<div class="institutional-chapter">Risk Assessment</div>',
            unsafe_allow_html=True,
        )
        st.subheader("🏛 Institutional Review")
        st.caption(
            "What it means: Scores the setup using institutional-style "
            "factors such as trend, liquidity, volatility, relative strength, "
            "leadership, and event risk."
        )

        grades_col, checklist_col = responsive_columns(2)

        with grades_col:

            fg1, fg2, fg3 = responsive_columns(3)

            fg1.metric(
                "Score",
                f"{opportunity_score} / {opportunity_max}",
            )
            fg1.caption(
                "Points earned from institutional factors."
            )

            fg2.metric(
                "Institutional Score",
                overall_rating,
            )
            fg2.caption(
                "Overall grade from A+ to D."
            )

            fg3.metric(
                "Score %",
                f"{opportunity_pct * 100:.1f}%",
            )
            fg3.caption(
                "Percent of total possible score."
            )

            st.dataframe(
                grade_df[grade_display_cols],
                width="stretch",
                hide_index=True,
            )

            if (
                overall_rating in (
                    "A+",
                    "A",
                    "A-",
                )
                and combined_label in (
                    "HIGH",
                    "EXTREME",
                )
            ):
                st.warning(
                    "High-quality candidate, but event risk is elevated. "
                    "This is a watchlist setup until event risk clears."
                )
            elif overall_rating in (
                "A+",
                "A",
                "A-",
            ):
                st.success(
                    "High-quality opportunity profile. Confirm with risk controls "
                    "and position sizing before acting."
                )
            elif overall_rating == "B":
                st.info(
                    "Moderate opportunity profile. Some conditions are constructive, "
                    "but confirmation is still missing."
                )
            else:
                st.info(
                    "Low-priority opportunity profile. Wait for stronger technical, "
                    "relative-strength, or event-risk confirmation."
                )

        with checklist_col:

            st.subheader("✅ BUY Checklist")

            buy_a, buy_b = responsive_columns(2)

            with buy_a:
                st.metric(
                    "BUY Readiness",
                    f"{passed_checks}/{total_checks}",
                )
                st.caption(
                    "Passed checklist weight / total weight."
                )

            with buy_b:
                st.metric(
                    "Readiness %",
                    f"{readiness_pct * 100:.0f}%",
                )
                st.caption(
                    "Overall checklist completion."
                )

            st.dataframe(
                checklist_display,
                width="stretch",
                hide_index=True,
            )

            with st.expander(
                "Event Risk Diagnostics",
                expanded=False,
            ):
                st.write(
                    {
                        "Earnings Risk": earnings_ctx,
                        "Economic Calendar": economic_ctx,
                        "Market Reaction": market_ctx,
                        "Relative Strength": {
                            "market_benchmark": "SPY",
                            "market_rs_score": latest_rs_score,
                            "market_rs_label": market_rs_label,
                            "sector_benchmark_symbol": sector_benchmark_symbol,
                            "sector_benchmark_label": sector_benchmark_label,
                            "sector_rs_score": latest_sector_rs_score,
                            "sector_rs_label": sector_rs_label,
                            "research_bias": research_bias,
                        },
                        "Sector Leadership": sector_leadership_ctx,
                        "Combined Event Risk": event_ctx,
                    }
                )

    with dashboard_right:

        st.markdown(
            '<div class="institutional-chapter">Fundamental Quality</div>',
            unsafe_allow_html=True,
        )
        st.subheader("📌 Fundamental Quality Review")
        st.caption(
            "What it means: Summarizes whether the stock currently has "
            "a strong enough setup to deserve attention."
        )

        thesis_checks = [
            ("Trend", trend == "BULLISH"),
            ("MA structure", ma_structure_pass),
            ("Position Within 52-Week Range", range_position_pass),
            ("Liquidity", liquidity_pass),
            ("Volatility", volatility_pass),
            ("Relative strength vs SPY", market_rs_label == "STRONG"),
            (
                f"Relative strength vs {sector_benchmark_symbol}",
                sector_rs_label == "STRONG",
            ),
            (
                "Sector leadership",
                sector_leadership_status in (
                    "ELITE",
                    "LEADER",
                    "STRONG",
                ),
            ),
            (
                "Event risk acceptable",
                event_ctx.get("combined_label") not in (
                    "HIGH",
                    "EXTREME",
                ),
            ),
            ("Research BUY signal", signal == "BUY"),
        ]

        thesis_score = sum(
            1
            for _, passed in thesis_checks
            if passed
        )

        thesis_total = len(thesis_checks)

        thesis_lines = []

        for label, passed in thesis_checks:
            thesis_lines.append(
                f"{'✅' if passed else '❌'} {label}"
            )

        thesis_summary = (
            f"**Thesis Score: {thesis_score}/{thesis_total}**\n\n"
            + "\n".join(f"- {line}" for line in thesis_lines)
        )

        thesis_conclusion = (
            "**Conclusion:** Not a priority candidate right now. "
            "Wait for stronger technical and relative-strength confirmation."
        )

        if (
            signal == "BUY"
            and event_ctx.get("combined_label") not in (
                "HIGH",
                "EXTREME",
            )
        ):
            thesis_conclusion = (
                "**Conclusion:** Strong candidate. Technicals, relative strength, "
                "and event risk are aligned enough for consideration."
            )
            st.success(thesis_summary + "\n\n" + thesis_conclusion)

        elif (
            research_bias == "BULLISH"
            and event_ctx.get("combined_label") in (
                "HIGH",
                "EXTREME",
            )
        ):
            thesis_conclusion = (
                "**Conclusion:** High-quality candidate, but timing is poor. "
                "Wait for event risk to clear before considering a new position."
            )
            st.warning(thesis_summary + "\n\n" + thesis_conclusion)

        elif research_bias == "BULLISH":
            thesis_conclusion = (
                "**Conclusion:** Constructive setup, but the research model has not "
                "confirmed a BUY yet."
            )
            st.info(thesis_summary + "\n\n" + thesis_conclusion)

        else:
            st.info(thesis_summary + "\n\n" + thesis_conclusion)

        st.markdown(
            '<div class="institutional-chapter">Portfolio Fit</div>',
            unsafe_allow_html=True,
        )
        st.subheader("🧮 Opportunity Scorecard")
        st.caption(
            "What it means: Converts the research factors into one "
            "institutional opportunity score."
        )

        portfolio_role = "Not a Fit"
        portfolio_role_class = "pf-role-value-bad"
        portfolio_role_note = "Not suitable for current portfolio"
        suggested_allocation = "0%"
        suggested_allocation_note = "No allocation recommended"
        review_again = "After strength improves"
        review_again_note = "Reassess when technical and RS improve"

        if trade_recommendation in ("BUY", "STRONG BUY") and combined_label not in ("HIGH", "EXTREME"):
            portfolio_role = "Selective Fit"
            portfolio_role_class = "pf-role-value-good"
            portfolio_role_note = "Suitable for risk-controlled entry"
            suggested_allocation = "2% - 4%"
            suggested_allocation_note = "Starter size with risk controls"
            review_again = "After catalyst window"
            review_again_note = "Reassess after earnings and regime shift"
        elif trade_recommendation == "WATCH":
            portfolio_role = "Watchlist"
            portfolio_role_class = "pf-role-value-bad"
            portfolio_role_note = "Not suitable for current portfolio"

        interpretation_text = (
            f"This stock is {portfolio_role.lower()} for the current portfolio. "
            f"{suggested_allocation_note}. Review after relative strength and technical setup improve."
        )
        if portfolio_role == "Selective Fit":
            interpretation_text = (
                "This stock is a selective fit for the current portfolio. "
                "Use starter sizing and reassess after catalyst and regime updates."
            )

        st.markdown(
            f"""
            <div class="pf-decision-card opportunity-scorecard">
                <div class="scorecard-row">
                    <div class="scorecard-cell">
                        <div class="scorecard-heading">Portfolio Role</div>
                        <div class="scorecard-role-value {portfolio_role_class}">{portfolio_role}</div>
                        <div class="scorecard-description">{portfolio_role_note}</div>
                    </div>
                    <div class="scorecard-cell scorecard-divider">
                        <div class="scorecard-heading">Suggested Allocation</div>
                        <div class="scorecard-allocation-value">{suggested_allocation}</div>
                        <div class="scorecard-description">{suggested_allocation_note}</div>
                    </div>
                    <div class="scorecard-cell scorecard-divider">
                        <div class="scorecard-heading">Review Again</div>
                        <div class="scorecard-review-value">{review_again}</div>
                        <div class="scorecard-description">{review_again_note}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<div class=\"pf-interpretation\"><strong>Interpretation:</strong> {interpretation_text}</div>",
            unsafe_allow_html=True,
        )

        sc1, sc2 = responsive_columns(2)

        with sc1:
            st.metric(
                "Institutional Score",
                f"{opportunity_score}/{opportunity_max}",
            )

        with sc2:
            st.metric(
                "Institutional Score",
                overall_rating,
            )

        sc3, sc4 = responsive_columns(2)

        with sc3:
            st.metric(
                "Checklist %",
                f"{opportunity_pct * 100:.0f}%",
            )

        with sc4:
            st.metric(
                "Event Risk",
                combined_label,
            )

        with st.expander(
            "View full opportunity checklist",
            expanded=False,
        ):
            scorecard_view = scorecard_df.copy()

            if not scorecard_view.empty:
                scorecard_view["Score"] = (
                    scorecard_view["Score"].astype(str)
                    + "/"
                    + scorecard_view["Max"].astype(str)
                )

                scorecard_view = scorecard_view[
                    [
                        "Factor",
                        "Score",
                        "Status",
                        "Note",
                    ]
                ]

                st.dataframe(
                    scorecard_view,
                    width="stretch",
                    hide_index=True,
                )

        st.markdown(
            '<div class="institutional-chapter">Commander Notes</div>',
            unsafe_allow_html=True,
        )
        st.subheader("🎯 Trade Recommendation")
        st.caption(
            "What it means: Final action generated from the research model, "
            "event risk engine, and market context."
        )

        recommendation_text = (
            f"**{trade_recommendation}**\n\n"
            f"**Guidance:** {trade_guidance}"
        )

        if recommendation_severity == "WARNING":
            st.warning(recommendation_text)
        elif recommendation_severity == "SUCCESS":
            st.success(recommendation_text)
        elif recommendation_severity == "ERROR":
            st.error(recommendation_text)
        else:
            st.info(recommendation_text)

        with st.expander(
            "Recommendation Reasons",
            expanded=False,
        ):
            reason_text = "\n".join(
                [
                    f"• {reason}"
                    for reason in trade_reasons
                ]
            )

            st.info(
                reason_text
                if reason_text
                else "No recommendation reasons available."
            )

        st.divider()

        st.subheader("📝 Analyst Summary")
        st.caption(
            "What it means: Plain-English summary of the current setup, "
            "risk level, and recommendation."
        )

        summary_lines = [
            (
                f"{ticker} currently has a "
                f"**{display_signal}** setup status "
                f"with a Research Score of "
                f"**{research_score_pct}% ({research_score_label})**."
            ),
            (
                f"Research bias is "
                f"**{research_bias}**."
            ),
            (
                f"The trend is "
                f"**{trend}** and relative strength versus SPY is "
                f"**{latest_rs_score:.4f}**."
            ),
            (
                f"Sector-relative strength versus "
                f"**{sector_benchmark_symbol}** is "
                f"**{latest_sector_rs_score:.4f} "
                f"({sector_rs_label})**."
            ),
            (
                f"Sector leadership rank is "
                f"**{sector_rank}/{sector_total}** "
                f"({sector_percentile} percentile, "
                f"{sector_leadership_badge(sector_leadership_status)})."
                if sector_rank is not None
                and sector_total
                else "Sector leadership rank is unavailable."
            ),
            (
                f"Combined event risk is "
                f"**{event_ctx.get('combined_badge', '🟢 NONE')}**."
            ),
            (
                f"Institutional opportunity score is "
                f"**{opportunity_score}/{opportunity_max}** "
                f"with an overall rating of "
                f"**{overall_rating}**."
            ),
            (
                f"Trade recommendation is "
                f"**{trade_recommendation}**."
            ),
        ]

        if days_until is not None:
            summary_lines.append(
                f"Next earnings are in "
                f"**{days_until} day(s)**."
            )

        summary_lines.append(
            trade_guidance
        )

        st.info(
            " ".join(summary_lines)
        )

    st.markdown(
        '<div class="institutional-chapter">Detailed Diagnostics</div>',
        unsafe_allow_html=True,
    )
    with st.expander("Detailed Diagnostics", expanded=False):
        st.markdown("#### Opportunity Scorecard")
        st.dataframe(
            scorecard_df,
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### Buy Checklist")
        st.dataframe(
            checklist_display,
            width="stretch",
            hide_index=True,
        )

        if "leadership_df" in locals() and not leadership_df.empty:
            st.markdown("#### Peer Leadership")
            st.dataframe(
                leadership_df.head(10),
                width="stretch",
                hide_index=True,
            )

        if "table_df" in locals():
            st.markdown("#### Model Table")
            st.dataframe(
                table_df.head(12),
                width="stretch",
                hide_index=True,
            )
