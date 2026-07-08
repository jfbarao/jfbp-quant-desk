import streamlit as st
import html
import textwrap
import os
from dataclasses import dataclass, replace
from typing import Any, Protocol

try:
    import yfinance as yf
except Exception:
    yf = None

try:
    from options_engine.trade_lifecycle_packet import TradeLifecyclePacket, TradeStage, run_shared_trade_lifecycle_engines
except Exception:
    TradeLifecyclePacket = None
    TradeStage = None
    run_shared_trade_lifecycle_engines = None
from datetime import date, datetime, timedelta, timezone

from options_engine.constants import (
    PAGE_TITLE,
    PAGE_ICON,
    APPROVAL_OPTIONS,
    PENDING_TEXT,
)
from options_engine.registry.strategy_registry import STRATEGY_REGISTRY
from options_engine.state.trade_state import get_trade
from options_engine.ui.ui_helpers import (
    section_header,
    status_pill,
    strategy_card,
)
from options_engine.calculators import calculate_trade
from options_engine.recommendation_engine import recommend_strategy
from options_engine.validators import validate_trade, get_validation_checks
from options_engine.approval_engine import approve_trade, approval_reason
from options_engine.execution_ticket import build_execution_ticket
from options_engine.decision_packet import (
    clear_packet_from_session,
)


st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
)


BEGINNER_MODE_KEY = "otcc_beginner_mode"
OPTION_CHAIN_PANEL_OPEN_KEY = "otcc_option_chain_panel_open"
SELECTOR_OPEN_KEY = "otcc_selector_open"
CONTRACT_SELECTION_ACTIVE_KEY = "otcc_contract_selection_active"
CHAIN_MODE_KEY = "otcc_chain_mode"
OPTION_CHAIN_CACHE_KEY = "otcc_option_chain"
CHAIN_KEY_STATE = "otcc_chain_key"
SELECTED_CHAIN_KEY_STATE = "otcc_selected_chain_key"
GENERATED_STRIKES_KEY = "otcc_generated_strikes"
CHAIN_TRACE_KEY = "otcc_chain_trace"
ACTIVE_KEY_STATE = "otcc_active_key"
SELECTED_CONTRACT_KEY = "otcc_selected_option_contract"
DISCOVERY_MODE_KEY = "otcc_discovery_mode"
STEP4_VALUE_SOURCE_KEY = "otcc_step4_value_source"
CONSTRUCTION_CONTEXT_KEY = "otcc_construction_context"
STEP5_VALIDATION_COMPLETE_KEY = "otcc_step5_validation_complete"
STEP5_VALIDATION_STATUS_KEY = "otcc_step5_validation_status"
OTCC_CONSTRUCTION_COMPLETE_KEY = "otcc_construction_complete"
OTCC_VALIDATION_COMPLETE_KEY = "otcc_validation_complete"
PRICE_CACHE_KEY = "otcc_price_cache"
OTCC_TEMP_UNAVAILABLE_MESSAGE = "Options Decision Center is currently undergoing enhancements and is temporarily unavailable. It will return in a future update."


def _otcc_dev_access_enabled() -> bool:
    flag = str(os.getenv("OTCC_ENABLE_DEV_ACCESS", "")).strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True

    try:
        query_flag = str(st.query_params.get("otcc_dev", "")).strip().lower()
    except Exception:
        query_flag = ""
    return query_flag in {"1", "true", "yes", "on"}


def _render_otcc_temporarily_unavailable() -> None:
    st.title(f"{PAGE_ICON} Options Decision Center")
    st.warning(f"**{OTCC_TEMP_UNAVAILABLE_MESSAGE}**")
    st.stop()


BEGINNER_GLOSSARY_TABLE = """
| Term | Meaning |
|---|---|
| Underlying | The stock or ETF |
| Strike | Price where shares may be bought or sold |
| Premium | Money paid or received for the option |
| Assignment | When the option obligation is triggered |
| Expiration | Final day of the option contract |
| Contract | Controls 100 shares |
| DTE | Days to expiration |
| Buying Power | Cash reserved by the broker |
| Break-even | Stock price where profit becomes zero |
| ROI | Return on invested capital |
"""


STRATEGY_LESSONS: dict[str, dict[str, str]] = {
    "Cash-Secured Put": {
        "title": "🎓 Strategy Lesson — Cash-Secured Put",
        "content": """
### What this strategy is

A **Cash-Secured Put** is an options strategy used to generate income while potentially buying a stock you already want to own.

You receive premium immediately, and in exchange you agree to buy 100 shares if the stock finishes below your selected strike price at expiration.

### Why JFBP Quant Desk recommended it

The Quant Engine determined that this opportunity satisfies the institutional conditions for a Cash-Secured Put.

The recommendation considers multiple factors, including:

- Market trend
- Relative strength
- Market regime
- Institutional quality
- Risk profile
- Option suitability

**You do not need to decide which strategy to use - the platform has already selected the most appropriate strategy for this opportunity.**

### Your role

The Options Decision Center is an **institutional trade review system**, not an option-chain scanner.

Your job is to:

1. Review the recommended strategy.
2. Select the option contract you prefer.
3. Verify the live calculations.
4. Review the institutional analysis.
5. Approve the trade if it meets your standards.

### What you may customize

If you wish, you may choose a different option contract by changing:

- Strike Price
- Expiration Date
- Number of Contracts

As live option-chain integration expands, the platform will automatically update premiums and trade calculations whenever a different contract is selected.

### What JFBP Quant Desk calculates automatically

Once a contract is selected, the platform automatically calculates:

- Premium Collected
- Buying Power Required
- Break-even Price
- Maximum Profit
- Maximum Loss
- Return on Investment (ROI)
- Annualized Return
- Reward / Risk
- Institutional Readiness Score

All calculations update instantly whenever the selected contract changes.

### Understanding the Risk

A Cash-Secured Put does **not** create unlimited option risk.

If the option expires worthless, you simply keep the premium.

If the option is assigned, you purchase the shares at the strike price.

From that point forward, your risk is identical to owning the stock.

The Maximum Loss shown by the platform assumes the worst theoretical case in which the company becomes worthless after assignment.

### Main risk

If the stock closes below your strike price at expiration, you may be assigned and required to purchase **100 shares per contract**.

### Beginner Tip

Think of this page as an **Institutional Trade Review**.

The Quant Engine has already done the difficult work of identifying the opportunity and recommending the appropriate strategy.

Your responsibility is to understand the recommendation, review the numbers, and decide whether to execute the trade.
""",
    },
    "Covered Call": {
        "title": "🎓 Strategy Lesson — Covered Call",
        "content": """
### What this strategy is

You sell a call option against shares you already own and collect premium.

### When traders use it

- Generate income on existing shares.
- Set a planned exit level if shares are called away.

### Required fields

- Short Strike
- Short Premium
- Expiration
- Contracts

### Which fields are not used

- Long Strike / Protection Strike = 0
- Long Premium = 0

### What the user enters

- Short Strike above or near intended sale price
- Short Premium from the option chain
- Expiration and Contracts

### What the engine calculates

- Credit
- Buying Power impact
- Max Profit / Max Loss estimates
- Break-even
- ROI / Annualized Return

### Main risk

Shares may be called away if price rises above strike by expiration.

### Beginner warning

Only use this if you own 100 shares per contract.

> The platform recommends the strategy. The user does not need to choose from all option types manually.
""",
    },
    "Long Call": {
        "title": "🎓 Strategy Lesson — Long Call",
        "content": """
### What this strategy is

You buy a call option to participate in upside with limited risk.

### When traders use it

- Bullish directional view.
- Seeking leveraged upside with predefined risk.

### Required fields

- Strike (mapped to Short Strike for now)
- Premium paid (mapped to Short Premium for now)
- Expiration
- Contracts

### Which fields are not used

- Long Strike / Protection Strike (not used in current shared-entry mapping)
- Long Premium (not used in current shared-entry mapping)

### What the user enters

- Selected strike and premium from broker chain
- Expiration and contracts

### What the engine calculates

- Cost basis and position sizing outputs
- Max profit/loss framework, break-even, ROI, annualized return

### Main risk

Maximum loss is typically the premium paid.

### Beginner warning

Current construction fields are shared across strategies. Future UI will rename fields dynamically.

> The platform recommends the strategy. The user does not need to choose from all option types manually.
""",
    },
    "Long Put": {
        "title": "🎓 Strategy Lesson — Long Put",
        "content": """
### What this strategy is

You buy a put option for bearish positioning or portfolio protection.

### When traders use it

- Bearish directional view.
- Hedging downside on shares or portfolio exposure.

### Required fields

- Strike (mapped to Short Strike for now)
- Premium paid (mapped to Short Premium for now)
- Expiration
- Contracts

### Which fields are not used

- Long Strike / Protection Strike (not used in current shared-entry mapping)
- Long Premium (not used in current shared-entry mapping)

### What the user enters

- Selected put strike and premium from broker chain
- Expiration and contracts

### What the engine calculates

- Position economics, break-even, ROI, annualized return, and risk framework

### Main risk

Maximum loss is typically the premium paid.

### Beginner warning

Current construction fields are shared across strategies. Future UI will rename fields dynamically.

> The platform recommends the strategy. The user does not need to choose from all option types manually.
""",
    },
    "Bull Put Spread": {
        "title": "🎓 Strategy Lesson — Bull Put Spread",
        "content": """
### What this strategy is

Credit spread: sell a higher-strike put and buy a lower-strike put for protection.

### When traders use it

- Bullish to neutral outlook.
- Income with defined downside risk.

### Required fields

- Short Strike = sold put strike
- Short Premium = premium received
- Long Strike / Protection Strike = bought put strike
- Long Premium = premium paid
- Expiration
- Contracts

### Which fields are not used

- None of the core spread fields are skipped.

### What the user enters

- Both strikes, both premiums, expiration, contracts

### What the engine calculates

- Net credit, max profit, max loss, break-even, ROI, annualized return

### Main risk

Loss occurs if price declines through the short strike; risk is capped by long put.

### Beginner warning

Ensure strike ordering is correct: short put strike should be above protection strike.

> The platform recommends the strategy. The user does not need to choose from all option types manually.
""",
    },
    "Bear Put Spread": {
        "title": "🎓 Strategy Lesson — Bear Put Spread",
        "content": """
### What this strategy is

Debit spread: buy a higher-strike put and sell a lower-strike put.

### When traders use it

- Bearish outlook with defined risk and defined reward cap.

### Required fields

- Long Strike / Protection Strike = bought put strike
- Long Premium = premium paid
- Short Strike = sold put strike
- Short Premium = premium received
- Expiration
- Contracts

### Which fields are not used

- None of the core spread fields are skipped.

### What the user enters

- Both strikes, both premiums, expiration, contracts

### What the engine calculates

- Net debit, max profit, max loss, break-even, ROI, annualized return

### Main risk

If move is too small or late, debit paid can decay in value before expiration.

### Beginner warning

Confirm strike ordering and net debit assumptions before approval.

> The platform recommends the strategy. The user does not need to choose from all option types manually.
""",
    },
    "Bull Call Spread": {
        "title": "🎓 Strategy Lesson — Bull Call Spread",
        "content": """
### Strategy Overview

Bull Call Spread is a **defined-risk debit spread**:

- Buy a lower-strike call
- Sell a higher-strike call

Use this when you are bullish but want controlled downside and lower capital than a standalone long call.

### Maximum Profit

Occurs when stock closes at or above the short strike at expiration.

- Formula: `(short strike - long strike - net debit) * 100 * contracts`

### Maximum Loss

Risk is predefined and limited to the net debit paid.

- Formula: `net debit * 100 * contracts`

### Breakeven

Breakeven at expiration is long strike plus net debit.

- Formula: `long strike + net debit`

### When to Exit

- Take gains as spread approaches target value.
- Reduce exposure if momentum weakens before expected move develops.
- Avoid holding low-liquidity spreads into expiration without a plan.

### Common Mistakes

- Reversing leg order (short strike below long strike).
- Entering with unrealistic time to expiration for expected move.
- Ignoring bid/ask spread and assuming midpoint always fills.
- Treating annualized return as a guaranteed realized return.

> The platform recommends the strategy. The user does not need to choose from all option types manually.
""",
    },
    "Bear Call Spread": {
        "title": "🎓 Strategy Lesson — Bear Call Spread",
        "content": """
### What this strategy is

Credit spread: sell a lower-strike call and buy a higher-strike call for protection.

### When traders use it

- Bearish to neutral outlook with defined risk.

### Required fields

- Short Strike = sold call strike
- Short Premium = premium received
- Long Strike / Protection Strike = bought call strike
- Long Premium = premium paid
- Expiration
- Contracts

### Which fields are not used

- None of the core spread fields are skipped.

### What the user enters

- Both call strikes, both premiums, expiration, contracts

### What the engine calculates

- Net credit, max profit, max loss, break-even, ROI, annualized return

### Main risk

Loss grows if price rallies through short strike; long call caps worst-case loss.

### Beginner warning

Credit spreads can lose quickly during sharp upside moves; size conservatively.

> The platform recommends the strategy. The user does not need to choose from all option types manually.
""",
    },
}


# ============================================================
# Institutional Option Chain Framework (Phase 1)
# ============================================================

@dataclass
class OptionContract:
    underlying: str
    expiration: date
    strike: float
    bid: float
    ask: float
    mid: float
    last: float
    delta: float
    gamma: float
    theta: float
    vega: float
    iv: float
    volume: int
    open_interest: int
    pop: float
    expected_return: float
    annualized_return: float
    institutional_score: float
    preferred: bool
    confidence: float
    contract_type: str = "Put"
    contracts: int = 1

    @property
    def contract_label(self) -> str:
        return f"{self.strike:g} {self.contract_type}"


class OptionChainProvider(Protocol):
    """Provider abstraction for options chain sourcing.

    Future hook (not implemented in Phase 1):
    When an IBKR/Tradier/Polygon/ORATS provider is active, fetch live chains
    through this contract and keep Trade Construction provider-agnostic.
    Supported future implementations can include: IBKR, Tradier, Polygon,
    ORATS, and Manual Entry providers.
    """

    def get_option_chain(
        self,
        underlying: str,
        strategy: str,
        reference_price: float = 0.0,
        requested_expiration: Any = None,
    ) -> list[OptionContract]:
        ...


def strategy_option_chain_type(strategy: str) -> str:
    strategy_key = str(strategy or "").strip()
    call_strategies = {"Covered Call", "Bull Call Spread", "Bear Call Spread", "Long Call"}
    put_strategies = {"Cash-Secured Put", "Bull Put Spread", "Bear Put Spread", "Long Put"}
    if strategy_key in call_strategies:
        return "CALLS"
    if strategy_key in put_strategies:
        return "PUTS"
    if "CALL" in strategy_key.upper():
        return "CALLS"
    return "PUTS"


def strategy_selected_leg_role(strategy: str) -> str:
    strategy_key = str(strategy or "").strip()
    long_first = {"Bull Call Spread", "Bear Put Spread", "Long Call", "Long Put"}
    if strategy_key in long_first:
        return "long"
    return "short"


def strategy_partner_leg_role(strategy: str) -> str | None:
    strategy_key = str(strategy or "").strip()
    if strategy_key in {"Bull Call Spread", "Bear Call Spread"}:
        return "higher"
    if strategy_key in {"Bull Put Spread", "Bear Put Spread"}:
        return "lower"
    return None


def _strategy_requires_second_leg(strategy: str) -> bool:
    return str(strategy or "").strip() in {"Bull Call Spread", "Bull Put Spread", "Bear Call Spread", "Bear Put Spread"}


def _is_selection_complete(strategy: str, selection: dict[str, Any]) -> bool:
    legs = selection.get("legs")
    if isinstance(legs, list) and legs:
        return len(legs) >= (2 if _strategy_requires_second_leg(strategy) else 1)
    if _strategy_requires_second_leg(strategy):
        return bool(selection.get("primary")) and bool(selection.get("secondary"))
    return bool(selection.get("primary")) or bool(selection.get("label"))


def _construction_context_key(trade) -> str:
    symbol = str(getattr(trade, "symbol", "") or "").strip().upper()
    strategy = str(getattr(trade, "active_strategy", lambda: "")() or getattr(trade, "recommended_strategy", "") or "").strip()
    expiration = str(getattr(trade, "expiration", "") or "")
    return f"{symbol}|{strategy}|{expiration}"


def reset_otcc_construction_state(trade=None, *, preserve_identity: bool = True) -> None:
    current_symbol = ""
    current_expiration = date.today()
    current_contracts = 1
    if trade is not None:
        try:
            if preserve_identity:
                current_symbol = str(getattr(trade, "symbol", "") or "").strip().upper()
                current_expiration = getattr(trade, "expiration", None) or date.today()
                current_contracts = int(getattr(trade, "contracts", 1) or 1)
            trade.legs.clear()
            trade.strike = 0.0
            trade.long_strike = 0.0
            trade.premium = 0.0
            trade.long_premium = 0.0
            trade.stock_price = 0.0
            trade.credit = 0.0
            trade.debit = 0.0
            trade.max_profit = 0.0
            trade.max_loss = 0.0
            trade.breakeven = 0.0
            trade.buying_power_required = 0.0
            trade.construction_complete = False
            trade.approval_status = PENDING_TEXT
            trade.reset_results()
            trade.reset_validation()
            if not preserve_identity:
                trade.symbol = ""
                trade.strategy = ""
                trade.user_selected_strategy = ""
                trade.recommended_strategy = ""
                trade.strategy_reason = ""
                trade.strategy_confidence = 0.0
                trade.institutional_grade = ""
                trade.mission = ""
                trade.objective = ""
                trade.market_bias = ""
                trade.expiration = date.today()
                trade.contracts = 1
        except Exception:
            pass

    # Selected opportunity / handoff / packet state.
    for key in [
        "construction_request",
        "recommendation_packet",
        "trade_lifecycle_packet",
        "trade_lifecycle_packet_memory",
        "decision_packet",
        "opportunity_packet",
        "options_decision_packet",
        "otcc_loaded_packet_fingerprint",
        "selected_symbol",
        "scanner_selected_symbol",
        "trade_command_symbol",
        "option_symbol",
        "trade_symbol",
        "opportunity_symbol",
        "active_symbol",
        "ticker",
        "symbol",
        "options_manual_symbol",
        "research_ticker",
    ]:
        st.session_state.pop(key, None)

    st.session_state[DISCOVERY_MODE_KEY] = True
    st.session_state["otcc_construction_dirty"] = False
    st.session_state.pop("otcc_selected_contract", None)
    st.session_state.pop(SELECTED_CONTRACT_KEY, None)
    st.session_state.pop("otcc_selected_long_leg", None)
    st.session_state.pop("otcc_selected_short_leg", None)
    st.session_state.pop("otcc_selected_put_leg", None)
    st.session_state.pop("otcc_selected_call_leg", None)
    st.session_state.pop("otcc_selected_contract_price", None)
    st.session_state.pop("otcc_selected_contract_premium", None)
    st.session_state.pop("otcc_selected_contract_strike", None)
    st.session_state.pop("otcc_recommendation_cards", None)
    st.session_state[OPTION_CHAIN_PANEL_OPEN_KEY] = False
    st.session_state[SELECTOR_OPEN_KEY] = False
    st.session_state.pop(CHAIN_MODE_KEY, None)
    st.session_state.pop(OPTION_CHAIN_CACHE_KEY, None)
    st.session_state.pop(CHAIN_KEY_STATE, None)
    st.session_state.pop(SELECTED_CHAIN_KEY_STATE, None)
    st.session_state.pop(GENERATED_STRIKES_KEY, None)
    st.session_state.pop(CHAIN_TRACE_KEY, None)
    st.session_state.pop(ACTIVE_KEY_STATE, None)
    if not preserve_identity:
        st.session_state.pop(CONTRACT_SELECTION_ACTIVE_KEY, None)
    st.session_state.pop(STEP4_VALUE_SOURCE_KEY, None)
    st.session_state.pop(CONSTRUCTION_CONTEXT_KEY, None)
    st.session_state[OTCC_CONSTRUCTION_COMPLETE_KEY] = False
    st.session_state[OTCC_VALIDATION_COMPLETE_KEY] = False
    st.session_state[STEP5_VALIDATION_COMPLETE_KEY] = False
    st.session_state[STEP5_VALIDATION_STATUS_KEY] = ""

    # Step 4 fields.
    st.session_state["otcc_short_strike"] = 0.0
    st.session_state["otcc_long_strike"] = 0.0
    st.session_state["otcc_short_premium"] = 0.0
    st.session_state["otcc_long_premium"] = 0.0
    st.session_state["short_strike"] = 0.0
    st.session_state["long_strike"] = 0.0
    st.session_state["short_premium"] = 0.0
    st.session_state["long_premium"] = 0.0

    # Step 4 math.
    st.session_state["net_debit"] = 0.0
    st.session_state["net_credit"] = 0.0
    st.session_state["max_profit"] = 0.0
    st.session_state["max_loss"] = 0.0
    st.session_state["breakeven"] = 0.0
    st.session_state["buying_power"] = 0.0
    st.session_state["otcc_net_debit"] = 0.0
    st.session_state["otcc_net_credit"] = 0.0
    st.session_state["otcc_max_profit"] = 0.0
    st.session_state["otcc_max_loss"] = 0.0
    st.session_state["otcc_breakeven"] = 0.0
    st.session_state["otcc_buying_power"] = 0.0

    # Validation / approval / execution packet mirrors.
    for key in [
        "approval",
        "approval_score",
        "approved",
        "approved_by",
        "approved_timestamp",
        "approval_notes",
        "execution_confidence",
        "institutional_decision",
        "institutional_decision_object",
        "otcc_decision_readiness_override",
        "otcc_decision_override",
        "trade_lifecycle_packet",
        "otcc_entry_plan",
        "otcc_profit_target",
        "otcc_exit_plan",
        "otcc_adjustment_plan",
        "otcc_assignment_plan",
        "otcc_risk_notes",
    ]:
        st.session_state.pop(key, None)

    for key in list(st.session_state.keys()):
        if key.startswith("otcc_approval_check_"):
            st.session_state.pop(key, None)

    if not preserve_identity:
        clear_packet_from_session(st.session_state)
        st.session_state["otcc_discovery_symbol"] = ""
        st.session_state["otcc_last_symbol_seen"] = ""
        st.session_state["otcc_last_strategy_seen"] = ""
        st.session_state["otcc_last_expiration_seen"] = ""

    st.session_state["otcc_construction_symbol_display"] = current_symbol
    st.session_state["otcc_expiration"] = current_expiration
    st.session_state["otcc_contracts"] = max(1, int(current_contracts or 1))


