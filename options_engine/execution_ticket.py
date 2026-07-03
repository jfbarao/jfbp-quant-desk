"""
Execution Ticket Engine

Phase 5

Builds human-readable order tickets and management plans for the
Options Trade Construction Center.

No Streamlit. No UI. No session state.
"""

from options_engine.models.trade_model import TradeModel


def _money(value: float) -> str:
    return f"${float(value or 0):,.2f}"


def _percent(value: float) -> str:
    return f"{float(value or 0):,.2f}%"


def build_order_summary(trade: TradeModel) -> str:
    strategy = trade.active_strategy()
    symbol = trade.symbol or "TBD"

    if strategy == "Cash-Secured Put":
        if not trade.strike or not trade.expiration:
            return "Order summary pending: enter expiration, strike, premium, and contracts."

        return (
            f"SELL {int(trade.contracts or 1)} {symbol} PUT\n"
            f"Expiration: {trade.expiration}\n"
            f"Strike: {trade.strike:,.2f}\n"
            f"Target Credit: {_money(trade.premium)} per share\n"
            f"Total Credit: {_money(trade.credit)}\n"
            f"Buying Power Required: {_money(trade.buying_power_required)}\n"
            f"Max Profit: {_money(trade.max_profit)}\n"
            f"Max Loss: {_money(trade.max_loss)}\n"
            f"Breakeven: {_money(trade.breakeven)}\n"
            f"ROI: {_percent(trade.roi)}\n"
            f"Annualized Return: {_percent(trade.annualized_return)}"
        )

    if strategy == "Bull Call Spread":
        if not trade.long_strike or not trade.strike or not trade.expiration:
            return "Order summary pending: enter long strike, short strike, premium, and contracts."

        return (
            f"BUY {int(trade.contracts or 1)} {symbol} CALL @ {trade.long_strike:,.2f}\n"
            f"SELL {int(trade.contracts or 1)} {symbol} CALL @ {trade.strike:,.2f}\n"
            f"Expiration: {trade.expiration}\n"
            f"Long Premium: {_money(trade.long_premium)} per share\n"
            f"Short Premium: {_money(trade.premium)} per share\n"
            f"Net Debit: {_money(trade.debit)}\n"
            f"Maximum Capital at Risk: {_money(trade.buying_power_required)}\n"
            f"Max Profit: {_money(trade.max_profit)}\n"
            f"Max Loss: {_money(trade.max_loss)}\n"
            f"Breakeven: {_money(trade.breakeven)}\n"
            f"ROI: {_percent(trade.roi)}\n"
            f"Annualized Return: {_percent(trade.annualized_return)}"
        )

    return (
        "Order summary pending: this strategy is registered, but the full "
        "execution ticket engine for it will be added in a later phase."
    )


def build_entry_plan(trade: TradeModel) -> str:
    strategy = trade.active_strategy()

    if strategy == "Cash-Secured Put":
        if trade.premium > 0:
            return (
                f"Enter only at or above {_money(trade.premium)} per share. "
                "Do not chase the order lower if the premium collapses."
            )

        return "Entry pending: enter target premium before placing the trade."

    if strategy == "Bull Call Spread":
        if trade.long_strike > 0 and trade.strike > 0:
            return (
                f"Enter the long call at {trade.long_strike:,.2f} and the short call at {trade.strike:,.2f}. "
                f"Target net debit is {_money(trade.debit)}."
            )

        return "Entry pending: select both call legs before placing the trade."

    return "Entry plan pending for this strategy."


def build_exit_plan(trade: TradeModel) -> str:
    strategy = trade.active_strategy()

    if strategy == "Cash-Secured Put":
        profit_target = trade.max_profit * 0.50 if trade.max_profit else 0.0

        if profit_target > 0:
            return (
                f"Consider closing at approximately 50% of max profit "
                f"({_money(profit_target)}) or before expiration risk increases."
            )

        return "Exit pending: calculate max profit first."

    if strategy == "Bull Call Spread":
        if trade.max_profit > 0:
            return (
                f"Consider taking profits if the spread reaches roughly 50% to 75% of max profit "
                f"({_money(trade.max_profit * 0.50)} to {_money(trade.max_profit * 0.75)})."
            )

        return "Exit pending: calculate spread profit first."

    return "Exit plan pending for this strategy."


def build_adjustment_plan(trade: TradeModel) -> str:
    strategy = trade.active_strategy()

    if strategy == "Bull Call Spread":
        return (
            "If momentum fades before target progression, consider reducing exposure or closing the spread early. "
            "Avoid widening risk beyond the original defined-risk structure."
        )

    if strategy == "Cash-Secured Put":
        return "If premium deteriorates or risk changes materially, reassess strike selection and assignment tolerance before adjustment."

    return "Adjustment plan placeholder: strategy-specific rules will be published with OMS integration."


def build_assignment_plan(trade: TradeModel) -> str:
    strategy = trade.active_strategy()
    symbol = trade.symbol or "the underlying"

    if strategy == "Cash-Secured Put":
        if trade.breakeven > 0:
            return (
                f"If assigned, effective share cost is approximately "
                f"{_money(trade.breakeven)} before commissions/fees. "
                f"Confirm that owning {symbol} fits portfolio allocation before accepting assignment."
            )

        return "Assignment plan pending: calculate breakeven first."

    if strategy == "Bull Call Spread":
        return (
            f"No stock assignment plan is needed for a defined-risk Bull Call Spread. "
            f"If the long call finishes in the money, manage or close the spread before expiration."
        )

    return "Assignment plan pending for this strategy."


def build_risk_notes(trade: TradeModel) -> str:
    strategy = trade.active_strategy()
    notes = [
        "Options involve risk and can lose money.",
        "Validate liquidity, earnings date, position size, and capital requirements before execution.",
    ]

    if strategy == "Bull Call Spread":
        notes.extend(
            [
                "Bull Call Spread risk is predefined and limited to the net debit paid.",
                "Maximum profit is realized if the stock closes at or above the short strike at expiration.",
                "No stock ownership is required to open this trade.",
            ]
        )
    else:
        notes.extend(
            [
                "Assignment is not a loss event by itself.",
                "Assignment simply converts the option position into stock ownership.",
                "Future profit or loss then depends on how the stock performs after assignment.",
            ]
        )

    if trade.approval_status:
        notes.append(f"Current approval status: {trade.approval_status}.")

    if trade.warnings:
        notes.append("Commander warnings: " + " | ".join(trade.warnings))

    return "\n".join(notes)


def build_execution_ticket(trade: TradeModel) -> dict:
    """
    Returns a complete execution package as plain text sections.
    """

    return {
        "order_summary": build_order_summary(trade),
        "entry_orders": build_entry_plan(trade),
        "profit_target": build_exit_plan(trade),
        "exit_rules": build_exit_plan(trade),
        "adjustment_plan": build_adjustment_plan(trade),
        "assignment_exercise_notes": build_assignment_plan(trade),
        "risk_notes": build_risk_notes(trade),
    }
