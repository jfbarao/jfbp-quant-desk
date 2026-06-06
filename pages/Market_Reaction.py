# =========================================================
# 🌎 MARKET REACTION PAGE — v1.9
# JFBP Quant Desk
# Public Dashboard + Private Portfolio Impact + Event History
# Market Playbook + Regime Dashboard + Similar Events
# =========================================================

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from analytics.market_reaction import generate_market_reaction_report
from analytics.market_event_history import (
    save_market_event,
    load_recent_market_events,
)


# =========================================================
# HELPERS
# =========================================================

def get_move(df, symbol: str):
    row = df[df["Symbol"] == symbol]

    if row.empty:
        return None

    try:
        return float(row.iloc[0]["Daily %"])
    except Exception:
        return None


def format_pct(value):
    if value is None:
        return "N/A"

    return f"{value:.2f}%"


def style_pct(val):
    try:
        val = float(val)
    except Exception:
        return ""

    if val > 0:
        return "color: green; font-weight: bold;"

    if val < 0:
        return "color: red; font-weight: bold;"

    return ""


def display_table(title: str, df):
    st.subheader(title)

    if df is None or df.empty:
        st.warning("No data available.")
        return

    styled = df.style.map(
        style_pct,
        subset=["Daily %"],
    )

    st.dataframe(
        styled,
        width="stretch",
        hide_index=True,
    )


def calculate_market_stress(indexes, sectors) -> tuple[int, str]:

    qqq = get_move(indexes, "QQQ")
    spy = get_move(indexes, "SPY")
    iwm = get_move(indexes, "IWM")
    vixy = get_move(indexes, "VIXY")
    xlk = get_move(sectors, "XLK")

    score = 0

    if qqq is not None:
        score += min(abs(min(qqq, 0)) * 10, 30)

    if spy is not None:
        score += min(abs(min(spy, 0)) * 8, 25)

    if iwm is not None:
        score += min(abs(min(iwm, 0)) * 5, 15)

    if xlk is not None:
        score += min(abs(min(xlk, 0)) * 5, 15)

    if vixy is not None and vixy > 0:
        score += min(vixy * 2, 15)

    score = int(min(score, 100))

    if score >= 80:
        label = "Severe Stress"
    elif score >= 60:
        label = "High Stress"
    elif score >= 40:
        label = "Moderate Stress"
    elif score >= 20:
        label = "Low Stress"
    else:
        label = "Calm Market"

    return score, label


def calculate_impact_label(portfolio_move: float) -> str:
    abs_move = abs(portfolio_move)

    if abs_move >= 2.0:
        return "HIGH"

    if abs_move >= 1.0:
        return "MODERATE"

    return "LOW"