def _clear_construction_selection_state(trade) -> None:
    reset_otcc_construction_state(trade)


def _safe_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except Exception:
        return None
    if parsed <= 0:
        return None
    return parsed


def _normalize_expiration(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "").strip()


def _parse_expiration_candidate(value: Any) -> date | None:
    if isinstance(value, date):
        return value

    text = str(value or "").strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return date.fromisoformat(text)
    except Exception:
        return None


def _resolve_packet_expiration(packet: Any) -> date | None:
    field_names = (
        "expiration",
        "selected_expiration",
        "recommended_expiration",
        "target_expiration",
        "expiry",
        "expiration_date",
    )

    for field_name in field_names:
        parsed = _parse_expiration_candidate(getattr(packet, field_name, None))
        if parsed is not None:
            return parsed

    for section_name in ("construction", "identity", "opportunity"):
        section = getattr(packet, section_name, None)
        if section is None:
            continue
        for field_name in field_names:
            parsed = _parse_expiration_candidate(getattr(section, field_name, None))
            if parsed is not None:
                return parsed

    if isinstance(packet, dict):
        for field_name in field_names:
            parsed = _parse_expiration_candidate(packet.get(field_name))
            if parsed is not None:
                return parsed
        for section_name in ("construction", "identity", "opportunity"):
            section = packet.get(section_name)
            if not isinstance(section, dict):
                continue
            for field_name in field_names:
                parsed = _parse_expiration_candidate(section.get(field_name))
                if parsed is not None:
                    return parsed

    return None


def _active_construction_key(symbol: str, strategy: str, expiration: Any, stock_price: float) -> str:
    symbol_norm = str(symbol or "").strip().upper()
    strategy_norm = str(strategy or "").strip()
    expiration_norm = _normalize_expiration(expiration)
    return f"{symbol_norm}|{strategy_norm}|{expiration_norm}|{float(stock_price or 0.0):.2f}"


def _selected_contract_matches_context(selected: dict[str, Any], symbol: str, expiration: Any, strategy: str) -> bool:
    selected_symbol = str(selected.get("symbol") or "").strip().upper()
    selected_expiration = _normalize_expiration(selected.get("expiration"))
    selected_strategy = str(selected.get("strategy") or "").strip()
    current_symbol = str(symbol or "").strip().upper()
    current_expiration = _normalize_expiration(expiration)
    current_strategy = str(strategy or "").strip()
    return bool(
        selected_symbol
        and selected_symbol == current_symbol
        and selected_expiration
        and selected_expiration == current_expiration
        and selected_strategy
        and selected_strategy == current_strategy
    )


def _ensure_widget_default(key: str, default: Any) -> Any:
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def _resolve_packet_price(symbol: str) -> float | None:
    packet = st.session_state.get("trade_lifecycle_packet")
    if TradeLifecyclePacket is not None and not isinstance(packet, TradeLifecyclePacket):
        packet = TradeLifecyclePacket.from_session(st.session_state)
    if packet is None:
        return None

    packet_symbol = str(getattr(packet.identity, "symbol", "") or "").strip().upper()
    if packet_symbol and packet_symbol != symbol:
        return None

    return _safe_float(getattr(packet.identity, "stock_price", 0.0))


def _resolve_underlying_price(symbol: str) -> float | None:
    symbol = str(symbol or "").strip().upper()
    if not symbol:
        return None

    packet_price = _resolve_packet_price(symbol)
    if packet_price is not None:
        return round(packet_price, 2)

    cache = st.session_state.setdefault(PRICE_CACHE_KEY, {})
    if isinstance(cache, dict):
        cached = _safe_float(cache.get(symbol))
        if cached is not None:
            return round(cached, 2)

    if yf is None:
        return None

    try:
        ticker = yf.Ticker(symbol)
        fast = getattr(ticker, "fast_info", {}) or {}
        for candidate in [fast.get("lastPrice"), fast.get("regularMarketPrice"), fast.get("previousClose")]:
            quote_price = _safe_float(candidate)
            if quote_price is not None:
                cache[symbol] = float(quote_price)
                st.session_state[PRICE_CACHE_KEY] = cache
                return round(float(quote_price), 2)
        hist = ticker.history(period="1d", interval="1m")
        if hist is not None and not hist.empty and "Close" in hist.columns:
            quote_price = _safe_float(hist["Close"].dropna().iloc[-1])
            if quote_price is not None:
                cache[symbol] = float(quote_price)
                st.session_state[PRICE_CACHE_KEY] = cache
                return round(float(quote_price), 2)
    except Exception:
        return None
    return None


def _selected_leg_action(strategy_key: str, selected_role: str, leg_index: int) -> str:
    if strategy_key in {"Long Call", "Long Put"}:
        return "BUY"
    if strategy_key in {"Cash-Secured Put", "Covered Call"}:
        return "SELL"
    if strategy_key in {"Bull Call Spread"}:
        return "BUY" if leg_index == 0 else "SELL"
    if strategy_key in {"Bull Put Spread", "Bear Call Spread"}:
        return "SELL" if leg_index == 0 else "BUY"
    if strategy_key == "Bear Put Spread":
        return "SELL" if leg_index == 0 else "BUY"
    return "BUY" if selected_role == "long" else "SELL"


def _selected_leg_option_type(strategy_key: str, contract: OptionContract) -> str:
    contract_type = str(getattr(contract, "contract_type", "") or "").upper().strip()
    if contract_type in {"CALL", "PUT"}:
        return contract_type
    if strategy_key in {"Long Put", "Cash-Secured Put", "Bull Put Spread", "Bear Put Spread"}:
        return "PUT"
    return "CALL"


def _contract_leg_payload(contract: OptionContract, strategy_key: str, leg_index: int) -> dict[str, Any]:
    action = _selected_leg_action(strategy_key, strategy_selected_leg_role(strategy_key), leg_index)
    option_type = _selected_leg_option_type(strategy_key, contract)
    return {
        "side": action,
        "option_type": option_type,
        "strike": float(getattr(contract, "strike", 0.0) or 0.0),
        "premium": float(getattr(contract, "mid", 0.0) or 0.0),
        "expiration": getattr(contract, "expiration", None),
        "contract_id": getattr(contract, "contract_label", None) or getattr(contract, "contract_id", None) or "",
        "quantity": int(getattr(contract, "contracts", 1) or 1),
    }


def _apply_trade_legs(trade, strategy_key: str, selected_contract: OptionContract, available_contracts: list[OptionContract] | None = None) -> None:
    legs: list[dict[str, Any]] = list(getattr(trade, "legs", []) or [])
    leg_index = len(legs)
    if _strategy_requires_second_leg(strategy_key) and leg_index >= 2:
        legs = []
        leg_index = 0

    primary_leg = _contract_leg_payload(selected_contract, strategy_key, leg_index)
    legs.append(primary_leg)

    if _strategy_requires_second_leg(strategy_key) and len(legs) == 1 and available_contracts:
        partner_contract = _find_partner_contract(available_contracts, selected_contract, strategy_key)
        if partner_contract is not None:
            legs.append(_contract_leg_payload(partner_contract, strategy_key, 1))

    trade.legs = legs
    trade.construction_complete = _is_selection_complete(strategy_key, {"legs": legs})


def _build_mock_chain_contracts(symbol: str, option_chain_type: str, stock_price: float, base_expiration: date) -> list[OptionContract]:
    increment = 2.5 if stock_price < 100 else 5.0
    center = round(stock_price / increment) * increment
    strikes = [round(center + (i * increment), 2) for i in range(-2, 3)]
    contract_type = "Call" if option_chain_type == "CALLS" else "Put"

    contracts: list[OptionContract] = []
    for strike in strikes:
        distance = abs(strike - stock_price)
        intrinsic = max(stock_price - strike, 0.0) if contract_type == "Call" else max(strike - stock_price, 0.0)
        time_value = max(0.35, 5.5 / (1.0 + distance / max(increment, 0.1)))
        mid = round(max(intrinsic + time_value, 0.15), 2)
        bid = round(max(mid - 0.1, 0.01), 2)
        ask = round(mid + 0.1, 2)
        last = round(mid * 0.99, 2)
        delta_base = 0.5 + (stock_price - strike) / (12.0 * increment)
        delta = round(max(min(delta_base, 0.95), 0.05), 2)
        if contract_type == "Put":
            delta = -delta
        gamma = round(0.015 + distance / 10000.0, 3)
        theta = round(-0.025 - distance / 2000.0, 3)
        vega = round(0.09 + distance / 1200.0, 3)
        iv = round(0.18 + distance / 800.0, 2)
        volume = int(max(75, 1200 - distance * 15))
        open_interest = int(max(150, 9000 - distance * 35))
        pop = round(max(20.0, 90.0 - distance * 1.5), 1)
        expected_return = round(max(1.0, 8.0 - distance * 0.12), 1)
        annualized_return = round(max(5.0, 24.0 - distance * 0.5), 1)
        institutional_score = round(max(55.0, 98.0 - distance * 0.8 + (open_interest / 10000.0)), 1)
        preferred = distance <= increment
        confidence = round(max(60.0, 96.0 - distance * 0.9), 1)

        contracts.append(
            OptionContract(
                underlying=symbol,
                expiration=base_expiration,
                strike=strike,
                bid=bid,
                ask=ask,
                mid=mid,
                last=last,
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                iv=iv,
                volume=volume,
                open_interest=open_interest,
                pop=pop,
                expected_return=expected_return,
                annualized_return=annualized_return,
                institutional_score=institutional_score,
                preferred=preferred,
                confidence=confidence,
                contract_type=contract_type,
            )
        )

    return contracts


class MockOptionChainProvider:
    def get_option_chain(
        self,
        underlying: str,
        strategy: str,
        reference_price: float = 0.0,
        requested_expiration: Any = None,
    ) -> list[OptionContract]:
        if isinstance(requested_expiration, date):
            base_expiration = requested_expiration
        else:
            base_expiration = date.today() + timedelta(days=21)
        symbol = (underlying or "AAPL").strip().upper()
        chain_type = strategy_option_chain_type(strategy)
        if reference_price > 0:
            stock_price = float(reference_price)
        else:
            return []
        contracts = _build_mock_chain_contracts(symbol, chain_type, stock_price, base_expiration)
        st.session_state[CHAIN_TRACE_KEY] = {
            "requested_symbol": symbol,
            "requested_expiration": _normalize_expiration(base_expiration),
            "current_stock_price": round(stock_price, 2),
            "generated_strikes": [float(getattr(contract, "strike", 0.0) or 0.0) for contract in contracts],
        }
        return contracts


class InstitutionalRankingEngine:
    def rank_contracts(self, contracts: list[OptionContract]) -> list[OptionContract]:
        return sorted(
            contracts,
            key=lambda c: (
                int(c.preferred),
                c.institutional_score,
                c.confidence,
                c.pop,
                c.annualized_return,
            ),
            reverse=True,
        )


def get_option_chain_provider() -> OptionChainProvider:
    # Phase 1: fixed provider for localhost workflow validation.
    return MockOptionChainProvider()


def get_ranked_option_chain(
    underlying: str,
    strategy: str,
    reference_price: float = 0.0,
    requested_expiration: Any = None,
) -> list[OptionContract]:
    provider = get_option_chain_provider()
    contracts = provider.get_option_chain(
        underlying,
        strategy,
        reference_price=reference_price,
        requested_expiration=requested_expiration,
    )
    ranking_engine = InstitutionalRankingEngine()
    return ranking_engine.rank_contracts(contracts)


def contract_tier_badge(contract: OptionContract) -> str:
    if contract.preferred or contract.institutional_score >= 97:
        return "★★★★★ Preferred"
    if contract.institutional_score >= 93:
        return "★★★★ Conservative"
    return "★★★ Aggressive"


def _find_partner_contract(contracts: list[OptionContract], selected: OptionContract, strategy: str) -> OptionContract | None:
    selected_type = str(getattr(selected, "contract_type", "") or "").strip()
    selected_strike = float(getattr(selected, "strike", 0.0) or 0.0)
    if not selected_type or selected_strike <= 0:
        return None

    partner_direction = strategy_partner_leg_role(strategy)
    same_type_contracts = [c for c in contracts if str(getattr(c, "contract_type", "") or "").strip() == selected_type and float(getattr(c, "strike", 0.0) or 0.0) != selected_strike]
    if partner_direction == "long" or partner_direction == "higher":
        candidates = [c for c in same_type_contracts if float(getattr(c, "strike", 0.0) or 0.0) > selected_strike]
        if candidates:
            return min(candidates, key=lambda c: float(getattr(c, "strike", 0.0) or 0.0))
    if partner_direction == "short" or partner_direction == "lower":
        candidates = [c for c in same_type_contracts if float(getattr(c, "strike", 0.0) or 0.0) < selected_strike]
        if candidates:
            return max(candidates, key=lambda c: float(getattr(c, "strike", 0.0) or 0.0))
    return None


def apply_option_contract_to_trade(trade, contract: OptionContract, strategy: str, available_contracts: list[OptionContract] | None = None) -> None:
    strategy_key = str(strategy or trade.active_strategy() or trade.recommended_strategy or "").strip()
    context_fingerprint = _construction_context_key(trade)
    previous_context = str(st.session_state.get(CONSTRUCTION_CONTEXT_KEY, "") or "")
    if context_fingerprint != previous_context:
        _clear_construction_selection_state(trade)
        st.session_state[CONSTRUCTION_CONTEXT_KEY] = context_fingerprint

    trade.symbol = contract.underlying
    trade.expiration = contract.expiration
    trade.contracts = int(contract.contracts or 1)
    trade.legs = list(getattr(trade, "legs", []) or [])
    _apply_trade_legs(trade, strategy_key, contract, available_contracts)

    trade.strike = 0.0
    trade.long_strike = 0.0
    trade.premium = 0.0
    trade.long_premium = 0.0

    legs = list(getattr(trade, "legs", []) or [])
    buy_leg = next((leg for leg in legs if str(leg.get("side") or "").upper() == "BUY"), None)
    sell_leg = next((leg for leg in legs if str(leg.get("side") or "").upper() == "SELL"), None)

    if buy_leg and sell_leg:
        trade.long_strike = float(buy_leg.get("strike", 0.0) or 0.0)
        trade.long_premium = float(buy_leg.get("premium", 0.0) or 0.0)
        trade.strike = float(sell_leg.get("strike", 0.0) or 0.0)
        trade.premium = float(sell_leg.get("premium", 0.0) or 0.0)
    elif buy_leg:
        trade.long_strike = float(buy_leg.get("strike", 0.0) or 0.0)
        trade.long_premium = float(buy_leg.get("premium", 0.0) or 0.0)
        trade.strike = float(buy_leg.get("strike", 0.0) or 0.0)
        trade.premium = float(buy_leg.get("premium", 0.0) or 0.0)
    elif sell_leg:
        trade.strike = float(sell_leg.get("strike", 0.0) or 0.0)
        trade.premium = float(sell_leg.get("premium", 0.0) or 0.0)

    st.session_state["otcc_construction_symbol_display"] = trade.symbol
    st.session_state["otcc_expiration"] = trade.expiration
    st.session_state["otcc_short_strike"] = trade.strike
    st.session_state["otcc_short_premium"] = trade.premium
    st.session_state["otcc_long_strike"] = trade.long_strike
    st.session_state["otcc_long_premium"] = trade.long_premium
    st.session_state["otcc_contracts"] = trade.contracts
    st.session_state[SELECTED_CONTRACT_KEY] = {
        "label": contract.contract_label,
        "tier": contract_tier_badge(contract),
        "score": contract.institutional_score,
        "confidence": contract.confidence,
        "pop": contract.pop,
        "annualized": contract.annualized_return,
        "symbol": trade.symbol,
        "strategy": strategy_key,
        "expiration": trade.expiration,
        "short_strike": trade.strike,
        "short_premium": trade.premium,
        "option_type": str(getattr(contract, "contract_type", "") or "").strip(),
        "long_strike": trade.long_strike,
        "long_premium": trade.long_premium,
        "legs": list(getattr(trade, "legs", []) or []),
        "has_long_leg": bool(buy_leg),
        "has_short_leg": bool(sell_leg),
    }
    st.session_state[SELECTED_CHAIN_KEY_STATE] = str(st.session_state.get(CHAIN_KEY_STATE, "") or "")
    st.session_state["otcc_construction_dirty"] = True

    trade.construction_complete = _is_selection_complete(strategy_key, st.session_state[SELECTED_CONTRACT_KEY])
    st.session_state[OTCC_CONSTRUCTION_COMPLETE_KEY] = trade.construction_complete
    if trade.construction_complete:
        st.session_state[OPTION_CHAIN_PANEL_OPEN_KEY] = False


