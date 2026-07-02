"""
Trade Calculation Engine

Phase 2

Pure calculation logic for the Options Trade Construction Center.
No Streamlit. No UI. No session state.
"""

from datetime import date

from options_engine.models.trade_model import TradeModel


# ==========================================================
# Helpers
# ==========================================================

def days_to_expiration(expiration: date | None) -> int:
    if expiration is None:
        return 0

    return max((expiration - date.today()).days, 0)


def safe_contracts(contracts: int) -> int:
    return max(int(contracts or 1), 1)


def reset_trade_calculations(trade: TradeModel) -> TradeModel:
    trade.reset_results()
    return trade


# ==========================================================
# Cash-Secured Put
# ==========================================================

def calculate_cash_secured_put(trade: TradeModel) -> TradeModel:
    """
    Calculates core metrics for a Cash-Secured Put.

    Required inputs:
        strike
        premium
        contracts
        expiration

    Outputs:
        credit
        max_profit
        max_loss
        breakeven
        roi
        annualized_return
        buying_power_required
    """

    trade.reset_results()

    strike = max(float(trade.strike or 0), 0)
    premium = max(float(trade.premium or 0), 0)
    contracts = safe_contracts(trade.contracts)
    shares = contracts * 100

    gross_obligation = strike * shares
    credit = premium * shares

    trade.credit = credit
    trade.debit = 0.0
    trade.buying_power_required = gross_obligation
    trade.max_profit = credit
    trade.max_loss = max(gross_obligation - credit, 0)
    trade.breakeven = max(strike - premium, 0)

    if trade.buying_power_required > 0:
        trade.roi = (trade.max_profit / trade.buying_power_required) * 100
    else:
        trade.roi = 0.0

    dte = days_to_expiration(trade.expiration)

    if dte > 0:
        trade.annualized_return = trade.roi * 365 / dte
    else:
        trade.annualized_return = 0.0

    if trade.max_loss > 0:
        trade.reward_risk_ratio = trade.max_profit / trade.max_loss
    else:
        trade.reward_risk_ratio = 0.0

    return trade


# ==========================================================
# Covered Call
# ==========================================================

def calculate_covered_call(trade: TradeModel) -> TradeModel:
    trade.reset_results()
    return trade


# ==========================================================
# Bull Put Spread
# ==========================================================

def calculate_bull_put_spread(trade: TradeModel) -> TradeModel:
    trade.reset_results()
    return trade


# ==========================================================
# Bull Call Spread
# ==========================================================

def calculate_bull_call_spread(trade: TradeModel) -> TradeModel:
    trade.reset_results()
    return trade


# ==========================================================
# Strategy Router
# ==========================================================

def calculate_trade(trade: TradeModel) -> TradeModel:
    """
    Routes the trade to the appropriate strategy calculator.
    """

    strategy = trade.active_strategy()

    if strategy == "Cash-Secured Put":
        return calculate_cash_secured_put(trade)

    if strategy == "Covered Call":
        return calculate_covered_call(trade)

    if strategy == "Bull Put Spread":
        return calculate_bull_put_spread(trade)

    if strategy == "Bull Call Spread":
        return calculate_bull_call_spread(trade)

    return reset_trade_calculations(trade)