def calculate_buy_the_dip_score(
    indexes,
    sectors,
    stress_score: int,
) -> tuple[int, str]:

    qqq = get_move(indexes, "QQQ")
    spy = get_move(indexes, "SPY")
    soxx = get_move(indexes, "SOXX")
    vixy = get_move(indexes, "VIXY")
    xlk = get_move(sectors, "XLK")

    score = 0

    if qqq is not None:
        score += min(abs(min(qqq, 0)) * 8, 30)

    if spy is not None:
        score += min(abs(min(spy, 0)) * 5, 20)

    if soxx is not None:
        score += min(abs(min(soxx, 0)) * 6, 25)

    if xlk is not None:
        score += min(abs(min(xlk, 0)) * 4, 15)

    if vixy is not None and vixy > 0:
        score += min(vixy, 15)

    score += min(stress_score // 5, 10)

    score = int(min(score, 100))

    if score >= 80:
        label = "Exceptional"
    elif score >= 60:
        label = "Attractive"
    elif score >= 40:
        label = "Watchlist"
    elif score >= 20:
        label = "Neutral"
    else:
        label = "Overheated"

    return score, label


def build_market_playbook(
    event_label: str,
    dip_score: int,
) -> tuple[str, str, str, str]:

    if "Semiconductor" in event_label:

        duration = "1–5 Trading Days"
        risk = "Medium"

        if dip_score >= 80:
            opportunity = "9/10"
            action = (
                "Accumulation is favored for quality tech, broad-market ETFs, "
                "and dividend-growth positions. Avoid leverage until market "
                "stress falls below 70."
            )
        elif dip_score >= 60:
            opportunity = "7/10"
            action = (
                "Scale in slowly. Favor quality and avoid chasing weak rebounds."
            )
        else:
            opportunity = "5/10"
            action = (
                "Watch for stabilization before adding risk."
            )

    elif "Risk-Off" in event_label:

        duration = "1–3 Weeks"
        risk = "High"

        if dip_score >= 70:
            opportunity = "7/10"
            action = (
                "Selective buying is reasonable, but keep cash available. "
                "Wait for broad stabilization before aggressive adds."
            )
        else:
            opportunity = "5/10"
            action = (
                "Remain defensive. Avoid forced buying until volatility cools."
            )

    elif "Defensive" in event_label:

        duration = "Several Sessions"
        risk = "Medium"
        opportunity = "6/10"
        action = (
            "Market is rotating away from growth. Favor quality, dividends, "
            "and defensive sectors until leadership improves."
        )

    elif "Energy" in event_label:

        duration = "Several Sessions"
        risk = "Medium"
        opportunity = "6/10"
        action = (
            "Rotation favors energy. Avoid assuming broad market strength "
            "unless SPY and QQQ confirm."
        )

    elif "Volatility" in event_label:

        duration = "1–10 Trading Days"
        risk = "High"
        opportunity = "6/10"
        action = (
            "Volatility is elevated. Scale entries, avoid leverage, and wait "
            "for confirmation before increasing exposure."
        )

    else:

        duration = "Unknown"
        risk = "Low"
        opportunity = "5/10"
        action = (
            "No major shock detected. Monitor conditions without forcing trades."
        )

    return duration, risk, opportunity, action


def build_playbook_df(
    event,
    dip_score: int,
    dip_label: str,
) -> pd.DataFrame:

    duration, risk, opportunity, action = build_market_playbook(
        event.label,
        dip_score,
    )

    return pd.DataFrame(
        [
            {"Metric": "Event", "Reading": event.label},
            {"Metric": "Buy-The-Dip Score", "Reading": f"{dip_score}/100"},
            {"Metric": "Opportunity", "Reading": dip_label},
            {"Metric": "Typical Duration", "Reading": duration},
            {"Metric": "Risk Level", "Reading": risk},
            {"Metric": "Opportunity Rating", "Reading": opportunity},
            {"Metric": "Suggested Action", "Reading": action},
        ]
    )


def all_values_negative(df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False

    values = pd.to_numeric(df["Daily %"], errors="coerce").dropna()

    if values.empty:
        return False

    return bool((values < 0).all())


def get_top_name(df: pd.DataFrame, strongest: bool = True) -> str:
    if df is None or df.empty:
        return "N/A"

    sorted_df = df.sort_values(
        "Daily %",
        ascending=not strongest,
        na_position="last",
    )

    row = sorted_df.iloc[0]

    return f"{row['Name']} ({format_pct(row['Daily %'])})"


def get_market_regime(
    indexes,
    sectors,
    stress_score: int,
) -> dict:

    qqq = get_move(indexes, "QQQ")
    spy = get_move(indexes, "SPY")
    iwm = get_move(indexes, "IWM")
    soxx = get_move(indexes, "SOXX")
    vixy = get_move(indexes, "VIXY")

    tlt = get_move(indexes, "TLT")
    gld = get_move(indexes, "GLD")
    uup = get_move(indexes, "UUP")
    hyg = get_move(indexes, "HYG")

    xlk = get_move(sectors, "XLK")
    xlp = get_move(sectors, "XLP")
    xlu = get_move(sectors, "XLU")
    xlv = get_move(sectors, "XLV")

    defensive_avg = pd.Series(
        [
            x for x in [xlp, xlu, xlv]
            if x is not None
        ]
    )

    defensive_score = (
        float(defensive_avg.mean())
        if not defensive_avg.empty
        else None
    )

    if stress_score >= 80:
        breadth_damage = "Severe"
    elif stress_score >= 60:
        breadth_damage = "High"
    elif stress_score >= 40:
        breadth_damage = "Moderate"
    else:
        breadth_damage = "Contained"

    if vixy is not None and vixy >= 5:
        volatility_regime = "Elevated"
    elif vixy is not None and vixy >= 2:
        volatility_regime = "Rising"
    else:
        volatility_regime = "Normal"

    if qqq is not None and spy is not None and qqq < spy:
        growth_vs_value = "Growth Underperforming"
    elif qqq is not None and spy is not None and qqq > spy:
        growth_vs_value = "Growth Leading"
    else:
        growth_vs_value = "Neutral"

    if defensive_score is not None and xlk is not None and defensive_score > xlk:
        rotation = "Defensive Rotation"
    else:
        rotation = "No Clear Defensive Rotation"

    if iwm is not None and spy is not None and iwm < spy:
        small_caps = "Small Caps Weak"
    elif iwm is not None and spy is not None and iwm > spy:
        small_caps = "Small Caps Leading"
    else:
        small_caps = "Neutral"

    if soxx is not None and soxx <= -2:
        semis = "Semiconductors Risk-Off"
    elif soxx is not None and soxx > 0:
        semis = "Semiconductors Risk-On"
    else:
        semis = "Neutral"

    if hyg is not None and hyg < 0:
        credit = "Credit Weak"
    elif hyg is not None and hyg > 0:
        credit = "Credit Stable"
    else:
        credit = "N/A"

    if tlt is not None and tlt > 0:
        bonds = "Bonds Bid"
    elif tlt is not None and tlt < 0:
        bonds = "Bonds Weak"
    else:
        bonds = "N/A"

    if gld is not None and gld > 0:
        gold = "Gold Bid"
    elif gld is not None and gld < 0:
        gold = "Gold Weak"
    else:
        gold = "N/A"

    if uup is not None and uup > 0:
        dollar = "Dollar Strong"
    elif uup is not None and uup < 0:
        dollar = "Dollar Weak"
    else:
        dollar = "N/A"

    if (
        stress_score >= 70
        and qqq is not None and qqq < 0
        and spy is not None and spy < 0
    ):
        overall = "Risk-Off / Defensive"
    elif qqq is not None and qqq > 0 and spy is not None and spy > 0:
        overall = "Risk-On"
    else:
        overall = "Mixed"

    return {
        "Overall Regime": overall,
        "Breadth Damage": breadth_damage,
        "Volatility Regime": volatility_regime,
        "Growth vs Value": growth_vs_value,
        "Rotation": rotation,
        "Small Caps": small_caps,
        "Semiconductors": semis,
        "Credit": credit,
        "Bonds": bonds,
        "Gold": gold,
        "Dollar": dollar,
    }


def build_event_scorecard(
    event,
    indexes,
    sectors,
    stress_score: int,
    stress_label: str,
) -> pd.DataFrame:

    regime = get_market_regime(
        indexes=indexes,
        sectors=sectors,
        stress_score=stress_score,
    )

    leadership = get_top_name(
        sectors,
        strongest=True,
    )

    weakest_group = get_top_name(
        sectors,
        strongest=False,
    )

    rows = [
        {"Metric": "Event Type", "Reading": event.label},
        {"Metric": "Market Stress", "Reading": f"{stress_score}/100 — {stress_label}"},
        {"Metric": "Leadership", "Reading": leadership},
        {"Metric": "Weakest Group", "Reading": weakest_group},
        {"Metric": "Overall Regime", "Reading": regime["Overall Regime"]},
        {"Metric": "Breadth Damage", "Reading": regime["Breadth Damage"]},
        {"Metric": "Volatility Regime", "Reading": regime["Volatility Regime"]},
        {"Metric": "Growth vs Value", "Reading": regime["Growth vs Value"]},
        {"Metric": "Rotation", "Reading": regime["Rotation"]},
        {"Metric": "Small Caps", "Reading": regime["Small Caps"]},
        {"Metric": "Semiconductors", "Reading": regime["Semiconductors"]},
    ]

    return pd.DataFrame(rows)


def build_regime_dashboard_df(
    indexes,
    sectors,
    stress_score: int,
) -> pd.DataFrame:

    regime = get_market_regime(
        indexes=indexes,
        sectors=sectors,
        stress_score=stress_score,
    )

    rows = [
        {"Regime Component": "Overall Market", "Reading": regime["Overall Regime"]},
        {"Regime Component": "Technology / Growth", "Reading": regime["Growth vs Value"]},
        {"Regime Component": "Semiconductors", "Reading": regime["Semiconductors"]},
        {"Regime Component": "Small Caps", "Reading": regime["Small Caps"]},
        {"Regime Component": "Defensives", "Reading": regime["Rotation"]},
        {"Regime Component": "Volatility", "Reading": regime["Volatility Regime"]},
        {"Regime Component": "Credit", "Reading": regime["Credit"]},
        {"Regime Component": "Bonds", "Reading": regime["Bonds"]},
        {"Regime Component": "Gold", "Reading": regime["Gold"]},
        {"Regime Component": "Dollar", "Reading": regime["Dollar"]},
    ]

    return pd.DataFrame(rows)


def build_market_summary(
    event,
    indexes,
    sectors,
    megacaps,
    stress_score: int,
    stress_label: str,
) -> str:

    qqq = get_move(indexes, "QQQ")
    spy = get_move(indexes, "SPY")
    vixy = get_move(indexes, "VIXY")
    soxx = get_move(indexes, "SOXX")

    weakest_megacaps = megacaps.sort_values(
        "Daily %",
        ascending=True,
        na_position="last",
    ).head(3)

    strongest_sectors = sectors.sort_values(
        "Daily %",
        ascending=False,
        na_position="last",
    ).head(3)

    weak_names = [
        f"{row['Symbol']} {format_pct(row['Daily %'])}"
        for _, row in weakest_megacaps.iterrows()
    ]

    strong_names = [
        f"{row['Name']} {format_pct(row['Daily %'])}"
        for _, row in strongest_sectors.iterrows()
    ]

    soxx_text = (
        f", SOXX is {format_pct(soxx)}"
        if soxx is not None
        else ""
    )

    return (
        f"{event.label} detected. "
        f"QQQ is {format_pct(qqq)}, SPY is {format_pct(spy)}"
        f"{soxx_text}, and VIXY is {format_pct(vixy)}. "
        f"The weakest megacaps are {', '.join(weak_names)}. "
        f"The strongest sectors are {', '.join(strong_names)}. "
        f"Market stress is {stress_score}/100 — {stress_label}."
    )


def safe_save_market_event(
    event,
    stress_score: int,
    stress_label: str,
    qqq,
    spy,
    dia,
    iwm,
    vixy,
    portfolio_move,
) -> None:

    try:
        save_market_event(
            event_label=event.label,
            confidence=event.confidence,
            stress_score=stress_score,
            stress_label=stress_label,
            qqq=qqq,
            spy=spy,
            dia=dia,
            iwm=iwm,
            vixy=vixy,
            portfolio_move=portfolio_move,
        )
    except Exception as exc:
        st.caption(f"Market event history not saved: {exc}")


def calculate_similarity_score(
    current: dict,
    historical_row: pd.Series,
) -> float:

    columns = [
        ("qqq", "QQQ"),
        ("spy", "SPY"),
        ("dia", "DIA"),
        ("iwm", "IWM"),
        ("vixy", "VIXY"),
    ]

    differences = []

    for current_key, history_key in columns:
        current_value = current.get(current_key)

        if current_value is None:
            continue

        if history_key not in historical_row:
            continue

        history_value = historical_row[history_key]

        if pd.isna(history_value):
            continue

        differences.append(abs(float(current_value) - float(history_value)))

    if not differences:
        return 0.0

    avg_difference = sum(differences) / len(differences)

    similarity = max(0.0, 100.0 - (avg_difference * 15.0))

    return round(similarity, 1)


def build_similar_events_df(
    history_df: pd.DataFrame,
    current_event_label: str,
    qqq,
    spy,
    dia,
    iwm,
    vixy,
) -> pd.DataFrame:

    if history_df is None or history_df.empty:
        return pd.DataFrame()

    current = {
        "qqq": qqq,
        "spy": spy,
        "dia": dia,
        "iwm": iwm,
        "vixy": vixy,
    }

    rows = []

    for _, row in history_df.iterrows():

        if row.get("Event") != current_event_label:
            continue

        similarity = calculate_similarity_score(
            current=current,
            historical_row=row,
        )

        rows.append(
            {
                "Date": row.get("Date"),
                "Event": row.get("Event"),
                "Similarity %": similarity,
                "QQQ": row.get("QQQ"),
                "SPY": row.get("SPY"),
                "IWM": row.get("IWM"),
                "VIXY": row.get("VIXY"),
                "Stress Score": row.get("Stress Score"),
            }
        )

    similar_df = pd.DataFrame(rows)

    if similar_df.empty:
        return similar_df

    similar_df = similar_df.sort_values(
        "Similarity %",
        ascending=False,
    ).head(5)

    return similar_df


# =========================================================
# PAGE
# =========================================================

def run_page() -> None:

    st.title("🌎 Market Reaction")

    st.caption(
        "Cross-market dashboard for detecting major selloffs, rotations, "
        "sector pressure, and megacap reaction."
    )

    refresh = st.button(
        "Refresh Market Reaction Data",
        width="stretch",
    )

    if refresh:
        st.rerun()

    with st.spinner("Loading market reaction data..."):
        report = generate_market_reaction_report()

    event = report["event"]
    indexes = report["indexes"]
    sectors = report["sectors"]
    megacaps = report["megacaps"]

    portfolio = report.get("portfolio")
    portfolio_move = None
    portfolio_df = None
    portfolio_impact = None

    if portfolio is not None:
        portfolio_move = portfolio.get("portfolio_move")
        portfolio_df = portfolio.get("portfolio_df")

        if portfolio_move is not None:
            portfolio_impact = calculate_impact_label(
                float(portfolio_move)
            )

    qqq = get_move(indexes, "QQQ")
    spy = get_move(indexes, "SPY")
    dia = get_move(indexes, "DIA")
    iwm = get_move(indexes, "IWM")
    soxx = get_move(indexes, "SOXX")
    tlt = get_move(indexes, "TLT")
    gld = get_move(indexes, "GLD")
    uup = get_move(indexes, "UUP")
    hyg = get_move(indexes, "HYG")
    vixy = get_move(indexes, "VIXY")

    stress_score, stress_label = calculate_market_stress(
        indexes,
        sectors,
    )

    dip_score, dip_label = calculate_buy_the_dip_score(
        indexes,
        sectors,
        stress_score,
    )

    playbook_df = build_playbook_df(
        event,
        dip_score,
        dip_label,
    )

    regime = get_market_regime(
        indexes=indexes,
        sectors=sectors,
        stress_score=stress_score,
    )

    overall_regime = regime.get("Overall Regime", "Mixed")

    if stress_score >= 70:
        scanner_playbook = "INSTITUTIONAL RISK OFF"
        scanner_regime = "RISK_OFF"
        scanner_buy_allowed = False
        scanner_sell_allowed = True
        scanner_execution_multiplier = 0.50

    elif stress_score >= 40:
        scanner_playbook = "CAUTION"
        scanner_regime = "NEUTRAL"
        scanner_buy_allowed = True
        scanner_sell_allowed = True
        scanner_execution_multiplier = 0.75

    elif overall_regime == "Risk-On":
        scanner_playbook = "RISK ON"
        scanner_regime = "RISK_ON"
        scanner_buy_allowed = True
        scanner_sell_allowed = True
        scanner_execution_multiplier = 1.00

    else:
        scanner_playbook = "NEUTRAL"
        scanner_regime = "NEUTRAL"
        scanner_buy_allowed = True
        scanner_sell_allowed = True
        scanner_execution_multiplier = 1.00

    # =====================================================
    # SCANNER / RISK ENGINE SESSION EXPORT
    # =====================================================
    # This is the bridge used by Scanner_page.py.
    # Scanner reads these keys inside market_reaction_context().

    st.session_state["market_reaction_score"] = int(stress_score)
    st.session_state["market_reaction_confidence"] = float(
        getattr(event, "confidence", 0) or 0
    )
    st.session_state["market_reaction_event"] = str(
        getattr(event, "label", "") or ""
    )
    st.session_state["market_reaction_playbook"] = scanner_playbook
    st.session_state["market_reaction_regime"] = scanner_regime
    st.session_state["market_reaction_overall_regime"] = overall_regime
    st.session_state["market_reaction_stress_label"] = stress_label
    st.session_state["market_reaction_dip_score"] = int(dip_score)
    st.session_state["market_reaction_dip_label"] = dip_label
    st.session_state["market_reaction_buy_allowed"] = scanner_buy_allowed
    st.session_state["market_reaction_sell_allowed"] = scanner_sell_allowed
    st.session_state["market_reaction_execution_multiplier"] = (
        scanner_execution_multiplier
    )

    summary = build_market_summary(
        event,
        indexes,
        sectors,
        megacaps,
        stress_score,
        stress_label,
    )

    scorecard_df = build_event_scorecard(
        event=event,
        indexes=indexes,
        sectors=sectors,
        stress_score=stress_score,
        stress_label=stress_label,
    )

    regime_df = build_regime_dashboard_df(
        indexes=indexes,
        sectors=sectors,
        stress_score=stress_score,
    )

    safe_save_market_event(
        event=event,
        stress_score=stress_score,
        stress_label=stress_label,
        qqq=qqq,
        spy=spy,
        dia=dia,
        iwm=iwm,
        vixy=vixy,
        portfolio_move=portfolio_move,
    )

    try:
        history_df = load_recent_market_events(50)
    except Exception:
        history_df = pd.DataFrame()

    similar_events_df = build_similar_events_df(
        history_df=history_df,
        current_event_label=event.label,
        qqq=qqq,
        spy=spy,
        dia=dia,
        iwm=iwm,
        vixy=vixy,
    )
    
    # =====================================================
    # EVENT BANNER
    # =====================================================

    st.divider()

    if event.label == "No Major Shock Detected":
        st.success(f"✅ {event.label}")
    else:
        st.warning(f"⚠️ {event.label}")

    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])

    with col1:
        st.metric("Event Confidence", f"{event.confidence}%")

    with col2:
        st.metric("Market Stress", f"{stress_score}/100", stress_label)

    with col3:
        st.metric("Buy-The-Dip", f"{dip_score}/100", dip_label)

    with col4:
        st.write(event.explanation)

    # =====================================================
    # MARKET SUMMARY
    # =====================================================

    st.divider()

    st.subheader("What Happened Today?")
    st.info(summary)

    # =====================================================
    # MARKET PLAYBOOK
    # =====================================================

    st.divider()

    with st.expander(
        "🎯 Market Playbook",
        expanded=True,
    ):
        st.dataframe(
            playbook_df,
            width="stretch",
            hide_index=True,
        )

    # =====================================================
    # MARKET REGIME DASHBOARD
    # =====================================================

    st.divider()

    with st.expander(
        "🧭 Market Regime Dashboard",
        expanded=True,
    ):
        st.dataframe(
            regime_df,
            width="stretch",
            hide_index=True,
        )

    # =====================================================
    # SIMILAR PAST EVENTS
    # =====================================================

    st.divider()

    with st.expander(
        "🔎 Similar Past Events",
        expanded=True,
    ):

        if similar_events_df.empty:
            st.info(
                "Not enough similar events recorded yet. "
                "This section becomes more useful as the event database grows."
            )
        else:
            st.dataframe(
                similar_events_df,
                width="stretch",
                hide_index=True,
            )

    # =====================================================
    # EVENT SCORECARD
    # =====================================================

    st.divider()

    with st.expander(
        "🧾 Market Event Scorecard",
        expanded=True,
    ):
        st.dataframe(
            scorecard_df,
            width="stretch",
            hide_index=True,
        )

    # =====================================================
    # MARKET SNAPSHOT
    # =====================================================

    st.divider()

    st.subheader("Market Snapshot")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("QQQ", format_pct(qqq))

    with col2:
        st.metric("SPY", format_pct(spy))

    with col3:
        st.metric("IWM", format_pct(iwm))

    with col4:
        st.metric("SOXX", format_pct(soxx))

    with col5:
        st.metric("VIXY", format_pct(vixy))

    col6, col7, col8, col9, col10 = st.columns(5)

    with col6:
        st.metric("DIA", format_pct(dia))

    with col7:
        st.metric("TLT", format_pct(tlt))

    with col8:
        st.metric("GLD", format_pct(gld))

    with col9:
        st.metric("UUP", format_pct(uup))

    with col10:
        st.metric("HYG", format_pct(hyg))

    # =====================================================
    # PRIVATE PORTFOLIO IMPACT
    # =====================================================

    st.divider()

    with st.expander(
        "🔒 Private Portfolio Impact",
        expanded=False,
    ):

        if portfolio is None or portfolio_df is None:
            st.info("Portfolio impact data is not available.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Estimated Portfolio Move",
                    format_pct(portfolio_move),
                )

            with col2:
                st.metric(
                    "Impact Level",
                    portfolio_impact,
                )

            st.caption(
                "Private view. Collapse this section before taking public screenshots."
            )

            st.dataframe(
                portfolio_df.style.map(
                    style_pct,
                    subset=["Daily %", "Contribution %"],
                ),
                width="stretch",
                hide_index=True,
            )

    # =====================================================
    # DAMAGE REPORT
    # =====================================================

    st.divider()

    st.subheader("Damage Report")

    col1, col2 = st.columns(2)

    weakest_sectors = sectors.sort_values(
        "Daily %",
        ascending=True,
        na_position="last",
    ).head(5)

    weakest_megacaps = megacaps.sort_values(
        "Daily %",
        ascending=True,
        na_position="last",
    ).head(5)

    with col1:
        st.markdown("### Weakest Sectors")
        st.dataframe(
            weakest_sectors,
            width="stretch",
            hide_index=True,
        )

    with col2:
        st.markdown("### Weakest Megacaps")
        st.dataframe(
            weakest_megacaps,
            width="stretch",
            hide_index=True,
        )

    # =====================================================
    # ROTATION REPORT
    # =====================================================

    st.divider()

    st.subheader("Rotation Report")

    col1, col2 = st.columns(2)

    strongest_sectors = sectors.sort_values(
        "Daily %",
        ascending=False,
        na_position="last",
    ).head(5)

    strongest_megacaps = megacaps.sort_values(
        "Daily %",
        ascending=False,
        na_position="last",
    ).head(5)

    megacap_title = (
        "Least Damaged Megacaps"
        if all_values_negative(megacaps)
        else "Strongest Megacaps"
    )

    with col1:
        st.markdown("### Strongest Sectors")
        st.dataframe(
            strongest_sectors,
            width="stretch",
            hide_index=True,
        )

    with col2:
        st.markdown(f"### {megacap_title}")
        st.dataframe(
            strongest_megacaps,
            width="stretch",
            hide_index=True,
        )

    # =====================================================
    # MARKET EVENT HISTORY
    # =====================================================

    st.divider()

    with st.expander(
        "📚 Recent Market Events",
        expanded=False,
    ):

        if history_df.empty:
            st.info("No market events have been recorded yet.")
        else:
            st.dataframe(
                history_df,
                width="stretch",
                hide_index=True,
            )

    # =====================================================
    # FULL TABLES
    # =====================================================

    st.divider()

    with st.expander("Full Market Tables", expanded=False):

        col1, col2 = st.columns(2)

        with col1:
            display_table("Major Indexes", indexes)

        with col2:
            display_table("Megacaps", megacaps)

        display_table("Sector Reaction", sectors)