def sync_trade_from_construction_state(trade) -> None:
    """Synchronize canonical trade inputs from Step 4 widget state before calculations."""
    current_strategy = str(trade.active_strategy() or trade.recommended_strategy or "").strip()
    selected = st.session_state.get(SELECTED_CONTRACT_KEY)
    if isinstance(selected, dict) and selected.get("label"):
        if not _selected_contract_matches_context(selected, trade.symbol, trade.expiration, current_strategy):
            st.session_state.pop(SELECTED_CONTRACT_KEY, None)
            st.session_state["otcc_short_strike"] = 0.0
            st.session_state["otcc_short_premium"] = 0.0
            st.session_state["otcc_long_strike"] = 0.0
            st.session_state["otcc_long_premium"] = 0.0
            st.session_state[STEP4_VALUE_SOURCE_KEY] = "selected_contract_discarded_context_mismatch"
            selected = None
    if isinstance(selected, dict) and selected.get("label"):
        st.session_state[STEP4_VALUE_SOURCE_KEY] = "selected_contract"
        trade.symbol = str(selected.get("symbol") or trade.symbol or "").strip().upper()
        trade.expiration = selected.get("expiration") if selected.get("expiration") is not None else st.session_state.get("otcc_expiration", trade.expiration)
        trade.contracts = max(1, int(st.session_state.get("otcc_contracts", trade.contracts) or 1))

        legs = list(selected.get("legs") or getattr(trade, "legs", []) or [])
        if legs:
            trade.legs = legs
            buy_leg = next((leg for leg in legs if str(leg.get("side") or "").upper() == "BUY"), None)
            sell_leg = next((leg for leg in legs if str(leg.get("side") or "").upper() == "SELL"), None)
            if buy_leg and sell_leg:
                trade.long_strike = float(buy_leg.get("strike", 0.0) or 0.0)
                trade.long_premium = float(buy_leg.get("premium", 0.0) or 0.0)
                trade.strike = float(sell_leg.get("strike", 0.0) or 0.0)
                trade.premium = float(sell_leg.get("premium", 0.0) or 0.0)
            elif buy_leg:
                trade.long_strike = float(buy_leg.get("strike", 0.0) or 0.0)
                trade.long_premium = float(buy_leg.get("premium", 0.0) or 0.0)
                trade.strike = 0.0
                trade.premium = 0.0
            elif sell_leg:
                trade.strike = float(sell_leg.get("strike", 0.0) or 0.0)
                trade.premium = float(sell_leg.get("premium", 0.0) or 0.0)
                trade.long_strike = 0.0
                trade.long_premium = 0.0
        else:
            trade.strike = float(selected.get("short_strike", trade.strike) or 0.0)
            trade.premium = float(selected.get("short_premium", trade.premium) or 0.0)
            trade.long_strike = float(selected.get("long_strike", st.session_state.get("otcc_long_strike", trade.long_strike)) or 0.0)
            trade.long_premium = float(selected.get("long_premium", st.session_state.get("otcc_long_premium", trade.long_premium)) or 0.0)
    else:
        st.session_state[STEP4_VALUE_SOURCE_KEY] = "step4_manual_fields"
        trade.symbol = str(st.session_state.get("otcc_construction_symbol_display", trade.symbol) or "").strip().upper()
        trade.expiration = st.session_state.get("otcc_expiration", trade.expiration)
        trade.strike = float(st.session_state.get("otcc_short_strike", trade.strike) or 0.0)
        trade.long_strike = float(st.session_state.get("otcc_long_strike", trade.long_strike) or 0.0)
        trade.premium = float(st.session_state.get("otcc_short_premium", trade.premium) or 0.0)
        trade.long_premium = float(st.session_state.get("otcc_long_premium", trade.long_premium) or 0.0)

    trade.contracts = max(1, int(st.session_state.get("otcc_contracts", trade.contracts) or 1))


def build_trade_math_snapshot(trade):
    """Build one canonical trade_math object from current Step 4 widget/session values."""
    sync_trade_from_construction_state(trade)
    trade_math = replace(trade)

    if _strategy_requires_second_leg(str(trade.active_strategy() or trade.recommended_strategy or "")) and len(getattr(trade_math, "legs", []) or []) < 2:
        trade_math.reset_results()
        trade_math.buying_power_required = 0.0
        trade_math.construction_complete = False
        trade.buying_power_required = 0.0
        trade.construction_complete = False
        return trade_math

    trade_math = calculate_trade(trade_math)

    # Keep canonical trade object aligned for downstream validation/approval steps.
    trade.credit = float(getattr(trade_math, "credit", 0.0) or 0.0)
    trade.debit = float(getattr(trade_math, "debit", 0.0) or 0.0)
    trade.max_profit = float(getattr(trade_math, "max_profit", 0.0) or 0.0)
    trade.max_loss = float(getattr(trade_math, "max_loss", 0.0) or 0.0)
    trade.breakeven = float(getattr(trade_math, "breakeven", 0.0) or 0.0)
    trade.roi = float(getattr(trade_math, "roi", 0.0) or 0.0)
    trade.annualized_return = float(getattr(trade_math, "annualized_return", 0.0) or 0.0)
    trade.reward_risk_ratio = float(getattr(trade_math, "reward_risk_ratio", 0.0) or 0.0)
    trade.buying_power_required = float(getattr(trade_math, "buying_power_required", 0.0) or 0.0)
    trade.construction_complete = bool(
        getattr(trade_math, "construction_complete", False)
        or (_strategy_requires_second_leg(str(trade.active_strategy() or trade.recommended_strategy or "")) and len(getattr(trade_math, "legs", []) or []) >= 2)
        or (not _strategy_requires_second_leg(str(trade.active_strategy() or trade.recommended_strategy or "")) and len(getattr(trade_math, "legs", []) or []) >= 1)
    )
    st.session_state[OTCC_CONSTRUCTION_COMPLETE_KEY] = trade.construction_complete
    return trade_math


# ============================================================
# Utility Helpers
# ============================================================

def money(value: float) -> str:
    return f"${value:,.2f}"


def percent(value: float) -> str:
    return f"{value:,.2f}%"


def score_label(value: float | int | None, waiting_text: str = "Waiting...") -> str:
    try:
        number = float(value) if value is not None else 0.0
    except Exception:
        number = 0.0
    return f"{number:,.1f}" if number > 0 else waiting_text


def strategy_uses_debit_capital(strategy: str) -> bool:
    strategy_key = str(strategy or "").strip()
    return strategy_key in {"Bull Call Spread", "Bear Put Spread", "Long Call", "Long Put"}


def capital_requirement_label(strategy: str) -> str:
    return "Required Debit" if strategy_uses_debit_capital(strategy) else "Buying Power Required"


def capital_requirement_help(strategy: str) -> str:
    if strategy_uses_debit_capital(strategy):
        return "Maximum capital at risk is limited to the net debit paid for this strategy."
    return "Cash your broker reserves because you may be required to purchase the shares if assigned."


def strategy_max_loss_label(strategy: str) -> str:
    if strategy_uses_debit_capital(strategy):
        return "Maximum Loss (Defined Risk)"
    return "Worst-Case Stock Ownership Loss"


def institutional_grade_from_score(score: float) -> str:
    value = float(score or 0.0)
    if value >= 98.0:
        return "A+"
    if value >= 95.0:
        return "A"
    if value >= 90.0:
        return "B+"
    if value >= 85.0:
        return "B"
    if value >= 80.0:
        return "C+"
    if value >= 75.0:
        return "C"
    if value >= 70.0:
        return "D"
    return "Review Required"


def institutional_grade_from_packet(packet, trade=None) -> str:
    try:
        score = float(getattr(getattr(packet, "approval", None), "score", 0.0) or 0.0)
    except Exception:
        score = 0.0
    if score <= 0 and trade is not None:
        score = float(compute_decision_readiness_score(trade, packet) or 0.0)
    return institutional_grade_from_score(score)


def validation_status_tone(status: str) -> str:
    text = str(status or "").upper().strip()
    if text in {"PASS", "OK", "APPROVED"} or "PASS" in text:
        return "pass"
    if text in {"REVIEW", "PASS / REVIEW", "WARN", "WARNING", "NEEDS ADJUSTMENT"}:
        return "review"
    if text in {"FAIL", "FAILED", "REJECT"}:
        return "fail"
    return "pending"


def trace_packet(stage: str, packet) -> None:
    """No-op trace hook retained for local debugging compatibility."""
    return


def resolve_packet_scores(packet) -> dict:
    """Resolve stage-aware scores from the canonical TradeLifecyclePacket only."""
    if TradeLifecyclePacket is None or not isinstance(packet, TradeLifecyclePacket):
        return {
            "opportunity_score": 0.0,
            "options_quality_score": 0.0,
            "execution_confidence": 0.0,
            "opportunity_label": "Waiting for Options Center...",
            "construction_label": "Waiting for Options Center...",
            "execution_label": "Waiting for Options Decision Center...",
        }

    opportunity_score = float(packet.opportunity.institutional_score or 0.0)
    options_quality_score = float(packet.construction.options_quality or 0.0)
    execution_confidence = float(packet.execution.execution_confidence or 0.0)

    return {
        "opportunity_score": opportunity_score,
        "options_quality_score": options_quality_score,
        "execution_confidence": execution_confidence,
        "opportunity_label": score_label(opportunity_score or options_quality_score, "Waiting for Options Center..."),
        "construction_label": score_label(options_quality_score, "Waiting for Options Center..."),
        "execution_label": score_label(execution_confidence, "Waiting for Options Decision Center..."),
    }


def is_placeholder_decision_score(value) -> bool:
    try:
        return abs(float(value) - 35.0) < 0.0001
    except Exception:
        return False


def workflow_checkpoint_states(trade, packet=None) -> dict[str, bool]:
    symbol = str(getattr(trade, "symbol", "") or getattr(packet, "symbol", "") or "").strip().upper()
    strategy = str(
        (trade.active_strategy() if hasattr(trade, "active_strategy") else "")
        or getattr(trade, "recommended_strategy", "")
        or getattr(packet, "recommended_strategy", "")
        or ""
    ).strip()

    review_score = float(getattr(getattr(packet, "approval", None), "score", 0.0) or 0.0)
    mission_complete = bool(symbol)
    strategy_selected = bool(strategy and strategy not in {"Pending", "No Options Trade", "No options structure", "No New Long Premium"})
    review_complete = review_score >= 75.0
    construction_complete = bool(st.session_state.get(OTCC_CONSTRUCTION_COMPLETE_KEY, False) or getattr(trade, "construction_complete", False))
    validation_status = str(getattr(trade, "validation_status", "") or "").upper().strip()
    validation_complete = bool(st.session_state.get(OTCC_VALIDATION_COMPLETE_KEY, False) or validation_status not in {"", "PENDING"})
    trade_approved = bool(getattr(getattr(packet, "approval", None), "approved", False)) or str(getattr(packet, "status", "")).upper() == "APPROVED"

    return {
        "Mission Briefing": mission_complete,
        "Strategy Recommendation": strategy_selected,
        "Institutional Review": review_complete,
        "Trade Construction": construction_complete,
        "Risk Validation": validation_complete,
        "Trade Approval": trade_approved,
    }


def construction_readiness_context(trade, packet=None) -> str:
    states = workflow_checkpoint_states(trade, packet)
    if states.get("Trade Approval", False):
        return "Construction Complete"
    if states.get("Risk Validation", False):
        return "Awaiting Final Approval"
    if states.get("Trade Construction", False):
        return "Awaiting Validation"
    return "In Progress"


def compute_decision_readiness_score(trade, packet=None) -> float:
    """Deterministic workflow readiness based on completed institutional milestones."""
    checkpoints = workflow_checkpoint_states(trade, packet)
    total = max(len(checkpoints), 1)
    completed = sum(1 for done in checkpoints.values() if done)
    return round((completed / total) * 100.0, 1)


def decision_readiness_label(score: float) -> str:
    if score >= 100:
        return "🟢 COMPLETE"
    if score >= 65:
        return "🟢 READY"
    if score >= 35:
        return "🟡 REVIEW"
    if score > 0:
        return "🔴 NOT READY"
    return "Pending"


def responsive_block_start(class_names: str) -> None:
    st.markdown(f'<div class="{class_names}">', unsafe_allow_html=True)


def responsive_block_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_step_separator() -> None:
    st.markdown('<div class="otcc-step-divider"></div>', unsafe_allow_html=True)


def _compact_panel_value(value) -> str:
    text = str(value if value is not None else "Pending")
    return html.escape(text)


def render_compact_metric_panel(items: list[tuple[str, str]], columns: int = 4) -> None:
    cols = max(1, int(columns or 1))
    cells = []
    for label, value in items:
        cells.append(
            f"""
            <div class="otcc-cmetric-item">
                <div class="otcc-cmetric-label">{html.escape(str(label))}</div>
                <div class="otcc-cmetric-value">{_compact_panel_value(value)}</div>
            </div>
            """
        )

    markup = textwrap.dedent(
        f"""
        <div class="otcc-cmetric-grid" style="grid-template-columns: repeat({cols}, minmax(0, 1fr));">
            {''.join(cells)}
        </div>
        """
    ).strip()
    st.markdown(markup, unsafe_allow_html=True)


def render_native_metric_grid(items: list[tuple[str, str]], columns: int = 4, block_class: str = "otcc-grid-4") -> None:
    cols = max(1, int(columns or 1))
    responsive_block_start(block_class)
    column_group = st.columns(cols)
    for idx, item in enumerate(items):
        if len(item) >= 3:
            label, value, help_text = item[0], item[1], item[2]
        else:
            label, value = item[0], item[1]
            help_text = None
        with column_group[idx % cols]:
            st.metric(label, value, help=help_text)
    responsive_block_end()


def beginner_mode_enabled() -> bool:
    return bool(st.session_state.get(BEGINNER_MODE_KEY, False))


def beginner_help(text: str) -> str | None:
    return text if beginner_mode_enabled() else None


def render_beginner_mode_toggle() -> None:
    with st.container(border=True):
        left, right = st.columns([0.42, 0.58], gap="small")
        with left:
            st.toggle(
                "☑ Beginner Mode",
                key=BEGINNER_MODE_KEY,
                value=bool(st.session_state.get(BEGINNER_MODE_KEY, False)),
                help="Show guided lessons, contextual help, and live explanations for new options traders.",
            )
        with right:
            if beginner_mode_enabled():
                st.caption("Guided learning is on. Professional workflow stays the same when this is off.")
            else:
                st.caption("Professional workflow mode. Turn on Beginner Mode for guided learning and tips.")


def render_strategy_lesson(selected_strategy: str) -> None:
    if not beginner_mode_enabled():
        return

    strategy_key = str(selected_strategy or "").strip()
    lesson = STRATEGY_LESSONS.get(strategy_key)
    if lesson is None:
        with st.expander("🎓 Strategy Crash Course", expanded=beginner_mode_enabled()):
            st.markdown(
                """
A beginner lesson for this strategy is not published yet.

Use the glossary below and confirm the trade structure before approval.
"""
            )
            st.markdown("### Beginner Glossary")
            st.markdown(BEGINNER_GLOSSARY_TABLE)
        return

    with st.expander(str(lesson.get("title") or "🎓 Strategy Crash Course"), expanded=beginner_mode_enabled()):
        st.markdown(str(lesson.get("content") or ""))


def render_live_explanation_card(trade) -> None:
    strategy = str(trade.active_strategy() or trade.recommended_strategy or "").strip()
    strike = float(getattr(trade, "strike", 0.0) or 0.0)
    premium = float(getattr(trade, "premium", 0.0) or 0.0)
    contracts = int(getattr(trade, "contracts", 0) or 0)
    has_trade_inputs = bool(strike > 0 and contracts > 0)

    credit_value = float(getattr(trade, "credit", 0.0) or 0.0)
    debit_value = float(getattr(trade, "debit", 0.0) or 0.0)
    buying_power_value = float(getattr(trade, "buying_power_required", 0.0) or 0.0)
    max_loss_value = float(getattr(trade, "max_loss", 0.0) or 0.0)
    breakeven_value = float(getattr(trade, "breakeven", 0.0) or 0.0)
    roi_value = float(getattr(trade, "roi", 0.0) or 0.0)
    annualized_value = float(getattr(trade, "annualized_return", 0.0) or 0.0)

    premium_collected = money(credit_value) if credit_value > 0 else "Waiting for premium"
    required_capital = money(buying_power_value) if buying_power_value > 0 else "Waiting for trade details"
    max_loss = money(max_loss_value) if has_trade_inputs and max_loss_value > 0 else "Waiting for trade details"
    breakeven = money(breakeven_value) if strike > 0 and premium > 0 else "Waiting for strike and premium"
    roi = percent(roi_value) if has_trade_inputs and abs(roi_value) > 0 else "Waiting for completed trade"
    annualized_return = percent(annualized_value) if has_trade_inputs and abs(annualized_value) > 0 else "Waiting for completed trade"

    if strategy == "Cash-Secured Put":
        strategy_line = f"You receive {premium_collected} immediately if your order fills."
        risk_line = (
            "If the option is assigned, you become the owner of 100 shares per contract. "
            "This number represents the maximum theoretical loss only if the stock eventually falls to $0 after assignment."
        )
        capital_label = "Buying Power"
        capital_line = f"Cash your broker reserves because you may be required to purchase the shares if assigned. Current reserved amount: {required_capital}."
        risk_label = "Worst-Case Stock Ownership Loss"
    elif strategy == "Covered Call":
        strategy_line = f"This covered call collects {premium_collected} against shares you already own."
        risk_line = f"Your key risk is equity downside in owned shares, with option-side max loss shown as {max_loss}."
        capital_label = "Buying Power"
        capital_line = f"Broker reserve shown for this covered position is {required_capital}."
        risk_label = "Worst-Case Stock Ownership Loss"
    elif strategy == "Bull Call Spread":
        net_debit = money(debit_value) if debit_value > 0 else "Waiting for debit"
        strategy_line = (
            f"This Bull Call Spread is a defined-risk debit strategy. Maximum profit occurs if the stock closes "
            "at or above the short strike at expiration."
        )
        risk_line = "Maximum loss is limited to the net debit paid. Risk is predefined and no stock ownership is required to enter this trade."
        capital_label = "Required Debit"
        capital_line = f"Capital at risk is limited to the net debit paid. Current required debit: {net_debit}."
        risk_label = "Maximum Loss (Defined Risk)"
    elif strategy in {"Bull Put Spread", "Bear Put Spread", "Bull Call Spread", "Bear Call Spread"}:
        strategy_line = f"This spread structure shows defined-risk math with premium impact of {premium_collected}."
        risk_line = f"Defined spread risk is capped at {max_loss} if the trade performs as poorly as possible."
        capital_label = capital_requirement_label(strategy)
        capital_line = f"{capital_requirement_help(strategy)} Current required capital: {required_capital}."
        risk_label = strategy_max_loss_label(strategy)
    elif strategy == "Long Call":
        strategy_line = f"This long call uses premium outlay math. Current net premium effect is {premium_collected}."
        risk_line = f"Long-call style risk is primarily premium paid; maximum modeled loss here is {max_loss}."
        capital_label = capital_requirement_label(strategy)
        capital_line = f"{capital_requirement_help(strategy)} Current required capital: {required_capital}."
        risk_label = strategy_max_loss_label(strategy)
    elif strategy == "Long Put":
        strategy_line = f"This long put can be used for protection or bearish positioning. Current net premium effect is {premium_collected}."
        risk_line = f"Long-put style risk is primarily premium paid; maximum modeled loss here is {max_loss}."
        capital_label = capital_requirement_label(strategy)
        capital_line = f"{capital_requirement_help(strategy)} Current required capital: {required_capital}."
        risk_label = strategy_max_loss_label(strategy)
    else:
        strategy_line = f"Trade economics currently show premium impact of {premium_collected}."
        risk_line = f"Worst-case modeled loss is {max_loss}."
        capital_label = capital_requirement_label(strategy)
        capital_line = f"{capital_requirement_help(strategy)} Current required capital: {required_capital}."
        risk_label = strategy_max_loss_label(strategy)

    def _render_content() -> None:
        st.markdown("### 📖 How to Read This Trade")
        if strategy_uses_debit_capital(strategy):
            st.markdown(f"**Net Debit**  \nCapital paid to enter the position. Current net debit: {money(debit_value) if debit_value > 0 else 'Waiting for debit' }.")
        else:
            st.markdown(f"**Premium Collected**  \nYou receive {premium_collected} immediately if your order fills.")
        st.markdown(f"**{capital_label}**  \n{capital_line}")
        st.markdown(f"**{risk_label}**  \n{risk_line}")
        st.markdown(f"**Break-even**  \nYou begin losing money only below {breakeven}.")
        st.markdown(f"**ROI**  \nYour expected return is {roi}.")
        st.markdown(f"**Annualized Return**  \nEquivalent yearly return based on this expiration is {annualized_return}.")
        st.caption(strategy_line)

    if beginner_mode_enabled():
        with st.container(border=True):
            _render_content()
    else:
        with st.expander("📖 How to Read This Trade", expanded=False):
            _render_content()


