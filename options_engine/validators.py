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
REVIEW = "Review"


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

    required = float(trade.buying_power_required or 0.0)
    return REVIEW, (
        f"Required Buying Power: ${required:,.0f}. "
        f"This trade requires approximately ${required:,.0f} of available buying power. "
        "Verify that your brokerage account has sufficient available buying power before execution."
    )


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
    premium_yield_pct = premium_yield * 100.0

    # Phase 1 institutional premium quality bands.
    # Future enhancement: replace fixed bands with chain-aware scoring inputs
    # (delta, IV rank/percentile, DTE, POP, expected return, option score,
    # confidence score).
    if premium_yield_pct >= 1.25:
        return PASS, f"EXCELLENT. Premium yield {premium_yield_pct:,.2f}% is strong for this strike and expiration."

    if premium_yield_pct >= 0.80:
        return PASS, f"GOOD. Premium yield {premium_yield_pct:,.2f}% is appropriate for this strike and expiration."

    if premium_yield_pct >= 0.50:
        return PASS, f"ACCEPTABLE. Premium yield {premium_yield_pct:,.2f}% is acceptable for this strike and expiration."

    return WARN, f"WEAK. Premium yield {premium_yield_pct:,.2f}% is below the preferred range for this strike and expiration."


def validate_position_size(trade: TradeModel) -> tuple[str, str]:
    if trade.max_loss <= 0:
        return PENDING, "Worst-Case Stock Ownership Loss has not been calculated yet."

    return REVIEW, "Confirm this position fits your personal portfolio allocation and risk management rules."


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
        "Premium Quality": validate_premium(trade),
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

    if REVIEW in statuses:
        return _set_status(trade, PASS, messages, warnings)

    return _set_status(trade, PASS, messages, warnings)
