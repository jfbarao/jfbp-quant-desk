"""
Validation Engine

Phase 3

Pure validation logic for the Options Trade Construction Center.
No Streamlit. No UI. No session state.
"""

from datetime import date

from options_engine.models.trade_model import TradeModel
from options_engine.calculators import days_to_expiration


PASS = "Pass"
WARN = "Warning"
FAIL = "Fail"
PENDING = "Pending"


def _set_status(trade: TradeModel, status: str, messages: list[str], warnings: list[str]) -> TradeModel:
    trade.validation_status = status
    trade.validation_messages = messages
    trade.warnings = warnings

    if status == PASS:
        trade.approval_status = "APPROVED"
        trade.institutional_grade = "A"
        trade.confidence_score = 90.0
    elif status == WARN:
        trade.approval_status = "NEEDS ADJUSTMENT"
        trade.institutional_grade = "B"
        trade.confidence_score = 70.0
    elif status == FAIL:
        trade.approval_status = "REJECT"
        trade.institutional_grade = "C"
        trade.confidence_score = 35.0
    else:
        trade.approval_status = "Pending"
        trade.institutional_grade = ""
        trade.confidence_score = 0.0

    return trade


def validate_buying_power(trade: TradeModel) -> tuple[str, str]:
    if trade.buying_power_required <= 0:
        return PENDING, "Buying power requirement has not been calculated yet."

    if trade.buying_power <= 0:
        return WARN, "Available buying power has not been entered."

    if trade.buying_power_required <= trade.buying_power:
        return PASS, "Buying power supports this trade."

    return FAIL, "Required buying power exceeds available buying power."


def validate_expiration(trade: TradeModel) -> tuple[str, str]:
    dte = days_to_expiration(trade.expiration)

    if trade.expiration is None:
        return PENDING, "Expiration has not been selected."

    if dte <= 0:
        return FAIL, "Expiration must be in the future."

    if dte < 7:
        return WARN, "Expiration is very close. Gamma and assignment risk may be elevated."

    if 21 <= dte <= 60:
        return PASS, "Expiration is within a practical construction window."

    if dte > 90:
        return WARN, "Expiration is long-dated. Annualized return may overstate practical efficiency."

    return PASS, "Expiration is acceptable."


def validate_premium(trade: TradeModel) -> tuple[str, str]:
    if trade.premium <= 0:
        return PENDING, "Premium has not been entered."

    if trade.strike <= 0:
        return PENDING, "Strike must be entered before premium can be judged."

    premium_yield = trade.premium / trade.strike

    if premium_yield >= 0.01:
        return PASS, "Premium is at least 1% of the short strike."

    if premium_yield >= 0.005:
        return WARN, "Premium is modest relative to the short strike."

    return FAIL, "Premium is too small relative to the capital at risk."


def validate_position_size(trade: TradeModel) -> tuple[str, str]:
    risk_reference = trade.max_risk_allowed or (trade.account_size * 0.05 if trade.account_size > 0 else 0)

    if trade.max_loss <= 0:
        return PENDING, "Max loss has not been calculated yet."

    if risk_reference <= 0:
        return WARN, "No account size or max risk limit is available for sizing."

    if trade.max_loss <= risk_reference:
        return PASS, "Position size is within the configured risk limit."

    return WARN, "Max loss exceeds the configured risk reference."


def validate_breakeven_vs_stock(trade: TradeModel) -> tuple[str, str]:
    if trade.stock_price <= 0:
        return PENDING, "Current stock price is not available."

    if trade.breakeven <= 0:
        return PENDING, "Breakeven has not been calculated yet."

    strategy = trade.active_strategy()

    if strategy == "Cash-Secured Put":
        if trade.breakeven < trade.stock_price:
            return PASS, "Breakeven is below the current stock price."
        return WARN, "Breakeven is at or above the current stock price."

    return PENDING, "Breakeven comparison is not yet available for this strategy."


def get_validation_checks(trade: TradeModel) -> dict[str, tuple[str, str]]:
    return {
        "Buying Power": validate_buying_power(trade),
        "Expiration": validate_expiration(trade),
        "Premium": validate_premium(trade),
        "Position Size": validate_position_size(trade),
        "Breakeven vs Stock": validate_breakeven_vs_stock(trade),
    }


def validate_trade(trade: TradeModel) -> TradeModel:
    checks = get_validation_checks(trade)

    messages: list[str] = []
    warnings: list[str] = []

    statuses = []

    for label, (status, message) in checks.items():
        statuses.append(status)
        messages.append(f"{label}: {message}")

        if status in {WARN, FAIL}:
            warnings.append(f"{label}: {message}")

    if FAIL in statuses:
        return _set_status(trade, FAIL, messages, warnings)

    if WARN in statuses:
        return _set_status(trade, WARN, messages, warnings)

    if PENDING in statuses:
        return _set_status(trade, PENDING, messages, warnings)

    return _set_status(trade, PASS, messages, warnings)