def risk_level_label(max_loss: float, max_profit: float) -> str:
    if max_loss <= 0:
        return "Pending"
    if max_loss <= max_profit * 5:
        return "Low"
    if max_loss <= max_profit * 20:
        return "Moderate"
    if max_loss <= max_profit * 50:
        return "Elevated"
    return "High"


def _render_math_value_card(label: str, value: str, tone: str = "neutral", help_text: str = "", emphasized: bool = False) -> None:
    tone_class = {
        "income": "otcc-tone-income",
        "risk": "otcc-tone-risk",
        "performance": "otcc-tone-performance",
        "position": "otcc-tone-position",
        "neutral": "otcc-tone-position",
    }.get(tone, "otcc-tone-position")
    emphasis_class = " otcc-math-value-key" if emphasized else ""
    st.markdown(
        f"""
        <div class="otcc-math-card {tone_class}">
            <div class="otcc-math-label">{html.escape(label)}</div>
            <div class="otcc-math-value{emphasis_class}">{html.escape(str(value))}</div>
            {f'<div class="otcc-math-help">{html.escape(help_text)}</div>' if help_text else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_institutional_trade_summary(trade, packet=None) -> None:
    try:
        readiness = float(compute_decision_readiness_score(trade, None) or 0.0)
    except Exception:
        readiness = 0.0
    status = str(getattr(trade, "approval_status", "") or "Pending")
    strategy = str(trade.active_strategy() or trade.recommended_strategy or "Pending")
    readiness_context = construction_readiness_context(trade, packet)
    capital_label = "Maximum Capital at Risk" if strategy_uses_debit_capital(strategy) else "Buying Power"
    capital_help = "Net debit paid for defined-risk debit strategy." if strategy_uses_debit_capital(strategy) else "Cash your broker reserves because you may be required to purchase the shares if assigned."
    risk_label = strategy_max_loss_label(strategy)
    summary_rows = [
        ("Underlying", str(getattr(trade, "symbol", "") or "Pending")),
        ("Strategy", strategy),
        ("Contracts", str(int(getattr(trade, "contracts", 0) or 0))),
        ("Short Strike", money(float(getattr(trade, "strike", 0.0) or 0.0)) if float(getattr(trade, "strike", 0.0) or 0.0) > 0 else "Pending"),
        ("Short Premium", money(float(getattr(trade, "premium", 0.0) or 0.0)) if float(getattr(trade, "premium", 0.0) or 0.0) > 0 else "Pending"),
        ("Expiration", str(getattr(trade, "expiration", "") or "Pending")),
        (
            capital_label,
            money(float(getattr(trade, "buying_power_required", 0.0) or 0.0)) if float(getattr(trade, "buying_power_required", 0.0) or 0.0) > 0 else "Waiting for strike",
            capital_help,
        ),
        ("Break-even", money(float(getattr(trade, "breakeven", 0.0) or 0.0)) if float(getattr(trade, "breakeven", 0.0) or 0.0) > 0 else "Waiting for strike and premium"),
        ("Maximum Profit", money(float(getattr(trade, "max_profit", 0.0) or 0.0)) if float(getattr(trade, "max_profit", 0.0) or 0.0) > 0 else "Pending"),
        (
            risk_label,
            money(float(getattr(trade, "max_loss", 0.0) or 0.0)) if float(getattr(trade, "max_loss", 0.0) or 0.0) > 0 else "Waiting for trade details",
            "Defined-risk maximum loss from the current structure.",
        ),
        ("Holding Return", percent(float(getattr(trade, "roi", 0.0) or 0.0)) if abs(float(getattr(trade, "roi", 0.0) or 0.0)) > 0 else "Waiting for completed trade"),
        ("Annualized Return (Info)", percent(float(getattr(trade, "annualized_return", 0.0) or 0.0)) if abs(float(getattr(trade, "annualized_return", 0.0) or 0.0)) > 0 else "Waiting for completed trade"),
        ("Construction Readiness", (f"{readiness:,.1f}% • {readiness_context}") if readiness > 0 else readiness_context),
        ("Approval Status", status),
    ]
    legs = list(getattr(trade, "legs", []) or [])
    buy_leg = next((leg for leg in legs if str(leg.get("side") or "").upper() == "BUY"), None)
    sell_leg = next((leg for leg in legs if str(leg.get("side") or "").upper() == "SELL"), None)
    incomplete_spread = _strategy_requires_second_leg(strategy) and len(legs) < 2

    with st.container(border=True):
        st.markdown("### 📄 Institutional Trade Summary")
        if buy_leg or sell_leg:
            st.markdown("**Selected Legs**")
            if buy_leg:
                buy_qty = int(buy_leg.get("quantity", 1) or 1)
                st.write(
                    f"✓ Buy Leg: BUY TO OPEN {buy_qty} {trade.symbol} {float(buy_leg.get('strike', 0.0) or 0.0):.2f} "
                    f"{str(buy_leg.get('option_type') or '').upper()} @ {float(buy_leg.get('premium', 0.0) or 0.0):.2f}"
                )
            if sell_leg:
                sell_qty = int(sell_leg.get("quantity", 1) or 1)
                st.write(
                    f"✓ Sell Leg: SELL TO OPEN {sell_qty} {trade.symbol} {float(sell_leg.get('strike', 0.0) or 0.0):.2f} "
                    f"{str(sell_leg.get('option_type') or '').upper()} @ {float(sell_leg.get('premium', 0.0) or 0.0):.2f}"
                )
            if incomplete_spread:
                st.info("Select short call to complete spread." if strategy == "Bull Call Spread" else "Select the second leg to complete spread.")
        render_native_metric_grid(summary_rows, columns=3, block_class="otcc-grid-3")
        premium_line = money(float(getattr(trade, "credit", 0.0) or 0.0)) if float(getattr(trade, "credit", 0.0) or 0.0) > 0 else "waiting premium"
        debit_line = money(float(getattr(trade, "debit", 0.0) or 0.0)) if float(getattr(trade, "debit", 0.0) or 0.0) > 0 else "waiting debit"
        max_loss_line = money(float(getattr(trade, "max_loss", 0.0) or 0.0)) if float(getattr(trade, "max_loss", 0.0) or 0.0) > 0 else "waiting risk"
        if strategy == "Bull Call Spread":
            debit_line_safe = debit_line.replace("$", "\\$")
            max_loss_line_safe = max_loss_line.replace("$", "\\$")
            st.caption(f"This debit spread requires {debit_line_safe} to enter. Maximum loss is limited to the net debit paid ({max_loss_line_safe}).")
        else:
            st.caption(f"This trade collects {premium_line} in premium. Worst-case stock ownership loss is {max_loss_line} only if assignment occurs and the underlying later falls to $0.")


def render_live_trade_math_dashboard(trade) -> None:
    strategy = str(trade.active_strategy() or trade.recommended_strategy or "").strip()
    strike = float(getattr(trade, "strike", 0.0) or 0.0)
    premium = float(getattr(trade, "premium", 0.0) or 0.0)
    contracts = int(getattr(trade, "contracts", 0) or 0)
    has_trade_inputs = bool(strike > 0 and contracts > 0)

    credit = float(getattr(trade, "credit", 0.0) or 0.0)
    debit = float(getattr(trade, "debit", 0.0) or 0.0)
    max_profit = float(getattr(trade, "max_profit", 0.0) or 0.0)
    max_loss = float(getattr(trade, "max_loss", 0.0) or 0.0)
    breakeven = float(getattr(trade, "breakeven", 0.0) or 0.0)
    buying_power = float(getattr(trade, "buying_power_required", 0.0) or 0.0)
    roi = float(getattr(trade, "roi", 0.0) or 0.0)
    annualized_return = float(getattr(trade, "annualized_return", 0.0) or 0.0)
    reward_risk = float(getattr(trade, "reward_risk_ratio", 0.0) or 0.0)
    legs = list(getattr(trade, "legs", []) or [])
    incomplete_spread = _strategy_requires_second_leg(strategy) and len(legs) < 2

    capital_at_risk = max_loss
    risk_level = risk_level_label(max_loss, max_profit)
    capital_label = capital_requirement_label(strategy)
    capital_help = capital_requirement_help(strategy)
    max_loss_label = strategy_max_loss_label(strategy)
    capital_at_risk_help = "Maximum capital exposed in this defined-risk structure." if strategy_uses_debit_capital(strategy) else "Capital committed to purchasing the underlying shares if assignment occurs."

    premium_display = money(credit) if credit > 0 else "Waiting for premium"
    max_profit_display = money(max_profit) if has_trade_inputs and max_profit > 0 else "Waiting for trade details"
    buying_power_display = money(buying_power) if buying_power > 0 else "Waiting for trade details"
    capital_at_risk_display = money(capital_at_risk) if has_trade_inputs and capital_at_risk > 0 else "Waiting for trade details"
    max_loss_display = money(max_loss) if has_trade_inputs and max_loss > 0 else "Waiting for trade details"
    breakeven_display = money(breakeven) if strike > 0 and premium > 0 else "Waiting for strike and premium"
    roi_display = percent(roi) if has_trade_inputs and abs(roi) > 0 else "Waiting for completed trade"
    annualized_display = percent(annualized_return) if has_trade_inputs and abs(annualized_return) > 0 else "Waiting for completed trade"
    reward_risk_display = f"{reward_risk:,.4f}" if has_trade_inputs and abs(reward_risk) > 0 else "Waiting for completed trade"
    contracts_display = str(int(contracts)) if contracts > 0 else "Waiting for contracts"
    credit_display = money(credit) if abs(credit) > 0 else "Waiting for premium"
    debit_display = money(debit) if abs(debit) > 0 else "Waiting for trade details"

    st.markdown("### Live Trade Math")
    st.caption(f"Selected Legs: {len(legs)}")

    with st.container(border=True):
        st.markdown("#### 🟢 Income")
        income_left, income_right = st.columns(2, gap="small")
        with income_left:
            _render_math_value_card(
                "Premium Collected",
                premium_display,
                tone="income",
                help_text="Money received immediately if the order fills.",
            )
        with income_right:
            _render_math_value_card(
                "Maximum Profit",
                max_profit_display,
                tone="income",
                help_text="Maximum modeled profit for this structure.",
            )

    with st.container(border=True):
        st.markdown("#### 🟠 Risk")
        risk_top_left, risk_top_right = st.columns(2, gap="small")
        with risk_top_left:
            _render_math_value_card(
                capital_label,
                buying_power_display,
                tone="risk",
                help_text=capital_help,
            )
        with risk_top_right:
            _render_math_value_card(
                "Capital at Risk",
                capital_at_risk_display,
                tone="risk",
                help_text=capital_at_risk_help,
            )

        _render_math_value_card(
            max_loss_label,
            max_loss_display,
            tone="risk",
            help_text="Maximum modeled loss for the current strategy structure.",
            emphasized=True,
        )

        risk_bottom_left, risk_bottom_right = st.columns(2, gap="small")
        with risk_bottom_left:
            _render_math_value_card(
                "Break-even",
                breakeven_display,
                tone="risk",
                help_text="Stock price where the trade begins to lose money at expiration.",
            )
        with risk_bottom_right:
            _render_math_value_card(
                "Risk Level",
                risk_level,
                tone="risk",
                help_text="Display-only risk tier based on maximum modeled loss relative to maximum profit.",
            )

    with st.container(border=True):
        st.markdown("#### 🔵 Performance")
        perf1, perf2, perf3 = st.columns(3, gap="small")
        with perf1:
            _render_math_value_card(
                "Holding Return",
                roi_display,
                tone="performance",
                help_text="Return over the planned holding period based on capital at risk.",
            )
        with perf2:
            _render_math_value_card(
                "Annualized Return (Info)",
                annualized_display,
                tone="performance",
                help_text="Informational annualized projection; compare with holding return for practical sizing decisions.",
            )
        with perf3:
            _render_math_value_card(
                "Reward / Risk",
                reward_risk_display,
                tone="performance",
                help_text="Potential reward divided by worst-case modeled loss.",
            )

    with st.container(border=True):
        st.markdown("#### 📋 Position")
        pos1, pos2, pos3 = st.columns(3, gap="small")
        with pos1:
            _render_math_value_card(
                "Contracts",
                contracts_display,
                tone="position",
                help_text="One option contract controls 100 shares.",
            )
        with pos2:
            _render_math_value_card("Credit", credit_display, tone="position")
        with pos3:
            _render_math_value_card("Debit", debit_display, tone="position")

    if incomplete_spread:
        st.info("Select short call to complete spread." if strategy == "Bull Call Spread" else "Select the second leg to complete spread.")

    if beginner_mode_enabled():
        if strategy == "Cash-Secured Put":
            st.caption("Income-oriented setup: premium now, potential share ownership later if assigned.")
        elif strategy == "Covered Call":
            st.caption("Share-ownership setup: call income is generated against stock already held.")
        elif strategy in {"Bull Put Spread", "Bear Put Spread", "Bull Call Spread", "Bear Call Spread"}:
            st.caption("Defined-risk spread setup: protection leg caps worst-case downside.")
        elif strategy == "Long Call":
            st.caption("Long call setup: directional upside with risk centered on premium paid.")
        elif strategy == "Long Put":
            st.caption("Long put setup: bearish/protective exposure with risk centered on premium paid.")


# ============================================================
# Institutional Review Helpers
# ============================================================

def packet_is_approved(packet) -> bool:
    try:
        return bool(getattr(getattr(packet, "approval", None), "approved", False)) or str(getattr(packet, "status", "")).upper() == "APPROVED"
    except Exception:
        return False


def approval_bool(value) -> bool:
    return bool(value)


def approval_percent(packet, trade=None) -> float:
    try:
        packet_score = float(getattr(getattr(packet, "approval", None), "score", 0.0) or 0.0)
    except Exception:
        packet_score = 0.0
    if packet_score > 0:
        return max(0.0, min(100.0, packet_score))
    try:
        return compute_decision_readiness_score(trade, packet) if trade is not None else 0.0
    except Exception:
        return 0.0


def approval_checklist_from_trade(trade, packet=None) -> dict:
    """Infer the institutional approval checklist from the canonical packet + current trade."""
    try:
        checked_trade = validate_trade(trade)
        checks = get_validation_checks(checked_trade)
    except Exception:
        checked_trade = trade
        checks = {}

    def check_pass(name: str) -> bool:
        try:
            status = str((checks.get(name) or ("", ""))[0]).upper().strip()
            return status in {"PASS", "OK", "APPROVED"} or "PASS" in status or "APPROVED" in status
        except Exception:
            return False

    opportunity_score = 0.0
    construction_score = 0.0
    if isinstance(packet, TradeLifecyclePacket):
        opportunity_score = float(packet.opportunity.institutional_score or 0.0)
        construction_score = float(packet.construction.options_quality or 0.0)

    strategy = str(
        (trade.active_strategy() if hasattr(trade, "active_strategy") else "")
        or getattr(trade, "recommended_strategy", "")
        or getattr(packet, "recommended_strategy", "")
        or ""
    ).strip()

    premium = float(getattr(trade, "premium", 0.0) or 0.0)
    long_premium = float(getattr(trade, "long_premium", 0.0) or 0.0)
    strike = float(getattr(trade, "strike", 0.0) or 0.0)
    expiration = getattr(trade, "expiration", None)
    contracts = int(getattr(trade, "contracts", 0) or 0)
    buying_power = float(getattr(trade, "buying_power", 0.0) or 0.0)
    buying_power_required = float(getattr(trade, "buying_power_required", 0.0) or 0.0)
    max_profit = float(getattr(trade, "max_profit", 0.0) or 0.0)
    max_loss = float(getattr(trade, "max_loss", 0.0) or 0.0)
    reward_risk = float(getattr(trade, "reward_risk_ratio", 0.0) or 0.0)

    return {
        "trend_confirmed": bool(strategy) and strategy not in {"Pending", "No Options Trade", "No options structure", "No New Long Premium"} and (opportunity_score >= 60 or construction_score >= 60),
        "premium_confirmed": check_pass("Premium Quality") or premium > 0 or long_premium > 0,
        "liquidity_confirmed": construction_score >= 60,
        "strike_confirmed": strike > 0,
        "expiration_confirmed": check_pass("Expiration") or expiration is not None,
        "position_size_confirmed": check_pass("Position Size") or contracts >= 1,
        "buying_power_confirmed": check_pass("Buying Power") or buying_power <= 0 or buying_power_required <= 0 or buying_power_required <= buying_power,
        "event_risk_confirmed": True,
        "risk_reward_confirmed": check_pass("Breakeven vs Stock") or reward_risk > 0 or max_profit > 0 or max_loss > 0,
    }


def institutional_review_checks(trade, packet=None) -> dict:
    """Return check values + reasons, auto-evaluating objective checks."""
    checks = approval_checklist_from_trade(trade, packet)
    strike = float(getattr(trade, "strike", 0.0) or 0.0)
    premium = float(getattr(trade, "premium", 0.0) or 0.0)
    contracts = int(getattr(trade, "contracts", 0) or 0)
    buying_power = float(getattr(trade, "buying_power", 0.0) or 0.0)
    buying_power_required = float(getattr(trade, "buying_power_required", 0.0) or 0.0)
    expiration = getattr(trade, "expiration", None)
    construction_score = float(getattr(getattr(packet, "construction", None), "options_quality", 0.0) or 0.0)

    reasons = {
        "trend_confirmed": "Trend/strategy alignment is missing.",
        "premium_confirmed": "Premium must be entered and greater than zero.",
        "liquidity_confirmed": "Construction quality below liquidity threshold (60).",
        "strike_confirmed": "Short strike must be greater than zero.",
        "expiration_confirmed": "Expiration date must be in the future.",
        "position_size_confirmed": "Verify this position size fits your portfolio allocation guidelines.",
        "buying_power_confirmed": "Verify that your brokerage account has sufficient available buying power before execution.",
        "event_risk_confirmed": "Event risk requires manual confirmation.",
        "risk_reward_confirmed": "Risk / Reward requires manual review confirmation.",
    }

    auto = {
        "trend_confirmed": True,
        "premium_confirmed": True,
        "liquidity_confirmed": True,
        "strike_confirmed": True,
        "expiration_confirmed": True,
        "position_size_confirmed": True,
        "buying_power_confirmed": True,
        "event_risk_confirmed": False,
        "risk_reward_confirmed": False,
    }

    values = {
        "trend_confirmed": bool(checks.get("trend_confirmed", False)),
        "premium_confirmed": bool(checks.get("premium_confirmed", premium > 0)),
        "liquidity_confirmed": bool(checks.get("liquidity_confirmed", construction_score >= 60)),
        "strike_confirmed": bool(checks.get("strike_confirmed", strike > 0)),
        "expiration_confirmed": bool(checks.get("expiration_confirmed", expiration is not None and expiration > date.today())),
        "position_size_confirmed": bool(checks.get("position_size_confirmed", contracts >= 1)),
        "buying_power_confirmed": bool(checks.get("buying_power_confirmed", buying_power <= 0 or buying_power_required <= 0 or buying_power_required <= buying_power)),
        "event_risk_confirmed": bool(getattr(getattr(packet, "approval", None), "event_risk_confirmed", False)),
        "risk_reward_confirmed": bool(getattr(getattr(packet, "approval", None), "risk_reward_confirmed", False)),
    }

    return {
        key: {
            "value": values[key],
            "auto": auto[key],
            "reason": "" if values[key] else reasons[key],
        }
        for key in values
    }


def render_workflow_progress(trade, packet=None) -> None:
    """Institutional workflow timeline shown below Mission Briefing."""
    checkpoint_states = workflow_checkpoint_states(trade, packet)
    approval_done = bool(checkpoint_states.get("Trade Approval", False))
    completed_stages = list(getattr(getattr(packet, "metadata", None), "completed_stages", []) or [])
    order = getattr(packet, "order", None)
    execution_handoff = bool(
        approval_done
        and (
            "ORDER_EXECUTION" in completed_stages
            or bool(getattr(order, "completed", False))
            or bool(getattr(order, "order_id", ""))
            or bool(getattr(order, "submitted_at", ""))
            or str(getattr(order, "status", "") or "").upper() in {"SENT", "SUBMITTED", "FILLED", "PARTIAL"}
        )
    )
    execution_partial = bool(approval_done and not execution_handoff)

    stage_labels = [
        "Mission Briefing",
        "Strategy Recommendation",
        "Institutional Review",
        "Trade Construction",
        "Risk Validation",
        "Trade Approval",
        "Execution Package",
    ]

    states = []
    current_assigned = False
    for label in stage_labels:
        if label == "Execution Package":
            done = execution_handoff
        else:
            done = bool(checkpoint_states.get(label, False))
        if done:
            states.append("complete")
            continue
        if not current_assigned:
            states.append("current")
            current_assigned = True
        else:
            states.append("pending")

    if all(state == "complete" for state in states):
        states = ["complete"] * len(stage_labels)

    node_html = []
    for idx, label in enumerate(stage_labels, start=1):
        state = states[idx - 1]
        if state == "complete":
            symbol = "🟢"
        elif state == "current":
            symbol = "🔵"
        else:
            symbol = "⚪"
        line_state = "complete" if idx < len(stage_labels) and states[idx - 1] == "complete" else "pending"
        node_html.append(
            f"""
            <div class="otcc-timeline-stage otcc-stage-{state}">
                <div class="otcc-timeline-circle">{symbol}</div>
                <div class="otcc-timeline-label">{label}</div>
            </div>
            {"<div class='otcc-timeline-connector otcc-line-" + line_state + "'>↓</div>" if idx < len(stage_labels) else ""}
            """
        )

    with st.container(border=True):
        st.markdown("### Workflow Progress")
        st.caption("Mission Briefing ↓ Strategy Recommendation ↓ Institutional Review ↓ Trade Construction ↓ Risk Validation ↓ Trade Approval ↓ Execution Package")
        st.markdown(
            f"""
            <div class="otcc-timeline-wrap">
                {''.join(node_html)}
            </div>
            """,
            unsafe_allow_html=True,
        )


def sync_approval_review_to_lifecycle(trade, packet=None, *, overwrite_checks: bool = True):
    """Write OP2 approval readiness into the canonical TradeLifecyclePacket."""
    if TradeLifecyclePacket is None:
        return packet

    if not isinstance(packet, TradeLifecyclePacket):
        packet = TradeLifecyclePacket.from_session(st.session_state)

    checklist = approval_checklist_from_trade(trade, packet)
    completed = sum(1 for value in checklist.values() if bool(value))
    total = max(len(checklist), 1)
    score = round((completed / total) * 100.0, 1)

    approval_updates = {"score": score}
    if overwrite_checks:
        approval_updates.update(checklist)

    packet.merge_update({"approval": approval_updates}, source="Options Decision Center", overwrite=True)
    if getattr(packet.approval, "approved", False):
        packet.status = "APPROVED"
    elif not str(getattr(packet, "status", "")).upper() == "APPROVED":
        packet.status = "DRAFT"
    packet.save_to_session(st.session_state)
    return packet


def approve_packet_in_lifecycle(trade, packet=None):
    if TradeLifecyclePacket is None:
        return packet
    if not isinstance(packet, TradeLifecyclePacket):
        packet = TradeLifecyclePacket.from_session(st.session_state)
    packet = sync_approval_review_to_lifecycle(trade, packet, overwrite_checks=True)
    packet.approval.approved = True
    packet.approval.approved_by = "Trade Review Desk"
    packet.approval.approved_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    packet.approval.notes = packet.approval.notes or "Approved in Options Decision Center."
    packet.status = "APPROVED"
    packet.save_to_session(st.session_state)
    try:
        trade.approval_status = "APPROVED"
    except Exception:
        pass
    return packet


def clear_packet_approval(trade, packet=None):
    if TradeLifecyclePacket is None:
        return packet
    if not isinstance(packet, TradeLifecyclePacket):
        packet = TradeLifecyclePacket.from_session(st.session_state)

    checklist_fields = [
        "trend_confirmed",
        "premium_confirmed",
        "liquidity_confirmed",
        "strike_confirmed",
        "expiration_confirmed",
        "position_size_confirmed",
        "buying_power_confirmed",
        "event_risk_confirmed",
        "risk_reward_confirmed",
    ]
    for field in checklist_fields:
        try:
            setattr(packet.approval, field, False)
        except Exception:
            pass

    packet.approval.score = 0.0
    packet.approval.approved = False
    packet.approval.approved_by = ""
    packet.approval.approved_timestamp = ""
    packet.approval.notes = ""
    packet.execution.approval = None
    packet.execution.execution_confidence = None
    packet.status = "DRAFT"

    try:
        completed = list(getattr(getattr(packet, "metadata", None), "completed_stages", []) or [])
        packet.metadata.completed_stages = [
            stage for stage in completed if stage not in {"EXECUTION_REVIEW", "ORDER_EXECUTION", "COMPLETE"}
        ]
    except Exception:
        pass

    packet.save_to_session(st.session_state)

    # Clear approval/decision-related session mirrors and stale checkbox state.
    for key in [
        "approval",
        "approval_score",
        "approved",
        "approved_by",
        "approved_timestamp",
        "approval_notes",
        "execution_confidence",
        "institutional_decision",
        "institutional_decision_object",
        "otcc_decision_readiness_override",
        "otcc_decision_override",
        STEP5_VALIDATION_COMPLETE_KEY,
        STEP5_VALIDATION_STATUS_KEY,
        OTCC_VALIDATION_COMPLETE_KEY,
    ]:
        st.session_state.pop(key, None)

    for key in list(st.session_state.keys()):
        if key.startswith("otcc_approval_check_"):
            st.session_state.pop(key, None)

    try:
        trade.approval_status = PENDING_TEXT
        trade.reset_validation()
    except Exception:
        pass
    return packet


def render_commander_approval(trade, packet=None):
    section_header(
        "Step 3",
        "Institutional Review",
        "Validate the proposed trade against institutional quality standards before construction is finalized.",
    )

    if TradeLifecyclePacket is None:
        st.warning("Lifecycle packet engine unavailable.")
        return packet

    if not isinstance(packet, TradeLifecyclePacket):
        packet = TradeLifecyclePacket.from_session(st.session_state)

    approval = getattr(packet, "approval", None)
    if approval is None:
        st.warning("Approval section unavailable in packet.")
        return packet

    checklist_fields = [
        ("trend_confirmed", "Trend confirmed"),
        ("premium_confirmed", "Premium acceptable"),
        ("liquidity_confirmed", "Liquidity acceptable"),
        ("strike_confirmed", "Strike approved"),
        ("expiration_confirmed", "Expiration approved"),
        ("position_size_confirmed", "Position size approved"),
        ("buying_power_confirmed", "Buying power verified"),
        ("event_risk_confirmed", "Event risk checked"),
        ("risk_reward_confirmed", "Risk / Reward approved"),
    ]
    changed = False
    check_meta = institutional_review_checks(trade, packet)

    with st.container(border=True):
        st.markdown(
            """
            <div class="otcc-approval-card">
                <div class="otcc-approval-title">Institutional Review Dashboard</div>
                <div class="otcc-approval-subtitle">Reviewed by Trade Review Desk</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        left, right = st.columns([1.2, 1.0])

        with left:
            st.markdown("### Institutional Checklist")
            responsive_block_start("otcc-grid-3 otcc-checklist-grid otcc-checklist-compact")
            cols = st.columns(3)
            for index, (key, label) in enumerate(checklist_fields):
                with cols[index % 3]:
                    current = bool(getattr(approval, key, False))
                    auto_check = bool(check_meta.get(key, {}).get("auto", False))
                    desired = bool(check_meta.get(key, {}).get("value", current))
                    widget_key = f"otcc_approval_check_{key}"
                    _ensure_widget_default(widget_key, desired if auto_check else current)
                    if auto_check:
                        if current != desired:
                            setattr(approval, key, desired)
                            changed = True
                        st.checkbox(label, key=widget_key, disabled=True)
                        if not desired:
                            st.caption(f"❌ {check_meta.get(key, {}).get('reason', '')}")
                    else:
                        new_value = st.checkbox(label, key=widget_key)
                        if new_value != current:
                            setattr(approval, key, new_value)
                            changed = True
            responsive_block_end()

        completed = sum(1 for key, _ in checklist_fields if bool(getattr(approval, key, False)))
        total = 9
        score = round((completed / total) * 100.0, 1)
        if float(getattr(approval, "score", 0.0) or 0.0) != score:
            approval.score = score
            changed = True

        if changed:
            packet.save_to_session(st.session_state)

        if score >= 75.0:
            readiness_color = "#166534"
            readiness_label = "Green"
        elif score >= 50.0:
            readiness_color = "#92400e"
            readiness_label = "Yellow"
        else:
            readiness_color = "#991b1b"
            readiness_label = "Red"

        with left:
            st.markdown(
                f"""
                <div class="otcc-readiness-wrap">
                    <div class="otcc-readiness-label">Review Readiness</div>
                    <div class="otcc-readiness-value">{score:,.1f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.progress(min(max(score / 100.0, 0.0), 1.0))
            st.markdown(f"<span style='color:{readiness_color};font-weight:800;'>{readiness_label} readiness</span>", unsafe_allow_html=True)
        with right:
            st.markdown("### Institutional Decision")
            review_status = "Construction Authorized" if score >= 75.0 else "Review In Progress"
            review_readiness = f"{compute_decision_readiness_score(trade, packet):,.1f}%"
            review_timestamp = str(getattr(approval, "approved_timestamp", "") or "Pending")
            decision_rows = [
                ("Review Status", review_status),
                ("Readiness", review_readiness),
                ("Reviewed By", "Trade Review Desk"),
                ("Review Timestamp", review_timestamp),
            ]
            st.markdown(
                "<div class='otcc-kv-card'>"
                + "".join(
                    f"<div class='otcc-kv-row'><div class='otcc-kv-key'>{key}</div><div class='otcc-kv-val'>{value}</div></div>"
                    for key, value in decision_rows
                )
                + "</div>",
                unsafe_allow_html=True,
            )
        st.caption("Final trade approval is completed in Step 6 after construction and validation.")

    return packet

def packet_source_display(packet) -> str:
    """Lifecycle owns the packet; modules are contributors, not sources."""
    return "Lifecycle Engine"


def packet_contributors_display(packet) -> str:
    if packet is None:
        return "Pending"
    try:
        label = packet.contributors_label()
        if label and label != "Pending":
            return label
    except Exception:
        pass

    contributors = []
    try:
        history = list(getattr(getattr(packet, "metadata", None), "history", []) or [])
    except Exception:
        history = []
    ignored = {
        "Lifecycle Engine",
        "Shared Lifecycle Engine",
        "legacy_session_import",
        "session_packet_reconcile",
        "symbol_stage_memory_save",
        "symbol_stage_memory_restore",
        "legacy_from_dict",
        "session_legacy",
    }
    for item in history:
        if not isinstance(item, dict):
            continue
        src = str(item.get("source") or "").strip()
        if src and src not in ignored and src not in contributors and not src.startswith("legacy_") and not src.startswith("session_"):
            contributors.append(src)
    return " / ".join(contributors) if contributors else "Pending"


def resolve_symbol_handoff(trade):
    possible_keys = [
        "option_symbol",
        "trade_command_symbol",
        "trade_symbol",
        "selected_symbol",
        "research_ticker",
        "scanner_selected_symbol",
        "opportunity_symbol",
        "active_symbol",
        "ticker",
    ]

    if trade.symbol:
        return trade.symbol

    for key in possible_keys:
        value = st.session_state.get(key)
        if isinstance(value, str) and value.strip():
            trade.symbol = value.strip().upper()
            return trade.symbol

    return trade.symbol


def inject_commander_css():
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.35rem !important;
                padding-bottom: 2.4rem !important;
                max-width: 1700px !important;
                padding-left: clamp(0.9rem, 2.2vw, 2.75rem) !important;
                padding-right: clamp(0.9rem, 2.2vw, 2.75rem) !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            .block-container h1 {
                margin-bottom: 0.2rem;
                font-size: clamp(1.85rem, 3.5vw, 2.55rem) !important;
                font-weight: 900 !important;
                color: #1f2937 !important;
            }

            .block-container h2 {
                margin-top: 0.45rem;
                margin-bottom: 0.15rem;
                line-height: 1.15;
                font-size: clamp(1.12rem, 2.2vw, 1.50rem) !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
            }

            .block-container h3 {
                font-size: clamp(1.0rem, 1.55vw, 1.22rem) !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
            }

            .block-container p {
                margin-bottom: 0.35rem;
            }

            .block-container div[data-testid="stCaptionContainer"] {
                font-size: 0.84rem;
                line-height: 1.35;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                padding: 0.88rem 0.92rem;
                border-radius: 14px;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
                gap: 0.26rem;
            }

            .otcc-step-divider {
                border-top: 1px solid rgba(148, 163, 184, 0.30);
                margin: 0.75rem 0 0.65rem 0;
            }

            div[data-testid="stVerticalBlock"] > div:has(> hr) {
                margin-top: 0.1rem;
                margin-bottom: 0.1rem;
            }

            div[data-testid="stAlert"] {
                padding-top: 0.45rem;
                padding-bottom: 0.45rem;
            }

            .otcc-commander-card {
                border: 1px solid rgba(148, 163, 184, 0.25);
                border-radius: 18px;
                padding: 0.9rem 1rem;
                margin-bottom: 0.55rem;
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.06), rgba(30, 41, 59, 0.02));
            }

            .otcc-kicker {
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #64748b;
                font-weight: 700;
                margin-bottom: 0.35rem;
            }

            .otcc-commander-title {
                font-size: 1.22rem;
                line-height: 1.2;
                font-weight: 800;
                margin-bottom: 0.2rem;
            }

            .otcc-commander-text {
                font-size: 0.9rem;
                color: #475569;
                line-height: 1.45;
            }

            .otcc-mission-selected {
                border: 2px solid #2563eb;
                border-radius: 14px;
                padding: 0.75rem 0.9rem;
                background: rgba(37, 99, 235, 0.08);
                margin-bottom: 0.65rem;
            }

            .otcc-mission-idle {
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 14px;
                padding: 0.75rem 0.9rem;
                background: rgba(248, 250, 252, 0.35);
                margin-bottom: 0.65rem;
            }

            .otcc-mission-title {
                font-weight: 800;
                font-size: 0.95rem;
                margin-bottom: 0.2rem;
            }

            .otcc-mission-desc {
                font-size: 0.8rem;
                color: #64748b;
                line-height: 1.35;
                min-height: 1.9rem;
            }

            .otcc-briefing-card {
                border: 1px solid rgba(34, 197, 94, 0.35);
                border-radius: 18px;
                padding: 1rem 1.1rem;
                margin-bottom: 0.75rem;
                background: rgba(240, 253, 244, 0.72);
            }

            .otcc-briefing-title {
                font-size: 1.35rem;
                font-weight: 850;
                color: #166534;
                line-height: 1.15;
                margin-bottom: 0.2rem;
            }

            .otcc-briefing-meta {
                color: #334155;
                font-size: 0.9rem;
                line-height: 1.35;
            }

            .otcc-approval-card {
                border: 1px solid rgba(37, 99, 235, 0.28);
                border-radius: 18px;
                padding: 0.8rem 0.95rem;
                margin-bottom: 0.55rem;
                background: linear-gradient(135deg, rgba(219, 234, 254, 0.40), rgba(255, 255, 255, 0.92));
            }

            .otcc-approval-title {
                font-size: 1rem;
                font-weight: 850;
                color: #1e3a8a;
                margin-bottom: 0.25rem;
                line-height: 1.2;
            }

            .otcc-approval-subtitle {
                color: #334155;
                font-size: 0.86rem;
                margin-bottom: 0.2rem;
            }

            .otcc-approved-banner {
                border: 1px solid rgba(34, 197, 94, 0.45);
                border-radius: 14px;
                padding: 0.6rem 0.75rem;
                margin-top: 0.45rem;
                background: rgba(240, 253, 244, 0.9);
            }

            .otcc-approved-banner-title {
                color: #166534;
                font-size: 0.98rem;
                font-weight: 850;
                margin-bottom: 0.3rem;
            }

            .otcc-approved-banner-meta {
                color: #14532d;
                font-size: 0.86rem;
                line-height: 1.35;
            }

            .otcc-kv-card {
                border: 1px solid rgba(148, 163, 184, 0.30);
                border-radius: 12px;
                background: rgba(248, 250, 252, 0.78);
                padding: 0.55rem 0.7rem;
            }

            .otcc-kv-row {
                display: grid;
                grid-template-columns: minmax(110px, 140px) minmax(0, 1fr);
                gap: 0.65rem;
                padding: 0.3rem 0;
                border-bottom: 1px dashed rgba(148, 163, 184, 0.25);
                align-items: start;
            }

            .otcc-kv-row:last-child {
                border-bottom: none;
            }

            .otcc-kv-key {
                color: #475569;
                font-size: 0.8rem;
                font-weight: 700;
                line-height: 1.3;
            }

            .otcc-kv-val {
                color: #0f172a;
                font-size: 0.9rem;
                font-weight: 700;
                line-height: 1.35;
                word-break: break-word;
                overflow-wrap: anywhere;
            }

            .otcc-readiness-wrap {
                margin-top: 0.1rem;
                margin-bottom: 0.1rem;
            }

            .otcc-readiness-label {
                font-size: 0.8rem;
                color: #475569;
                font-weight: 700;
            }

            .otcc-readiness-value {
                font-size: 1.42rem;
                line-height: 1.08;
                font-weight: 800;
                color: #0f172a;
            }

            .otcc-timeline-wrap {
                display: flex;
                align-items: flex-start;
                gap: 0.25rem;
                flex-wrap: nowrap;
            }

            .otcc-timeline-stage {
                flex: 1 1 0;
                min-width: 110px;
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                gap: 0.4rem;
            }

            .otcc-timeline-circle {
                width: 2rem;
                height: 2rem;
                border-radius: 999px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.02rem;
                font-weight: 700;
                line-height: 1;
            }

            .otcc-stage-complete .otcc-timeline-circle {
                background: transparent;
            }

            .otcc-stage-current .otcc-timeline-circle {
                background: rgba(37, 99, 235, 0.12);
                transform: scale(1.24);
                box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.14), 0 0 18px rgba(37, 99, 235, 0.30);
            }

            .otcc-stage-current .otcc-timeline-label {
                color: #1d4ed8;
                font-weight: 800;
                font-size: 0.75rem;
            }

            .otcc-stage-pending .otcc-timeline-circle {
                background: transparent;
            }

            .otcc-timeline-label {
                font-size: 0.68rem;
                font-weight: 700;
                color: #334155;
                line-height: 1.3;
                white-space: normal;
                overflow-wrap: anywhere;
            }

            .otcc-timeline-connector {
                flex: 0 0 clamp(12px, 1.5vw, 24px);
                height: 2rem;
                margin-top: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1rem;
                color: #94a3b8;
                font-weight: 800;
            }

            .otcc-line-complete {
                color: #16a34a;
            }

            .otcc-stage-current + .otcc-timeline-connector {
                color: #2563eb;
                font-size: 1.2rem;
                font-weight: 900;
            }

            .otcc-main-two-col [data-testid="stHorizontalBlock"] {
                gap: 0.9rem;
            }

            .otcc-step23-row [data-testid="stHorizontalBlock"],
            .otcc-step67-row [data-testid="stHorizontalBlock"] {
                gap: 0.55rem;
                align-items: stretch;
            }

            .otcc-step4-row [data-testid="stHorizontalBlock"] {
                gap: 0.55rem;
            }

            .otcc-step4-row [data-testid="column"] {
                min-width: 0;
            }

            .otcc-step4-row [data-testid="stMetricLabel"] > div {
                font-size: 0.72rem !important;
                line-height: 1.2;
            }

            .otcc-step4-row [data-testid="stMetricValue"] > div,
            .otcc-step4-row div[data-testid="stMetricValue"] {
                font-size: clamp(0.8rem, 0.9vw, 0.94rem) !important;
                font-weight: 760;
                line-height: 1.05;
            }

            /* Strongly scoped overrides for Live Trade Math only */
            .otcc-live-math-panel div[data-testid="stMetricLabel"],
            .otcc-live-math-panel div[data-testid="stMetricLabel"] * {
                font-size: 0.72rem !important;
                line-height: 1.2 !important;
            }

            .otcc-live-math-panel div[data-testid="stMetricValue"],
            .otcc-live-math-panel div[data-testid="stMetricValue"] > div,
            .otcc-live-math-panel div[data-testid="stMetricValue"] p,
            .otcc-live-math-panel div[data-testid="stMetricValue"] span {
                font-size: 1.34rem !important;
                font-weight: 680 !important;
                line-height: 1.06 !important;
                letter-spacing: -0.01em;
            }

            .otcc-live-math-panel .otcc-math-card {
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 12px;
                background: rgba(15, 23, 42, 0.35);
                padding: 0.7rem 0.85rem;
                min-height: 102px;
            }

            .otcc-live-math-panel .otcc-math-label {
                font-size: 0.76rem;
                letter-spacing: 0.01em;
                text-transform: uppercase;
                color: #cbd5e1;
                margin-bottom: 0.25rem;
            }

            .otcc-live-math-panel .otcc-math-value {
                font-size: 1.1rem;
                font-weight: 700;
                line-height: 1.3;
                color: #e2e8f0;
            }

            .otcc-live-math-panel .otcc-math-help {
                margin-top: 0.28rem;
                font-size: 0.74rem;
                color: #94a3b8;
                line-height: 1.35;
            }

            .otcc-live-math-panel .otcc-math-value-key {
                color: #fecaca;
                text-shadow: 0 0 18px rgba(239, 68, 68, 0.2);
            }

            .otcc-live-math-panel .otcc-tone-income {
                border-left: 4px solid rgba(34, 197, 94, 0.55);
            }

            .otcc-live-math-panel .otcc-tone-risk {
                border-left: 4px solid rgba(249, 115, 22, 0.62);
            }

            .otcc-live-math-panel .otcc-tone-performance {
                border-left: 4px solid rgba(56, 189, 248, 0.62);
            }

            .otcc-live-math-panel .otcc-tone-position {
                border-left: 4px solid rgba(148, 163, 184, 0.55);
            }

            div[data-testid="stMetricLabel"] {
                font-size: 0.74rem !important;
            }

            div[data-testid="stMetricValue"],
            div[data-testid="stMetricValue"] > div,
            div[data-testid="stMetricValue"] p,
            div[data-testid="stMetricValue"] span {
                font-size: 1.5rem !important;
                line-height: 1.08 !important;
                font-weight: 720 !important;
            }

            .otcc-step4-row [data-testid="stMarkdownContainer"] h3 {
                font-size: 0.9rem !important;
                margin-bottom: 0.2rem;
            }

            .otcc-step23-row [data-testid="column"],
            .otcc-step67-row [data-testid="column"] {
                min-width: 0;
            }

            .otcc-step23-row [data-testid="stVerticalBlock"],
            .otcc-step67-row [data-testid="stVerticalBlock"] {
                gap: 0.3rem;
            }

            .otcc-checklist-compact [data-testid="stCheckbox"] {
                margin-bottom: 0.08rem;
            }

            .otcc-checklist-compact [data-testid="stMarkdownContainer"] p {
                font-size: 0.82rem;
            }

            .otcc-checklist-compact [data-testid="stCaptionContainer"] {
                font-size: 0.74rem;
                line-height: 1.25;
            }

            .otcc-construction-card,
            .otcc-review-card,
            .otcc-compact-card {
                padding-top: 0.15rem;
            }

            .otcc-construction-card [data-testid="stMetricValue"] > div,
            .otcc-review-card [data-testid="stMetricValue"] > div,
            .otcc-compact-card [data-testid="stMetricValue"] > div {
                font-size: clamp(0.96rem, 1.1vw, 1.12rem);
                line-height: 1.1;
            }

            .otcc-construction-card div[data-testid="stMetricValue"],
            .otcc-review-card div[data-testid="stMetricValue"],
            .otcc-compact-card div[data-testid="stMetricValue"] {
                font-size: clamp(0.98rem, 1.12vw, 1.15rem) !important;
            }

            .otcc-construction-card [data-testid="stMetricLabel"] > div,
            .otcc-review-card [data-testid="stMetricLabel"] > div,
            .otcc-compact-card [data-testid="stMetricLabel"] > div {
                font-size: 0.74rem;
                font-weight: 650;
            }

            .otcc-cmetric-grid {
                display: grid;
                gap: 0.28rem 0.45rem;
                margin-top: 0.2rem;
                margin-bottom: 0.2rem;
            }

            .otcc-cmetric-item {
                min-width: 0;
                padding: 0.08rem 0;
            }

            .otcc-cmetric-label {
                font-size: 0.74rem;
                color: #475569;
                line-height: 1.2;
                margin-bottom: 0.1rem;
                white-space: normal;
                overflow: visible;
                text-overflow: clip;
            }

            .otcc-cmetric-value {
                font-size: 1rem;
                font-weight: 750;
                color: #111827;
                line-height: 1.15;
                white-space: normal;
                word-break: break-word;
                overflow-wrap: anywhere;
            }

            .otcc-status-card {
                border: 1px solid rgba(148, 163, 184, 0.30);
                border-radius: 8px;
                padding: 0.4rem 0.45rem;
                margin-bottom: 0.12rem;
                background: rgba(255, 255, 255, 0.70);
            }

            .otcc-status-title {
                font-size: 0.78rem;
                font-weight: 780;
                color: #1f2937;
                margin-bottom: 0.12rem;
            }

            .otcc-status-body {
                font-size: 0.82rem;
                color: #334155;
                line-height: 1.28;
            }

            .otcc-construction-card [data-testid="stMarkdownContainer"] h3,
            .otcc-review-card [data-testid="stMarkdownContainer"] h3,
            .otcc-compact-card [data-testid="stMarkdownContainer"] h3 {
                margin-top: 0.2rem;
                margin-bottom: 0.35rem;
            }

            .otcc-construction-card [data-testid="stVerticalBlock"],
            .otcc-review-card [data-testid="stVerticalBlock"],
            .otcc-compact-card [data-testid="stVerticalBlock"] {
                gap: 0.25rem;
            }

            .otcc-construction-card [data-testid="stButton"] {
                margin-top: 0.25rem;
            }

            [data-testid="stButton"] button,
            [data-testid="baseButton-secondary"],
            [data-testid="baseButton-primary"] {
                min-height: 2.35rem !important;
                padding-top: 0.22rem !important;
                padding-bottom: 0.22rem !important;
                font-size: 0.86rem !important;
                line-height: 1.2;
                border-radius: 10px !important;
            }

            .otcc-construction-card div[data-testid="stTextInput"],
            .otcc-construction-card div[data-testid="stNumberInput"],
            .otcc-construction-card div[data-testid="stDateInput"] {
                margin-bottom: 0.08rem;
            }

            .otcc-step4-row [data-baseweb="input"],
            .otcc-step4-row [data-baseweb="select"] {
                min-height: 1.9rem;
            }

            .otcc-step4-row [data-baseweb="input"] input,
            .otcc-step4-row [data-baseweb="select"] input {
                font-size: 0.82rem !important;
            }

            .otcc-construction-card [data-testid="stButton"] button {
                min-height: 2.0rem !important;
                font-size: 0.82rem !important;
            }

            [data-baseweb="input"] input,
            [data-baseweb="select"] input,
            [data-baseweb="textarea"] textarea {
                font-size: 0.9rem !important;
            }

            [data-baseweb="input"],
            [data-baseweb="select"] {
                min-height: 2.2rem;
            }

            [data-testid="stExpander"] details > summary {
                padding-top: 0.26rem;
                padding-bottom: 0.26rem;
                font-size: 0.84rem;
            }

            .otcc-compact-card [data-testid="stExpander"] {
                margin-top: 0.25rem;
            }

            .otcc-grid-4 [data-testid="stHorizontalBlock"],
            .otcc-grid-3 [data-testid="stHorizontalBlock"],
            .otcc-grid-2 [data-testid="stHorizontalBlock"],
            .otcc-actions-row [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
                gap: 0.8rem;
            }

            .otcc-grid-4 [data-testid="column"],
            .otcc-grid-3 [data-testid="column"],
            .otcc-grid-2 [data-testid="column"],
            .otcc-actions-row [data-testid="column"],
            .otcc-main-two-col [data-testid="column"] {
                min-width: 0;
            }

            div[data-testid="stMetricLabel"] > div,
            div[data-testid="stMetricValue"] > div {
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
                overflow-wrap: anywhere;
                word-break: break-word;
            }

            div[data-testid="stMetricLabel"] {
                font-size: 0.74rem;
            }

            @media (max-width: 1440px) {
                .otcc-step23-row [data-testid="column"]:first-child {
                    flex: 0 0 44% !important;
                    width: 44% !important;
                }

                .otcc-step23-row [data-testid="column"]:last-child {
                    flex: 0 0 56% !important;
                    width: 56% !important;
                }

                .otcc-grid-4 [data-testid="column"] {
                    flex: 1 1 calc(50% - 0.65rem) !important;
                    width: calc(50% - 0.65rem) !important;
                }

                .otcc-briefing-title {
                    font-size: 1.2rem;
                }

                .otcc-cmetric-value {
                    font-size: 0.95rem;
                }
            }

            @media (max-width: 1280px) {
                .otcc-grid-3 [data-testid="column"] {
                    flex: 1 1 calc(50% - 0.65rem) !important;
                    width: calc(50% - 0.65rem) !important;
                }
            }

            @media (max-width: 1024px) {
                .otcc-timeline-wrap {
                    gap: 0.15rem;
                }

                .otcc-timeline-stage {
                    min-width: 98px;
                }

                div[data-testid="stMetricValue"] {
                    font-size: 1rem !important;
                }

                .otcc-grid-2 [data-testid="column"],
                .otcc-actions-row [data-testid="column"] {
                    flex: 1 1 calc(50% - 0.8rem) !important;
                    width: calc(50% - 0.8rem) !important;
                }

                .otcc-step23-row [data-testid="column"],
                .otcc-step4-row [data-testid="column"],
                .otcc-step67-row [data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                }
            }

            @media (max-width: 768px) {
                .otcc-commander-title {
                    font-size: 1.02rem;
                }

                .otcc-briefing-title {
                    font-size: 1.04rem;
                }

                .otcc-approval-title {
                    font-size: 0.9rem;
                }

                .otcc-kv-row {
                    grid-template-columns: 1fr;
                    gap: 0.2rem;
                }

                .otcc-grid-4 [data-testid="column"],
                .otcc-grid-3 [data-testid="column"],
                .otcc-grid-2 [data-testid="column"],
                .otcc-actions-row [data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                }

                .otcc-timeline-wrap {
                    flex-wrap: wrap;
                    row-gap: 0.65rem;
                }

                .otcc-timeline-stage {
                    flex: 1 1 calc(25% - 0.25rem);
                    min-width: 132px;
                }

                .otcc-timeline-connector {
                    display: none;
                }

                div[data-testid="stMetricValue"] {
                    font-size: 0.92rem !important;
                }

                .otcc-cmetric-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                }

                .otcc-cmetric-value {
                    font-size: 0.88rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_commander_intro(trade):
    st.markdown(
        """
        <div class="otcc-commander-card">
            <div class="otcc-kicker">Strategy Desk · Options Decision Engine</div>
            <div class="otcc-commander-title">Define today’s options objective.</div>
            <div class="otcc-commander-text">
                Start with intent. The engine uses mission, symbol,
                market bias, and account context to guide construction.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mission_options = [
        {
            "label": "Generate Income",
            "icon": "💰",
            "description": "Collect premium using income-focused option structures.",
        },
        {
            "label": "Buy Shares at a Discount",
            "icon": "🟢",
            "description": "Use options to potentially acquire stock below the current price.",
        },
        {
            "label": "Bullish Directional Trade",
            "icon": "📈",
            "description": "Express a bullish view with controlled risk and defined structure.",
        },
        {
            "label": "Protect Existing Shares",
            "icon": "🛡️",
            "description": "Reduce downside risk or generate income against an existing position.",
        },
        {
            "label": "High Probability Income",
            "icon": "🎯",
            "description": "Prioritize probability, discipline, and premium efficiency.",
        },
    ]

    responsive_block_start("otcc-grid-3")
    cols = st.columns(3)

    for index, mission in enumerate(mission_options):
        selected = trade.mission == mission["label"]
        css_class = "otcc-mission-selected" if selected else "otcc-mission-idle"

        with cols[index % 3]:
            st.markdown(
                f"""
                <div class="{css_class}">
                    <div class="otcc-mission-title">{mission['icon']} {mission['label']}</div>
                    <div class="otcc-mission-desc">{mission['description']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            button_label = "Selected Mission" if selected else "Choose Mission"
            if st.button(
                button_label,
                key=f"otcc_mission_card_{index}",
                use_container_width=True,
            ):
                trade.mission = mission["label"]
                trade.objective = mission["label"]
                trade.reset_validation()
                st.rerun()
    responsive_block_end()




def render_opportunity_selection(trade):
    section_header(
        "Step 1",
        "Opportunity Selection",
        "No upstream packet found. Select the underlying and mission to begin decision workflow.",
    )

    resolve_symbol_handoff(trade)

    with st.container(border=True):
        st.caption("Discovery Mode: manually define the symbol and objective when no lifecycle packet is available.")

        st.session_state.setdefault("otcc_discovery_symbol", str(getattr(trade, "symbol", "") or ""))
        previous_symbol = str(st.session_state.get("otcc_last_symbol_seen", "") or "").strip().upper()
        symbol_value = st.text_input(
            "Underlying Symbol",
            key="otcc_discovery_symbol",
            help=beginner_help("Enter the stock or ETF ticker to evaluate in the Options Decision Center."),
        )

        normalized_symbol = str(symbol_value or "").strip().upper()
        if normalized_symbol:
            if previous_symbol and normalized_symbol != previous_symbol:
                reset_otcc_construction_state(trade)
                st.session_state["otcc_last_symbol_seen"] = normalized_symbol
                trade.symbol = normalized_symbol
                st.rerun()
            st.session_state["otcc_last_symbol_seen"] = normalized_symbol
            trade.symbol = normalized_symbol
            st.caption(f"Selected symbol: {normalized_symbol}")
        else:
            st.info("Enter a symbol to seed strategy selection and trade construction.")

    render_commander_intro(trade)


def apply_trade_lifecycle_packet_to_trade(packet, trade) -> None:
    """Apply canonical packet fields to the local construction trade state."""
    if packet is None or trade is None:
        return
    if packet.identity.symbol:
        trade.symbol = packet.identity.symbol
    try:
        trade.stock_price = float(getattr(packet.identity, "stock_price", 0.0) or 0.0)
    except Exception:
        trade.stock_price = 0.0
    if packet.identity.strategy or packet.construction.strategy_type:
        trade.recommended_strategy = packet.construction.strategy_type or packet.identity.strategy
        trade.strategy = trade.strategy or trade.recommended_strategy
    packet_expiration = _resolve_packet_expiration(packet)
    if packet_expiration is not None:
        trade.expiration = packet_expiration
        st.session_state["otcc_expiration"] = packet_expiration
    if packet.opportunity.summary:
        trade.strategy_reason = packet.opportunity.summary
    if packet.construction.options_quality is not None:
        trade.strategy_confidence = float(packet.construction.options_quality or 0.0)
    else:
        # OP1-0701-H: Options Quality belongs to the construction stage.
        # Do not display an Opportunity score as Options Quality.
        trade.strategy_confidence = 0.0
    if packet.opportunity.approval:
        trade.institutional_grade = packet.opportunity.approval


def apply_decision_packet_if_needed(trade):
    # Canonical-only path: render KPIs from the shared lifecycle packet.
    # OP1-0701-H: run shared backend engines first so missing stage scores can
    # be populated without manually visiting every page.
    if TradeLifecyclePacket is not None:
        if run_shared_trade_lifecycle_engines is not None:
            canonical = run_shared_trade_lifecycle_engines(st.session_state, trade, overwrite=False, save=True)
        else:
            canonical = TradeLifecyclePacket.from_session(st.session_state)
        has_payload = bool(
            canonical.identity.symbol
            or canonical.opportunity.institutional_score is not None
            or canonical.construction.options_quality is not None
        )
        if has_payload:
            fingerprint = canonical.fingerprint()
            loaded = st.session_state.get("otcc_loaded_packet_fingerprint")
            if loaded != fingerprint:
                apply_trade_lifecycle_packet_to_trade(canonical, trade)
                st.session_state["otcc_loaded_packet_fingerprint"] = fingerprint
            return canonical
    return None


def sync_execution_review_to_lifecycle(trade, packet=None, *, resolve_confidence: bool = False):
    """Write Decision Center review output into canonical lifecycle packet."""
    if TradeLifecyclePacket is None or trade is None:
        return packet

    symbol = str(getattr(trade, "symbol", "") or st.session_state.get("selected_symbol") or "").upper().strip()
    if not symbol:
        return packet

    confidence = compute_decision_readiness_score(trade, packet)

    # OP1-0702-A: never preserve the old placeholder Decision Review score.
    # Decision Review now means checklist-based readiness.
    if confidence <= 0:
        existing = getattr(getattr(packet, "execution", None), "execution_confidence", None)
        if existing is not None and not is_placeholder_decision_score(existing):
            confidence = float(existing or 0.0)
    if confidence <= 0:
        return packet

    risk_per_trade = None
    account_size = float(getattr(trade, "account_size", 0.0) or 0.0)
    max_risk_allowed = float(getattr(trade, "max_risk_allowed", 0.0) or 0.0)
    if account_size > 0 and max_risk_allowed > 0:
        risk_per_trade = (max_risk_allowed / account_size) * 100.0

    if isinstance(packet, TradeLifecyclePacket):
        packet.merge_update(
            {
                "identity": {
                    "symbol": symbol,
                    "strategy": trade.active_strategy() or trade.recommended_strategy,
                },
                "execution": {
                    "execution_confidence": confidence,
                    "position_size": float(getattr(trade, "contracts", 0) or 0),
                    "account": str(getattr(trade, "account_type", "") or ""),
                    "risk_per_trade": risk_per_trade,
                    "approval": getattr(trade, "approval_status", None),
                },
            },
            source="Options Decision Center",
            overwrite=False,
        )
        if TradeStage is not None:
            packet.mark_stage_complete(TradeStage.EXECUTION_REVIEW, source="Options Decision Center")
        packet.save_to_session(st.session_state)
        return packet

    return TradeLifecyclePacket.update_execution_in_session(
        st.session_state,
        source="Options Decision Center",
        overwrite=False,
        symbol=symbol,
        strategy=trade.active_strategy() or trade.recommended_strategy,
        execution_confidence=confidence,
        position_size=float(getattr(trade, "contracts", 0) or 0),
        account=str(getattr(trade, "account_type", "") or ""),
        risk_per_trade=risk_per_trade,
        approval=getattr(trade, "approval_status", None),
    )

def render_opportunity_briefing(trade, packet):
    section_header(
        "Step 1",
        "Mission Briefing",
        "Opportunity context received from an upstream JFBP module.",
    )

    source = packet_source_display(packet) or "Lifecycle Engine"
    contributors = packet_contributors_display(packet)
    symbol = packet.symbol or trade.symbol or "Pending"
    strategy = packet.recommended_strategy or trade.recommended_strategy or trade.active_strategy() or "Pending"
    scores = resolve_packet_scores(packet)
    mission = trade.mission or packet.mission or "Pending"
    opportunity_grade = packet.opportunity_grade or "Pending"
    institutional_grade = packet.institutional_grade or trade.institutional_grade or "Pending"

    briefing_html = f"""
        <div class="otcc-briefing-card">
            <div class="otcc-kicker">Strategy Desk · Institutional Briefing Mode</div>
            <div class="otcc-briefing-title">Opportunity Received: {symbol} {strategy}</div>
            <div class="otcc-briefing-meta">
                Source: <strong>{source}</strong> · Contributors: <strong>{contributors}</strong> · Mission: <strong>{mission}</strong><br>
                Opportunity Grade: <strong>{opportunity_grade}</strong> ·
                Institutional Grade: <strong>{institutional_grade}</strong>
            </div>
        </div>
    """
    st.markdown(briefing_html, unsafe_allow_html=True)

    responsive_block_start("otcc-grid-3")
    score_cols = st.columns(3)
    score_cols[0].metric(
        "Options Opportunity",
        scores.get("opportunity_label") or score_label(scores["opportunity_score"], "Waiting for Options Center..."),
        help="Options opportunity score published by Options Center or preserved by the Lifecycle Engine.",
    )
    score_cols[1].metric(
        "Trade Construction",
        scores.get("construction_label") or score_label(scores["options_quality_score"], "Waiting for Options Trade Construction Center..."),
        help="Options quality from Options Center / Trade Construction. Waiting until computed.",
    )
    score_cols[2].metric(
        "Decision Readiness",
        scores.get("execution_label") or score_label(scores["execution_confidence"], "Waiting for Options Decision Center..."),
        help="Checklist-based readiness after Options Decision Center validation and approval.",
    )
    responsive_block_end()

    st.info(
        "The opportunity has been identified and the recommended strategy has been generated. "
        "Complete the institutional review, validate the trade structure, and confirm execution readiness before approving the trade."
    )

    responsive_block_start("otcc-grid-2")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Construct Received Opportunity", key="otcc_construct_packet", use_container_width=True):
            reset_otcc_construction_state(trade)
            trade.user_selected_strategy = strategy if strategy != "Pending" else trade.user_selected_strategy
            trade.strategy = trade.user_selected_strategy or trade.recommended_strategy
            trade.construction_complete = False
            trade.approval_status = PENDING_TEXT
            st.rerun()

    with c2:
        if st.button("Begin New Analysis", key="otcc_clear_packet", use_container_width=True):
            reset_otcc_construction_state(trade, preserve_identity=False)
            st.rerun()
    responsive_block_end()

    with st.expander("Briefing packet details", expanded=False):
        st.json(packet.to_dict())


def render_other_strategy_selection(trade):
    with st.expander("Choose a different strategy", expanded=False):
        strategy_items = list(STRATEGY_REGISTRY.items())
        responsive_block_start("otcc-grid-2")
        rows = [st.columns(2), st.columns(2)]

        for idx, (key, strategy) in enumerate(strategy_items):
            row = rows[idx // 2]
            col = row[idx % 2]

            with col:
                selected = trade.active_strategy() == key
                if strategy_card(key, strategy, selected=selected):
                    reset_otcc_construction_state(trade)
                    trade.user_selected_strategy = key
                    trade.strategy = key
                    trade.construction_complete = False
                    trade.approval_status = PENDING_TEXT
                    trade.reset_results()
                    trade.reset_validation()
                    st.rerun()
        responsive_block_end()


def render_contract_selection_panel(trade, strategy: str, locked: bool) -> None:
    chain_type = strategy_option_chain_type(strategy)
    requested_symbol = str(getattr(trade, "symbol", "") or "").strip().upper()
    requested_expiration = getattr(trade, "expiration", None)
    selection_requested = bool(st.session_state.get(CONTRACT_SELECTION_ACTIVE_KEY, False))

    trade.stock_price = 0.0
    if requested_symbol:
        resolved_price = _resolve_underlying_price(requested_symbol)
        if resolved_price is not None:
            trade.stock_price = resolved_price

    stock_price = float(getattr(trade, "stock_price", 0.0) or 0.0)
    active_key = _active_construction_key(requested_symbol, strategy, requested_expiration, stock_price)
    previous_active_key = str(st.session_state.get(ACTIVE_KEY_STATE, "") or "")
    if previous_active_key != active_key:
        reset_otcc_construction_state(trade)
        st.session_state[ACTIVE_KEY_STATE] = active_key
        trade.stock_price = stock_price
        if selection_requested:
            st.session_state[SELECTOR_OPEN_KEY] = True
            st.session_state[OPTION_CHAIN_PANEL_OPEN_KEY] = True
            st.session_state[CHAIN_MODE_KEY] = chain_type

    selected = st.session_state.get(SELECTED_CONTRACT_KEY)
    if isinstance(selected, dict) and selected.get("label"):
        if not _selected_contract_matches_context(selected, requested_symbol, requested_expiration, strategy):
            st.session_state.pop(SELECTED_CONTRACT_KEY, None)
            st.session_state.pop("otcc_selected_contract", None)
            st.session_state.pop("otcc_selected_long_leg", None)
            st.session_state.pop("otcc_selected_short_leg", None)
            st.session_state.pop("otcc_selected_put_leg", None)
            st.session_state.pop("otcc_selected_call_leg", None)
            st.session_state[STEP4_VALUE_SOURCE_KEY] = "selected_contract_discarded_context_mismatch"
            selected = None

    contract_selected = bool(isinstance(selected, dict) and selected.get("label"))
    button_label = "Change Selected Contract" if contract_selected else "Select Option Contract"
    if st.button(button_label, key="otcc_select_option_contract", use_container_width=False, disabled=locked):
        st.session_state[SELECTOR_OPEN_KEY] = True
        st.session_state[CONTRACT_SELECTION_ACTIVE_KEY] = True
        st.session_state[OPTION_CHAIN_PANEL_OPEN_KEY] = True
        st.session_state[CHAIN_MODE_KEY] = chain_type
        st.rerun()

    if isinstance(selected, dict) and selected.get("label"):
        st.caption(
            "Selected contract: "
            f"{selected.get('label')} | {selected.get('tier')} | "
            f"Score {selected.get('score', 0):,.1f} | "
            f"Confidence {selected.get('confidence', 0):,.1f}%"
        )
        st.info("Contract-derived fields are locked. Use Change Selected Contract to choose a different strike, expiration, or premium.")

    with st.expander(f"Option Chain Selection ({chain_type})", expanded=bool(st.session_state.get(SELECTOR_OPEN_KEY, False))):
        st.caption(f"Option Chain Provider -> Institutional Ranking Engine -> Trade Construction -> Risk Validation -> Approval -> Execution | Strategy chain: {chain_type}")
        st.caption("Future placeholder: when IBKR is active, live chain download and ranking will feed this panel automatically.")

        chain_key = _active_construction_key(requested_symbol, strategy, requested_expiration, stock_price)
        previous_chain_key = str(st.session_state.get(CHAIN_KEY_STATE, "") or "")
        if chain_key != previous_chain_key:
            reset_otcc_construction_state(trade)
            st.session_state[CHAIN_KEY_STATE] = chain_key
            st.session_state[ACTIVE_KEY_STATE] = chain_key
            if selection_requested:
                st.session_state[SELECTOR_OPEN_KEY] = True
                st.session_state[OPTION_CHAIN_PANEL_OPEN_KEY] = True
                st.session_state[CHAIN_MODE_KEY] = chain_type

        # Always rebuild recommendation cards from the current request context.
        contracts = get_ranked_option_chain(
            requested_symbol,
            strategy,
            reference_price=stock_price,
            requested_expiration=requested_expiration,
        )
        st.session_state[OPTION_CHAIN_CACHE_KEY] = {
            "chain_key": chain_key,
            "contracts": contracts,
        }

        st.session_state[GENERATED_STRIKES_KEY] = [float(getattr(c, "strike", 0.0) or 0.0) for c in contracts]
        if not contracts:
            st.info("No current price is available for this symbol yet, so recommendation cards cannot be generated.")
            return

        current_legs = list(getattr(trade, "legs", []) or [])
        if _strategy_requires_second_leg(strategy) and len(current_legs) == 1:
            current_leg = current_legs[0]
            current_side = str(current_leg.get("side") or "").upper()
            current_strike = float(current_leg.get("strike", 0.0) or 0.0)
            if strategy == "Bull Call Spread" and current_side == "BUY":
                contracts = [c for c in contracts if str(getattr(c, "contract_type", "") or "").upper() == "CALL" and float(getattr(c, "strike", 0.0) or 0.0) > current_strike]
                st.info("Select short call to complete spread.")
            elif strategy == "Bull Put Spread" and current_side == "SELL":
                contracts = [c for c in contracts if str(getattr(c, "contract_type", "") or "").upper() == "PUT" and float(getattr(c, "strike", 0.0) or 0.0) < current_strike]
                contracts = list(reversed(contracts))
                st.info("Select long put to complete spread.")
            elif strategy == "Bear Call Spread" and current_side == "SELL":
                contracts = [c for c in contracts if str(getattr(c, "contract_type", "") or "").upper() == "CALL" and float(getattr(c, "strike", 0.0) or 0.0) > current_strike]
                st.info("Select long call to complete spread.")
            elif strategy == "Bear Put Spread" and current_side == "SELL":
                contracts = [c for c in contracts if str(getattr(c, "contract_type", "") or "").upper() == "PUT" and float(getattr(c, "strike", 0.0) or 0.0) < current_strike]
                contracts = list(reversed(contracts))
                st.info("Select long put to complete spread.")

        rendered_strikes = [float(getattr(c, "strike", 0.0) or 0.0) for c in contracts]
        generator_trace = st.session_state.get(CHAIN_TRACE_KEY)
        if not isinstance(generator_trace, dict):
            generator_trace = {}
        st.session_state[CHAIN_TRACE_KEY] = {
            "requested_symbol": requested_symbol,
            "requested_expiration": _normalize_expiration(requested_expiration),
            "current_stock_price": round(stock_price, 2),
            "generated_strikes": list(generator_trace.get("generated_strikes", [])),
            "rendered_strikes": rendered_strikes,
            "chain_key": chain_key,
        }

        for idx, contract in enumerate(contracts):
            with st.container(border=True):
                head_left, head_right = st.columns([1.15, 0.85], gap="small")
                with head_left:
                    st.markdown(f"#### {contract.contract_label}{contract_tier_badge(contract)}")
                with head_right:
                    st.markdown(f"**Bid/Ask:** {money(contract.bid)} / {money(contract.ask)}")
                    st.markdown(f"**Mid:** {money(contract.mid)}")

                metric_rows = [
                    ("Institutional Score", score_label(contract.institutional_score, "Pending")),
                    ("Confidence", percent(contract.confidence)),
                    ("Expected POP", percent(contract.pop)),
                    ("Expected Return", percent(contract.expected_return)),
                    ("Annualized Return", percent(contract.annualized_return)),
                    ("Delta", f"{contract.delta:,.2f}"),
                    ("Volume / OI", f"{contract.volume:,} / {contract.open_interest:,}"),
                ]
                render_native_metric_grid(metric_rows, columns=3, block_class="otcc-grid-3")

                if st.button(
                    f"Use {contract.contract_label}",
                    key=f"otcc_use_contract_{idx}",
                    use_container_width=True,
                    disabled=locked,
                ):
                    apply_option_contract_to_trade(trade, contract, strategy, contracts)
                    sync_trade_from_construction_state(trade)
                    build_trade_math_snapshot(trade)
                    st.session_state["otcc_construction_dirty"] = False
                    st.session_state[CONTRACT_SELECTION_ACTIVE_KEY] = False
                    st.session_state[CHAIN_MODE_KEY] = chain_type
                    st.session_state[OPTION_CHAIN_PANEL_OPEN_KEY] = False
                    st.session_state[SELECTOR_OPEN_KEY] = False
                    st.rerun()

        with st.expander("Developer Debug", expanded=False):
            selected_contract_dbg = st.session_state.get(SELECTED_CONTRACT_KEY)
            if not isinstance(selected_contract_dbg, dict):
                selected_contract_dbg = {}
            chain_trace = st.session_state.get(CHAIN_TRACE_KEY)
            if not isinstance(chain_trace, dict):
                chain_trace = {}
            st.json(
                {
                    "current_symbol": str(getattr(trade, "symbol", "") or "").strip().upper(),
                    "current_strategy": str(strategy or "").strip(),
                    "current_expiration": _normalize_expiration(getattr(trade, "expiration", None)),
                    "step4_value_source": str(st.session_state.get(STEP4_VALUE_SOURCE_KEY, "") or "unknown"),
                    "selected_contract_symbol": str(selected_contract_dbg.get("symbol") or ""),
                    "selected_contract_strike": float(selected_contract_dbg.get("short_strike", 0.0) or 0.0),
                    "selected_contract_premium": float(selected_contract_dbg.get("short_premium", 0.0) or 0.0),
                    "current_stock_price": float(getattr(trade, "stock_price", 0.0) or 0.0),
                    "active_key": str(st.session_state.get(ACTIVE_KEY_STATE, "") or ""),
                    "current_chain_key": str(st.session_state.get(CHAIN_KEY_STATE, "") or ""),
                    "selected_chain_key": str(st.session_state.get(SELECTED_CHAIN_KEY_STATE, "") or ""),
                    "generated_strikes": list(st.session_state.get(GENERATED_STRIKES_KEY, []) or []),
                    "requested_symbol": str(chain_trace.get("requested_symbol") or ""),
                    "requested_expiration": str(chain_trace.get("requested_expiration") or ""),
                    "requested_stock_price": float(chain_trace.get("current_stock_price", 0.0) or 0.0),
                    "trace_generated_strikes": list(chain_trace.get("generated_strikes", []) or []),
                    "trace_rendered_strikes": list(chain_trace.get("rendered_strikes", []) or []),
                }
            )


# ============================================================
# Step 2 — Strategy Selection
# ============================================================

def render_strategy_selection(trade, packet=None):
    locked = packet_is_approved(packet)
    section_header(
        "Step 2",
        "Strategy Recommendation",
        "Accept the recommended structure or deliberately choose a different one.",
    )

    if locked:
        st.info("This trade is approved. Clear Approval in Step 3 before changing the strategy.")

    if not trade.recommended_strategy:
        st.info("No recommendation yet. Complete the trade briefing first.")
        if not locked:
            render_other_strategy_selection(trade)
        else:
            st.caption("Strategy selection is locked because this packet is approved.")
        return

    with st.container(border=True):
        st.markdown("### Recommended Structure")
        responsive_block_start("otcc-grid-2")
        c1, c2 = st.columns(2)
        c1.metric("Strategy", trade.recommended_strategy)
        c2.metric("Options Quality", percent(trade.strategy_confidence) if float(trade.strategy_confidence or 0.0) > 0 else "Waiting for Options Center...")
        responsive_block_end()
        st.write(trade.strategy_reason or "Recommendation received from upstream context.")

        if st.button("Construct Recommended Trade", key="otcc_construct_recommended", use_container_width=True, disabled=locked):
            reset_otcc_construction_state(trade)
            trade.user_selected_strategy = trade.recommended_strategy
            trade.strategy = trade.recommended_strategy
            trade.construction_complete = False
            trade.approval_status = PENDING_TEXT
            trade.reset_results()
            trade.reset_validation()
            st.rerun()

    if not locked:
        render_other_strategy_selection(trade)
    else:
        st.caption("Strategy selection is locked because this packet is approved.")

# ============================================================
# Step 4 — Trade Construction
# ============================================================

def render_trade_construction(trade, packet=None):
    strategy = trade.active_strategy()
    locked = bool(packet and getattr(getattr(packet, "approval", None), "approved", False))
    symbol_seen = str(getattr(trade, "symbol", "") or "").strip().upper()
    strategy_seen = str(strategy or "").strip()
    expiration_seen = _normalize_expiration(st.session_state.get("otcc_expiration", getattr(trade, "expiration", None)))
    previous_symbol_seen = str(st.session_state.get("otcc_last_symbol_seen", "") or "").strip().upper()
    previous_strategy_seen = str(st.session_state.get("otcc_last_strategy_seen", "") or "").strip()
    previous_expiration_seen = str(st.session_state.get("otcc_last_expiration_seen", "") or "").strip()
    if previous_symbol_seen and symbol_seen and symbol_seen != previous_symbol_seen:
        reset_otcc_construction_state(trade)
        st.session_state["otcc_last_symbol_seen"] = symbol_seen
        st.session_state["otcc_last_strategy_seen"] = strategy_seen
        st.session_state["otcc_last_expiration_seen"] = expiration_seen
        st.rerun()
    if previous_strategy_seen and strategy_seen and strategy_seen != previous_strategy_seen:
        reset_otcc_construction_state(trade)
        st.session_state["otcc_last_symbol_seen"] = symbol_seen
        st.session_state["otcc_last_strategy_seen"] = strategy_seen
        st.session_state["otcc_last_expiration_seen"] = expiration_seen
        st.rerun()
    if previous_expiration_seen and expiration_seen and expiration_seen != previous_expiration_seen:
        reset_otcc_construction_state(trade)
        st.session_state["otcc_last_symbol_seen"] = symbol_seen
        st.session_state["otcc_last_strategy_seen"] = strategy_seen
        st.session_state["otcc_last_expiration_seen"] = expiration_seen
        st.rerun()
    st.session_state["otcc_last_symbol_seen"] = symbol_seen
    st.session_state["otcc_last_strategy_seen"] = strategy_seen
    st.session_state["otcc_last_expiration_seen"] = expiration_seen

    context_fingerprint = _construction_context_key(trade)
    previous_context = str(st.session_state.get(CONSTRUCTION_CONTEXT_KEY, "") or "")
    if context_fingerprint != previous_context:
        reset_otcc_construction_state(trade)
        st.session_state[CONSTRUCTION_CONTEXT_KEY] = context_fingerprint
    subtitle_text = "Review the completed strategy prior to validation and approval." if locked else "Enter the trade structure. Strategy math updates live from selected contract legs."
    section_header(
        "Step 4",
        f"{strategy or 'Trade'} Construction",
        subtitle_text,
    )

    if not strategy:
        st.warning("Accept the recommendation or select a strategy first.")
        return

    st.success(f"Selected Strategy: {strategy}")
    render_contract_selection_panel(trade, strategy, locked)
    if beginner_mode_enabled():
        st.info("Beginner Mode is on. Open the lesson below and use the help icons on the fields to stay oriented.")
    if locked:
        st.warning("🔒 Trade construction locked.")
        st.caption("Clear approval to modify this trade.")

    render_strategy_lesson(strategy)

    with st.container(border=True):
        responsive_block_start("otcc-construction-card")
        responsive_block_start("otcc-step4-row")
        left, right = st.columns([1.18, 0.92], gap="medium")

        with left:
            # Manual entry stays isolated here so a future broker option-chain picker can swap in without restructuring Step 4.
            responsive_block_start("otcc-grid-3")
            col1, col2, col3 = st.columns(3)
            st.session_state["otcc_construction_symbol_display"] = str(getattr(trade, "symbol", "") or "").strip().upper()
            st.session_state["otcc_expiration"] = trade.expiration or date.today()
            st.session_state["otcc_short_strike"] = float(trade.strike or 0.0)
            st.session_state["otcc_long_strike"] = float(trade.long_strike or 0.0)
            st.session_state["otcc_short_premium"] = float(trade.premium or 0.0)
            st.session_state["otcc_long_premium"] = float(trade.long_premium or 0.0)
            st.session_state["otcc_contracts"] = int(trade.contracts or 1)

            selected_contract = st.session_state.get(SELECTED_CONTRACT_KEY)
            contract_selected = bool(isinstance(selected_contract, dict) and selected_contract.get("label"))
            has_long_leg = bool(selected_contract.get("has_long_leg", False)) if contract_selected else False
            lock_core_contract_fields = bool(locked or contract_selected)
            lock_long_leg_fields = bool(locked or (contract_selected and has_long_leg))

            with col1:
                st.text_input(
                    "Underlying",
                    key="otcc_construction_symbol_display",
                    disabled=True,
                    help=beginner_help("The stock or ETF you want to own."),
                )

                trade.expiration = st.date_input(
                    "Expiration",
                    key="otcc_expiration",
                    disabled=lock_core_contract_fields,
                    help=beginner_help("Select the expiration date of the option contract you are trading. Use your broker chain date, and do not treat the default date as a recommendation."),
                )

            with col2:
                trade.strike = st.number_input(
                    "Short Strike",
                    min_value=0.0,
                    step=0.5,
                    key="otcc_short_strike",
                    disabled=lock_core_contract_fields,
                    help=beginner_help("Short strike for the option leg you are selling. Confirm strike placement against your directional thesis and risk plan."),
                )

                trade.long_strike = st.number_input(
                    "Long Strike / Protection Strike",
                    min_value=0.0,
                    step=0.5,
                    key="otcc_long_strike",
                    disabled=lock_long_leg_fields,
                    help=beginner_help("Used when the strategy includes a long protection or long debit leg. Single-leg strategies may leave this at 0."),
                )

            with col3:
                trade.premium = st.number_input(
                    "Short Premium",
                    min_value=0.0,
                    step=0.01,
                    key="otcc_short_premium",
                    disabled=lock_core_contract_fields,
                    help=beginner_help("Short Premium is the money received for selling the option. Enter the premium from your broker's option chain."),
                )

                trade.long_premium = st.number_input(
                    "Long Premium",
                    min_value=0.0,
                    step=0.01,
                    key="otcc_long_premium",
                    disabled=lock_long_leg_fields,
                    help=beginner_help("Premium paid for the long option leg. Required for debit spreads and protection legs."),
                )

                trade.contracts = st.number_input(
                    "Contracts",
                    min_value=1,
                    step=1,
                    key="otcc_contracts",
                    disabled=locked,
                    help=beginner_help("Each contract represents 100 shares. Example: 3 contracts = 300 shares."),
                )
            responsive_block_end()

        trade_math = build_trade_math_snapshot(trade)

        with left:
            render_live_explanation_card(trade_math)
            render_institutional_trade_summary(trade_math, None)

        with right:
            responsive_block_start("otcc-live-math-panel")
            render_live_trade_math_dashboard(trade_math)
            responsive_block_end()

        responsive_block_end()

        if st.button("Mark Construction Complete", use_container_width=True, disabled=locked):
            trade.construction_complete = True
            trade.approval_status = "Pending validation"
            st.session_state[OTCC_CONSTRUCTION_COMPLETE_KEY] = True
            st.session_state[OTCC_VALIDATION_COMPLETE_KEY] = False
            st.session_state[STEP5_VALIDATION_COMPLETE_KEY] = False
            st.session_state[STEP5_VALIDATION_STATUS_KEY] = ""
            st.rerun()
        responsive_block_end()

    return trade_math


# ============================================================
# Step 4 — Risk Validation
# ============================================================

def render_risk_validation(trade, packet=None):
    section_header(
        "Step 5",
        "Risk Validation",
        "Validate objective constraints before approval.",
    )

    validation_completed = bool(st.session_state.get(STEP5_VALIDATION_COMPLETE_KEY, False))
    stored_status = str(st.session_state.get(STEP5_VALIDATION_STATUS_KEY, "") or "").upper().strip()

    trade = validate_trade(trade)
    checks = get_validation_checks(trade)

    strategy = str(trade.active_strategy() or trade.recommended_strategy or "").strip()
    capital_check_label = "Required Debit" if strategy_uses_debit_capital(strategy) else "Buying Power"

    display_checks = {
        capital_check_label: checks["Buying Power"],
        "Expiration": checks["Expiration"],
        "Premium Quality": checks["Premium Quality"],
        "Position Size": checks["Position Size"],
        "Breakeven vs Stock": checks["Breakeven vs Stock"],
        "Overall Status": (trade.validation_status, "Aggregate validation result."),
    }

    with st.container(border=True):
        responsive_block_start("otcc-compact-card")
        responsive_block_start("otcc-grid-3")
        cols = st.columns(3)

        for index, (label, (status, message)) in enumerate(display_checks.items()):
            display_status = status
            if label == capital_check_label and str(status).strip().upper() == "REVIEW":
                display_status = "PASS / REVIEW"
            tone_class = validation_status_tone(display_status)
            if tone_class == "pass":
                status_badge = "🟢 PASS"
            elif tone_class == "review":
                status_badge = "🟡 REVIEW"
            elif tone_class == "fail":
                status_badge = "🔴 FAIL"
            else:
                status_badge = "⚪ PENDING"
            with cols[index % 3]:
                st.markdown(
                    f"""
                    <div class="otcc-status-card otcc-status-{tone_class}">
                        <div class="otcc-status-title">{html.escape(label)}</div>
                        <div class="otcc-status-body">{html.escape(status_badge)} — {html.escape(str(message))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        responsive_block_end()
        responsive_block_end()

    if trade.warnings:
        with st.expander("Validation warnings", expanded=False):
            for warning in trade.warnings:
                st.warning(warning)

    if trade.validation_messages:
        with st.expander("Validation detail", expanded=False):
            for message in trade.validation_messages:
                    if str(message).startswith("Buying Power:"):
                        required_value = money(float(getattr(trade, "buying_power_required", 0.0) or 0.0))
                        if strategy_uses_debit_capital(strategy):
                            st.write(f"• Required Debit: {required_value}")
                            st.write("• Trader Confirmation: Verify the net debit amount before execution.")
                        else:
                            st.write(f"• Buying Power Required: {required_value}")
                            st.write("• Trader Confirmation: Verify sufficient buying power exists before execution.")
                    elif str(message).startswith("Position Size:"):
                        st.write("• Position Size: Trader should verify allocation against personal portfolio rules.")
                    else:
                        st.write(f"• {message}")

    construction_complete = bool(st.session_state.get(OTCC_CONSTRUCTION_COMPLETE_KEY, False))
    can_validate = construction_complete
    if validation_completed and stored_status not in {"", "PENDING"}:
        st.success("✅ Validation Complete")

    action_label = "Validation Complete" if validation_completed and stored_status not in {"", "PENDING"} else ("Validate Trade Risk" if can_validate else "Complete Step 4 before validation")
    if st.button(action_label, key="otcc_validate_trade_risk", use_container_width=True, disabled=not can_validate or (validation_completed and stored_status not in {"", "PENDING"})):
        trade = validate_trade(trade)
        status_text = str(getattr(trade, "validation_status", "") or "").upper().strip()
        st.session_state[STEP5_VALIDATION_COMPLETE_KEY] = True
        st.session_state[STEP5_VALIDATION_STATUS_KEY] = status_text
        st.session_state[OTCC_VALIDATION_COMPLETE_KEY] = True
        if isinstance(packet, TradeLifecyclePacket):
            packet.merge_update(
                {
                    "approval": {
                        "notes": f"Risk validation completed: {status_text or 'PENDING'}",
                    }
                },
                source="Options Decision Center",
                overwrite=True,
            )
            packet.save_to_session(st.session_state)
        st.rerun()

    return packet


# ============================================================
# Step 5 — Trade Approval
# ============================================================

def render_trade_approval(trade, packet=None):
    section_header(
        "Step 6",
        "Trade Approval",
        "Convert validation evidence into an approval decision.",
    )

    trade = approve_trade(trade)
    packet = sync_execution_review_to_lifecycle(trade, packet)

    packet_approval = getattr(packet, "approval", None)
    final_approved = bool(getattr(packet_approval, "approved", False)) if packet_approval is not None else False
    final_approved_by = str(getattr(packet_approval, "approved_by", "") or "Pending") if packet_approval is not None else "Pending"
    final_approved_ts = str(getattr(packet_approval, "approved_timestamp", "") or "Pending") if packet_approval is not None else "Pending"

    construction_complete = bool(st.session_state.get(OTCC_CONSTRUCTION_COMPLETE_KEY, False))
    validation_complete = bool(st.session_state.get(OTCC_VALIDATION_COMPLETE_KEY, False))
    trade_math_ready = all(
        [
            float(getattr(trade, "strike", 0.0) or 0.0) > 0,
            float(getattr(trade, "premium", 0.0) or 0.0) > 0,
            int(getattr(trade, "contracts", 0) or 0) >= 1,
            float(getattr(trade, "buying_power_required", 0.0) or 0.0) > 0,
            float(getattr(trade, "max_loss", 0.0) or 0.0) > 0,
            float(getattr(trade, "breakeven", 0.0) or 0.0) > 0,
        ]
    )
    can_finalize_approval = bool(construction_complete and validation_complete and trade_math_ready)
    computed_grade = institutional_grade_from_packet(packet, trade)
    trade.institutional_grade = computed_grade

    with st.container(border=True):
        responsive_block_start("otcc-compact-card")
        readiness_score = compute_decision_readiness_score(trade, packet)
        outstanding = 0
        if not trade.construction_complete:
            outstanding += 1
        outstanding += len(getattr(trade, "warnings", []) or [])

        st.markdown("### Institutional Decision")
        render_native_metric_grid(
            [
                ("Institutional Grade", computed_grade),
                ("Decision Readiness", f"{readiness_score:,.1f}%"),
                ("Approval Status", "Approved for Execution" if final_approved else (trade.approval_status or "WAIT")),
                ("Outstanding Issues", str(outstanding)),
            ],
            columns=4,
            block_class="otcc-grid-4",
        )

        st.markdown(
            "<div class='otcc-kv-card'>"
            + f"<div class='otcc-kv-row'><div class='otcc-kv-key'>Approved By</div><div class='otcc-kv-val'>{html.escape(final_approved_by)}</div></div>"
            + f"<div class='otcc-kv-row'><div class='otcc-kv-key'>Timestamp</div><div class='otcc-kv-val'>{html.escape(final_approved_ts)}</div></div>"
            + "</div>",
            unsafe_allow_html=True,
        )

        if outstanding > 0:
            st.warning(f"Outstanding Issues: {outstanding}")
        else:
            st.success("No outstanding issues.")

        st.markdown("**Decision Summary**")
        approval_state = str(trade.approval_status or "").upper().strip()
        if final_approved:
            decision_summary = "All institutional reviews have been completed. Trade approved and ready for execution."
        elif approval_state in {"REJECT", "FAILED", "FAIL", "NEEDS ADJUSTMENT"}:
            decision_summary = "Trade requires additional review before execution."
        else:
            decision_summary = "Waiting for construction and validation."
        st.info(decision_summary)

        if not construction_complete:
            st.warning("Construction is not marked complete yet. The approval engine will remain in WAIT mode.")
        if not can_finalize_approval:
            missing = []
            if not construction_complete:
                missing.append("Construction not complete")
            if not validation_complete:
                missing.append("Validation not complete")
            if not trade_math_ready:
                missing.append("Trade math not ready")
            st.warning("Final approval is blocked: " + " | ".join(missing))

        strategy = str(trade.active_strategy() or trade.recommended_strategy or "").strip()
        if trade.warnings:
            with st.expander("Approval Warnings", expanded=False):
                for warning in trade.warnings:
                    warning_text = str(warning)
                    if "Available buying power has not been entered" in warning_text:
                        required_value = money(float(getattr(trade, "buying_power_required", 0.0) or 0.0))
                        if strategy_uses_debit_capital(strategy):
                            st.warning(f"Verify that your broker order uses approximately {required_value} net debit before execution.")
                        else:
                            st.warning(f"Verify that your brokerage account has at least {required_value} available buying power before execution.")
                    elif "No account size or max risk limit is available" in warning_text:
                        st.warning("Verify this position size fits your portfolio allocation guidelines.")
                    else:
                        st.warning(warning_text)

        if trade.validation_messages:
            with st.expander("Approval Evidence", expanded=False):
                for message in trade.validation_messages:
                    if str(message).startswith("Buying Power:"):
                        required_value = money(float(getattr(trade, "buying_power_required", 0.0) or 0.0))
                        if strategy_uses_debit_capital(strategy):
                            st.write(f"• Required Debit: {required_value}")
                            st.write("• Trader Confirmation: Verify the net debit amount before execution.")
                        else:
                            st.write(f"• Buying Power Required: {required_value}")
                            st.write("• Trader Confirmation: Verify sufficient buying power exists before execution.")
                    elif str(message).startswith("Position Size:"):
                        st.write("• Position Size: Trader should verify allocation against personal portfolio rules.")
                    else:
                        st.write(f"• {message}")

        responsive_block_start("otcc-actions-row")
        a1, a2, a3 = st.columns(3)
        with a1:
            if st.button("Approve Trade", key="otcc_approve_trade_final", use_container_width=True, type="primary", disabled=final_approved):
                if not can_finalize_approval:
                    st.warning("Complete Step 4 construction and Step 5 validation before final approval.")
                else:
                    approve_packet_in_lifecycle(trade, packet)
                    st.rerun()
        with a2:
            if st.button("Clear Approval", key="otcc_clear_trade_approval_final", use_container_width=True, disabled=not final_approved):
                clear_packet_approval(trade, packet)
                st.rerun()
        with a3:
            if st.button("Cancel Decision", key="otcc_cancel_trade_decision_final", use_container_width=True):
                clear_packet_approval(trade, packet)
                st.rerun()
        responsive_block_end()

        st.caption("Phase 4 approval engine.")
        responsive_block_end()


# ============================================================
# Step 6 — Execution Package
# ============================================================

def render_execution_package(trade):
    section_header(
        "Step 7",
        "Execution Package",
        "Generated order ticket and management plan.",
    )

    trade = approve_trade(trade)
    ticket = build_execution_ticket(trade)

    strategy = trade.active_strategy() or "Pending"
    is_debit_strategy = strategy_uses_debit_capital(strategy)
    capital_label = "Maximum Capital at Risk" if is_debit_strategy else "Buying Power"
    symbol = trade.symbol or "Pending"

    summary_rows = [
        ("Underlying", symbol),
        ("Strategy", strategy),
        ("Expiration", str(getattr(trade, "expiration", "") or "Pending")),
        ("Strike", f"{float(getattr(trade, 'strike', 0.0) or 0.0):.2f}" if float(getattr(trade, 'strike', 0.0) or 0.0) > 0 else "Pending"),
        ("Premium", money(getattr(trade, "premium", 0.0) or 0.0)),
        ("Contracts", int(getattr(trade, "contracts", 0) or 0)),
    ]
    if is_debit_strategy:
        summary_rows.extend(
            [
                ("Required Debit", money(getattr(trade, "debit", 0.0) or 0.0)),
                ("Maximum Capital at Risk", money(getattr(trade, "buying_power_required", 0.0) or 0.0)),
            ]
        )
    else:
        summary_rows.append((capital_label, money(getattr(trade, "buying_power_required", 0.0) or 0.0)))
    summary_rows.extend(
        [
            ("Maximum Risk", money(getattr(trade, "max_loss", 0.0) or 0.0)),
            ("Maximum Profit", money(getattr(trade, "max_profit", 0.0) or 0.0)),
            ("Reward / Risk", f"{float(getattr(trade, 'reward_risk_ratio', 0.0) or 0.0):,.4f}"),
            ("Breakeven", money(getattr(trade, "breakeven", 0.0) or 0.0)),
        ]
    )

    with st.container(border=True):
        responsive_block_start("otcc-compact-card")
        st.markdown("### Execution Summary")
        render_native_metric_grid(summary_rows, columns=4, block_class="otcc-grid-4")

        with st.expander("OMS Ticket", expanded=False):
            st.code(ticket["order_summary"], language="text")

        with st.expander("Entry Orders", expanded=False):
            trade.entry_plan = st.text_area(
                "Entry Orders",
                value=ticket["entry_orders"],
                key="otcc_entry_plan",
            )

        with st.expander("Profit Target", expanded=False):
            st.text_area(
                "Profit Target",
                value=ticket["profit_target"],
                key="otcc_profit_target",
                disabled=True,
            )

        with st.expander("Exit Rules", expanded=False):
            trade.exit_plan = st.text_area(
                "Exit Rules",
                value=ticket["exit_rules"],
                key="otcc_exit_plan",
            )

        with st.expander("Adjustment Plan", expanded=False):
            st.text_area(
                "Adjustment Plan",
                value=ticket["adjustment_plan"],
                key="otcc_adjustment_plan",
                disabled=True,
            )

        with st.expander("Assignment / Exercise Notes", expanded=False):
            trade.assignment_plan = st.text_area(
                "Assignment / Exercise Notes",
                value=ticket["assignment_exercise_notes"],
                key="otcc_assignment_plan",
            )

        with st.expander("Risk Notes", expanded=False):
            trade.risk_notes = st.text_area(
                "Risk Notes",
                value=ticket["risk_notes"],
                key="otcc_risk_notes",
            )
            if strategy_uses_debit_capital(strategy):
                st.info(
                    "Defined-risk debit strategy: maximum loss is limited to the net debit paid.\n\n"
                    "No stock ownership is required to open this trade."
                )
            else:
                st.info(
                    "Assignment is not a loss event by itself.\n\n"
                    "Assignment simply converts the option position into stock ownership.\n\n"
                    "Future profit or loss then depends on how the stock performs after assignment."
                )
        responsive_block_end()


# ============================================================
# Main
# ============================================================

def main():
    if not _otcc_dev_access_enabled():
        _render_otcc_temporarily_unavailable()

    trade = get_trade()
    inject_commander_css()
    st.session_state.setdefault(BEGINNER_MODE_KEY, False)
    st.session_state.setdefault(OTCC_CONSTRUCTION_COMPLETE_KEY, bool(getattr(trade, "construction_complete", False)))
    existing_validation_status = str(getattr(trade, "validation_status", "") or "").upper().strip()
    st.session_state.setdefault(OTCC_VALIDATION_COMPLETE_KEY, existing_validation_status not in {"", "PENDING"})
    packet = apply_decision_packet_if_needed(trade)

    # On page load, resolve Decision Review immediately from current trade
    # state and persist it to lifecycle without requiring user interaction.
    has_valid_context = bool(
        (packet is not None and (getattr(packet, "symbol", "") or getattr(packet, "recommended_strategy", "")))
        or (str(getattr(trade, "symbol", "") or "").strip() and str(trade.active_strategy() or trade.recommended_strategy or "").strip())
    )
    if has_valid_context:
        packet = sync_execution_review_to_lifecycle(trade, packet, resolve_confidence=True)


    st.title(f"{PAGE_ICON} Options Decision Center")
    st.caption(
        "Institutional workflow for receiving, evaluating, validating, and approving options trades."
    )

    render_beginner_mode_toggle()

    with st.expander("ℹ️ How to Use the Options Decision Center", expanded=False):
        st.markdown(
            """
## Before You Begin

The **Options Decision Center** does **not** search for trading opportunities.

It receives opportunities that have already been analyzed by the JFBP Quant Desk Quant Engine.

Choose one of the following entry points:

### 🎯 Opportunity Center

Displays the highest-ranked opportunities across all asset classes.

Use this when you want the Quant Engine to select the best opportunity available.

### 🛡️ Options Center

Displays opportunities specifically qualified for options strategies.

Use this when you only want trades that are suitable for options.

Click **Options Decision Center** to send the selected opportunity into the institutional trade workflow.

## Institutional Workflow

### 1. Receive Opportunity

Receive a qualified opportunity from:

- Opportunity Center
- Options Center

↓

### 2. Mission Briefing

Review why the Quant Engine selected this opportunity.

↓

### 3. Strategy Recommendation

Review the recommended options strategy.

↓

### 4. Institutional Review

Verify that institutional quality standards have been met.

↓

### 5. Trade Construction

Select an option contract (or manually enter one) and review the live calculations.

↓

### 6. Risk Validation

Confirm:

- Buying Power
- Break-even
- Maximum Loss
- ROI
- Annualized Return
- Risk Metrics

↓

### 7. Trade Approval

Approve the completed trade after all institutional checks pass.

↓

### 8. Execution Package

Review the final institutional trade ticket before sending the order to your broker.
"""
        )
        st.info(
            "💡 **New to Options?**\n\n"
            "The Options Decision Center walks you through each step.\n\n"
            "If you are unfamiliar with options terminology, open the **Strategy Lesson** and use the **ⓘ Help** icons beside each field. "
            "The system explains each concept as you build the trade."
        )

    render_step_separator()
    if packet is not None:
        render_opportunity_briefing(trade, packet)
    else:
        render_opportunity_selection(trade)

    render_workflow_progress(trade, packet)

    render_step_separator()
    responsive_block_start("otcc-step23-row")
    col_left, col_right = st.columns([0.95, 1.15], gap="medium")
    with col_left:
        render_strategy_selection(trade, packet)
    with col_right:
        packet = render_commander_approval(trade, packet)
    responsive_block_end()

    render_step_separator()
    trade_math = render_trade_construction(trade, packet)
    trade_for_downstream = trade_math if trade_math is not None else trade

    render_step_separator()
    packet = render_risk_validation(trade_for_downstream, packet)

    render_step_separator()
    responsive_block_start("otcc-step67-row")
    col_approval, col_execution = st.columns(2, gap="medium")
    with col_approval:
        render_trade_approval(trade_for_downstream, packet)
    with col_execution:
        render_execution_package(trade_for_downstream)
    responsive_block_end()


def run_page():
    main()


if __name__ == "__main__":
    main()
