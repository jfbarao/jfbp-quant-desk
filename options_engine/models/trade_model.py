from dataclasses import dataclass, field
from datetime import date


@dataclass
class TradeModel:
    """
    TradeModel v2

    Central decision object for the Options Trade Construction Center.

    This model is intentionally broader than option math. It carries the
    mission, market context, account context, strategy selection, construction
    inputs, calculated outputs, validation status, and execution notes.
    """

    # ========================================================
    # Mission / Objective
    # ========================================================

    mission: str = ""
    objective: str = ""
    risk_profile: str = ""
    time_horizon: str = ""

    # ========================================================
    # Market / Opportunity Context
    # ========================================================

    symbol: str = ""
    stock_price: float = 0.0
    market_bias: str = ""
    trend: str = ""
    volatility_rank: float = 0.0
    iv_percentile: float = 0.0
    expected_move: float = 0.0
    earnings_date: date | None = None
    dividend_date: date | None = None

    # ========================================================
    # Account / Portfolio Context
    # ========================================================

    account_type: str = ""
    account_size: float = 0.0
    buying_power: float = 0.0
    max_risk_allowed: float = 0.0
    existing_shares: int = 0
    portfolio_allocation: float = 0.0

    # ========================================================
    # Strategy Selection
    # ========================================================

    recommended_strategy: str = ""
    user_selected_strategy: str = ""
    strategy: str = ""

    strategy_confidence: float = 0.0
    strategy_reason: str = ""

    # ========================================================
    # Trade Construction Inputs
    # ========================================================

    expiration: date | None = None
    contracts: int = 1

    strike: float = 0.0
    long_strike: float = 0.0

    premium: float = 0.0
    long_premium: float = 0.0

    # ========================================================
    # Calculated Results
    # ========================================================

    credit: float = 0.0
    debit: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    breakeven: float = 0.0
    roi: float = 0.0
    annualized_return: float = 0.0
    reward_risk_ratio: float = 0.0
    buying_power_required: float = 0.0

    # ========================================================
    # Validation / Approval
    # ========================================================

    construction_complete: bool = False
    validation_status: str = "Pending"
    approval_status: str = "Pending"
    institutional_grade: str = ""
    confidence_score: float = 0.0

    validation_messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # ========================================================
    # Execution Plan
    # ========================================================

    entry_plan: str = ""
    exit_plan: str = ""
    assignment_plan: str = ""
    risk_notes: str = ""
    notes: str = ""

    # ========================================================
    # Convenience Helpers
    # ========================================================

    def active_strategy(self) -> str:
        """
        Returns the strategy currently being constructed.
        User selection takes priority over recommendation.
        """
        return self.user_selected_strategy or self.strategy or self.recommended_strategy

    def has_symbol(self) -> bool:
        return bool(self.symbol.strip())

    def has_strategy(self) -> bool:
        return bool(self.active_strategy())

    def reset_results(self) -> None:
        """
        Clears calculated outputs without erasing the trade setup.
        """
        self.credit = 0.0
        self.debit = 0.0
        self.max_profit = 0.0
        self.max_loss = 0.0
        self.breakeven = 0.0
        self.roi = 0.0
        self.annualized_return = 0.0
        self.reward_risk_ratio = 0.0
        self.buying_power_required = 0.0

    def reset_validation(self) -> None:
        """
        Clears validation and approval outputs.
        """
        self.validation_status = "Pending"
        self.approval_status = "Pending"
        self.institutional_grade = ""
        self.confidence_score = 0.0
        self.validation_messages.clear()
        self.warnings.clear()