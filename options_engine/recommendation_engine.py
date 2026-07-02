"""
Strategy Recommendation Engine

Phase 2C

Commander Jimmy's first rule-based recommendation layer.

This module converts mission, market bias, account context, and share
ownership into an initial recommended options strategy.

No Streamlit. No UI. No session state.
"""

from options_engine.models.trade_model import TradeModel


def _set_recommendation(
    trade: TradeModel,
    strategy: str,
    confidence: float,
    reason: str,
) -> TradeModel:
    trade.recommended_strategy = strategy
    trade.strategy_confidence = confidence
    trade.strategy_reason = reason
    return trade


def _clear_recommendation(trade: TradeModel) -> TradeModel:
    trade.recommended_strategy = ""
    trade.strategy_confidence = 0.0
    trade.strategy_reason = ""
    return trade


def recommend_strategy(trade: TradeModel) -> TradeModel:
    """
    Recommend the first suitable strategy for the current mission.

    Phase 2C rules are intentionally simple and explainable.
    The engine will become more sophisticated after validation,
    liquidity, IV, earnings, and portfolio context are connected.
    """

    mission = str(trade.mission or "").strip()
    market_bias = str(trade.market_bias or "").strip()
    existing_shares = int(trade.existing_shares or 0)
    buying_power = float(trade.buying_power or 0.0)
    stock_price = float(trade.stock_price or 0.0)

    if not mission:
        return _clear_recommendation(trade)

    if mission == "Generate Income":
        if existing_shares >= 100:
            return _set_recommendation(
                trade,
                "Covered Call",
                86.0,
                (
                    "Mission is income and the account already has at least 100 shares. "
                    "Covered Call is the natural income overlay for an existing stock position."
                ),
            )

        if buying_power > 0:
            return _set_recommendation(
                trade,
                "Cash-Secured Put",
                84.0,
                (
                    "Mission is income, no shares are marked as owned, and buying power is available. "
                    "Cash-Secured Put supports premium collection while keeping assignment as a defined plan."
                ),
            )

        return _set_recommendation(
            trade,
            "Bull Put Spread",
            72.0,
            (
                "Mission is income but buying power is limited or unknown. "
                "Bull Put Spread may provide defined-risk premium exposure with less capital than a cash-secured put."
            ),
        )

    if mission == "Buy Shares at a Discount":
        return _set_recommendation(
            trade,
            "Cash-Secured Put",
            88.0,
            (
                "Mission is to acquire shares below the current market price. "
                "Cash-Secured Put directly matches that objective because assignment is acceptable by design."
            ),
        )

    if mission == "Bullish Directional Trade":
        if market_bias == "Bullish":
            return _set_recommendation(
                trade,
                "Bull Call Spread",
                82.0,
                (
                    "Mission is bullish and market bias is bullish. "
                    "Bull Call Spread expresses upside participation with defined risk."
                ),
            )

        return _set_recommendation(
            trade,
            "Bull Call Spread",
            68.0,
            (
                "Mission is bullish directional, but market bias is not confirmed bullish. "
                "Bull Call Spread remains suitable because risk is defined, but confidence is reduced."
            ),
        )

    if mission == "Protect Existing Shares":
        if existing_shares >= 100:
            return _set_recommendation(
                trade,
                "Covered Call",
                74.0,
                (
                    "Existing shares are present. Covered Call can generate income against the position, "
                    "but this is not true downside protection. Protective put logic will come later."
                ),
            )

        return _set_recommendation(
            trade,
            "Bull Put Spread",
            55.0,
            (
                "Protection was requested, but no existing shares are marked as owned. "
                "Commander Jimmy is using a placeholder defined-risk structure until hedge logic is added."
            ),
        )

    if mission == "High Probability Income":
        return _set_recommendation(
            trade,
            "Bull Put Spread",
            80.0,
            (
                "Mission prioritizes probability and defined risk. "
                "Bull Put Spread can target premium income while limiting downside exposure."
            ),
        )

    return _clear_recommendation(trade)


def recommendation_summary(trade: TradeModel) -> dict:
    """
    Returns a compact recommendation summary for future UI components,
    logging, or execution tickets.
    """

    return {
        "mission": trade.mission,
        "recommended_strategy": trade.recommended_strategy,
        "confidence": trade.strategy_confidence,
        "reason": trade.strategy_reason,
    }
