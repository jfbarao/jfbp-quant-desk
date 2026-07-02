"""
Approval Engine

Phase 4

Converts validation results into an institutional trade decision.

No Streamlit. No UI. No session state.
"""

from options_engine.models.trade_model import TradeModel
from options_engine.validators import validate_trade


def _status_counts(trade: TradeModel) -> tuple[int, int, int]:
    """
    Counts validation messages by severity using simple text matching.

    This keeps the first approval engine compatible with the current
    validator output while leaving room for structured validation objects later.
    """
    warnings = len(getattr(trade, "warnings", []) or [])

    messages = getattr(trade, "validation_messages", []) or []
    failures = 0
    passes = 0

    for message in messages:
        text = str(message).lower()
        if "fail" in text or "reject" in text or "exceeds" in text:
            failures += 1
        elif "pass" in text or "acceptable" in text or "within" in text:
            passes += 1

    return passes, warnings, failures


def approve_trade(trade: TradeModel) -> TradeModel:
    """
    Runs validation and assigns:
        approval_status
        confidence_score
        institutional_grade
        warnings

    First version logic:
        Missing setup          -> WAIT
        Critical failure       -> REJECT
        Warning / adjustment   -> NEEDS ADJUSTMENT
        Clean validation       -> APPROVED
    """

    trade = validate_trade(trade)

    strategy = trade.active_strategy()

    if not trade.symbol or not strategy or trade.strike <= 0 or trade.premium <= 0:
        trade.approval_status = "WAIT"
        trade.confidence_score = 35.0
        trade.institutional_grade = "Pending"
        return trade

    if not trade.construction_complete:
        trade.approval_status = "WAIT"
        trade.confidence_score = 45.0
        trade.institutional_grade = "Pending"
        return trade

    passes, warning_count, failure_count = _status_counts(trade)

    validation_status = str(trade.validation_status or "").upper()

    if validation_status in {"REJECT", "FAILED", "FAIL"} or failure_count > 0:
        trade.approval_status = "REJECT"
        trade.confidence_score = 25.0
        trade.institutional_grade = "F"
        return trade

    if validation_status in {"NEEDS ADJUSTMENT", "WARNING"} or warning_count > 0:
        trade.approval_status = "NEEDS ADJUSTMENT"
        trade.confidence_score = 65.0
        trade.institutional_grade = "C"
        return trade

    if validation_status in {"PASS", "APPROVED"} or passes >= 4:
        trade.approval_status = "APPROVED"
        trade.confidence_score = 88.0
        trade.institutional_grade = "A-"
        return trade

    trade.approval_status = "WAIT"
    trade.confidence_score = 50.0
    trade.institutional_grade = "Pending"
    return trade


def approval_reason(trade: TradeModel) -> str:
    """
    Human-readable explanation for the approval card.
    """
    status = str(trade.approval_status or "WAIT").upper()

    if status == "APPROVED":
        return "Validation checks support the trade. Risk, buying power, premium, and structure appear acceptable for this phase."

    if status == "NEEDS ADJUSTMENT":
        return "One or more checks require adjustment before this trade should be considered execution-ready."

    if status == "REJECT":
        return "One or more critical checks failed. The current structure should not proceed."

    return "Waiting for a complete trade structure and validation result."
