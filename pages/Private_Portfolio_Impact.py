# =========================================================
# 🔒 PRIVATE PORTFOLIO DASHBOARD
# JFBP Quant Desk
# Family Office compression pass + How-to-use guide + organized tabs
# =========================================================

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core.responsive import inject_responsive_css as jfbp_inject_responsive_css
from core.responsive import columns as jfbp_columns
from core.ui_cards import inject_card_css as jfbp_inject_card_css
from core.ui_cards import metric_card as jfbp_metric_card

from analytics.market_reaction import generate_market_reaction_report

try:
    from pages.SaaS_Core import get_supabase_client
except Exception:  # pragma: no cover
    get_supabase_client = None

try:
    import yfinance as yf
except Exception:
    yf = None


# =========================================================
# CONFIG
# =========================================================

DATA_DIR = Path("data")
TRANSACTIONS_FILE = DATA_DIR / "private_portfolio_transactions.csv"
LEGACY_HOLDINGS_FILE = DATA_DIR / "private_portfolio_holdings.csv"
PRIVATE_PORTFOLIO_TABLE = "portfolio_positions"

ACCOUNT_OPTIONS = [
    "TFSA",
    "RRSP",
    "Non-Registered",
    "TFSA USD",
    "RRSP USD",
    "Non-Registered USD",
]

PORTFOLIO_OPTIONS = [
    "All Accounts",
    "CAD Accounts",
    "USD Accounts",
    "TFSA",
    "RRSP",
    "Non-Registered",
    "TFSA USD",
    "RRSP USD",
    "Non-Registered USD",
]

USD_ACCOUNTS = {
    "TFSA USD",
    "RRSP USD",
    "Non-Registered USD",
}

CAD_ACCOUNTS = {
    "TFSA",
    "RRSP",
    "Non-Registered",
}

TRANSACTION_TYPES = [
    "BUY",
    "SELL",
    "DIVIDEND",
    "DRIP",
    "EARNINGS",
    "INTEREST",
    "MANUFACTURED_DIVIDEND",
    "CASH_DEPOSIT",
    "CASH_WITHDRAWAL",
]

CASH_TRANSACTION_TYPES = {
    "CASH_DEPOSIT",
    "CASH_WITHDRAWAL",
}

INCOME_TRANSACTION_TYPES = {
    "DIVIDEND",
    "EARNINGS",
    "INTEREST",
    "MANUFACTURED_DIVIDEND",
}

TRANSACTION_COLUMNS = [
    "Date",
    "Account",
    "Symbol",
    "Type",
    "Shares",
    "Price",
    "Amount",
    "Notes",
]


# =========================================================
# HELPERS
# =========================================================

def format_pct(value):
    if value is None:
        return "N/A"

    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.2f}%"
    except Exception:
        return "N/A"


def format_money(value):
    if value is None:
        return "N/A"

    try:
        if pd.isna(value):
            return "N/A"
        return f"${float(value):,.2f}"
    except Exception:
        return "N/A"


def format_money_currency(value, currency: str = "CAD"):
    money = format_money(value)

    if money == "N/A":
        return money

    currency = str(currency or "CAD").upper().strip()
    return f"{money} {currency}"


def safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def clean_symbol(symbol) -> str:
    return str(symbol or "").upper().strip()


def clean_account(account) -> str:
    account_text = str(account or "").strip()

    if account_text in ACCOUNT_OPTIONS:
        return account_text

    account_key = (
        account_text.upper()
        .replace("_", "-")
        .replace("/", " ")
        .replace("  ", " ")
        .strip()
    )

    if account_key in ("TFSA", "TFSA CAD"):
        return "TFSA"

    if account_key in ("RRSP", "RRSP CAD"):
        return "RRSP"

    if account_key in ("NON-REGISTERED", "NON REGISTERED", "TAXABLE", "NON-REGISTERED CAD"):
        return "Non-Registered"

    if account_key in ("TFSA USD", "USD TFSA"):
        return "TFSA USD"

    if account_key in ("RRSP USD", "USD RRSP"):
        return "RRSP USD"

    if account_key in ("NON-REGISTERED USD", "NON REGISTERED USD", "TAXABLE USD", "USD NON-REGISTERED"):
        return "Non-Registered USD"

    return "TFSA"


def account_currency(account) -> str:
    account = clean_account(account)
    return "USD" if account in USD_ACCOUNTS else "CAD"


def clean_transaction_type(value) -> str:
    text = str(value or "").upper().strip().replace(" ", "_").replace("-", "_")

    if text in TRANSACTION_TYPES:
        return text

    if text in ("MARKET_BUY", "BUY_TO_OPEN", "PURCHASE"):
        return "BUY"

    if text in ("REINVESTED", "DIVIDEND_REINVESTED"):
        return "DRIP"

    if text in ("DIV", "CASH_DIVIDEND"):
        return "DIVIDEND"

    if text in ("INT", "CASH_INTEREST"):
        return "INTEREST"

    if text in ("EARNING", "EARN"):
        return "EARNINGS"

    if text in ("DEPOSIT", "CASH_IN", "CONTRIBUTION", "CONTRIBUTION_IN", "ADD_CASH"):
        return "CASH_DEPOSIT"

    if text in ("WITHDRAWAL", "WITHDRAW", "CASH_OUT", "REMOVE_CASH"):
        return "CASH_WITHDRAWAL"

    return "BUY"


def _current_saas_user_id() -> str:
    saas_user = st.session_state.get("saas_user")
    user_id = getattr(saas_user, "user_id", "") if saas_user is not None else ""

    if user_id:
        return str(user_id or "").strip()

    auth_user = (
        st.session_state.get("user")
        or st.session_state.get("auth_user")
        or {}
    )

    if isinstance(auth_user, dict):
        user_id = auth_user.get("id") or auth_user.get("user_id") or ""
        if user_id:
            return str(user_id or "").strip()

    user_obj = getattr(auth_user, "user", None)
    if user_obj is not None:
        user_id = getattr(user_obj, "id", "") or getattr(user_obj, "user_id", "")
        if user_id:
            return str(user_id or "").strip()

    user_id = getattr(auth_user, "id", "") or getattr(auth_user, "user_id", "")
    return str(user_id or "").strip()


def _transactions_file_for_user(user_id: str) -> Path:
    user_id = str(user_id or "").strip()
    if not user_id:
        return DATA_DIR / "private_portfolio_transactions_anonymous.csv"

    safe_user = "".join(ch for ch in user_id.lower() if ch.isalnum())[:32]
    if not safe_user:
        safe_user = "anonymous"
    return DATA_DIR / f"private_portfolio_transactions_{safe_user}.csv"


def _private_portfolio_supabase_available(user_id: str) -> tuple[bool, str, object]:
    user_id = str(user_id or "").strip()
    if not user_id:
        return False, "Login required for user-scoped Supabase persistence.", None

    if get_supabase_client is None:
        return False, "Supabase client import is unavailable.", None

    try:
        client = get_supabase_client()
    except Exception as exc:
        return False, f"Supabase client unavailable: {exc}", None

    if client is None:
        return False, "Supabase client unavailable.", None

    try:
        (
            client.table(PRIVATE_PORTFOLIO_TABLE)
            .select("user_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        return (
            False,
            "Private portfolio table missing or inaccessible. Expected table: "
            f"{PRIVATE_PORTFOLIO_TABLE}. Error: {exc}",
            client,
        )

    return True, "", client


def _supabase_rows_to_transactions_df(rows) -> pd.DataFrame:
    if not rows:
        return empty_transactions_df()

    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        symbol = clean_symbol(row.get("symbol") or row.get("Symbol") or "")
        if not symbol:
            continue

        shares = safe_float(row.get("shares") or row.get("Shares"), 0.0)
        avg_price = safe_float(row.get("avg_price") or row.get("Avg Cost") or row.get("Price"), 0.0)
        cost_basis = safe_float(row.get("cost_basis") or row.get("Cost Basis"), 0.0)
        market_value = safe_float(row.get("market_value") or row.get("Market Value"), 0.0)
        realized_pnl = safe_float(row.get("realized_pnl") or row.get("Realized P&L"), 0.0)

        # portfolio_positions stores symbol-level snapshots, not full ledger rows.
        amount = cost_basis if cost_basis > 0 else shares * avg_price
        notes = (
            "Imported from Supabase position snapshot"
            f" (market_value={market_value:.2f}, realized_pnl={realized_pnl:.2f})"
        )

        normalized.append(
            {
                "Date": str(row.get("date") or row.get("Date") or "").strip(),
                "Account": clean_account(row.get("account") or row.get("Account") or "TFSA"),
                "Symbol": symbol,
                "Type": clean_transaction_type(row.get("transaction_type") or row.get("type") or row.get("Type") or "BUY"),
                "Shares": shares,
                "Price": avg_price,
                "Amount": amount,
                "Notes": str(row.get("notes") or row.get("Notes") or notes).strip(),
            }
        )

    if not normalized:
        return empty_transactions_df()

    return clean_transactions_df(pd.DataFrame(normalized, columns=TRANSACTION_COLUMNS)).reset_index(drop=True)


def _transactions_df_to_supabase_rows(transactions_df: pd.DataFrame, user_id: str) -> list[dict]:
    rows = []
    transactions = clean_transactions_df(transactions_df)

    if transactions.empty:
        return rows

    grouped = transactions.groupby(["Symbol"], dropna=False)

    for (symbol,), group in grouped:
        symbol = clean_symbol(symbol)
        if not symbol:
            continue

        shares = 0.0
        cost_basis = 0.0
        realized_pnl = 0.0

        for _, tx in group.iterrows():
            tx_type = clean_transaction_type(tx.get("Type"))
            tx_shares = safe_float(tx.get("Shares"))
            tx_price = safe_float(tx.get("Price"))
            tx_amount = safe_float(tx.get("Amount"))

            if tx_type in ("BUY", "DRIP"):
                trade_cost = tx_amount if tx_amount > 0 else tx_shares * tx_price
                shares += tx_shares
                cost_basis += trade_cost
            elif tx_type == "SELL":
                if shares > 0 and tx_shares > 0:
                    avg_cost_before_sale = cost_basis / shares if shares > 0 else 0.0
                    sale_proceeds = tx_amount if tx_amount > 0 else tx_shares * tx_price
                    cost_removed = avg_cost_before_sale * tx_shares
                    realized_pnl += sale_proceeds - cost_removed
                    shares -= tx_shares
                    cost_basis -= cost_removed

        if shares <= 0:
            continue

        avg_price = cost_basis / shares if shares > 0 else 0.0
        market_value = shares * avg_price

        rows.append(
            {
                "user_id": user_id,
                "symbol": symbol,
                "shares": float(shares),
                "cost_basis": float(max(cost_basis, 0.0)),
                "market_value": float(max(market_value, 0.0)),
                "avg_price": float(max(avg_price, 0.0)),
                "realized_pnl": float(realized_pnl),
            }
        )

    return rows


def _load_transactions_fallback_local(user_id: str, default_df: pd.DataFrame) -> pd.DataFrame:
    fallback_file = _transactions_file_for_user(user_id)

    if fallback_file.exists():
        try:
            transactions_df = pd.read_csv(fallback_file)
            return clean_transactions_df(transactions_df).reset_index(drop=True)
        except Exception as exc:
            st.session_state["private_portfolio_last_persistence_error"] = f"Local fallback load failed: {exc}"

    if not user_id and TRANSACTIONS_FILE.exists():
        try:
            transactions_df = pd.read_csv(TRANSACTIONS_FILE)
            return clean_transactions_df(transactions_df).reset_index(drop=True)
        except Exception as exc:
            st.session_state["private_portfolio_last_persistence_error"] = f"Legacy local load failed: {exc}"

    transactions_df = migrate_legacy_holdings_to_transactions()

    if transactions_df.empty and default_df is not None and not default_df.empty:
        transactions_df = default_df.copy()

    return clean_transactions_df(transactions_df).reset_index(drop=True)


def _save_transactions_fallback_local(transactions_df: pd.DataFrame, user_id: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fallback_file = _transactions_file_for_user(user_id)
    clean_df = clean_transactions_df(transactions_df)
    clean_df.to_csv(fallback_file, index=False)




def private_portfolio_url(
    view_name: str = "All Accounts",
    focus_account: str = "",
    focus_symbol: str = "",
) -> str:
    """Internal navigation URL for this Private Portfolio page.

    These links stay inside the Private Portfolio page. Account links open the
    selected account view and the account drilldown. Symbol links open the
    symbol drilldown showing every account where that symbol exists, plus any
    closed trades.
    """
    view_name = str(view_name or "All Accounts").strip()

    if view_name not in PORTFOLIO_OPTIONS:
        view_name = clean_account(view_name)

    if view_name not in PORTFOLIO_OPTIONS:
        view_name = "All Accounts"

    params = [f"portfolio_view={quote_plus(view_name)}"]

    focus_account = str(focus_account or "").strip()
    if focus_account:
        params.append(f"focus_account={quote_plus(clean_account(focus_account))}")

    focus_symbol = clean_symbol(focus_symbol)
    if focus_symbol:
        params.append(f"focus_symbol={quote_plus(focus_symbol)}")

    return "?" + "&".join(params)


def portfolio_view_url(view_name) -> str:
    """Internal page link that reloads the dashboard with the selected portfolio view."""
    return private_portfolio_url(view_name=view_name)


def symbol_link(symbol) -> str:
    """Render symbol text.

    Real navigation is handled by Portfolio Navigation Center using Streamlit
    buttons/selectors. HTML links were removed because relative hrefs can be
    hijacked by the app router and open the wrong page.
    """
    symbol = clean_symbol(symbol)
    if not symbol:
        return ""
    return f'<span class="jfbp-link jfbp-symbol-link">{html.escape(symbol)}</span>'

def account_link(account) -> str:
    """Render account text without leaving the Private Portfolio page.

    Real navigation is handled by Portfolio Navigation Center using Streamlit
    buttons/selectors.
    """
    account_text = str(account or "All Accounts").strip()

    if account_text not in PORTFOLIO_OPTIONS:
        account_text = clean_account(account_text)

    if account_text not in PORTFOLIO_OPTIONS:
        account_text = "All Accounts"

    return f'<span class="jfbp-link jfbp-account-link">{html.escape(account_text)}</span>'

def _query_param_value(name: str, default: str = "") -> str:
    try:
        value = st.query_params.get(name, default)
        if isinstance(value, list):
            value = value[0] if value else default
    except Exception:
        value = default

    return str(value or default).strip()


def get_requested_portfolio_view() -> str:
    """Read portfolio_view from the URL query string, safely."""
    requested = _query_param_value("portfolio_view", "All Accounts")
    return requested if requested in PORTFOLIO_OPTIONS else "All Accounts"


def get_requested_focus_account() -> str:
    requested = _query_param_value("focus_account", "")

    if not requested:
        return ""

    if requested in PORTFOLIO_OPTIONS:
        return requested

    cleaned = clean_account(requested)
    return cleaned if cleaned in ACCOUNT_OPTIONS else ""


def get_requested_focus_symbol() -> str:
    return clean_symbol(_query_param_value("focus_symbol", ""))


def calculate_impact_label(portfolio_move: float) -> str:
    abs_move = abs(portfolio_move)

    if abs_move >= 2.0:
        return "HIGH"

    if abs_move >= 1.0:
        return "MODERATE"

    return "LOW"


def metric_card(label: str, value, detail: str = "", tone: str = "neutral"):
    """Shared JFBP metric card wrapper for Private Portfolio.

    The local function name is preserved for compatibility with the existing
    page, while the visual rendering now comes from core.ui_cards.
    """
    jfbp_metric_card(label, value, detail, tone=tone)



def render_private_portfolio_help() -> None:
    """User guide for the Private Portfolio / Family Office page."""
    with st.expander("📘 How to use this page", expanded=False):
        st.markdown(
            """
            **Private Portfolio is your personal Family Office dashboard.** It tracks your CAD and USD accounts, holdings, income, allocation, ledger history, realized gains, and cash-flow-aware performance.

            **Recommended workflow**
            1. Choose the Portfolio View: All Accounts, CAD Accounts, USD Accounts, TFSA, RRSP, or Non-Registered.
            2. Review the Commander Wealth Report and Executive Wealth Brief first.
            3. Use Portfolio Navigation Center to drill into an account or symbol.
            4. Review the tabs: Accounts & Holdings, Allocation, Income, Ledger, Realized P&L, and Cash Flow.
            5. Update the Transaction Ledger whenever you buy, sell, receive dividends, make deposits, or make withdrawals.

            **Important sections**
            - **Commander Wealth Report:** the fast read on status, value, income, return, concentration, and next action.
            - **Accounts & Holdings:** account balances, holding cards, portfolio health, and radar signals.
            - **Allocation:** currency exposure, asset allocation, grade, and rebalancing guidance.
            - **Income:** dividends received, projected annual/monthly income, yield on cost, and income forecast.
            - **Ledger:** the source-of-truth transaction database.
            - **Realized P&L:** closed-trade profit/loss from SELL transactions.
            - **Cash Flow:** deposits and withdrawals used for time-weighted return readiness.

            **Best practice:** keep the ledger clean. The more complete the BUY, SELL, DIVIDEND, DRIP, CASH_DEPOSIT, and CASH_WITHDRAWAL rows are, the more accurate the dashboard becomes.
            """
        )

def normalize_market_df(portfolio_df: pd.DataFrame | None) -> pd.DataFrame:
    if portfolio_df is None or portfolio_df.empty:
        return pd.DataFrame(
            columns=[
                "Symbol",
                "Name",
                "Change %",
                "Weight",
                "Price",
                "Contribution %",
            ]
        )

    df = portfolio_df.copy()

    rename_map = {
        "symbol": "Symbol",
        "ticker": "Symbol",
        "name": "Name",
        "Daily %": "Change %",
        "daily_pct": "Change %",
        "Weight %": "Weight",
        "weight": "Weight",
        "Current Price": "Price",
        "price": "Price",
        "last": "Price",
        "close": "Price",
        "Contribution %": "Contribution %",
        "contribution_pct": "Contribution %",
    }

    df = df.rename(
        columns={
            col: rename_map.get(col, col)
            for col in df.columns
        }
    )

    if "Symbol" not in df.columns:
        df.insert(0, "Symbol", "N/A")

    if "Name" not in df.columns:
        df["Name"] = df["Symbol"]

    if "Change %" not in df.columns:
        df["Change %"] = 0.0

    if "Weight" not in df.columns:
        df["Weight"] = 0.0

    if "Price" not in df.columns:
        df["Price"] = None

    if "Contribution %" not in df.columns:
        df["Contribution %"] = 0.0

    df["Symbol"] = df["Symbol"].map(clean_symbol)
    df["Name"] = df["Name"].astype(str)

    df["Change %"] = pd.to_numeric(
        df["Change %"],
        errors="coerce",
    ).fillna(0.0)

    df["Weight"] = pd.to_numeric(
        df["Weight"],
        errors="coerce",
    ).fillna(0.0)

    df["Contribution %"] = pd.to_numeric(
        df["Contribution %"],
        errors="coerce",
    ).fillna(0.0)

    df["Price"] = pd.to_numeric(
        df["Price"],
        errors="coerce",
    )

    return df[
        [
            "Symbol",
            "Name",
            "Change %",
            "Weight",
            "Price",
            "Contribution %",
        ]
    ].drop_duplicates(
        subset=["Symbol"],
        keep="first",
    )


def default_transactions_from_market(market_df: pd.DataFrame) -> pd.DataFrame:
    if market_df is None or market_df.empty:
        return pd.DataFrame(columns=TRANSACTION_COLUMNS)

    rows = []

    for symbol in market_df["Symbol"].dropna().unique():
        symbol = clean_symbol(symbol)

        if not symbol or symbol == "N/A":
            continue

        rows.append(
            {
                "Date": "",
                "Account": "TFSA",
                "Symbol": symbol,
                "Type": "BUY",
                "Shares": 0.0,
                "Price": 0.0,
                "Amount": 0.0,
                "Notes": "",
            }
        )

    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def empty_transactions_df() -> pd.DataFrame:
    return pd.DataFrame(columns=TRANSACTION_COLUMNS)


def clean_transactions_df(transactions_df: pd.DataFrame) -> pd.DataFrame:
    df = transactions_df.copy()

    for col in TRANSACTION_COLUMNS:
        if col not in df.columns:
            if col in ("Date", "Symbol", "Notes"):
                df[col] = ""
            elif col == "Account":
                df[col] = "TFSA"
            elif col == "Type":
                df[col] = "BUY"
            else:
                df[col] = 0.0

    df = df[TRANSACTION_COLUMNS].copy()

    df["Date"] = df["Date"].fillna("").astype(str)
    df["Account"] = df["Account"].map(clean_account)
    df["Type"] = df["Type"].map(clean_transaction_type)
    df["Symbol"] = df["Symbol"].map(clean_symbol)

    # Cash-flow rows are account-level events, so the symbol can be blank.
    # We normalize blank cash-flow symbols to CASH so data_editor rows are
    # preserved and TWR / cash-flow analytics can read them.
    cash_mask = df["Type"].isin(CASH_TRANSACTION_TYPES)
    df.loc[cash_mask & (df["Symbol"].astype(str).str.strip() == ""), "Symbol"] = "CASH"

    for col in ["Shares", "Price", "Amount"]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        ).fillna(0.0)

    df.loc[cash_mask, "Shares"] = 0.0
    df.loc[cash_mask, "Price"] = 0.0

    df["Notes"] = df["Notes"].fillna("").astype(str)

    df = df[
        df["Symbol"].astype(str).str.strip() != ""
    ].copy()

    return df.reset_index(drop=True)


def migrate_legacy_holdings_to_transactions() -> pd.DataFrame:
    if not LEGACY_HOLDINGS_FILE.exists():
        return empty_transactions_df()

    try:
        legacy_df = pd.read_csv(LEGACY_HOLDINGS_FILE)
    except Exception:
        return empty_transactions_df()

    if legacy_df.empty:
        return empty_transactions_df()

    rows = []

    for _, row in legacy_df.iterrows():
        account = clean_account(row.get("Account"))
        symbol = clean_symbol(row.get("Symbol"))

        if not symbol:
            continue

        initial_shares = safe_float(
            row.get("Initial Shares", row.get("Shares", 0.0))
        )
        initial_cost = safe_float(
            row.get("Initial Avg Cost", row.get("Avg Cost", 0.0))
        )
        initial_date = str(
            row.get(
                "Initial Purchase Date",
                row.get("Purchase Date", ""),
            )
            or ""
        )

        if initial_shares > 0:
            rows.append(
                {
                    "Date": initial_date,
                    "Account": account,
                    "Symbol": symbol,
                    "Type": "BUY",
                    "Shares": initial_shares,
                    "Price": initial_cost,
                    "Amount": initial_shares * initial_cost,
                    "Notes": "Migrated initial buy",
                }
            )

        added_shares = safe_float(row.get("Added Shares", 0.0))
        added_cost = safe_float(row.get("Added Avg Cost", 0.0))
        added_date = str(row.get("Added Date", "") or "")

        if added_shares > 0:
            rows.append(
                {
                    "Date": added_date,
                    "Account": account,
                    "Symbol": symbol,
                    "Type": "BUY",
                    "Shares": added_shares,
                    "Price": added_cost,
                    "Amount": added_shares * added_cost,
                    "Notes": "Migrated added shares",
                }
            )

        reinvested_shares = safe_float(row.get("Reinvested Shares", 0.0))
        reinvested_cost = safe_float(row.get("Reinvested Avg Cost", 0.0))
        reinvested_date = str(row.get("Reinvested Date", "") or "")

        if reinvested_shares > 0:
            rows.append(
                {
                    "Date": reinvested_date,
                    "Account": account,
                    "Symbol": symbol,
                    "Type": "DRIP",
                    "Shares": reinvested_shares,
                    "Price": reinvested_cost,
                    "Amount": reinvested_shares * reinvested_cost,
                    "Notes": "Migrated dividend reinvestment",
                }
            )

        dividends = safe_float(row.get("Dividends Received", 0.0))
        dividend_date = str(row.get("Dividend Date", "") or "")

        if dividends > 0:
            rows.append(
                {
                    "Date": dividend_date,
                    "Account": account,
                    "Symbol": symbol,
                    "Type": "DIVIDEND",
                    "Shares": 0.0,
                    "Price": 0.0,
                    "Amount": dividends,
                    "Notes": "Migrated dividend",
                }
            )

    if not rows:
        return empty_transactions_df()

    return clean_transactions_df(
        pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)
    )


def load_transactions(default_df: pd.DataFrame, user_id: str | None = None) -> pd.DataFrame:
    """Load the saved transaction ledger.

    Important behavior:
    - If data/private_portfolio_transactions.csv exists, it is the source of truth.
    - We do NOT reseed deleted rows from Market Pulse/default holdings.
    - Defaults are only used the very first time, when no saved ledger exists.

    This prevents deleted holdings, such as VFV in RRSP, from coming back after
    refresh or Streamlit restart.
    """
    user_id = str(user_id or "").strip()
    st.session_state["private_portfolio_current_user_id"] = user_id
    st.session_state["private_portfolio_user_id_present"] = bool(user_id)

    if user_id:
        ready, reason, client = _private_portfolio_supabase_available(user_id)
        if ready:
            try:
                response = (
                    client.table(PRIVATE_PORTFOLIO_TABLE)
                    .select("*")
                    .eq("user_id", user_id)
                    .order("symbol")
                    .execute()
                )
                rows = getattr(response, "data", None) or []
                loaded_df = _supabase_rows_to_transactions_df(rows)
                st.session_state["private_portfolio_supabase_loaded"] = True
                st.session_state["private_portfolio_supabase_load_status"] = "OK"
                st.session_state["private_portfolio_last_persistence_error"] = ""
                st.session_state["private_portfolio_record_count"] = len(loaded_df)
                return loaded_df
            except Exception as exc:
                st.session_state["private_portfolio_supabase_loaded"] = False
                st.session_state["private_portfolio_supabase_load_status"] = "ERROR"
                st.session_state["private_portfolio_last_persistence_error"] = f"Supabase load failed: {exc}"
                st.warning(f"Private Portfolio load warning: Supabase load failed ({exc}). Using emergency fallback for this user.")
        else:
            st.session_state["private_portfolio_supabase_loaded"] = False
            st.session_state["private_portfolio_supabase_load_status"] = "SKIPPED"
            st.session_state["private_portfolio_last_persistence_error"] = reason
            st.warning(f"Private Portfolio load warning: Supabase unavailable ({reason}). Using emergency fallback for this user.")

        fallback_df = _load_transactions_fallback_local(user_id=user_id, default_df=default_df)
        st.session_state["private_portfolio_record_count"] = len(fallback_df)
        return fallback_df

    st.session_state["private_portfolio_supabase_loaded"] = False
    st.session_state["private_portfolio_supabase_load_status"] = "SKIPPED"
    anon_df = _load_transactions_fallback_local(user_id="", default_df=default_df)
    st.session_state["private_portfolio_record_count"] = len(anon_df)
    return anon_df


def save_transactions(transactions_df: pd.DataFrame, user_id: str | None = None) -> None:
    user_id = str(user_id or "").strip()

    if user_id:
        ready, reason, client = _private_portfolio_supabase_available(user_id)
        rows = _transactions_df_to_supabase_rows(transactions_df, user_id)

        if ready:
            try:
                (
                    client.table(PRIVATE_PORTFOLIO_TABLE)
                    .delete()
                    .eq("user_id", user_id)
                    .execute()
                )

                if rows:
                    client.table(PRIVATE_PORTFOLIO_TABLE).insert(rows).execute()

                st.session_state["private_portfolio_supabase_saved"] = True
                st.session_state["private_portfolio_supabase_save_status"] = "OK"
                st.session_state["private_portfolio_last_persistence_error"] = ""
                st.session_state["private_portfolio_record_count"] = len(rows)
                _save_transactions_fallback_local(transactions_df, user_id=user_id)
                return
            except Exception as exc:
                st.session_state["private_portfolio_supabase_saved"] = False
                st.session_state["private_portfolio_supabase_save_status"] = "ERROR"
                st.session_state["private_portfolio_last_persistence_error"] = f"Supabase save failed: {exc}"
                st.warning(f"Private Portfolio save warning: Supabase save failed ({exc}). Using emergency fallback for this user.")
        else:
            st.session_state["private_portfolio_supabase_saved"] = False
            st.session_state["private_portfolio_supabase_save_status"] = "SKIPPED"
            st.session_state["private_portfolio_last_persistence_error"] = reason
            st.warning(f"Private Portfolio save warning: Supabase unavailable ({reason}). Using emergency fallback for this user.")

        _save_transactions_fallback_local(transactions_df, user_id=user_id)
        st.session_state["private_portfolio_record_count"] = len(clean_transactions_df(transactions_df))
        return

    st.session_state["private_portfolio_supabase_saved"] = False
    st.session_state["private_portfolio_supabase_save_status"] = "SKIPPED"
    _save_transactions_fallback_local(transactions_df, user_id="")
    st.session_state["private_portfolio_record_count"] = len(clean_transactions_df(transactions_df))


@st.cache_data(ttl=300)
def fetch_usd_cad_rate() -> float:
    if yf is None:
        return 1.37

    try:
        ticker = yf.Ticker("CAD=X")
        history = ticker.history(period="5d")

        if history is None or history.empty:
            return 1.37

        return float(history["Close"].dropna().iloc[-1])

    except Exception:
        return 1.37


def fx_to_cad(currency: str, usd_cad_rate: float) -> float:
    return float(usd_cad_rate) if str(currency).upper().strip() == "USD" else 1.0


@st.cache_data(ttl=300)
def fetch_current_prices(symbols: tuple[str, ...]) -> dict[str, float]:
    prices: dict[str, float] = {}

    if yf is None:
        return prices

    for symbol in symbols:
        symbol = clean_symbol(symbol)

        if not symbol:
            continue

        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period="5d")

            if history is None or history.empty:
                continue

            price = history["Close"].dropna().iloc[-1]
            prices[symbol] = float(price)

        except Exception:
            continue

    return prices


def build_private_portfolio_table(
    transactions_df: pd.DataFrame,
    market_df: pd.DataFrame,
) -> pd.DataFrame:
    transactions = clean_transactions_df(
        transactions_df
    )

    # Cash deposits and withdrawals are account-level cash-flow records.
    # They feed the cash-flow / TWR engine, but they are not holdings and
    # should not create a fake CASH position in the holdings table.
    transactions = transactions[
        ~transactions["Type"].isin(CASH_TRANSACTION_TYPES)
    ].copy()

    market = market_df.copy()

    if "Symbol" not in market.columns:
        market["Symbol"] = ""

    market["Symbol"] = market["Symbol"].map(clean_symbol)

    market_lookup = market.drop_duplicates(
        subset=["Symbol"],
        keep="first",
    ).set_index("Symbol")

    rows = []

    grouped = transactions.groupby(
        ["Account", "Symbol"],
        dropna=False,
    )

    for (account, symbol), group in grouped:
        account = clean_account(account)
        symbol = clean_symbol(symbol)

        if not symbol:
            continue

        shares = 0.0
        cost_basis = 0.0
        dividends = 0.0
        realized_gain = 0.0

        for _, tx in group.iterrows():
            tx_type = clean_transaction_type(tx.get("Type"))
            tx_shares = safe_float(tx.get("Shares"))
            tx_price = safe_float(tx.get("Price"))
            tx_amount = safe_float(tx.get("Amount"))

            if tx_type == "BUY":
                trade_cost = tx_amount if tx_amount > 0 else tx_shares * tx_price
                shares += tx_shares
                cost_basis += trade_cost

            elif tx_type == "DRIP":
                trade_cost = tx_amount if tx_amount > 0 else tx_shares * tx_price
                shares += tx_shares
                cost_basis += trade_cost

            elif tx_type == "SELL":
                if shares > 0 and tx_shares > 0:
                    avg_cost_before_sale = cost_basis / shares if shares > 0 else 0.0
                    sale_proceeds = (
                        tx_amount
                        if tx_amount > 0
                        else tx_shares * tx_price
                    )
                    cost_removed = avg_cost_before_sale * tx_shares
                    realized_gain += sale_proceeds - cost_removed
                    shares -= tx_shares
                    cost_basis -= cost_removed

            elif tx_type in ("DIVIDEND", "MANUFACTURED_DIVIDEND", "EARNINGS", "INTEREST"):
                dividends += tx_amount

        if symbol in market_lookup.index:
            market_row = market_lookup.loc[symbol]
            name = str(market_row.get("Name", symbol))
            change_pct = safe_float(market_row.get("Change %"))
            price = safe_float(market_row.get("Price"), default=float("nan"))
        else:
            name = symbol
            change_pct = 0.0
            price = float("nan")

        currency = account_currency(account)

        rows.append(
            {
                "Account": account,
                "Currency": currency,
                "Symbol": symbol,
                "Name": name,
                "Total Shares": max(shares, 0.0),
                "Cost Basis": max(cost_basis, 0.0),
                "Dividends": dividends,
                "Realized $": realized_gain,
                "Day %": change_pct,
                "Price": price,
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "Account",
                "Currency",
                "Symbol",
                "Name",
                "Total Shares",
                "Avg Cost",
                "Price",
                "Market Value",
                "Cost Basis",
                "Dividends",
                "Realized $",
                "Unrealized $",
                "Total Gain $",
                "Total Return %",
                "Day %",
                "Weight",
                "Contribution %",
            ]
        )

    missing_price_symbols = tuple(
        df.loc[
            df["Price"].isna(),
            "Symbol",
        ].dropna().unique()
    )

    fetched_prices = fetch_current_prices(
        missing_price_symbols
    )

    if fetched_prices:
        df["Price"] = df.apply(
            lambda row: fetched_prices.get(
                clean_symbol(row.get("Symbol")),
                row.get("Price"),
            )
            if pd.isna(row.get("Price"))
            else row.get("Price"),
            axis=1,
        )

    df["Price"] = pd.to_numeric(
        df["Price"],
        errors="coerce",
    )

    usd_cad_rate = fetch_usd_cad_rate()

    df["FX to CAD"] = df["Currency"].apply(
        lambda currency: fx_to_cad(currency, usd_cad_rate)
    )

    df["Market Value"] = df["Total Shares"] * df["Price"].fillna(0.0)

    df["Avg Cost"] = df.apply(
        lambda row: (
            row["Cost Basis"] / row["Total Shares"]
            if row["Total Shares"] > 0
            else 0.0
        ),
        axis=1,
    )

    df["Unrealized $"] = df["Market Value"] - df["Cost Basis"]
    df["Total Gain $"] = (
        df["Unrealized $"]
        + df["Dividends"]
        + df["Realized $"]
    )

    df["Market Value CAD"] = df["Market Value"] * df["FX to CAD"]
    df["Cost Basis CAD"] = df["Cost Basis"] * df["FX to CAD"]
    df["Dividends CAD"] = df["Dividends"] * df["FX to CAD"]
    df["Realized CAD"] = df["Realized $"] * df["FX to CAD"]
    df["Unrealized CAD"] = df["Unrealized $"] * df["FX to CAD"]
    df["Total Gain CAD"] = df["Total Gain $"] * df["FX to CAD"]

    df["Total Return %"] = df.apply(
        lambda row: (
            row["Total Gain $"] / row["Cost Basis"] * 100
            if row["Cost Basis"] > 0
            else 0.0
        ),
        axis=1,
    )

    total_market_value = float(df["Market Value CAD"].sum())

    df["Weight"] = df.apply(
        lambda row: (
            row["Market Value CAD"] / total_market_value * 100
            if total_market_value > 0
            else 0.0
        ),
        axis=1,
    )

    df["Contribution %"] = (
        df["Weight"]
        * df["Day %"]
        / 100
    )

    display_cols = [
        "Account",
        "Currency",
        "Symbol",
        "Name",
        "Total Shares",
        "Avg Cost",
        "Price",
        "Market Value",
        "Cost Basis",
        "Dividends",
        "Realized $",
        "Unrealized $",
        "Total Gain $",
        "Market Value CAD",
        "Cost Basis CAD",
        "Dividends CAD",
        "Realized CAD",
        "Unrealized CAD",
        "Total Gain CAD",
        "Total Return %",
        "Day %",
        "Weight",
        "Contribution %",
    ]

    return df[display_cols].sort_values(
        "Market Value",
        ascending=False,
        na_position="last",
    )




def build_realized_trades_table(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Build a realized P&L table from SELL transactions.

    Uses average-cost accounting within each Account/Symbol group. This makes
    closed and partial sales visible even when the position no longer appears
    in active holdings.
    """
    transactions = clean_transactions_df(transactions_df)

    if transactions.empty:
        return pd.DataFrame(
            columns=[
                "Date",
                "Account",
                "Currency",
                "Symbol",
                "Shares Sold",
                "Sell Price",
                "Sale Proceeds",
                "Cost Removed",
                "Realized P&L",
                "Realized P&L CAD",
                "Return %",
                "Notes",
            ]
        )

    working = transactions.copy()
    working["_row_order"] = range(len(working))
    working["_date_sort"] = pd.to_datetime(
        working["Date"],
        errors="coerce",
    )

    rows = []

    for (account, symbol), group in working.groupby(["Account", "Symbol"], dropna=False):
        account = clean_account(account)
        symbol = clean_symbol(symbol)

        if not symbol:
            continue

        group = group.sort_values(
            ["_date_sort", "_row_order"],
            na_position="last",
        )

        shares = 0.0
        cost_basis = 0.0
        currency = account_currency(account)
        fx_rate = fx_to_cad(currency, fetch_usd_cad_rate())

        for _, tx in group.iterrows():
            tx_type = clean_transaction_type(tx.get("Type"))
            tx_shares = safe_float(tx.get("Shares"))
            tx_price = safe_float(tx.get("Price"))
            tx_amount = safe_float(tx.get("Amount"))

            if tx_type in ("BUY", "DRIP"):
                trade_cost = tx_amount if tx_amount > 0 else tx_shares * tx_price
                shares += tx_shares
                cost_basis += trade_cost

            elif tx_type == "SELL":
                if tx_shares <= 0:
                    continue

                sale_proceeds = (
                    tx_amount
                    if tx_amount > 0
                    else tx_shares * tx_price
                )

                if shares > 0:
                    avg_cost_before_sale = cost_basis / shares
                    cost_removed = avg_cost_before_sale * min(tx_shares, shares)
                else:
                    avg_cost_before_sale = 0.0
                    cost_removed = 0.0

                realized_gain = sale_proceeds - cost_removed
                realized_return = (
                    realized_gain / cost_removed * 100
                    if cost_removed > 0
                    else 0.0
                )

                rows.append(
                    {
                        "Date": str(tx.get("Date", "")),
                        "Account": account,
                        "Currency": currency,
                        "Symbol": symbol,
                        "Shares Sold": tx_shares,
                        "Sell Price": tx_price if tx_price > 0 else (sale_proceeds / tx_shares if tx_shares > 0 else 0.0),
                        "Sale Proceeds": sale_proceeds,
                        "Cost Removed": cost_removed,
                        "Realized P&L": realized_gain,
                        "Realized P&L CAD": realized_gain * fx_rate,
                        "Return %": realized_return,
                        "Notes": str(tx.get("Notes", "")),
                    }
                )

                shares -= min(tx_shares, shares)
                cost_basis -= min(cost_removed, cost_basis)

    realized_df = pd.DataFrame(rows)

    if realized_df.empty:
        return pd.DataFrame(
            columns=[
                "Date",
                "Account",
                "Currency",
                "Symbol",
                "Shares Sold",
                "Sell Price",
                "Sale Proceeds",
                "Cost Removed",
                "Realized P&L",
                "Realized P&L CAD",
                "Return %",
                "Notes",
            ]
        )

    realized_df["_date_sort"] = pd.to_datetime(
        realized_df["Date"],
        errors="coerce",
    )

    realized_df = realized_df.sort_values(
        ["_date_sort", "Symbol", "Account"],
        ascending=[False, True, True],
        na_position="last",
    ).drop(columns=["_date_sort"])

    return realized_df.reset_index(drop=True)


def render_realized_pnl_center(realized_df: pd.DataFrame) -> None:
    """Render realized profit/loss cards and a closed-trades table."""
    if realized_df is None or realized_df.empty:
        st.info("No SELL transactions recorded yet. Realized profit/loss will appear here after a sale is saved.")
        return

    total_realized = float(realized_df["Realized P&L CAD"].sum())
    total_proceeds = float(
        (
            realized_df["Sale Proceeds"]
            * realized_df["Currency"].map(lambda currency: fx_to_cad(currency, fetch_usd_cad_rate()))
        ).sum()
    )
    closed_trades = int(len(realized_df))
    wins = int((realized_df["Realized P&L CAD"] > 0).sum())
    losses = int((realized_df["Realized P&L CAD"] < 0).sum())

    best_row = realized_df.sort_values("Realized P&L CAD", ascending=False).iloc[0]
    worst_row = realized_df.sort_values("Realized P&L CAD", ascending=True).iloc[0]

    row1 = st.columns(4)

    with row1[0]:
        metric_card(
            "Realized P&L",
            f"{format_money(total_realized)} CAD",
            "Closed/partial sales",
            tone="good" if total_realized >= 0 else "risk",
        )

    with row1[1]:
        metric_card(
            "Sale Proceeds",
            f"{format_money(total_proceeds)} CAD",
            f"{closed_trades} sell transaction(s)",
            tone="neutral",
        )

    with row1[2]:
        metric_card(
            "Win / Loss",
            f"{wins}/{losses}",
            "Profitable vs losing sells",
            tone="good" if wins >= losses else "warning",
        )

    with row1[3]:
        metric_card(
            "Best Sale",
            str(best_row.get("Symbol", "N/A")),
            f"{format_money(best_row.get('Realized P&L CAD'))} CAD",
            tone="good" if safe_float(best_row.get("Realized P&L CAD")) >= 0 else "risk",
        )

    display_df = realized_df.copy()

    columns = [
        ("Date", "Date", "text"),
        ("Account", "Account", "account"),
        ("Symbol", "Symbol", "symbol"),
        ("Shares Sold", "Shares Sold", "number"),
        ("Sell Price", "Sell Price", "money_native"),
        ("Sale Proceeds", "Sale Proceeds", "money_native"),
        ("Cost Removed", "Cost Removed", "money_native"),
        ("Realized P&L", "Realized P&L", "money_native_gain"),
        ("Realized P&L CAD", "P&L CAD", "money_cad_gain"),
        ("Return %", "Return %", "pct_gain"),
        ("Notes", "Notes", "text"),
    ]

    def cell_text(row, source_col: str, kind: str) -> tuple[str, str]:
        currency = row.get("Currency", "CAD")
        value = row.get(source_col)

        if kind == "account":
            return account_link(value), "account"

        if kind == "symbol":
            return symbol_link(value), "symbol"

        if kind == "number":
            return f"{safe_float(value):,.4f}", "num"

        if kind == "money_native":
            return html.escape(format_money_currency(value, currency)), "num"

        if kind == "money_native_gain":
            numeric = safe_float(value)
            css = "gain" if numeric >= 0 else "loss"
            return html.escape(format_money_currency(numeric, currency)), f"num {css} strong"

        if kind == "money_cad_gain":
            numeric = safe_float(value)
            css = "gain" if numeric >= 0 else "loss"
            return html.escape(format_money_currency(numeric, "CAD")), f"num {css} strong"

        if kind == "pct_gain":
            numeric = safe_float(value)
            css = "gain" if numeric >= 0 else "loss"
            return html.escape(format_pct(numeric)), f"num {css} strong"

        return html.escape(str(value)), ""

    header_html = "".join(
        f"<th>{html.escape(label)}</th>"
        for source, label, kind in columns
    )

    body_rows = []
    for _, row in display_df.iterrows():
        cells = []
        for source, label, kind in columns:
            text, css = cell_text(row, source, kind)
            cells.append(f'<td class="{css}">{text}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    st.markdown(
        f"""
        <style>
            .jfbp-realized-table-wrap {{
                width: 100%;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                background: white;
                margin-top: 0.25rem;
                margin-bottom: 1.25rem;
            }}
            .jfbp-realized-table {{
                width: 100%;
                border-collapse: collapse;
                table-layout: auto;
                font-size: clamp(0.72rem, 0.60vw, 0.88rem);
            }}
            .jfbp-realized-table th {{
                background: #f8fafc;
                color: #64748b;
                text-align: left;
                padding: 0.55rem 0.55rem;
                border-bottom: 1px solid #d1d5db;
                font-weight: 850;
                white-space: nowrap;
            }}
            .jfbp-realized-table td {{
                padding: 0.52rem 0.55rem;
                border-bottom: 1px solid #e5e7eb;
                color: #111827;
                white-space: nowrap;
            }}
            .jfbp-realized-table tr:last-child td {{
                border-bottom: none;
            }}
            .jfbp-realized-table .num {{
                text-align: right;
            }}
            .jfbp-realized-table .strong {{
                font-weight: 850;
            }}
            .jfbp-realized-table .symbol {{
                color: #2563eb;
                font-weight: 900;
            }}
            .jfbp-realized-table .gain {{
                color: #15803d;
            }}
            .jfbp-realized-table .loss {{
                color: #dc2626;
            }}
        </style>
        <div class="jfbp-realized-table-wrap">
            <table class="jfbp-realized-table">
                <thead><tr>{header_html}</tr></thead>
                <tbody>{''.join(body_rows)}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )



def _format_drilldown_df(df: pd.DataFrame) -> pd.DataFrame:
    """Small helper for clean drilldown dataframes."""
    if df is None or df.empty:
        return pd.DataFrame()

    display_df = df.copy()

    money_cols = [
        "Market Value",
        "Cost Basis",
        "Dividends",
        "Realized $",
        "Unrealized $",
        "Total Gain $",
        "Market Value CAD",
        "Total Gain CAD",
        "Sale Proceeds",
        "Cost Removed",
        "Realized P&L",
        "Realized P&L CAD",
        "Amount",
        "Price",
    ]

    pct_cols = [
        "Total Return %",
        "Return %",
        "Day %",
        "Weight",
    ]

    for col in money_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].map(format_money)

    for col in pct_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].map(format_pct)

    return display_df


def render_drilldown_center(
    clean_df: pd.DataFrame,
    realized_trades_df: pd.DataFrame,
    saved_transactions_df: pd.DataFrame,
    focus_account: str = "",
    focus_symbol: str = "",
) -> None:
    """Internal destination for account and symbol links.

    Account link behavior:
    - Opens the selected account view.
    - Shows open positions, closed trades, and ledger rows for that account.

    Symbol link behavior:
    - Opens all accounts where the symbol exists.
    - Shows open positions, closed trades, and ledger rows for that symbol.
    """
    if focus_account and focus_account not in PORTFOLIO_OPTIONS:
        focus_account = clean_account(focus_account)
    focus_symbol = clean_symbol(focus_symbol)

    if not focus_account and not focus_symbol:
        return

    title_parts = []
    if focus_account:
        title_parts.append(focus_account)
    if focus_symbol:
        title_parts.append(focus_symbol)

    st.subheader("🔎 Drilldown Center")
    st.caption(
        "Internal portfolio navigation. Account links show account activity; "
        "symbol links show every account holding or trading that symbol."
    )

    if title_parts:
        metric_card(
            "Current Drilldown",
            " · ".join(title_parts),
            "Open holdings, closed trades, and transaction history",
            tone="info",
        )

    open_df = clean_df.copy() if clean_df is not None else pd.DataFrame()
    closed_df = realized_trades_df.copy() if realized_trades_df is not None else pd.DataFrame()
    tx_df = saved_transactions_df.copy() if saved_transactions_df is not None else pd.DataFrame()

    def account_focus_mask(series: pd.Series) -> pd.Series:
        accounts = series.map(clean_account)

        if focus_account == "All Accounts":
            return pd.Series(True, index=series.index)

        if focus_account == "CAD Accounts":
            return accounts.isin(CAD_ACCOUNTS)

        if focus_account == "USD Accounts":
            return accounts.isin(USD_ACCOUNTS)

        if focus_account == "TFSA":
            return accounts.isin({"TFSA", "TFSA USD"})

        if focus_account == "RRSP":
            return accounts.isin({"RRSP", "RRSP USD"})

        if focus_account == "Non-Registered":
            return accounts.isin({"Non-Registered", "Non-Registered USD"})

        return accounts == focus_account

    if focus_account:
        if not open_df.empty and "Account" in open_df.columns:
            open_df = open_df[account_focus_mask(open_df["Account"])].copy()
        if not closed_df.empty and "Account" in closed_df.columns:
            closed_df = closed_df[account_focus_mask(closed_df["Account"])].copy()
        if not tx_df.empty and "Account" in tx_df.columns:
            tx_df = tx_df[account_focus_mask(tx_df["Account"])].copy()

    if focus_symbol:
        if not open_df.empty and "Symbol" in open_df.columns:
            open_df = open_df[open_df["Symbol"].map(clean_symbol) == focus_symbol].copy()
        if not closed_df.empty and "Symbol" in closed_df.columns:
            closed_df = closed_df[closed_df["Symbol"].map(clean_symbol) == focus_symbol].copy()
        if not tx_df.empty and "Symbol" in tx_df.columns:
            tx_df = tx_df[tx_df["Symbol"].map(clean_symbol) == focus_symbol].copy()

    open_positions = open_df[
        pd.to_numeric(open_df.get("Total Shares", 0), errors="coerce").fillna(0.0) > 0
    ].copy() if not open_df.empty and "Total Shares" in open_df.columns else pd.DataFrame()

    summary_cols = [
        col for col in [
            "Account",
            "Currency",
            "Symbol",
            "Total Shares",
            "Avg Cost",
            "Price",
            "Market Value",
            "Market Value CAD",
            "Cost Basis",
            "Unrealized $",
            "Realized $",
            "Dividends",
            "Total Gain $",
            "Total Return %",
            "Weight",
        ]
        if col in open_positions.columns
    ]

    realized_cols = [
        col for col in [
            "Date",
            "Account",
            "Currency",
            "Symbol",
            "Shares Sold",
            "Sell Price",
            "Sale Proceeds",
            "Cost Removed",
            "Realized P&L",
            "Realized P&L CAD",
            "Return %",
            "Notes",
        ]
        if col in closed_df.columns
    ]

    tx_cols = [
        col for col in [
            "Date",
            "Account",
            "Symbol",
            "Type",
            "Shares",
            "Price",
            "Amount",
            "Notes",
        ]
        if col in tx_df.columns
    ]

    tab_open, tab_closed, tab_ledger = st.tabs(
        [
            "Open Positions",
            "Closed Trades / Realized P&L",
            "Ledger Rows",
        ]
    )

    with tab_open:
        if open_positions.empty:
            st.info("No open position found for this selection.")
        else:
            st.dataframe(
                _format_drilldown_df(open_positions[summary_cols]),
                use_container_width=True,
                hide_index=True,
            )

    with tab_closed:
        if closed_df.empty:
            st.info("No closed trades found for this selection.")
        else:
            st.dataframe(
                _format_drilldown_df(closed_df[realized_cols]),
                use_container_width=True,
                hide_index=True,
            )

    with tab_ledger:
        if tx_df.empty:
            st.info("No transaction ledger rows found for this selection.")
        else:
            tx_display = tx_df[tx_cols].copy()
            if "Date" in tx_display.columns:
                tx_display["_date_sort"] = pd.to_datetime(tx_display["Date"], errors="coerce")
                tx_display = tx_display.sort_values("_date_sort", ascending=False, na_position="last").drop(columns=["_date_sort"])
            st.dataframe(
                _format_drilldown_df(tx_display),
                use_container_width=True,
                hide_index=True,
            )

    if st.button(
        "Clear drilldown",
        width="stretch",
        key="portfolio_drilldown_clear_inside",
    ):
        _clear_drilldown_state()
        st.rerun()


def render_portfolio_table(df: pd.DataFrame):
    """Render a responsive HTML portfolio table directly in the Streamlit page.

    This avoids the fixed iframe behavior from components.html and gives Safari
    a normal responsive table. On smaller screens, lower-priority columns are
    hidden while the key portfolio columns remain visible.
    """
    if df is None or df.empty:
        st.info("No portfolio rows to display.")
        return

    display_df = df.copy()

    columns = [
        ("Account", "Account", "col-account", "account"),
        ("Currency", "Currency", "col-currency", "text"),
        ("Symbol", "Symbol", "col-symbol", "symbol"),
        ("Name", "Name", "col-name", "text"),
        ("Total Shares", "Shares", "col-shares", "number"),
        ("Avg Cost", "Avg Cost", "col-avg-cost", "money_native"),
        ("Price", "Price", "col-price", "money_native"),
        ("Market Value", "Market Value", "col-market-value", "money_native_bold"),
        ("Cost Basis", "Cost Basis", "col-cost-basis", "money_native"),
        ("Dividends", "Dividends", "col-dividends", "money_native"),
        ("Realized $", "Realized", "col-realized", "money_native"),
        ("Unrealized $", "Unrealized", "col-unrealized", "money_native_gain"),
        ("Total Gain $", "Total Gain", "col-total-gain", "money_native_gain"),
        ("Market Value CAD", "Value CAD", "col-value-cad", "money_cad_bold"),
        ("Total Gain CAD", "Gain CAD", "col-gain-cad", "money_cad_gain"),
        ("Total Return %", "Simple Return", "col-return", "pct_gain"),
        ("Day %", "Day", "col-day", "pct_day"),
        ("Weight", "Weight", "col-weight", "pct"),
        ("Contribution %", "Contribution", "col-contribution", "pct_day"),
    ]

    columns = [col for col in columns if col[0] in display_df.columns]

    def cell_value(row, source_col: str, kind: str) -> tuple[str, str]:
        currency = row.get("Currency", "CAD")
        value = row.get(source_col)
        css = ""

        if kind == "account":
            return account_link(value), "account"

        if kind == "symbol":
            return symbol_link(value), "symbol"

        if kind == "number":
            return f"{safe_float(value):,.4f}", "num"

        if kind == "money_native":
            return html.escape(format_money_currency(value, currency)), "num"

        if kind == "money_native_bold":
            return html.escape(format_money_currency(value, currency)), "num strong"

        if kind == "money_native_gain":
            numeric = safe_float(value)
            css = "gain" if numeric >= 0 else "loss"
            return html.escape(format_money_currency(numeric, currency)), f"num {css} strong"

        if kind == "money_cad_bold":
            return html.escape(format_money_currency(value, "CAD")), "num strong"

        if kind == "money_cad_gain":
            numeric = safe_float(value)
            css = "gain" if numeric >= 0 else "loss"
            return html.escape(format_money_currency(numeric, "CAD")), f"num {css} strong"

        if kind == "pct_gain":
            numeric = safe_float(value)
            css = "gain" if numeric >= 0 else "loss"
            return html.escape(format_pct(numeric)), f"num {css} strong"

        if kind == "pct_day":
            numeric = safe_float(value)
            css = "gain" if numeric >= 0 else "loss"
            return html.escape(format_pct(numeric)), f"num {css} strong"

        if kind == "pct":
            return html.escape(format_pct(value)), "num"

        return html.escape(str(value)), css

    header_html = "".join(
        f'<th class="{css}">{html.escape(label)}</th>'
        for source, label, css, kind in columns
    )

    body_rows = []
    for _, row in display_df.iterrows():
        cells = []
        for source, label, col_css, kind in columns:
            text, cell_css = cell_value(row, source, kind)
            cells.append(f'<td class="{col_css} {cell_css}">{text}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    table_html = f"""
    <style>
        .jfbp-responsive-table-wrap {{
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            background: white;
        }}
        .jfbp-responsive-table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: auto;
            font-size: clamp(0.72rem, 0.60vw, 0.88rem);
        }}
        .jfbp-responsive-table th {{
            background: #f8fafc;
            color: #64748b;
            text-align: left;
            padding: 0.55rem 0.55rem;
            border-bottom: 1px solid #d1d5db;
            font-weight: 850;
            white-space: nowrap;
        }}
        .jfbp-responsive-table td {{
            padding: 0.52rem 0.55rem;
            border-bottom: 1px solid #e5e7eb;
            color: #111827;
            white-space: nowrap;
        }}
        .jfbp-responsive-table tr:last-child td {{
            border-bottom: none;
        }}
        .jfbp-responsive-table .num {{
            text-align: right;
        }}
        .jfbp-responsive-table .strong {{
            font-weight: 850;
        }}
        .jfbp-responsive-table .symbol {{
            color: #2563eb;
            font-weight: 900;
        }}
        .jfbp-responsive-table .gain {{
            color: #15803d;
        }}
        .jfbp-responsive-table .loss {{
            color: #dc2626;
        }}
        @media (max-width: 1550px) {{
            .jfbp-responsive-table .col-cost-basis,
            .jfbp-responsive-table .col-dividends,
            .jfbp-responsive-table .col-realized,
            .jfbp-responsive-table .col-total-gain {{
                display: none;
            }}
        }}
        @media (max-width: 1200px) {{
            .jfbp-responsive-table .col-currency,
            .jfbp-responsive-table .col-name,
            .jfbp-responsive-table .col-avg-cost,
            .jfbp-responsive-table .col-value-cad,
            .jfbp-responsive-table .col-contribution {{
                display: none;
            }}
        }}
        @media (max-width: 850px) {{
            .jfbp-responsive-table .col-shares,
            .jfbp-responsive-table .col-price,
            .jfbp-responsive-table .col-gain-cad,
            .jfbp-responsive-table .col-day {{
                display: none;
            }}
        }}
    </style>
    <div class="jfbp-responsive-table-wrap">
        <table class="jfbp-responsive-table">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{''.join(body_rows)}</tbody>
        </table>
    </div>
    """


    st.markdown(table_html, unsafe_allow_html=True)


def render_account_balance_cards(active_df: pd.DataFrame) -> None:
    """Render Wealthsimple-style account balance cards.

    Values are shown in CAD equivalent so CAD and USD accounts can be compared
    on one line. Registered account totals combine CAD and USD sub-accounts.
    """
    if active_df is None or active_df.empty:
        return

    df = active_df.copy()

    def account_group(account: str) -> str:
        account = clean_account(account)
        if account in ("TFSA", "TFSA USD"):
            return "TFSA"
        if account in ("RRSP", "RRSP USD"):
            return "RRSP"
        if account in ("Non-Registered", "Non-Registered USD"):
            return "Non-Registered"
        return account

    df["Account Group"] = df["Account"].map(account_group)

    rows = []

    for group_name in ["TFSA", "RRSP", "Non-Registered"]:
        group_df = df[df["Account Group"] == group_name].copy()

        if group_df.empty:
            continue

        market_value = float(group_df["Market Value CAD"].sum())
        total_gain = float(group_df["Total Gain CAD"].sum())
        cost_basis = float(group_df["Cost Basis CAD"].sum())
        return_pct = total_gain / cost_basis * 100 if cost_basis > 0 else 0.0
        holdings = int(len(group_df))

        rows.append(
            {
                "label": group_name,
                "subtitle": f"{holdings} holdings",
                "value": f"{format_money(market_value)} CAD",
                "detail": f"{format_pct(return_pct)} all time",
                "tone": "good" if return_pct >= 0 else "risk",
            }
        )

    usd_df = df[df["Currency"].astype(str).str.upper() == "USD"].copy()

    if not usd_df.empty:
        market_value = float(usd_df["Market Value CAD"].sum())
        native_value = float(usd_df["Market Value"].sum())
        total_gain = float(usd_df["Total Gain CAD"].sum())
        cost_basis = float(usd_df["Cost Basis CAD"].sum())
        return_pct = total_gain / cost_basis * 100 if cost_basis > 0 else 0.0

        rows.append(
            {
                "label": "USD Accounts",
                "subtitle": f"{format_money(native_value)} USD",
                "value": f"{format_money(market_value)} CAD",
                "detail": f"{format_pct(return_pct)} all time",
                "tone": "good" if return_pct >= 0 else "risk",
            }
        )

    if not rows:
        return

    cards = ""

    for row in rows:
        tone = row.get("tone", "neutral")
        border = "#bbf7d0" if tone == "good" else "#fecaca"
        value_color = "#166534" if tone == "good" else "#991b1b"

        cards += f"""
        <div class="jfbp-account-card">
            <div>
                <div class="jfbp-account-title">{account_link(row['label'])}</div>
                <div class="jfbp-account-subtitle">{html.escape(str(row['subtitle']))}</div>
            </div>
            <div class="jfbp-account-right">
                <div class="jfbp-account-value">{html.escape(str(row['value']))}</div>
                <div class="jfbp-account-detail" style="color:{value_color};">{html.escape(str(row['detail']))}</div>
            </div>
        </div>
        """

    st.markdown(
        f"""
        <style>
            .jfbp-account-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 0.85rem;
                margin-top: 0.25rem;
                margin-bottom: 1.25rem;
            }}
            .jfbp-account-card {{
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                align-items: center;
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 1.0rem 1.15rem;
                min-height: 96px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }}
            .jfbp-account-title {{
                color: #111827;
                font-size: 1.0rem;
                font-weight: 850;
                line-height: 1.15;
            }}
            .jfbp-account-subtitle {{
                color: #64748b;
                font-size: 0.84rem;
                margin-top: 0.35rem;
            }}
            .jfbp-account-right {{
                text-align: right;
                white-space: nowrap;
            }}
            .jfbp-account-value {{
                color: #111827;
                font-size: 1.05rem;
                font-weight: 900;
                line-height: 1.2;
            }}
            .jfbp-account-detail {{
                font-size: 0.86rem;
                margin-top: 0.35rem;
                font-weight: 700;
            }}
            @media (max-width: 700px) {{
                .jfbp-account-card {{
                    align-items: flex-start;
                    flex-direction: column;
                }}
                .jfbp-account-right {{
                    text-align: left;
                }}
            }}
        </style>
        <div class="jfbp-account-grid">{cards}</div>
        """,
        unsafe_allow_html=True,
    )


def render_holding_cards(active_df: pd.DataFrame) -> None:
    """Render responsive holding cards similar to a broker holdings list."""
    if active_df is None or active_df.empty:
        return

    display_df = active_df.copy().sort_values(
        "Market Value CAD",
        ascending=False,
        na_position="last",
    )

    cards = ""

    for _, row in display_df.iterrows():
        symbol = str(row.get("Symbol", "N/A"))
        account = str(row.get("Account", ""))
        currency = str(row.get("Currency", "CAD"))
        shares = safe_float(row.get("Total Shares"))
        market_value = safe_float(row.get("Market Value"))
        market_value_cad = safe_float(row.get("Market Value CAD"))
        day_pct = safe_float(row.get("Day %"))
        day_move_cad = market_value_cad * day_pct / 100.0
        weight = safe_float(row.get("Weight"))

        day_class = "gain" if day_pct >= 0 else "loss"
        value_line = format_money_currency(market_value, currency)

        if currency.upper() == "USD":
            cad_line = f"{format_money(market_value_cad)} CAD"
        else:
            cad_line = ""

        cards += f"""
        <div class="jfbp-holding-card">
            <div class="jfbp-holding-left">
                <div class="jfbp-symbol-dot">{html.escape(symbol[:1])}</div>
                <div>
                    <div class="jfbp-holding-symbol">{symbol_link(symbol)}</div>
                    <div class="jfbp-holding-meta">{shares:,.4f} shares · {account_link(account)}</div>
                </div>
            </div>
            <div class="jfbp-holding-right">
                <div class="jfbp-holding-value">{html.escape(value_line)}</div>
                <div class="jfbp-holding-cad">{html.escape(cad_line)}</div>
                <div class="jfbp-holding-day {day_class}">
                    {html.escape(format_money(day_move_cad))} CAD ({html.escape(format_pct(day_pct))})
                </div>
                <div class="jfbp-holding-weight">Weight {weight:.2f}%</div>
            </div>
        </div>
        """

    st.markdown(
        f"""
        <style>
            .jfbp-holdings-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 0.85rem;
                margin-top: 0.25rem;
                margin-bottom: 1.25rem;
            }}
            .jfbp-holding-card {{
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                align-items: center;
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 1.0rem 1.15rem;
                min-height: 112px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }}
            .jfbp-holding-left {{
                display: flex;
                align-items: center;
                gap: 0.8rem;
                min-width: 0;
            }}
            .jfbp-symbol-dot {{
                width: 42px;
                height: 42px;
                border-radius: 999px;
                background: #eff6ff;
                color: #1d4ed8;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 950;
                flex: 0 0 auto;
            }}
            .jfbp-holding-symbol {{
                color: #111827;
                font-size: 1.04rem;
                font-weight: 950;
                line-height: 1.15;
            }}
            .jfbp-holding-meta {{
                color: #64748b;
                font-size: 0.84rem;
                margin-top: 0.3rem;
            }}
            .jfbp-holding-right {{
                text-align: right;
                white-space: nowrap;
            }}
            .jfbp-holding-value {{
                color: #111827;
                font-size: 1.02rem;
                font-weight: 950;
                line-height: 1.2;
            }}
            .jfbp-holding-cad {{
                color: #64748b;
                font-size: 0.76rem;
                min-height: 1rem;
                margin-top: 0.12rem;
            }}
            .jfbp-holding-day {{
                font-size: 0.86rem;
                margin-top: 0.3rem;
                font-weight: 800;
            }}
            .jfbp-holding-day.gain {{
                color: #15803d;
            }}
            .jfbp-holding-day.loss {{
                color: #dc2626;
            }}
            .jfbp-holding-weight {{
                color: #64748b;
                font-size: 0.76rem;
                margin-top: 0.25rem;
            }}
            @media (max-width: 700px) {{
                .jfbp-holding-card {{
                    align-items: flex-start;
                    flex-direction: column;
                }}
                .jfbp-holding-right {{
                    text-align: left;
                }}
            }}
        </style>
        <div class="jfbp-holdings-grid">{cards}</div>
        """,
        unsafe_allow_html=True,
    )



def render_currency_exposure_cards(active_df: pd.DataFrame) -> None:
    if active_df is None or active_df.empty:
        return

    df = active_df.copy()
    total_value = float(df["Market Value CAD"].sum())

    if total_value <= 0:
        return

    exposure = (
        df.groupby("Currency", dropna=False)["Market Value CAD"]
        .sum()
        .reset_index()
        .sort_values("Market Value CAD", ascending=False)
    )

    cards = ""

    for _, row in exposure.iterrows():
        currency = str(row.get("Currency", "CAD")).upper()
        value = safe_float(row.get("Market Value CAD"))
        pct = value / total_value * 100 if total_value > 0 else 0.0

        cards += f"""
        <div class="jfbp-exposure-card">
            <div class="jfbp-exposure-header">
                <div>
                    <div class="jfbp-exposure-title">{html.escape(currency)} Exposure</div>
                    <div class="jfbp-exposure-subtitle">{html.escape(format_money(value))} CAD</div>
                </div>
                <div class="jfbp-exposure-pct">{pct:.1f}%</div>
            </div>
            <div class="jfbp-exposure-bar-wrap">
                <div class="jfbp-exposure-bar" style="width:{max(0, min(100, pct)):.1f}%;"></div>
            </div>
        </div>
        """

    st.markdown(
        f"""
        <style>
            .jfbp-exposure-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 0.85rem;
                margin-top: 0.25rem;
                margin-bottom: 1.25rem;
            }}
            .jfbp-exposure-card {{
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 1.0rem 1.15rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }}
            .jfbp-exposure-header {{
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 1rem;
            }}
            .jfbp-exposure-title {{
                color: #111827;
                font-size: 1.0rem;
                font-weight: 900;
            }}
            .jfbp-exposure-subtitle {{
                color: #64748b;
                font-size: 0.84rem;
                margin-top: 0.3rem;
            }}
            .jfbp-exposure-pct {{
                color: #166534;
                font-size: 1.15rem;
                font-weight: 950;
                white-space: nowrap;
            }}
            .jfbp-exposure-bar-wrap {{
                width: 100%;
                height: 10px;
                border-radius: 999px;
                background: #e5e7eb;
                margin-top: 0.85rem;
                overflow: hidden;
            }}
            .jfbp-exposure-bar {{
                height: 100%;
                border-radius: 999px;
                background: #86efac;
            }}
        </style>
        <div class="jfbp-exposure-grid">{cards}</div>
        """,
        unsafe_allow_html=True,
    )


def classify_asset(symbol: str) -> str:
    symbol = clean_symbol(symbol)

    canadian_equity = {"VCN.TO", "VDY.TO", "CDZ.TO", "ZEB.TO"}
    us_equity = {"VFV.TO", "SCHD", "SPY", "VOO", "QQQ", "VTI"}
    international_equity = {"VIU.TO", "VEA", "IEFA"}
    mixed_global = {"VEQT.TO", "XEQT.TO"}
    fixed_income = {"VAB.TO", "ZAG.TO", "XBB.TO"}

    if symbol in canadian_equity:
        return "Canadian Equity"
    if symbol in us_equity:
        return "U.S. Equity"
    if symbol in international_equity:
        return "International Equity"
    if symbol in mixed_global:
        return "Global / Mixed Equity"
    if symbol in fixed_income:
        return "Fixed Income"

    return "Other"


def render_asset_allocation_cards(active_df: pd.DataFrame) -> None:
    if active_df is None or active_df.empty:
        return

    df = active_df.copy()
    df["Asset Class"] = df["Symbol"].map(classify_asset)

    total_value = float(df["Market Value CAD"].sum())
    if total_value <= 0:
        return

    allocation = (
        df.groupby("Asset Class", dropna=False)["Market Value CAD"]
        .sum()
        .reset_index()
        .sort_values("Market Value CAD", ascending=False)
    )

    cards = ""

    for _, row in allocation.iterrows():
        label = str(row.get("Asset Class", "Other"))
        value = safe_float(row.get("Market Value CAD"))
        pct = value / total_value * 100 if total_value > 0 else 0.0

        cards += f"""
        <div class="jfbp-allocation-row">
            <div class="jfbp-allocation-label">{html.escape(label)}</div>
            <div class="jfbp-allocation-value">{html.escape(format_money(value))} CAD · {pct:.1f}%</div>
            <div class="jfbp-allocation-bar-wrap">
                <div class="jfbp-allocation-bar" style="width:{max(0, min(100, pct)):.1f}%;"></div>
            </div>
        </div>
        """

    st.markdown(
        f"""
        <style>
            .jfbp-allocation-card {{
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 1.05rem 1.15rem;
                margin-top: 0.25rem;
                margin-bottom: 1.25rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }}
            .jfbp-allocation-row {{ margin-bottom: 0.85rem; }}
            .jfbp-allocation-row:last-child {{ margin-bottom: 0; }}
            .jfbp-allocation-label {{
                font-weight: 900;
                color: #111827;
                margin-bottom: 0.2rem;
            }}
            .jfbp-allocation-value {{
                color: #64748b;
                font-size: 0.84rem;
                margin-bottom: 0.35rem;
            }}
            .jfbp-allocation-bar-wrap {{
                width: 100%;
                height: 10px;
                border-radius: 999px;
                background: #e5e7eb;
                overflow: hidden;
            }}
            .jfbp-allocation-bar {{
                height: 100%;
                border-radius: 999px;
                background: #bfdbfe;
            }}
        </style>
        <div class="jfbp-allocation-card">{cards}</div>
        """,
        unsafe_allow_html=True,
    )



def build_conic_gradient(items: list[dict]) -> str:
    """Build a CSS conic-gradient string from percentage items."""
    colors = [
        "#2563eb",
        "#16a34a",
        "#f59e0b",
        "#7c3aed",
        "#0f766e",
        "#dc2626",
        "#64748b",
    ]

    start = 0.0
    parts = []

    for idx, item in enumerate(items):
        pct = max(0.0, safe_float(item.get("pct")))
        end = min(100.0, start + pct)
        color = colors[idx % len(colors)]
        parts.append(f"{color} {start:.2f}% {end:.2f}%")
        item["color"] = color
        start = end

    if start < 100.0:
        parts.append(f"#e5e7eb {start:.2f}% 100%")

    return "conic-gradient(" + ", ".join(parts) + ")"


def render_donut_card(title: str, subtitle: str, items: list[dict]) -> str:
    if not items:
        return ""

    gradient = build_conic_gradient(items)

    legend = ""
    for item in items:
        label = html.escape(str(item.get("label", "N/A")))
        value = html.escape(str(item.get("value", "")))
        pct = safe_float(item.get("pct"))
        color = html.escape(str(item.get("color", "#64748b")))

        legend += f"""
        <div class="jfbp-donut-legend-row">
            <div class="jfbp-donut-legend-left">
                <span class="jfbp-donut-dot" style="background:{color};"></span>
                <span>{label}</span>
            </div>
            <div class="jfbp-donut-legend-right">
                <strong>{pct:.1f}%</strong>
                <span>{value}</span>
            </div>
        </div>
        """

    largest = max(items, key=lambda x: safe_float(x.get("pct")))
    center_label = html.escape(str(largest.get("label", "Top")))
    center_pct = safe_float(largest.get("pct"))

    return f"""
    <div class="jfbp-donut-card">
        <div class="jfbp-donut-header">
            <div>
                <div class="jfbp-donut-title">{html.escape(title)}</div>
                <div class="jfbp-donut-subtitle">{html.escape(subtitle)}</div>
            </div>
        </div>
        <div class="jfbp-donut-body">
            <div class="jfbp-donut" style="background:{gradient};">
                <div class="jfbp-donut-hole">
                    <div class="jfbp-donut-center-pct">{center_pct:.1f}%</div>
                    <div class="jfbp-donut-center-label">{center_label}</div>
                </div>
            </div>
            <div class="jfbp-donut-legend">
                {legend}
            </div>
        </div>
    </div>
    """


def render_donut_dashboard_legacy_unused(active_df: pd.DataFrame) -> None:
    """Render visual donut charts for currency and asset allocation."""
    if active_df is None or active_df.empty:
        return

    df = active_df.copy()
    total_value = float(df["Market Value CAD"].sum())

    if total_value <= 0:
        return

    currency_df = (
        df.groupby("Currency", dropna=False)["Market Value CAD"]
        .sum()
        .reset_index()
        .sort_values("Market Value CAD", ascending=False)
    )

    currency_rows = []

    for _, row in currency_df.iterrows():
        label = str(row.get("Currency", "CAD"))
        value = safe_float(row.get("Market Value CAD"))
        pct = value / total_value * 100 if total_value > 0 else 0.0

        currency_rows.append(
            {
                "label": label,
                "value": f"{format_money(value)} CAD",
                "pct": pct,
            }
        )

    asset_df = df.copy()
    asset_df["Asset Class"] = asset_df["Symbol"].map(classify_asset)

    asset_rows_df = (
        asset_df.groupby("Asset Class", dropna=False)["Market Value CAD"]
        .sum()
        .reset_index()
        .sort_values("Market Value CAD", ascending=False)
    )

    asset_rows = []

    for _, row in asset_rows_df.iterrows():
        label = str(row.get("Asset Class", "Other"))
        value = safe_float(row.get("Market Value CAD"))
        pct = value / total_value * 100 if total_value > 0 else 0.0

        asset_rows.append(
            {
                "label": label,
                "value": f"{format_money(value)} CAD",
                "pct": pct,
            }
        )

    donut_html = f"""
    <style>
        .jfbp-donut-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 0.95rem;
            margin-top: 0.25rem;
            margin-bottom: 1.25rem;
            min-width: 0;
            width: 100%;
            overflow: visible;
        }}

        .jfbp-donut-card {{
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            padding: 0.8rem 0.9rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            min-width: 0;
            width: 100%;
            max-width: 100%;
            overflow: hidden;
        }}

        .jfbp-donut-title {{
            font-size: 1.05rem;
            line-height: 1.2;
            font-weight: 950;
            color: #111827;
        }}

        .jfbp-donut-subtitle {{
            color: #64748b;
            font-size: 0.84rem;
            margin-top: 0.3rem;
        }}

        .jfbp-donut-body {{
            display: grid;
            grid-template-columns: minmax(130px, 170px) minmax(0, 1fr);
            align-items: center;
            gap: 0.9rem;
            margin-top: 1rem;
            min-width: 0;
            width: 100%;
        }}

        .jfbp-donut {{
            width: min(160px, 100%);
            max-width: 160px;
            aspect-ratio: 1 / 1;
            height: auto;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.05);
            justify-self: center;
            flex-shrink: 0;
        }}

        .jfbp-donut-hole {{
            width: 92px;
            height: 92px;
            border-radius: 50%;
            background: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.12);
            padding: 0.4rem;
        }}

        .jfbp-donut-center-pct {{
            font-size: 1.12rem;
            font-weight: 950;
            color: #111827;
            line-height: 1.1;
        }}

        .jfbp-donut-center-label {{
            margin-top: 0.25rem;
            color: #64748b;
            font-size: 0.72rem;
            font-weight: 750;
            line-height: 1.15;
        }}

        .jfbp-donut-legend {{
            display: flex;
            flex-direction: column;
            gap: 0.55rem;
            min-width: 0;
            width: 100%;
            overflow: hidden;
        }}

        .jfbp-donut-legend-row {{
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            gap: 0.75rem;
            border-bottom: 1px solid #f1f5f9;
            padding-bottom: 0.45rem;
            min-width: 0;
        }}

        .jfbp-donut-legend-row:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}

        .jfbp-donut-legend-left {{
            display: flex;
            align-items: center;
            gap: 0.45rem;
            color: #111827;
            font-size: 0.78rem;
            font-weight: 850;
            min-width: 0;
            overflow-wrap: anywhere;
        }}

        .jfbp-donut-dot {{
            width: 10px;
            height: 10px;
            border-radius: 999px;
            flex: 0 0 auto;
        }}

        .jfbp-donut-legend-right {{
            text-align: right;
            white-space: normal;
            min-width: 0;
            overflow-wrap: anywhere;
        }}

        .jfbp-donut-legend-right strong {{
            display: block;
            color: #111827;
            font-size: 0.88rem;
            line-height: 1.1;
        }}

        .jfbp-donut-legend-right span {{
            display: block;
            color: #64748b;
            font-size: 0.74rem;
            margin-top: 0.18rem;
        }}

        @media (max-width: 1180px) {{
            .jfbp-donut-body {{
                grid-template-columns: minmax(130px, 180px) minmax(0, 1fr);
            }}
        }}

        @media (max-width: 780px) {{
            .jfbp-donut-body {{
                grid-template-columns: 1fr;
                justify-items: center;
            }}

            .jfbp-donut {{
                width: min(180px, 82vw);
                max-width: 180px;
            }}

            .jfbp-donut-legend {{
                width: 100%;
            }}

            .jfbp-donut-legend-row {{
                grid-template-columns: minmax(0, 1fr);
                gap: 0.3rem;
            }}

            .jfbp-donut-legend-right {{
                text-align: left;
                padding-left: 1.45rem;
            }}
        }}
    </style>

    <div class="jfbp-donut-grid">
        {render_donut_card("Currency Donut", "CAD vs USD exposure", currency_rows)}
        {render_donut_card("Asset Allocation Donut", "ETF allocation by asset class", asset_rows)}
    </div>
    """

    st.markdown(
        donut_html,
        unsafe_allow_html=True,
    )
    
    st.markdown(donut_html, unsafe_allow_html=True)

def calculate_portfolio_health(active_df: pd.DataFrame) -> dict:
    if active_df is None or active_df.empty:
        return {"score": 0, "grade": "N/A", "concentration": "N/A", "income": "N/A", "currency": "N/A"}

    df = active_df.copy()
    holding_count = len(df)
    max_weight = float(df["Weight"].max()) if "Weight" in df.columns else 0.0
    total_gain = float(df["Total Gain CAD"].sum())
    cost_basis = float(df["Cost Basis CAD"].sum())
    return_pct = total_gain / cost_basis * 100 if cost_basis > 0 else 0.0
    dividends = float(df["Dividends CAD"].sum()) if "Dividends CAD" in df.columns else 0.0
    total_value = float(df["Market Value CAD"].sum())
    usd_value = float(df.loc[df["Currency"].astype(str).str.upper() == "USD", "Market Value CAD"].sum())
    usd_pct = usd_value / total_value * 100 if total_value > 0 else 0.0

    diversification_points = min(30, holding_count * 4)
    concentration_points = 25 if max_weight <= 25 else 18 if max_weight <= 35 else 10 if max_weight <= 50 else 4
    return_points = 20 if return_pct >= 10 else 15 if return_pct >= 3 else 10 if return_pct >= 0 else 4
    income_points = 15 if dividends > 2000 else 10 if dividends > 500 else 5 if dividends > 0 else 0
    currency_points = 10 if 10 <= usd_pct <= 40 else 7 if usd_pct <= 55 else 4

    score = int(round(diversification_points + concentration_points + return_points + income_points + currency_points))
    score = max(0, min(100, score))

    if score >= 85:
        grade = "Strong"
    elif score >= 70:
        grade = "Healthy"
    elif score >= 55:
        grade = "Watch"
    else:
        grade = "Needs Work"

    if max_weight <= 25:
        concentration = "Low"
    elif max_weight <= 35:
        concentration = "Moderate"
    else:
        concentration = "High"

    return {
        "score": score,
        "grade": grade,
        "concentration": concentration,
        "income": "Strong" if dividends > 2000 else "Building" if dividends > 0 else "None",
        "currency": f"{usd_pct:.1f}% USD",
    }


def render_portfolio_health_cards(active_df: pd.DataFrame) -> None:
    """Render portfolio health in three rows so it stays readable in the right column."""
    health = calculate_portfolio_health(active_df)

    top_position = "N/A"
    top_weight = 0.0

    if active_df is not None and not active_df.empty and "Weight" in active_df.columns:
        top_row = active_df.sort_values(
            "Weight",
            ascending=False,
            na_position="last",
        ).iloc[0]
        top_position = str(top_row.get("Symbol", "N/A"))
        top_weight = safe_float(top_row.get("Weight"))

    row1 = st.columns(2)
    row2 = st.columns(2)
    row3 = st.columns(2)

    with row1[0]:
        metric_card(
            "Portfolio Health",
            f"{health['score']}/100",
            health["grade"],
            tone="info",
        )

    with row1[1]:
        metric_card(
            "Diversification",
            health["grade"],
            "Based on holding count",
            tone="good" if health["score"] >= 70 else "warning",
        )

    with row2[0]:
        metric_card(
            "Concentration Risk",
            health["concentration"],
            "Largest position weight",
            tone="good" if health["concentration"] == "Low" else "warning",
        )

    with row2[1]:
        metric_card(
            "Currency Exposure",
            health["currency"],
            "CAD/USD mix",
            tone="neutral",
        )

    with row3[0]:
        metric_card(
            "Income Strategy",
            health["income"],
            "Dividend base",
            tone="good" if health["income"] == "Strong" else "warning",
        )

    with row3[1]:
        metric_card(
            "Top Position",
            top_position,
            f"{top_weight:.1f}% portfolio weight",
            tone="info",
        )

def estimate_forward_yield(symbol: str) -> float:
    """Estimated forward yield by ETF symbol.

    This is intentionally conservative and can be refined later with live ETF
    yield data or a local dividend-yield table.
    """
    symbol = clean_symbol(symbol)

    yield_map = {
        "SCHD": 0.038,
        "VDY.TO": 0.042,
        "VCN.TO": 0.030,
        "VFV.TO": 0.012,
        "VEQT.TO": 0.018,
        "XEQT.TO": 0.018,
        "VIU.TO": 0.027,
        "CDZ.TO": 0.040,
        "ZEB.TO": 0.045,
        "VAB.TO": 0.033,
    }

    return yield_map.get(symbol, 0.020)


def calculate_projected_income(active_df: pd.DataFrame) -> tuple[float, float, float]:
    """Calculate estimated annual and monthly dividend income.

    Uses a conservative ETF yield table instead of assuming one flat portfolio
    yield. Returns annual income, monthly income, and weighted projected yield.
    """
    if active_df is None or active_df.empty:
        return 0.0, 0.0, 0.0

    df = active_df.copy()

    if "Market Value CAD" not in df.columns or "Symbol" not in df.columns:
        return 0.0, 0.0, 0.0

    df["Estimated Yield"] = df["Symbol"].map(estimate_forward_yield)
    df["Projected Income CAD"] = df["Market Value CAD"].fillna(0.0) * df["Estimated Yield"]

    annual_income = float(df["Projected Income CAD"].sum())
    monthly_income = annual_income / 12.0
    portfolio_value = float(df["Market Value CAD"].sum())
    projected_yield = annual_income / portfolio_value * 100 if portfolio_value > 0 else 0.0

    return annual_income, monthly_income, projected_yield


def render_dividend_command_center(active_df: pd.DataFrame) -> None:
    """Render dividend metrics in three rows so income history and projected income both show."""
    if active_df is None or active_df.empty:
        return

    dividends = float(active_df["Dividends CAD"].sum()) if "Dividends CAD" in active_df.columns else 0.0
    portfolio_value = float(active_df["Market Value CAD"].sum())
    cost_basis = float(active_df["Cost Basis CAD"].sum())
    yield_on_cost = dividends / cost_basis * 100 if cost_basis > 0 else 0.0
    received_yield = dividends / portfolio_value * 100 if portfolio_value > 0 else 0.0
    monthly_avg = dividends / 12.0

    projected_annual_income, projected_monthly_income, projected_yield = calculate_projected_income(active_df)

    row1 = st.columns(2)
    row2 = st.columns(2)
    row3 = st.columns(2)

    with row1[0]:
        metric_card(
            "Dividends Received",
            f"{format_money(dividends)} CAD",
            "Ledger total",
            tone="good" if dividends > 0 else "neutral",
        )

    with row1[1]:
        metric_card(
            "Monthly Avg",
            f"{format_money(monthly_avg)} CAD",
            "Received / 12",
            tone="good" if monthly_avg > 0 else "neutral",
        )

    with row2[0]:
        metric_card(
            "Yield on Cost",
            format_pct(yield_on_cost),
            "Received vs cost",
            tone="good" if yield_on_cost > 0 else "neutral",
        )

    with row2[1]:
        metric_card(
            "Portfolio Yield",
            format_pct(received_yield),
            "Received vs value",
            tone="good" if received_yield > 0 else "neutral",
        )

    with row3[0]:
        metric_card(
            "Projected Annual Income",
            f"{format_money(projected_annual_income)} CAD",
            f"Estimated forward yield {projected_yield:.2f}%",
            tone="good" if projected_annual_income > 0 else "neutral",
        )

    with row3[1]:
        metric_card(
            "Projected Monthly Income",
            f"{format_money(projected_monthly_income)} CAD",
            "Annual projection / 12",
            tone="good" if projected_monthly_income > 0 else "neutral",
        )


def render_portfolio_trend(active_df: pd.DataFrame) -> None:
    """Render a lightweight portfolio value chart using current holding values."""
    if active_df is None or active_df.empty:
        return

    if "Symbol" not in active_df.columns or "Market Value CAD" not in active_df.columns:
        return

    chart_df = (
        active_df[["Symbol", "Market Value CAD"]]
        .copy()
        .sort_values("Market Value CAD", ascending=False)
        .head(10)
    )

    if chart_df.empty:
        return

    chart_df = chart_df.set_index("Symbol")

    st.bar_chart(
        chart_df,
        height=310,
        use_container_width=True,
    )


def render_portfolio_performance_snapshot(
    total_return_pct: float,
    time_weighted_return,
    weighted_move: float,
    total_gain: float,
    total_dividends: float,
    total_realized: float,
    unrealized_gain: float,
) -> None:
    """Render only performance metrics that are actually supported by current data.

    The app currently has live/current holdings plus the local transaction ledger.
    It does not yet store daily portfolio snapshots, so 1W/1M/3M/6M/YTD/1Y
    range buttons would repeat the same value and create false precision.

    Real metrics available now:
    - Today: weighted daily move from current holdings
    - All-time simple return: ledger-built gain divided by cost basis
    - TWR: cash-flow adjusted return when CASH_DEPOSIT / CASH_WITHDRAWAL rows exist
    - Gain breakdown: unrealized, realized, and income
    """
    st.caption(
        "Real performance metrics only. Historical range buttons will return after the dashboard starts saving daily portfolio snapshots."
    )

    row1 = st.columns(3)

    with row1[0]:
        metric_card(
            "Today",
            format_pct(weighted_move),
            "Weighted daily move",
            tone="good" if safe_float(weighted_move) >= 0 else "risk",
        )

    with row1[1]:
        metric_card(
            "All-Time Simple Return",
            format_pct(total_return_pct),
            f"{format_money(total_gain)} CAD total gain",
            tone="good" if safe_float(total_return_pct) >= 0 else "risk",
        )

    with row1[2]:
        metric_card(
            "Time-Weighted Return",
            format_pct(time_weighted_return),
            "Cash-flow adjusted" if time_weighted_return is not None else "Add CASH_DEPOSIT / CASH_WITHDRAWAL rows",
            tone="good" if (time_weighted_return is not None and safe_float(time_weighted_return) >= 0) else "neutral",
        )

    row2 = st.columns(3)

    with row2[0]:
        metric_card(
            "Unrealized Gain",
            f"{format_money(unrealized_gain)} CAD",
            "Open positions",
            tone="good" if safe_float(unrealized_gain) >= 0 else "risk",
        )

    with row2[1]:
        metric_card(
            "Realized Gain",
            f"{format_money(total_realized)} CAD",
            "Closed positions",
            tone="good" if safe_float(total_realized) >= 0 else "risk",
        )

    with row2[2]:
        metric_card(
            "Dividends Received",
            f"{format_money(total_dividends)} CAD",
            "Ledger income",
            tone="good" if safe_float(total_dividends) > 0 else "neutral",
        )


# =========================================================
# PORTFOLIO INTELLIGENCE — RADAR / REBALANCE / GRADE / INCOME FORECAST
# =========================================================

def _portfolio_card_html(title: str, rows: list[tuple[str, str, str]], tone: str = "neutral") -> None:
    """Render a compact institutional card with label/value/detail rows."""
    palette = {
        "neutral": ("#ffffff", "#e5e7eb", "#111827"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
    }

    bg, border, title_color = palette.get(tone, palette["neutral"])

    body = ""
    for label, value, detail in rows:
        detail_html = (
            f'<div class="jfbp-intel-detail">{html.escape(str(detail))}</div>'
            if detail
            else ""
        )
        body += f"""
        <div class="jfbp-intel-row">
            <div>
                <div class="jfbp-intel-label">{html.escape(str(label))}</div>
                {detail_html}
            </div>
            <div class="jfbp-intel-value">{html.escape(str(value))}</div>
        </div>
        """

    st.markdown(
        f"""
        <style>
            .jfbp-intel-card {{
                background:{bg};
                border:1px solid {border};
                border-radius:16px;
                padding:1.0rem 1.15rem;
                margin-top:0.25rem;
                margin-bottom:1.25rem;
                box-shadow:0 1px 2px rgba(15, 23, 42, 0.04);
            }}
            .jfbp-intel-title {{
                color:{title_color};
                font-weight:950;
                font-size:0.78rem;
                letter-spacing:0.055em;
                text-transform:uppercase;
                margin-bottom:0.75rem;
            }}
            .jfbp-intel-row {{
                display:flex;
                justify-content:space-between;
                gap:0.85rem;
                align-items:flex-start;
                padding:0.52rem 0;
                border-bottom:1px solid rgba(148, 163, 184, 0.22);
            }}
            .jfbp-intel-row:last-child {{
                border-bottom:none;
                padding-bottom:0;
            }}
            .jfbp-intel-label {{
                color:#64748b;
                font-size:0.78rem;
                font-weight:850;
                text-transform:uppercase;
                letter-spacing:0.035em;
            }}
            .jfbp-intel-detail {{
                color:#64748b;
                font-size:0.76rem;
                margin-top:0.18rem;
            }}
            .jfbp-intel-value {{
                color:#111827;
                font-weight:950;
                font-size:0.95rem;
                text-align:right;
                white-space:nowrap;
            }}
            @media (max-width: 700px) {{
                .jfbp-intel-row {{
                    flex-direction:column;
                    gap:0.25rem;
                }}
                .jfbp-intel-value {{ text-align:left; }}
            }}
        </style>
        <div class="jfbp-intel-card">
            <div class="jfbp-intel-title">{html.escape(str(title))}</div>
            {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


def calculate_portfolio_radar(active_df: pd.DataFrame) -> dict:
    """Find the most important live portfolio signals."""
    if active_df is None or active_df.empty:
        return {}

    df = active_df.copy()
    df["Estimated Yield"] = df["Symbol"].map(estimate_forward_yield)
    df["Projected Income CAD"] = df["Market Value CAD"].fillna(0.0) * df["Estimated Yield"]

    def row_symbol(sort_col: str, ascending: bool = False) -> tuple[str, float]:
        if sort_col not in df.columns or df.empty:
            return "N/A", 0.0
        row = df.sort_values(sort_col, ascending=ascending, na_position="last").iloc[0]
        return str(row.get("Symbol", "N/A")), safe_float(row.get(sort_col))

    largest_symbol, largest_weight = row_symbol("Weight", ascending=False)
    strongest_symbol, strongest_day = row_symbol("Day %", ascending=False)
    weakest_symbol, weakest_day = row_symbol("Day %", ascending=True)
    best_symbol, best_return = row_symbol("Total Return %", ascending=False)
    income_symbol, income_value = row_symbol("Projected Income CAD", ascending=False)

    return {
        "largest_symbol": largest_symbol,
        "largest_weight": largest_weight,
        "strongest_symbol": strongest_symbol,
        "strongest_day": strongest_day,
        "weakest_symbol": weakest_symbol,
        "weakest_day": weakest_day,
        "best_symbol": best_symbol,
        "best_return": best_return,
        "income_symbol": income_symbol,
        "income_value": income_value,
    }


def render_portfolio_radar(active_df: pd.DataFrame) -> None:
    """Render compact Portfolio Radar intelligence."""
    radar = calculate_portfolio_radar(active_df)
    if not radar:
        return

    rows = [
        (
            "Largest Position",
            radar["largest_symbol"],
            f"{radar['largest_weight']:.1f}% portfolio weight",
        ),
        (
            "Weakest Today",
            radar["weakest_symbol"],
            format_pct(radar["weakest_day"]),
        ),
        (
            "Strongest Today",
            radar["strongest_symbol"],
            format_pct(radar["strongest_day"]),
        ),
        (
            "Best All-Time",
            radar["best_symbol"],
            format_pct(radar["best_return"]),
        ),
        (
            "Income Leader",
            radar["income_symbol"],
            f"{format_money(radar['income_value'])} CAD projected",
        ),
    ]

    _portfolio_card_html(
        "📡 Portfolio Radar",
        rows,
        tone="info",
    )


def target_weight_map() -> dict[str, float]:
    """Strategic target weights used by the first-pass rebalancing engine.

    These are editable defaults. Unknown symbols are ignored so the engine does
    not create fake targets for positions that were not planned.
    """
    return {
        "SCHD": 20.0,
        "VDY.TO": 20.0,
        "VEQT.TO": 20.0,
        "VFV.TO": 15.0,
        "VCN.TO": 10.0,
        "VIU.TO": 10.0,
        "CDZ.TO": 5.0,
        "VAB.TO": 0.0,
    }


def calculate_rebalance_alert(active_df: pd.DataFrame) -> dict:
    """Find the largest target/current allocation gap."""
    if active_df is None or active_df.empty:
        return {}

    targets = target_weight_map()
    rows = []

    for _, row in active_df.iterrows():
        symbol = clean_symbol(row.get("Symbol"))
        if symbol not in targets:
            continue
        current = safe_float(row.get("Weight"))
        target = float(targets[symbol])
        gap = current - target
        rows.append(
            {
                "symbol": symbol,
                "current": current,
                "target": target,
                "gap": gap,
                "abs_gap": abs(gap),
            }
        )

    if not rows:
        return {
            "symbol": "N/A",
            "target": 0.0,
            "current": 0.0,
            "gap": 0.0,
            "action": "Set targets",
            "detail": "No target weights found for current holdings.",
            "tone": "neutral",
        }

    alert = sorted(rows, key=lambda item: item["abs_gap"], reverse=True)[0]

    if alert["abs_gap"] < 2.0:
        action = "On Target"
        detail = "Largest gap is under 2%."
        tone = "good"
    elif alert["gap"] > 0:
        action = f"Trim {alert['gap']:.1f}%"
        detail = "Current weight is above target."
        tone = "warning"
    else:
        action = f"Add {abs(alert['gap']):.1f}%"
        detail = "Current weight is below target."
        tone = "info"

    return {
        **alert,
        "action": action,
        "detail": detail,
        "tone": tone,
    }


def render_rebalance_engine(active_df: pd.DataFrame) -> None:
    """Render a compact rebalancing alert card."""
    alert = calculate_rebalance_alert(active_df)
    if not alert:
        return

    rows = [
        ("Symbol", alert["symbol"], alert.get("detail", "")),
        ("Target", f"{alert['target']:.1f}%", "Strategic allocation"),
        ("Current", f"{alert['current']:.1f}%", "Current portfolio weight"),
        ("Action", alert["action"], "First-pass allocation signal"),
    ]

    _portfolio_card_html(
        "⚖️ Rebalance Alert",
        rows,
        tone=alert.get("tone", "neutral"),
    )


def _letter_grade(score: float) -> str:
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 85:
        return "A-"
    if score >= 80:
        return "B+"
    if score >= 75:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 65:
        return "C+"
    if score >= 60:
        return "C"
    return "D"


def calculate_portfolio_grade(active_df: pd.DataFrame) -> dict:
    """Calculate institutional-style portfolio component grades."""
    if active_df is None or active_df.empty:
        return {}

    df = active_df.copy()
    holding_count = len(df)
    max_weight = safe_float(df["Weight"].max()) if "Weight" in df.columns else 0.0
    annual_income, _, projected_yield = calculate_projected_income(df)
    total_value = safe_float(df["Market Value CAD"].sum()) if "Market Value CAD" in df.columns else 0.0
    usd_value = safe_float(df.loc[df["Currency"].astype(str).str.upper() == "USD", "Market Value CAD"].sum()) if "Currency" in df.columns else 0.0
    usd_pct = usd_value / total_value * 100 if total_value > 0 else 0.0

    diversification_score = min(100, holding_count * 12.5)
    income_score = min(100, projected_yield / 4.0 * 100) if projected_yield > 0 else 0.0
    concentration_score = 100 if max_weight <= 20 else 88 if max_weight <= 25 else 76 if max_weight <= 35 else 58 if max_weight <= 50 else 40
    currency_score = 100 if 10 <= usd_pct <= 40 else 84 if usd_pct <= 55 else 68

    # Risk grade rewards diversification and concentration control.
    risk_score = concentration_score * 0.65 + diversification_score * 0.25 + currency_score * 0.10
    overall_score = (
        diversification_score * 0.30
        + income_score * 0.25
        + risk_score * 0.25
        + concentration_score * 0.20
    )

    return {
        "diversification": _letter_grade(diversification_score),
        "income": _letter_grade(income_score),
        "risk": _letter_grade(risk_score),
        "concentration": _letter_grade(concentration_score),
        "overall": _letter_grade(overall_score),
        "overall_score": overall_score,
        "annual_income": annual_income,
        "projected_yield": projected_yield,
    }


def render_portfolio_grade(active_df: pd.DataFrame) -> None:
    """Render Portfolio Grade similar to the institutional stock pages."""
    grade = calculate_portfolio_grade(active_df)
    if not grade:
        return

    rows = [
        ("Diversification", grade["diversification"], "Holding count and spread"),
        ("Income", grade["income"], f"Projected yield {grade['projected_yield']:.2f}%"),
        ("Risk", grade["risk"], "Concentration and currency balance"),
        ("Concentration", grade["concentration"], "Largest holding control"),
        ("Overall Grade", grade["overall"], f"Score {grade['overall_score']:.0f}/100"),
    ]

    _portfolio_card_html(
        "🏛️ Portfolio Grade",
        rows,
        tone="good" if grade["overall_score"] >= 80 else "warning",
    )


def distribution_months(symbol: str) -> list[int]:
    """Approximate distribution schedule by ETF.

    Monthly ETFs spread income across all months. Quarterly ETFs are allocated
    to common distribution months. Annual/mixed ETFs are spread conservatively.
    """
    symbol = clean_symbol(symbol)

    monthly = {
        "VDY.TO",
        "CDZ.TO",
        "ZEB.TO",
    }

    quarterly_mar = {
        "SCHD",
        "VFV.TO",
        "VCN.TO",
        "VIU.TO",
        "VAB.TO",
    }

    mixed_or_annual = {
        "VEQT.TO",
        "XEQT.TO",
    }

    if symbol in monthly:
        return list(range(1, 13))

    if symbol in quarterly_mar:
        return [3, 6, 9, 12]

    if symbol in mixed_or_annual:
        return [1, 4, 7, 12]

    return [3, 6, 9, 12]


def calculate_monthly_income_forecast(active_df: pd.DataFrame) -> pd.DataFrame:
    """Build a 12-month estimated dividend/distribution forecast."""
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    forecast = {month: 0.0 for month in month_names}

    if active_df is None or active_df.empty:
        return pd.DataFrame({"Month": month_names, "Income CAD": [0.0] * 12})

    df = active_df.copy()

    for _, row in df.iterrows():
        symbol = clean_symbol(row.get("Symbol"))
        market_value = safe_float(row.get("Market Value CAD"))
        annual_income = market_value * estimate_forward_yield(symbol)
        months = distribution_months(symbol)

        if not months:
            continue

        payment = annual_income / len(months)

        for month_num in months:
            forecast[month_names[month_num - 1]] += payment

    return pd.DataFrame(
        {
            "Month": month_names,
            "Income CAD": [forecast[month] for month in month_names],
        }
    )


def render_monthly_income_forecast(active_df: pd.DataFrame) -> None:
    """Render the estimated monthly income forecast as a compact table."""
    forecast_df = calculate_monthly_income_forecast(active_df)

    if forecast_df.empty:
        return

    annual_total = float(forecast_df["Income CAD"].sum())
    best_row = forecast_df.sort_values("Income CAD", ascending=False).iloc[0]

    rows_html = ""
    for _, row in forecast_df.iterrows():
        income = safe_float(row.get("Income CAD"))
        rows_html += f"""
        <tr>
            <td>{html.escape(str(row.get('Month', '')))}</td>
            <td>{html.escape(format_money(income))} CAD</td>
        </tr>
        """

    st.markdown(
        f"""
        <style>
            .jfbp-income-forecast-card {{
                background:#ffffff;
                border:1px solid #e5e7eb;
                border-radius:16px;
                padding:1.0rem 1.15rem;
                margin-top:0.25rem;
                margin-bottom:1.25rem;
                box-shadow:0 1px 2px rgba(15, 23, 42, 0.04);
            }}
            .jfbp-income-forecast-title {{
                color:#166534;
                font-weight:950;
                font-size:0.78rem;
                letter-spacing:0.055em;
                text-transform:uppercase;
                margin-bottom:0.35rem;
            }}
            .jfbp-income-forecast-subtitle {{
                color:#64748b;
                font-size:0.78rem;
                margin-bottom:0.75rem;
            }}
            .jfbp-income-table {{
                width:100%;
                border-collapse:collapse;
                font-size:0.84rem;
            }}
            .jfbp-income-table th {{
                color:#64748b;
                background:#f8fafc;
                text-align:left;
                padding:0.45rem 0.5rem;
                border-bottom:1px solid #e5e7eb;
                font-weight:900;
            }}
            .jfbp-income-table td {{
                color:#111827;
                padding:0.42rem 0.5rem;
                border-bottom:1px solid #f1f5f9;
            }}
            .jfbp-income-table td:last-child,
            .jfbp-income-table th:last-child {{
                text-align:right;
                font-weight:850;
            }}
            .jfbp-income-table tr:last-child td {{
                border-bottom:none;
            }}
        </style>
        <div class="jfbp-income-forecast-card">
            <div class="jfbp-income-forecast-title">🗓️ Monthly Income Forecast</div>
            <div class="jfbp-income-forecast-subtitle">
                Estimated annual income {html.escape(format_money(annual_total))} CAD · strongest month {html.escape(str(best_row['Month']))}
            </div>
            <table class="jfbp-income-table">
                <thead><tr><th>Month</th><th>Estimated Income</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# SVG DONUT DASHBOARD — SAFARI SAFE
# =========================================================

def _donut_svg(items: list[dict], title: str, subtitle: str) -> str:
    """Build a self-contained SVG donut card."""
    clean_items = []
    total = 0.0

    for item in items:
        label = str(item.get("label", "N/A"))
        value = safe_float(item.get("value"))
        if value <= 0:
            continue
        total += value
        clean_items.append({"label": label, "value": value})

    if not clean_items or total <= 0:
        return ""

    colors = ["#2563eb", "#16a34a", "#f59e0b", "#7c3aed", "#0f766e", "#dc2626", "#64748b"]
    radius = 70
    circumference = 2 * 3.141592653589793 * radius
    offset = 0.0
    circles = []
    legend = []

    for idx, item in enumerate(clean_items):
        pct = item["value"] / total * 100.0
        dash = circumference * pct / 100.0
        gap = circumference - dash
        color = colors[idx % len(colors)]
        circles.append(
            f'<circle cx="95" cy="95" r="{radius}" fill="none" stroke="{color}" stroke-width="30" '
            f'stroke-dasharray="{dash:.4f} {gap:.4f}" stroke-dashoffset="{-offset:.4f}" '
            f'stroke-linecap="butt" transform="rotate(-90 95 95)" />'
        )
        offset += dash
        legend.append(
            f'''
            <div class="jfbp-svg-donut-legend-row">
                <div class="jfbp-svg-donut-legend-left">
                    <span class="jfbp-svg-donut-dot" style="background:{color};"></span>
                    <span>{html.escape(item["label"])}</span>
                </div>
                <div class="jfbp-svg-donut-legend-right">
                    <strong>{pct:.1f}%</strong>
                    <span>{html.escape(format_money(item["value"]))} CAD</span>
                </div>
            </div>
            '''
        )

    largest = max(clean_items, key=lambda x: x["value"])
    largest_pct = largest["value"] / total * 100.0

    return f'''
    <div class="jfbp-svg-donut-card">
        <div class="jfbp-svg-donut-title">{html.escape(title)}</div>
        <div class="jfbp-svg-donut-subtitle">{html.escape(subtitle)}</div>
        <div class="jfbp-svg-donut-body">
            <div class="jfbp-svg-donut-chart-wrap">
                <svg class="jfbp-svg-donut-chart" viewBox="0 0 190 190" role="img" aria-label="{html.escape(title)}">
                    <circle cx="95" cy="95" r="{radius}" fill="none" stroke="#e5e7eb" stroke-width="30" />
                    {''.join(circles)}
                    <circle cx="95" cy="95" r="47" fill="#ffffff" />
                    <text x="95" y="88" text-anchor="middle" class="jfbp-svg-donut-center-pct">{largest_pct:.1f}%</text>
                    <text x="95" y="108" text-anchor="middle" class="jfbp-svg-donut-center-label">{html.escape(largest['label'])}</text>
                </svg>
            </div>
            <div class="jfbp-svg-donut-legend">
                {''.join(legend)}
            </div>
        </div>
    </div>
    '''


def _render_single_donut_component(card_html: str) -> None:
    """Render one donut card in its own component."""
    if not card_html:
        return

    component_html = """
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8" />
        <style>
            * { box-sizing: border-box; }
            body {
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: transparent;
                color: #111827;
            }
            .jfbp-svg-donut-card {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 18px;
                padding: 18px 20px;
                min-height: 300px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }
            .jfbp-svg-donut-title {
                font-size: 16px;
                line-height: 1.2;
                font-weight: 950;
                color: #111827;
            }
            .jfbp-svg-donut-subtitle {
                color: #64748b;
                font-size: 13px;
                margin-top: 5px;
            }
            .jfbp-svg-donut-body {
                display: grid;
                grid-template-columns: 210px 1fr;
                gap: 18px;
                align-items: center;
                margin-top: 16px;
            }
            .jfbp-svg-donut-chart-wrap {
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .jfbp-svg-donut-chart {
                width: 190px;
                height: 190px;
                display: block;
            }
            .jfbp-svg-donut-center-pct {
                font-size: 23px;
                font-weight: 950;
                fill: #111827;
            }
            .jfbp-svg-donut-center-label {
                font-size: 11px;
                font-weight: 750;
                fill: #64748b;
            }
            .jfbp-svg-donut-legend {
                display: flex;
                flex-direction: column;
                gap: 9px;
                min-width: 0;
            }
            .jfbp-svg-donut-legend-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
                border-bottom: 1px solid #f1f5f9;
                padding-bottom: 8px;
            }
            .jfbp-svg-donut-legend-row:last-child {
                border-bottom: none;
                padding-bottom: 0;
            }
            .jfbp-svg-donut-legend-left {
                display: flex;
                align-items: center;
                gap: 8px;
                color: #111827;
                font-size: 13px;
                font-weight: 850;
                min-width: 0;
            }
            .jfbp-svg-donut-dot {
                width: 10px;
                height: 10px;
                border-radius: 999px;
                flex: 0 0 auto;
            }
            .jfbp-svg-donut-legend-right {
                text-align: right;
                white-space: nowrap;
            }
            .jfbp-svg-donut-legend-right strong {
                display: block;
                color: #111827;
                font-size: 13px;
                line-height: 1.1;
            }
            .jfbp-svg-donut-legend-right span {
                display: block;
                color: #64748b;
                font-size: 11px;
                margin-top: 3px;
            }
            @media (max-width: 720px) {
                .jfbp-svg-donut-card { min-height: 430px; }
                .jfbp-svg-donut-body {
                    grid-template-columns: 1fr;
                    justify-items: center;
                }
                .jfbp-svg-donut-legend { width: 100%; }
            }
        </style>
    </head>
    <body>__CARD_HTML__</body>
    </html>
    """.replace("__CARD_HTML__", card_html)

    components.html(component_html, height=460, scrolling=False)


def render_donut_dashboard(active_df: pd.DataFrame) -> None:
    """Render Safari-safe SVG donuts without clipping on narrow screens."""
    if active_df is None or active_df.empty:
        return

    df = active_df.copy()
    if "Market Value CAD" not in df.columns:
        return

    total_value = float(df["Market Value CAD"].sum())
    if total_value <= 0:
        return

    currency_df = (
        df.groupby("Currency", dropna=False)["Market Value CAD"]
        .sum()
        .reset_index()
        .sort_values("Market Value CAD", ascending=False)
    )
    currency_items = [
        {
            "label": str(row.get("Currency", "CAD")),
            "value": safe_float(row.get("Market Value CAD")),
        }
        for _, row in currency_df.iterrows()
    ]

    asset_df = df.copy()
    asset_df["Asset Class"] = asset_df["Symbol"].map(classify_asset)
    asset_rows_df = (
        asset_df.groupby("Asset Class", dropna=False)["Market Value CAD"]
        .sum()
        .reset_index()
        .sort_values("Market Value CAD", ascending=False)
    )
    asset_items = [
        {
            "label": str(row.get("Asset Class", "Other")),
            "value": safe_float(row.get("Market Value CAD")),
        }
        for _, row in asset_rows_df.iterrows()
    ]

    currency_card = _donut_svg(
        currency_items,
        "Currency Donut",
        "CAD vs USD exposure",
    )
    asset_card = _donut_svg(
        asset_items,
        "Asset Allocation Donut",
        "ETF allocation by asset class",
    )

    donut_left, donut_right = st.columns(2)

    with donut_left:
        _render_single_donut_component(currency_card)

    with donut_right:
        _render_single_donut_component(asset_card)



def _set_drilldown_state(
    view_name: str = "All Accounts",
    focus_account: str = "",
    focus_symbol: str = "",
) -> None:
    """Use session state for reliable internal navigation.

    This avoids HTML href routing issues in Streamlit apps where a relative
    query-string link can reopen the wrong router page.
    """
    view_name = str(view_name or "All Accounts").strip()

    if view_name not in PORTFOLIO_OPTIONS:
        view_name = clean_account(view_name)

    if view_name not in PORTFOLIO_OPTIONS:
        view_name = "All Accounts"

    st.session_state["private_portfolio_requested_view"] = view_name
    st.session_state["private_portfolio_focus_account"] = str(focus_account or "").strip()
    st.session_state["private_portfolio_focus_symbol"] = clean_symbol(focus_symbol)


def _clear_drilldown_state() -> None:
    st.session_state["private_portfolio_requested_view"] = "All Accounts"
    st.session_state["private_portfolio_focus_account"] = ""
    st.session_state["private_portfolio_focus_symbol"] = ""


def get_session_portfolio_view() -> str:
    requested = st.session_state.get(
        "private_portfolio_requested_view",
        get_requested_portfolio_view(),
    )
    return requested if requested in PORTFOLIO_OPTIONS else "All Accounts"


def get_session_focus_account() -> str:
    requested = str(st.session_state.get(
        "private_portfolio_focus_account",
        get_requested_focus_account(),
    ) or "").strip()

    if not requested:
        return ""

    if requested in PORTFOLIO_OPTIONS:
        return requested

    cleaned = clean_account(requested)
    return cleaned if cleaned in ACCOUNT_OPTIONS else ""


def get_session_focus_symbol() -> str:
    return clean_symbol(st.session_state.get(
        "private_portfolio_focus_symbol",
        get_requested_focus_symbol(),
    ))


def render_portfolio_navigation_center(active_df: pd.DataFrame) -> None:
    """Real internal navigation for accounts and symbols.

    Account buttons open account activity. Symbol selector opens all accounts
    where that symbol exists, including open and closed trades.
    """
    if active_df is None or active_df.empty:
        return

    st.markdown(
        """
        <style>
            .jfbp-nav-title {
                color: #111827;
                font-size: 1.02rem;
                font-weight: 900;
                margin-bottom: 0.14rem;
                line-height: 1.2;
            }
            .jfbp-nav-caption {
                color: #64748b;
                font-size: 0.84rem;
                font-weight: 700;
                margin-bottom: 0.45rem;
                line-height: 1.35;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(
            """
            <div class="jfbp-nav-title">Portfolio Navigation Center</div>
            <div class="jfbp-nav-caption">Drill into accounts and symbols without leaving Private Portfolio.</div>
            """,
            unsafe_allow_html=True,
        )

        account_cols = st.columns(4)

        account_buttons = [
            ("All", "All Accounts", ""),
            ("TFSA", "TFSA", "TFSA"),
            ("RRSP", "RRSP", "RRSP"),
            ("Non-Reg", "Non-Registered", "Non-Registered"),
        ]

        for idx, (label, view_name, focus_account) in enumerate(account_buttons):
            with account_cols[idx]:
                if st.button(
                    label,
                    width="stretch",
                    key=f"portfolio_nav_account_{idx}_{view_name}",
                ):
                    _set_drilldown_state(
                        view_name=view_name,
                        focus_account=focus_account,
                        focus_symbol="",
                    )
                    st.rerun()

        symbol_options = sorted(
            active_df["Symbol"].dropna().map(clean_symbol).unique().tolist()
        ) if "Symbol" in active_df.columns else []

        nav_left, nav_mid, nav_right = st.columns([2, 1, 1])

        with nav_left:
            selected_symbol = st.selectbox(
                "Symbol Drilldown",
                [""] + symbol_options,
                format_func=lambda value: "Choose a symbol" if value == "" else value,
                key="portfolio_symbol_drilldown_select",
            )

        with nav_mid:
            if st.button(
                "Open Symbol",
                width="stretch",
                key="portfolio_open_symbol_button",
                disabled=not bool(selected_symbol),
            ):
                _set_drilldown_state(
                    view_name="All Accounts",
                    focus_account="",
                    focus_symbol=selected_symbol,
                )
                st.rerun()

        with nav_right:
            if st.button(
                "Clear Drilldown",
                width="stretch",
                key="portfolio_clear_drilldown_button",
            ):
                _clear_drilldown_state()
                st.rerun()


# =========================================================
# CASH FLOW + PERFORMANCE ENGINE
# =========================================================

def cash_flow_direction(tx_type: str) -> int:
    tx_type = clean_transaction_type(tx_type)
    if tx_type == "CASH_DEPOSIT":
        return 1
    if tx_type == "CASH_WITHDRAWAL":
        return -1
    return 0


def build_cash_flow_table(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Return external cash deposits/withdrawals from the ledger."""
    transactions = clean_transactions_df(transactions_df)

    if transactions.empty:
        return pd.DataFrame(
            columns=[
                "Date", "Account", "Currency", "Type", "Amount", "Amount CAD", "Notes",
            ]
        )

    cash_df = transactions[
        transactions["Type"].isin(CASH_TRANSACTION_TYPES)
    ].copy()

    if cash_df.empty:
        return pd.DataFrame(
            columns=[
                "Date", "Account", "Currency", "Type", "Amount", "Amount CAD", "Notes",
            ]
        )

    usd_cad_rate = fetch_usd_cad_rate()
    cash_df["Currency"] = cash_df["Account"].map(account_currency)
    cash_df["Direction"] = cash_df["Type"].map(cash_flow_direction)
    cash_df["Signed Amount"] = cash_df["Amount"].fillna(0.0) * cash_df["Direction"]
    cash_df["Amount CAD"] = cash_df.apply(
        lambda row: safe_float(row.get("Signed Amount")) * fx_to_cad(row.get("Currency"), usd_cad_rate),
        axis=1,
    )
    cash_df["_date_sort"] = pd.to_datetime(cash_df["Date"], errors="coerce")

    return cash_df.sort_values(
        ["_date_sort", "Account", "Type"],
        ascending=[False, True, True],
        na_position="last",
    ).drop(columns=["_date_sort"]).reset_index(drop=True)


def calculate_cash_flow_summary(transactions_df: pd.DataFrame) -> dict:
    cash_df = build_cash_flow_table(transactions_df)

    if cash_df.empty:
        return {
            "deposits": 0.0,
            "withdrawals": 0.0,
            "net": 0.0,
            "count": 0,
            "first_date": "N/A",
            "last_date": "N/A",
        }

    deposits = float(cash_df.loc[cash_df["Amount CAD"] > 0, "Amount CAD"].sum())
    withdrawals = abs(float(cash_df.loc[cash_df["Amount CAD"] < 0, "Amount CAD"].sum()))
    net = deposits - withdrawals

    dates = pd.to_datetime(cash_df["Date"], errors="coerce").dropna()

    return {
        "deposits": deposits,
        "withdrawals": withdrawals,
        "net": net,
        "count": int(len(cash_df)),
        "first_date": dates.min().strftime("%Y-%m-%d") if not dates.empty else "N/A",
        "last_date": dates.max().strftime("%Y-%m-%d") if not dates.empty else "N/A",
    }


@st.cache_data(ttl=3600)
def fetch_price_on_date(symbol: str, date_text: str) -> float | None:
    """Fetch the nearest available close on or before a date."""
    symbol = clean_symbol(symbol)

    if yf is None or not symbol or symbol == "CASH":
        return None

    date_value = pd.to_datetime(date_text, errors="coerce")
    if pd.isna(date_value):
        return None

    try:
        start = (date_value - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
        end = (date_value + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        history = yf.Ticker(symbol).history(start=start, end=end)

        if history is None or history.empty or "Close" not in history.columns:
            return None

        close = history["Close"].dropna()
        if close.empty:
            return None

        return float(close.iloc[-1])

    except Exception:
        return None


def estimate_portfolio_value_on_date(transactions_df: pd.DataFrame, valuation_date) -> float | None:
    """Estimate total portfolio value including reconstructed cash balance.

    This is used only for the first-pass TWR engine. It reconstructs cash by
    applying deposits, withdrawals, buys, sells, and cash income through the
    valuation date. Prices use yfinance historical closes when available.
    """
    transactions = clean_transactions_df(transactions_df)

    if transactions.empty:
        return None

    valuation_date = pd.to_datetime(valuation_date, errors="coerce")
    if pd.isna(valuation_date):
        return None

    working = transactions.copy()
    working["_date"] = pd.to_datetime(working["Date"], errors="coerce")
    working = working[working["_date"].notna()].copy()
    working = working[working["_date"] <= valuation_date].copy()

    if working.empty:
        return 0.0

    usd_cad_rate = fetch_usd_cad_rate()
    cash_cad = 0.0
    positions: dict[tuple[str, str], float] = {}

    for _, tx in working.sort_values("_date").iterrows():
        account = clean_account(tx.get("Account"))
        currency = account_currency(account)
        fx_rate = fx_to_cad(currency, usd_cad_rate)
        symbol = clean_symbol(tx.get("Symbol"))
        tx_type = clean_transaction_type(tx.get("Type"))
        shares = safe_float(tx.get("Shares"))
        price = safe_float(tx.get("Price"))
        amount = safe_float(tx.get("Amount"))
        amount_value = amount if amount > 0 else shares * price
        key = (account, symbol)

        if tx_type == "CASH_DEPOSIT":
            cash_cad += amount * fx_rate
        elif tx_type == "CASH_WITHDRAWAL":
            cash_cad -= amount * fx_rate
        elif tx_type == "BUY":
            positions[key] = positions.get(key, 0.0) + shares
            cash_cad -= amount_value * fx_rate
        elif tx_type == "SELL":
            positions[key] = positions.get(key, 0.0) - shares
            cash_cad += amount_value * fx_rate
        elif tx_type == "DRIP":
            positions[key] = positions.get(key, 0.0) + shares
        elif tx_type in INCOME_TRANSACTION_TYPES:
            cash_cad += amount * fx_rate

    holdings_value_cad = 0.0
    for (account, symbol), shares in positions.items():
        if shares <= 0 or not symbol or symbol == "CASH":
            continue

        currency = account_currency(account)
        price = fetch_price_on_date(symbol, valuation_date.strftime("%Y-%m-%d"))

        if price is None:
            # Fall back to the last transaction price for that symbol/account.
            symbol_rows = working[
                (working["Account"].map(clean_account) == account)
                & (working["Symbol"].map(clean_symbol) == symbol)
                & (working["Price"].fillna(0.0) > 0)
            ]
            if symbol_rows.empty:
                continue
            price = safe_float(symbol_rows.iloc[-1].get("Price"))

        holdings_value_cad += shares * price * fx_to_cad(currency, usd_cad_rate)

    return holdings_value_cad + cash_cad


def calculate_time_weighted_return_from_cashflows(transactions_df: pd.DataFrame, current_portfolio_value: float) -> float | None:
    """First-pass TWR from cash-flow dates.

    Requires CASH_DEPOSIT / CASH_WITHDRAWAL rows. Without those external cash
    flows, the function returns None rather than manufacturing a fake TWR.
    """
    transactions = clean_transactions_df(transactions_df)
    cash_df = build_cash_flow_table(transactions)

    if cash_df.empty:
        return None

    cash_dates = pd.to_datetime(cash_df["Date"], errors="coerce").dropna().sort_values().unique()

    if len(cash_dates) == 0:
        return None

    period_returns = []
    start_date = pd.Timestamp(cash_dates[0])
    start_value = estimate_portfolio_value_on_date(transactions, start_date)

    if start_value is None or start_value <= 0:
        return None

    # Value just before each later external cash flow, then restart after that flow.
    for next_date_raw in cash_dates[1:]:
        next_date = pd.Timestamp(next_date_raw)
        day_before = next_date - pd.Timedelta(days=1)
        end_value = estimate_portfolio_value_on_date(transactions, day_before)

        if end_value is not None and start_value > 0:
            period_returns.append(end_value / start_value - 1.0)

        start_value = estimate_portfolio_value_on_date(transactions, next_date)
        if start_value is None or start_value <= 0:
            return None

    # Final period ends at current dashboard value. This avoids a second live price pass.
    if current_portfolio_value > 0 and start_value > 0:
        period_returns.append(current_portfolio_value / start_value - 1.0)

    if not period_returns:
        return None

    compounded = 1.0
    for value in period_returns:
        compounded *= 1.0 + value

    return (compounded - 1.0) * 100.0


def render_cash_flow_center(transactions_df: pd.DataFrame) -> None:
    """Render external deposits and withdrawals for TWR readiness."""
    cash_df = build_cash_flow_table(transactions_df)
    summary = calculate_cash_flow_summary(transactions_df)

    row = st.columns(4)

    with row[0]:
        metric_card(
            "Deposits",
            f"{format_money(summary['deposits'])} CAD",
            "External cash in",
            tone="good" if summary["deposits"] > 0 else "neutral",
        )

    with row[1]:
        metric_card(
            "Withdrawals",
            f"{format_money(summary['withdrawals'])} CAD",
            "External cash out",
            tone="warning" if summary["withdrawals"] > 0 else "neutral",
        )

    with row[2]:
        metric_card(
            "Net Contributions",
            f"{format_money(summary['net'])} CAD",
            f"{summary['count']} cash-flow row(s)",
            tone="info",
        )

    with row[3]:
        metric_card(
            "Cash-Flow History",
            summary["first_date"],
            f"Last: {summary['last_date']}",
            tone="neutral",
        )

    if cash_df.empty:
        st.info("Add CASH_DEPOSIT and CASH_WITHDRAWAL rows in the Transaction Ledger to activate cash-flow-aware performance tracking.")
        return

    display_df = cash_df[["Date", "Account", "Currency", "Type", "Amount", "Amount CAD", "Notes"]].copy()
    display_df["Amount"] = display_df.apply(
        lambda row: format_money_currency(abs(safe_float(row.get("Amount"))), row.get("Currency", "CAD")),
        axis=1,
    )
    display_df["Amount CAD"] = display_df["Amount CAD"].map(lambda value: f"{format_money(value)} CAD")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )



# =========================================================
# FAMILY OFFICE COMMANDER LAYER — v2.0
# =========================================================

def inject_family_office_css() -> None:
    st.markdown(
        """
        <style>
            .jfbp-wealth-hero {
                border: 1px solid #bbf7d0;
                background: #ecfdf5;
                border-radius: 18px;
                padding: 0.88rem 0.92rem;
                margin: 0.60rem 0 0.82rem 0;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
            }
            .jfbp-wealth-hero.watch {
                border-color: #fde68a;
                background: #fffbeb;
            }
            .jfbp-wealth-hero.risk {
                border-color: #fecaca;
                background: #fef2f2;
            }
            .jfbp-wealth-kicker {
                font-size: 0.72rem;
                letter-spacing: 0.055em;
                text-transform: uppercase;
                color: #64748b;
                font-weight: 850;
                margin-bottom: 0.24rem;
            }
            .jfbp-wealth-title {
                font-size: clamp(1.22rem, 2.35vw, 1.62rem);
                line-height: 1.14;
                font-weight: 880;
                color: #166534;
                margin-bottom: 0.30rem;
            }
            .jfbp-wealth-hero.watch .jfbp-wealth-title { color: #92400e; }
            .jfbp-wealth-hero.risk .jfbp-wealth-title { color: #991b1b; }
            .jfbp-wealth-summary {
                font-size: 0.94rem;
                color: #334155;
                font-weight: 700;
                line-height: 1.38;
                margin-bottom: 0.36rem;
            }
            .jfbp-wealth-action {
                background: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                padding: 0.60rem 0.78rem;
                color: #111827;
                font-size: 0.94rem;
                font-weight: 820;
                line-height: 1.35;
            }
            .jfbp-family-score-row {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                gap: 0.75rem;
                align-items: center;
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 0.68rem 0.75rem;
                margin-bottom: 0.45rem;
            }
            .jfbp-family-score-label {
                font-weight: 950;
                color: #111827;
            }
            .jfbp-family-score-detail {
                color: #64748b;
                font-size: 0.78rem;
                margin-top: 0.12rem;
            }
            .jfbp-family-score-value {
                font-weight: 950;
                color: #1d4ed8;
                white-space: nowrap;
            }
            @media (max-width: 760px) {
                .jfbp-family-score-row { grid-template-columns: 1fr; }
                .jfbp-family-score-value { white-space: normal; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _family_letter_from_health(score: float) -> str:
    try:
        score = float(score)
    except Exception:
        score = 0.0
    if score >= 90: return "A"
    if score >= 80: return "B+"
    if score >= 70: return "B"
    if score >= 60: return "C"
    return "D"


def _family_tone_from_status(status: str) -> str:
    status = str(status or "").upper()
    if status in ("STRONG", "HEALTHY", "ON TRACK"):
        return "good"
    if status in ("WATCH", "BUILDING", "ACCUMULATION"):
        return "warning"
    return "risk"


def _family_hero_class(tone: str) -> str:
    if tone == "risk":
        return "risk"
    if tone == "warning":
        return "watch"
    return ""


def calculate_dynamic_wealth_status(
    health_score: float,
    total_return_pct: float,
    max_weight: float,
    top3_weight: float,
    projected_annual_income: float,
    projected_yield: float,
    cash_flow_count: int,
) -> dict:
    """Commander wealth-status engine.

    Converts portfolio condition into the same command language used across
    the rest of JFBP Quant Desk. The status is advisory only and is based on
    diversification, concentration, income, return profile, and ledger quality.
    """
    health_score = safe_float(health_score)
    total_return_pct = safe_float(total_return_pct)
    max_weight = safe_float(max_weight)
    top3_weight = safe_float(top3_weight)
    projected_annual_income = safe_float(projected_annual_income)
    projected_yield = safe_float(projected_yield)
    cash_flow_count = int(cash_flow_count or 0)

    # Retirement readiness target is planning-only. It already exists on the
    # page, so the status engine can use it without adding another input.
    target_income = safe_float(
        st.session_state.get("private_portfolio_income_target", 36000.0),
        36000.0,
    )
    income_coverage = (
        projected_annual_income / target_income * 100.0
        if target_income > 0
        else 0.0
    )

    concerns = []
    strengths = []
    tone = "good"

    if max_weight >= 45 or top3_weight >= 70 or health_score < 55:
        status = "🔴 DEFENSIVE"
        tone = "risk"
        if max_weight >= 45:
            concerns.append(f"largest holding is {max_weight:.1f}%")
        if top3_weight >= 70:
            concerns.append(f"top 3 concentration is {top3_weight:.1f}%")
        if health_score < 55:
            concerns.append(f"health score is {health_score:.0f}/100")
        action = "Reduce concentration risk and review laggards before adding new capital."

    elif max_weight >= 35 or top3_weight >= 60 or total_return_pct < -5:
        status = "🟠 CAUTION"
        tone = "warning"
        if max_weight >= 35:
            concerns.append(f"largest holding is {max_weight:.1f}%")
        if top3_weight >= 60:
            concerns.append(f"top 3 concentration is {top3_weight:.1f}%")
        if total_return_pct < -5:
            concerns.append(f"simple return is {total_return_pct:.2f}%")
        action = "Hold new exposure until concentration and underperformers are reviewed."

    elif health_score < 70 or total_return_pct < 0 or cash_flow_count == 0:
        status = "🟡 REVIEW"
        tone = "warning"
        if health_score < 70:
            concerns.append(f"health score is {health_score:.0f}/100")
        if total_return_pct < 0:
            concerns.append(f"simple return is {total_return_pct:.2f}%")
        if cash_flow_count == 0:
            concerns.append("cash-flow rows are missing for TWR accuracy")
        action = "Portfolio is usable, but review data quality, allocation drift, and underperformers."

    elif income_coverage >= 60 and projected_yield >= 2.0 and total_return_pct >= 0 and health_score >= 80:
        status = "🟢 ON TRACK"
        tone = "good"
        strengths.append(f"income coverage {income_coverage:.1f}%")
        strengths.append(f"health score {health_score:.0f}/100")
        action = "Portfolio is constructive. Continue accumulation and monitor allocation drift."

    else:
        status = "🟢 ACCUMULATING"
        tone = "good"
        if projected_annual_income > 0:
            strengths.append(f"projected income {format_money(projected_annual_income)} CAD")
        if total_return_pct >= 0:
            strengths.append(f"simple return {total_return_pct:.2f}%")
        action = "Portfolio is building. Continue deposits, income tracking, and disciplined allocation."

    detail_parts = concerns if concerns else strengths
    detail = " · ".join(detail_parts) if detail_parts else "No major portfolio warning detected."

    return {
        "status": status,
        "tone": tone,
        "action": action,
        "detail": detail,
        "income_coverage": income_coverage,
        "target_income": target_income,
    }


def build_family_office_snapshot(
    active_df: pd.DataFrame,
    portfolio_value: float,
    total_gain: float,
    total_return_pct: float,
    time_weighted_return,
    unrealized_gain: float,
    total_dividends: float,
    total_realized: float,
    weighted_move: float,
    holding_count: int,
    projected_annual_income: float,
    projected_monthly_income: float,
    projected_yield: float,
    cash_flow_summary: dict,
) -> dict:
    health = calculate_portfolio_health(active_df)
    grade = calculate_portfolio_grade(active_df)
    radar = calculate_portfolio_radar(active_df)

    max_weight = 0.0
    top_symbol = "N/A"
    top3_weight = 0.0
    top3_symbols = "N/A"

    if active_df is not None and not active_df.empty and "Weight" in active_df.columns:
        weight_df = active_df.copy().sort_values("Weight", ascending=False, na_position="last")
        top_row = weight_df.iloc[0]
        max_weight = safe_float(top_row.get("Weight"))
        top_symbol = clean_symbol(top_row.get("Symbol")) or "N/A"
        top3 = weight_df.head(3)
        top3_weight = float(top3["Weight"].map(safe_float).sum())
        top3_symbols = ", ".join(top3["Symbol"].map(clean_symbol).tolist())

    score = safe_float(health.get("score"))
    grade_letter = grade.get("overall") if grade else _family_letter_from_health(score)

    status_engine = calculate_dynamic_wealth_status(
        health_score=score,
        total_return_pct=total_return_pct,
        max_weight=max_weight,
        top3_weight=top3_weight,
        projected_annual_income=projected_annual_income,
        projected_yield=projected_yield,
        cash_flow_count=int(cash_flow_summary.get("count", 0) or 0),
    )

    wealth_status = status_engine["status"]
    action = status_engine["action"]
    tone = status_engine["tone"]

    return {
        "wealth_status": wealth_status,
        "tone": tone,
        "action": action,
        "status_detail": status_engine.get("detail", ""),
        "income_coverage": status_engine.get("income_coverage", 0.0),
        "target_income": status_engine.get("target_income", 0.0),
        "portfolio_value": portfolio_value,
        "total_gain": total_gain,
        "total_return_pct": total_return_pct,
        "time_weighted_return": time_weighted_return,
        "unrealized_gain": unrealized_gain,
        "total_dividends": total_dividends,
        "total_realized": total_realized,
        "weighted_move": weighted_move,
        "holding_count": holding_count,
        "projected_annual_income": projected_annual_income,
        "projected_monthly_income": projected_monthly_income,
        "projected_yield": projected_yield,
        "health_score": score,
        "health_grade": health.get("grade", "N/A"),
        "grade_letter": grade_letter,
        "top_symbol": top_symbol,
        "top_weight": max_weight,
        "top3_weight": top3_weight,
        "top3_symbols": top3_symbols,
        "radar": radar,
        "cash_flow_net": safe_float(cash_flow_summary.get("net")),
        "cash_flow_count": int(cash_flow_summary.get("count", 0) or 0),
    }


def render_commander_wealth_report(snapshot: dict, selected_account: str) -> None:
    tone = snapshot.get("tone", "good")
    hero_class = _family_hero_class(tone)
    twr = snapshot.get("time_weighted_return")
    twr_text = format_pct(twr) if twr is not None else "N/A"

    st.subheader("🏦 Commander Wealth Report")
    st.caption("Fast family-office read: value, income, return, concentration, and immediate action.")

    st.markdown(
        f"""
        <div class="jfbp-wealth-hero {hero_class}">
            <div class="jfbp-wealth-kicker">Institutional Family Office Command · {html.escape(str(selected_account))}</div>
            <div class="jfbp-wealth-title">🏦 WEALTH STATUS: {html.escape(str(snapshot.get('wealth_status', 'N/A')))}</div>
            <div class="jfbp-wealth-summary">
                Portfolio Value: {html.escape(format_money(snapshot.get('portfolio_value')))} CAD ·
                Total Gain: {html.escape(format_money(snapshot.get('total_gain')))} CAD ·
                Simple Return: {html.escape(format_pct(snapshot.get('total_return_pct')))} ·
                TWR: {html.escape(twr_text)} ·
                Annual Income: {html.escape(format_money(snapshot.get('projected_annual_income')))} CAD ·
                Income Coverage: {html.escape(f"{safe_float(snapshot.get('income_coverage')):.1f}%")} ·
                Grade: {html.escape(str(snapshot.get('grade_letter', 'N/A')))}
            </div>
            <div class="jfbp-wealth-action">ACTION: {html.escape(str(snapshot.get('action', '')))}<br><span style="color:#64748b;font-weight:800;">Signal: {html.escape(str(snapshot.get('status_detail', '')))}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Portfolio Grade", snapshot.get("grade_letter", "N/A"), f"Health {snapshot.get('health_score', 0):.0f}/100", tone=tone)
    with c2:
        metric_card("Monthly Income", f"{format_money(snapshot.get('projected_monthly_income'))} CAD", f"Yield {snapshot.get('projected_yield', 0):.2f}%", tone="good" if snapshot.get("projected_monthly_income", 0) > 0 else "neutral")
    with c3:
        metric_card("Largest Holding", snapshot.get("top_symbol", "N/A"), f"{snapshot.get('top_weight', 0):.1f}% portfolio weight", tone="risk" if snapshot.get("top_weight", 0) >= 35 else "info")
    with c4:
        metric_card("Top 3 Concentration", f"{snapshot.get('top3_weight', 0):.1f}%", snapshot.get("top3_symbols", "N/A"), tone="risk" if snapshot.get("top3_weight", 0) >= 65 else "warning" if snapshot.get("top3_weight", 0) >= 50 else "good")


def render_executive_wealth_brief(snapshot: dict) -> None:
    st.subheader("Executive Wealth Brief")
    st.caption("Operational dashboard metrics for workflow execution, concentration control, and ledger readiness.")
    r1 = st.columns(4)
    r2 = st.columns(4)
    with r1[0]: metric_card("Active Holdings", f"{snapshot.get('holding_count', 0)}", "Current open positions", tone="info")
    with r1[1]: metric_card("Advancing Today", format_pct(snapshot.get("weighted_move")), calculate_impact_label(snapshot.get("weighted_move", 0)), tone="good" if snapshot.get("weighted_move", 0) >= 0 else "risk")
    with r1[2]: metric_card("Largest Position", snapshot.get("top_symbol", "N/A"), f"{snapshot.get('top_weight', 0):.1f}% portfolio weight", tone="risk" if snapshot.get("top_weight", 0) >= 35 else "info")
    with r1[3]: metric_card("Top 3 Concentration", f"{snapshot.get('top3_weight', 0):.1f}%", snapshot.get("top3_symbols", "N/A"), tone="risk" if snapshot.get("top3_weight", 0) >= 65 else "warning" if snapshot.get("top3_weight", 0) >= 50 else "good")
    with r2[0]: metric_card("Unrealized Gain", f"{format_money(snapshot.get('unrealized_gain'))} CAD", "Open positions", tone="good" if snapshot.get("unrealized_gain", 0) >= 0 else "risk")
    with r2[1]: metric_card("Realized Gain", f"{format_money(snapshot.get('total_realized'))} CAD", "Closed trades", tone="good" if snapshot.get("total_realized", 0) >= 0 else "risk")
    with r2[2]: metric_card("Dividends Received", f"{format_money(snapshot.get('total_dividends'))} CAD", "Ledger income", tone="good" if snapshot.get("total_dividends", 0) > 0 else "neutral")
    with r2[3]: metric_card("Cash-Flow Ledger", f"{snapshot.get('cash_flow_count', 0)} rows", f"Net {format_money(snapshot.get('cash_flow_net'))} CAD", tone="info")


def calculate_private_holding_scores(active_df: pd.DataFrame) -> pd.DataFrame:
    if active_df is None or active_df.empty:
        return pd.DataFrame()
    df = active_df.copy()
    total_value = safe_float(df.get("Market Value CAD", pd.Series([0])).sum())
    rows = []
    for _, row in df.iterrows():
        symbol = clean_symbol(row.get("Symbol"))
        weight = safe_float(row.get("Weight"))
        total_return = safe_float(row.get("Total Return %"))
        value = safe_float(row.get("Market Value CAD"))
        projected_income = value * estimate_forward_yield(symbol)
        income_score = min(35, (projected_income / max(total_value * 0.04, 1)) * 35)
        return_score = max(0, min(35, 17.5 + total_return * 0.7))
        diversification_score = 20 if weight <= 20 else 15 if weight <= 30 else 8 if weight <= 45 else 2
        day_score = 10 if safe_float(row.get("Day %")) >= 0 else 4
        score = int(round(min(100, income_score + return_score + diversification_score + day_score)))
        if weight >= 40:
            action = "TRIM / REVIEW"
        elif total_return < -10:
            action = "REVIEW"
        elif projected_income > 0 and total_return >= 0:
            action = "CORE / HOLD"
        else:
            action = "HOLD"
        rows.append({
            "Rank": 0,
            "Symbol": symbol,
            "Account": str(row.get("Account", "")),
            "Weight": f"{weight:.1f}%",
            "Market Value CAD": format_money(value),
            "Total Return": format_pct(total_return),
            "Projected Income": f"{format_money(projected_income)} CAD",
            "Score": f"{score}/100",
            "Action": action,
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["_score"] = out["Score"].str.replace("/100", "", regex=False).astype(float)
    out = out.sort_values("_score", ascending=False).reset_index(drop=True)
    out["Rank"] = [f"#{i+1}" for i in range(len(out))]
    return out.drop(columns=["_score"])


def render_private_holding_ranking_engine(active_df: pd.DataFrame) -> None:
    st.subheader("🏆 Holdings Ranking Engine")
    st.caption("Ranks holdings by income contribution, return profile, diversification value, and open risk.")
    rank_df = calculate_private_holding_scores(active_df)
    if rank_df.empty:
        st.info("No active holdings to rank.")
        return

    # Freeze fix:
    # Streamlit can under-reserve vertical space for dataframes when this
    # section renders inside responsive columns. A stable height plus a
    # small spacer prevents the Family Office Scorecard header from
    # overlapping the bottom rows of the ranking table.
    ranking_height = min(
        420,
        max(320, 38 * (len(rank_df) + 1)),
    )

    st.dataframe(
        rank_df,
        use_container_width=True,
        hide_index=True,
        height=ranking_height,
    )

    st.markdown(
        "<div style='height: 1.25rem;'></div>",
        unsafe_allow_html=True,
    )


def render_family_scorecard(snapshot: dict, active_df: pd.DataFrame) -> None:
    st.subheader("📋 Family Office Scorecard")
    st.caption("Investor report card for diversification, income, growth, risk, and data quality.")
    holding_count = int(snapshot.get("holding_count", 0) or 0)
    diversification_score = min(100, holding_count * 12)
    income_score = min(100, snapshot.get("projected_yield", 0) / 4.0 * 100) if snapshot.get("projected_yield", 0) > 0 else 0
    growth_score = max(0, min(100, 50 + snapshot.get("total_return_pct", 0) * 2))
    risk_score = 100 if snapshot.get("top3_weight", 0) <= 45 else 75 if snapshot.get("top3_weight", 0) <= 60 else 45
    data_score = 100 if snapshot.get("cash_flow_count", 0) > 0 else 70
    rows = [
        ("Diversification", diversification_score, f"{holding_count} active holdings"),
        ("Income", income_score, f"Projected yield {snapshot.get('projected_yield', 0):.2f}%"),
        ("Growth", growth_score, f"Simple return {format_pct(snapshot.get('total_return_pct'))}"),
        ("Risk", risk_score, f"Top 3 concentration {snapshot.get('top3_weight', 0):.1f}%"),
        ("Data Quality", data_score, "Cash-flow rows improve TWR accuracy"),
    ]
    for label, score, detail in rows:
        icon = "🟢" if score >= 75 else "🟡" if score >= 55 else "🔴"
        st.markdown(
            f"""
            <div class="jfbp-family-score-row">
                <div>
                    <div class="jfbp-family-score-label">{icon} {html.escape(label)}</div>
                    <div class="jfbp-family-score-detail">{html.escape(detail)}</div>
                </div>
                <div class="jfbp-family-score-value">{score:.0f}/100</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_retirement_readiness_monitor(snapshot: dict) -> None:
    """Compact planning monitor for the right rail.

    The earlier version used four skinny cards in the 30% column, which made
    the right rail very tall and created dead space on the left. This version
    keeps the planning target visible, then uses two compact rows so the
    command layer stays balanced.
    """
    st.subheader("🧭 Retirement Readiness Monitor")
    st.caption("Income-coverage view. Target can be adjusted for planning only; it does not change portfolio data.")
    default_target = float(st.session_state.get("private_portfolio_income_target", 36000.0) or 36000.0)
    target_income = st.number_input(
        "Target annual portfolio income (CAD)",
        min_value=0.0,
        value=default_target,
        step=1000.0,
        key="private_portfolio_income_target",
    )
    annual_income = safe_float(snapshot.get("projected_annual_income"))
    coverage = annual_income / target_income * 100 if target_income > 0 else 0.0
    gap = max(0.0, target_income - annual_income)

    top = st.columns(2)
    bottom = st.columns(2)
    with top[0]:
        metric_card("Projected Income", f"{format_money(annual_income)} CAD", "Current estimate", tone="good" if annual_income > 0 else "neutral")
    with top[1]:
        metric_card("Coverage Ratio", f"{coverage:.1f}%", "Projected / target", tone="good" if coverage >= 100 else "warning")
    with bottom[0]:
        metric_card("Target Income", f"{format_money(target_income)} CAD", "Planning target", tone="info")
    with bottom[1]:
        metric_card("Income Gap", f"{format_money(gap)} CAD", "Annual gap", tone="good" if gap <= 0 else "warning")


def render_portfolio_summary_cards(
    portfolio_value: float,
    total_gain: float,
    total_return_pct: float,
    time_weighted_return,
    unrealized_gain: float,
    total_dividends: float,
    total_realized: float,
    weighted_move: float,
    holding_count: int,
    positive_count: int,
) -> None:
    """Reusable compact portfolio summary for the command layer."""
    portfolio_impact = calculate_impact_label(weighted_move)

    row1 = st.columns(3)
    row2 = st.columns(3)
    row3 = st.columns(2)

    with row1[0]:
        metric_card("Portfolio Value", f"{format_money(portfolio_value)} CAD", f"{holding_count} holdings", tone="info")
    with row1[1]:
        metric_card("Simple Return", format_pct(total_return_pct), f"{format_money(total_gain)} CAD", tone="good" if total_return_pct >= 0 else "risk")
    with row1[2]:
        metric_card(
            "Time-Weighted Return",
            format_pct(time_weighted_return),
            "Cash-flow adjusted" if time_weighted_return is not None else "Add deposit/withdrawal rows",
            tone="good" if (time_weighted_return or 0) >= 0 and time_weighted_return is not None else "neutral",
        )

    with row2[0]:
        metric_card("Unrealized Gain", f"{format_money(unrealized_gain)} CAD", "Open positions", tone="good" if unrealized_gain >= 0 else "risk")
    with row2[1]:
        metric_card("Today's Move", format_pct(weighted_move), portfolio_impact, tone="good" if weighted_move >= 0 else "risk")
    with row2[2]:
        metric_card("Dividends", f"{format_money(total_dividends)} CAD", "Total received", tone="good" if total_dividends > 0 else "neutral")

    with row3[0]:
        metric_card("Realized Gain", f"{format_money(total_realized)} CAD", "Closed positions", tone="good" if total_realized >= 0 else "risk")
    with row3[1]:
        metric_card("Advancing", f"{positive_count}/{holding_count}", "Holdings positive today", tone="good" if positive_count >= holding_count / 2 else "warning")


def render_family_office_command_layer(
    selected_account: str,
    active_df: pd.DataFrame,
    portfolio_value: float,
    total_gain: float,
    total_return_pct: float,
    time_weighted_return,
    unrealized_gain: float,
    total_dividends: float,
    total_realized: float,
    weighted_move: float,
    holding_count: int,
    positive_count: int,
    cash_flow_summary: dict,
) -> dict:
    inject_family_office_css()
    projected_annual_income, projected_monthly_income, projected_yield = calculate_projected_income(active_df)
    snapshot = build_family_office_snapshot(
        active_df=active_df,
        portfolio_value=portfolio_value,
        total_gain=total_gain,
        total_return_pct=total_return_pct,
        time_weighted_return=time_weighted_return,
        unrealized_gain=unrealized_gain,
        total_dividends=total_dividends,
        total_realized=total_realized,
        weighted_move=weighted_move,
        holding_count=holding_count,
        projected_annual_income=projected_annual_income,
        projected_monthly_income=projected_monthly_income,
        projected_yield=projected_yield,
        cash_flow_summary=cash_flow_summary,
    )

    render_commander_wealth_report(snapshot, selected_account)
    render_executive_wealth_brief(snapshot)

    render_retirement_readiness_monitor(snapshot)
    with st.expander("⚖️ Rebalance Command Center", expanded=True):
        st.caption("Strategic target drift. Advisory only; not an automatic rebalance instruction.")
        render_rebalance_engine(active_df)

    return snapshot


# =========================================================
# PAGE
# =========================================================

def render_transaction_ledger_editor(transactions_df: pd.DataFrame, user_id: str | None = None) -> None:
    """Maintenance editor for adding/saving portfolio transactions.

    v36 stability fix:
    - The editor is wrapped in a Streamlit form so typing/editing rows does not
      trigger a full page rerun on every cell change.
    - The ledger expander is opened by default from the caller, so it will not
      collapse while you are working.
    - Delete tools operate from the saved/current ledger and only rerun after a
      deliberate delete or save action.
    """
    st.session_state["private_portfolio_ledger_open"] = True

    st.caption(
        "Add one row for every event: BUY, SELL, DIVIDEND, DRIP, EARNINGS, INTEREST, "
        "MANUFACTURED_DIVIDEND, CASH_DEPOSIT, or CASH_WITHDRAWAL. For dividends and cash flows, "
        "enter Amount and leave Shares/Price at 0. For DRIP, enter Shares, Price, and optionally Amount."
    )

    editor_version = st.session_state.get("private_portfolio_editor_version", 0)

    with st.form(
        key=f"private_portfolio_transactions_form_{editor_version}",
        clear_on_submit=False,
    ):
        edited_transactions = st.data_editor(
            transactions_df,
            num_rows="dynamic",
            use_container_width=True,
            height=360,
            hide_index=True,
            column_config={
                "Date": st.column_config.TextColumn(
                    "Date",
                    help="Use YYYY-MM-DD format.",
                    width="medium",
                ),
                "Account": st.column_config.SelectboxColumn(
                    "Account",
                    options=ACCOUNT_OPTIONS,
                    required=True,
                    width="medium",
                ),
                "Symbol": st.column_config.TextColumn(
                    "Symbol",
                    help="Ticker symbol, for example VFV.TO or SCHD. For cash-flow rows, use CASH or leave blank before saving.",
                    required=False,
                    width="small",
                ),
                "Type": st.column_config.SelectboxColumn(
                    "Type",
                    options=TRANSACTION_TYPES,
                    required=True,
                    width="medium",
                ),
                "Shares": st.column_config.NumberColumn(
                    "Shares",
                    min_value=0.0,
                    step=0.0001,
                    format="%.4f",
                ),
                "Price": st.column_config.NumberColumn(
                    "Price",
                    min_value=0.0,
                    step=0.01,
                    format="$%.2f",
                ),
                "Amount": st.column_config.NumberColumn(
                    "Amount",
                    min_value=0.0,
                    step=0.01,
                    format="$%.2f",
                ),
                "Notes": st.column_config.TextColumn(
                    "Notes",
                ),
            },
            key=f"private_portfolio_transactions_editor_{editor_version}",
        )

        save_col, file_col = st.columns([1, 3])

        with save_col:
            save_clicked = st.form_submit_button(
                "Save Transactions",
                type="primary",
                width="stretch",
            )

        with file_col:
            if user_id:
                st.caption("Storage: Supabase primary (user-scoped) with local emergency fallback.")
            else:
                st.caption(f"Saved file: {_transactions_file_for_user('')}")

    if save_clicked:
        save_transactions(edited_transactions, user_id=user_id)
        st.session_state["private_portfolio_editor_version"] = editor_version + 1
        st.session_state["private_portfolio_ledger_open"] = True
        st.success("Transactions saved.")
        st.rerun()

    with st.expander("🗑️ Delete Transaction Rows", expanded=False):
        st.caption(
            "Use this when a row refuses to disappear from the editor. "
            "This delete tool uses the current saved ledger and only reruns after you press Delete."
        )

        delete_preview_df = clean_transactions_df(transactions_df)

        delete_col1, delete_col2, delete_col3, delete_col4 = st.columns([1, 1, 1, 1])

        with delete_col1:
            delete_account = st.selectbox(
                "Account",
                ["Any Account"] + ACCOUNT_OPTIONS,
                key="private_portfolio_delete_account",
            )

        symbols_available = sorted(
            [
                sym for sym in delete_preview_df["Symbol"].dropna().unique().tolist()
                if str(sym).strip()
            ]
        )

        with delete_col2:
            delete_symbol = st.selectbox(
                "Symbol",
                ["Any Symbol"] + symbols_available,
                key="private_portfolio_delete_symbol",
            )

        with delete_col3:
            delete_type = st.selectbox(
                "Type",
                ["Any Type"] + TRANSACTION_TYPES,
                key="private_portfolio_delete_type",
            )

        delete_mask = pd.Series(True, index=delete_preview_df.index)

        if delete_account != "Any Account":
            delete_mask &= delete_preview_df["Account"].map(clean_account) == clean_account(delete_account)

        if delete_symbol != "Any Symbol":
            delete_mask &= delete_preview_df["Symbol"].map(clean_symbol) == clean_symbol(delete_symbol)

        if delete_type != "Any Type":
            delete_mask &= delete_preview_df["Type"].map(clean_transaction_type) == clean_transaction_type(delete_type)

        rows_to_delete = int(delete_mask.sum()) if not delete_preview_df.empty else 0

        with delete_col4:
            st.write("")
            delete_clicked = st.button(
                f"Delete {rows_to_delete} row(s)",
                type="secondary",
                width="stretch",
                disabled=rows_to_delete <= 0,
                key="private_portfolio_delete_rows_button",
            )

        if rows_to_delete > 0:
            st.dataframe(
                delete_preview_df.loc[delete_mask, TRANSACTION_COLUMNS],
                use_container_width=True,
                hide_index=True,
            )

        if delete_clicked and rows_to_delete > 0:
            remaining_df = delete_preview_df.loc[~delete_mask, TRANSACTION_COLUMNS].copy()
            save_transactions(remaining_df, user_id=user_id)
            st.session_state["private_portfolio_editor_version"] = editor_version + 1
            st.session_state["private_portfolio_ledger_open"] = True
            st.success(f"Deleted {rows_to_delete} transaction row(s) and saved the ledger.")
            st.rerun()


def run_page() -> None:

    jfbp_inject_responsive_css(max_width=1500)
    jfbp_inject_card_css()

    st.markdown(
        """
        <style>
            .block-container {
                max-width: 100% !important;
                padding-top: 1.25rem !important;
                padding-left: clamp(0.75rem, 2vw, 2rem) !important;
                padding-right: clamp(0.75rem, 2vw, 2rem) !important;
            }
            div[data-testid="stDataFrame"],
            div[data-testid="stDataEditor"] {
                width: 100% !important;
            }
            div[data-testid="stDataFrame"] div,
            div[data-testid="stDataEditor"] div {
                max-width: 100% !important;
            }
            .jfbp-section-tight h2,
            .jfbp-section-tight h3 {
                margin-bottom: 0.2rem !important;
            }
            .jfbp-link {
                color: #2563eb !important;
                font-weight: 900;
                text-decoration: none !important;
            }
            .jfbp-link:hover {
                text-decoration: underline !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] {
                border: 1px solid #e5e7eb !important;
                border-radius: 16px !important;
                background: #ffffff !important;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] > div {
                padding: 0.78rem 0.86rem !important;
            }
            div[data-testid="stTabs"] {
                margin-top: 0.15rem !important;
            }

            /* Mobile stability pass: keep Streamlit grids/tables inside the viewport. */
            @media (max-width: 900px) {
                .block-container {
                    padding-left: 0.55rem !important;
                    padding-right: 0.55rem !important;
                }

                div[data-testid="stHorizontalBlock"] {
                    gap: 0.75rem !important;
                }

                div[data-testid="stDataFrame"],
                div[data-testid="stDataEditor"] {
                    overflow-x: auto !important;
                    -webkit-overflow-scrolling: touch !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    title_col, refresh_col = st.columns([5, 1])

    with title_col:
        st.title("🏦 Private Portfolio")
        st.caption(
            "Family Office command center for personal portfolio value, income, allocation, ledger history, and retirement readiness. "
            "Logged-in users use Supabase as primary storage with user-scoped persistence."
        )
        render_private_portfolio_help()

    with refresh_col:
        refresh = st.button(
            "Refresh Data",
            width="stretch",
        )

    if refresh:
        st.rerun()

    if bool(str(_current_saas_user_id() or "").strip()):
        st.warning(
            "Private Portfolio Supabase storage currently uses position snapshots from portfolio_positions, "
            "not full transaction history. Ledger rows remain locally persisted as emergency fallback."
        )

    with st.spinner("Loading private portfolio data..."):
        report = generate_market_reaction_report()

    portfolio = report.get("portfolio")
    source_portfolio_df = None

    if portfolio is not None:
        source_portfolio_df = portfolio.get("portfolio_df")

    market_df = normalize_market_df(source_portfolio_df)
    default_transactions_df = default_transactions_from_market(market_df)
    current_user_id = _current_saas_user_id()
    transactions_df = load_transactions(default_transactions_df, user_id=current_user_id)
    saved_transactions_df = clean_transactions_df(transactions_df)

    requested_view = get_session_portfolio_view()
    focus_account = get_session_focus_account()
    focus_symbol = get_session_focus_symbol()

    selected_account = st.selectbox(
        "Portfolio View",
        PORTFOLIO_OPTIONS,
        index=PORTFOLIO_OPTIONS.index(requested_view),
        help="Choose one account or view all accounts combined.",
        key="private_portfolio_view_select",
    )

    if selected_account == "All Accounts":
        dashboard_transactions_df = saved_transactions_df.copy()
    elif selected_account == "CAD Accounts":
        dashboard_transactions_df = saved_transactions_df[
            saved_transactions_df["Account"].map(clean_account).isin(CAD_ACCOUNTS)
        ].copy()
    elif selected_account == "USD Accounts":
        dashboard_transactions_df = saved_transactions_df[
            saved_transactions_df["Account"].map(clean_account).isin(USD_ACCOUNTS)
        ].copy()
    else:
        dashboard_transactions_df = saved_transactions_df[
            saved_transactions_df["Account"].map(clean_account) == selected_account
        ].copy()

    clean_df = build_private_portfolio_table(
        dashboard_transactions_df,
        market_df,
    )

    active_df = clean_df[
        pd.to_numeric(
            clean_df["Total Shares"],
            errors="coerce",
        ).fillna(0.0)
        > 0
    ].copy()

    if active_df.empty:
        st.info(
            "Add transactions in the Transaction Ledger below, then click Save Transactions "
            "to build the selected portfolio dashboard."
        )
        with st.expander("🔧 Transaction Ledger", expanded=True):
            render_transaction_ledger_editor(transactions_df, user_id=current_user_id)
        return

    realized_trades_df = build_realized_trades_table(dashboard_transactions_df)

    portfolio_value = float(active_df["Market Value CAD"].sum())
    total_cost_basis = float(active_df["Cost Basis CAD"].sum())
    total_dividends = float(clean_df["Dividends CAD"].sum()) if "Dividends CAD" in clean_df.columns else 0.0
    total_realized = float(realized_trades_df["Realized P&L CAD"].sum()) if not realized_trades_df.empty else 0.0
    unrealized_gain = float(active_df["Unrealized CAD"].sum())
    total_gain = unrealized_gain + total_dividends + total_realized
    total_return_pct = total_gain / total_cost_basis * 100 if total_cost_basis > 0 else 0.0

    # Time-weighted return activates once CASH_DEPOSIT / CASH_WITHDRAWAL rows
    # exist. It reconstructs sub-period returns around external cash flows.
    time_weighted_return = calculate_time_weighted_return_from_cashflows(
        dashboard_transactions_df,
        portfolio_value,
    )
    cash_flow_summary = calculate_cash_flow_summary(dashboard_transactions_df)

    weighted_move = float(active_df["Contribution %"].sum())
    portfolio_impact = calculate_impact_label(weighted_move)

    positive_count = int(
        (
            pd.to_numeric(active_df["Day %"], errors="coerce").fillna(0.0)
            > 0
        ).sum()
    )

    holding_count = len(active_df)

    snapshot = render_family_office_command_layer(
        selected_account=selected_account,
        active_df=active_df,
        portfolio_value=portfolio_value,
        total_gain=total_gain,
        total_return_pct=total_return_pct,
        time_weighted_return=time_weighted_return,
        unrealized_gain=unrealized_gain,
        total_dividends=total_dividends,
        total_realized=total_realized,
        weighted_move=weighted_move,
        holding_count=holding_count,
        positive_count=positive_count,
        cash_flow_summary=cash_flow_summary,
    )

    render_portfolio_navigation_center(active_df)

    if focus_account or focus_symbol:
        st.divider()

    render_drilldown_center(
        clean_df=clean_df,
        realized_trades_df=realized_trades_df,
        saved_transactions_df=saved_transactions_df,
        focus_account=focus_account,
        focus_symbol=focus_symbol,
    )

    if focus_account or focus_symbol:
        st.divider()

    # =====================================================
    # ORGANIZED FAMILY OFFICE WORKSPACE
    # =====================================================

    st.markdown(
        """
        <style>
            @media (max-width: 1180px) {
                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                }

                div[data-testid="stHorizontalBlock"] > div {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }
            }

            div[data-testid="stPlotlyChart"] {
                width: 100% !important;
                overflow: visible !important;
            }

            div[data-testid="stPlotlyChart"] > div {
                width: 100% !important;
            }

            div[data-testid="stDataFrame"] {
                width: 100% !important;
                overflow-x: auto !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    tab_accounts, tab_allocation, tab_income, tab_ledger, tab_realized, tab_cash = st.tabs(
        [
            "🏦 Accounts & Holdings",
            "📊 Allocation",
            "💵 Income",
            "📒 Ledger",
            "✅ Realized P&L",
            "💸 Cash Flow",
        ]
    )

    with tab_accounts:
        st.subheader("Account Balances")
        st.caption(
            "CAD-equivalent balances. TFSA, RRSP, and Non-Registered combine CAD and USD sub-accounts."
        )
        render_account_balance_cards(active_df)

        st.subheader("Holdings Snapshot")
        st.caption(
            "Broker-style holding cards sorted by market value. Day move is estimated from current value and daily percent move."
        )
        render_holding_cards(active_df)

        st.subheader("Portfolio Health")
        st.caption(
            "Score based on diversification, concentration, return, income, and currency exposure."
        )
        render_portfolio_health_cards(active_df)

        st.subheader("Portfolio Radar")
        st.caption(
            "Live portfolio signals: leaders, laggards, income, concentration, and strength."
        )
        render_portfolio_radar(active_df)

        st.subheader("Portfolio Trend")
        with st.container(border=True):
            st.caption(
                "Current performance snapshot and largest holdings by current market value."
            )
            render_portfolio_performance_snapshot(
                total_return_pct=total_return_pct,
                time_weighted_return=time_weighted_return,
                weighted_move=weighted_move,
                total_gain=total_gain,
                total_dividends=total_dividends,
                total_realized=total_realized,
                unrealized_gain=unrealized_gain,
            )
            render_portfolio_trend(active_df)

        with st.expander("🏆 Holdings Ranking & Family Office Scorecard", expanded=False):
            st.caption(
                "Advanced diagnostics for holding quality, income contribution, concentration, "
                "growth, risk, and data quality."
            )
            render_private_holding_ranking_engine(active_df)
            render_family_scorecard(snapshot, active_df)

        with st.expander("📊 Portfolio Summary", expanded=False):
            render_portfolio_summary_cards(
                portfolio_value=portfolio_value,
                total_gain=total_gain,
                total_return_pct=total_return_pct,
                time_weighted_return=time_weighted_return,
                unrealized_gain=unrealized_gain,
                total_dividends=total_dividends,
                total_realized=total_realized,
                weighted_move=weighted_move,
                holding_count=holding_count,
                positive_count=positive_count,
            )

    with tab_allocation:
        st.subheader("Allocation Center")
        st.caption(
            "Donuts show the big picture. Detail cards below provide exact asset-class and currency exposure."
        )
        render_donut_dashboard(active_df)

        with st.expander("Asset Allocation Details", expanded=True):
            st.caption(
                "Detailed asset-allocation breakdown used by the dashboard. Shows the exact percentage and dollar exposure by asset class."
            )
            render_asset_allocation_cards(active_df)

        st.subheader("⚖️ Rebalance Command Center")
        st.caption("Strategic target drift. Advisory only; not an automatic rebalance instruction.")
        render_rebalance_engine(active_df)

        st.subheader("🏛️ Portfolio Grade")
        st.caption("Institutional-style grade based on diversification, income, risk, and concentration.")
        render_portfolio_grade(active_df)

    with tab_income:
        st.subheader("💵 Income & Yield Dashboard")
        st.caption(
            "Income-focused view showing dividends received, projected income, portfolio yield, and yield on cost."
        )

        projected_annual_income, projected_monthly_income, projected_yield = calculate_projected_income(active_df)

        yield_on_cost = (
            (total_dividends / total_cost_basis) * 100
            if total_cost_basis > 0
            else 0
        )

        income_row_1 = st.columns(3)
        income_row_2 = st.columns(3)

        with income_row_1[0]:
            metric_card("Annual Income", f"{format_money(projected_annual_income)} CAD", "Projected", tone="good")
        with income_row_1[1]:
            metric_card("Monthly Income", f"{format_money(projected_monthly_income)} CAD", "Projected", tone="good")
        with income_row_1[2]:
            metric_card("Portfolio Yield", format_pct(projected_yield), "Forward yield", tone="good")

        with income_row_2[0]:
            metric_card("Yield On Cost", format_pct(yield_on_cost), "Received vs cost", tone="good")
        with income_row_2[1]:
            metric_card("Dividends Received", f"{format_money(total_dividends)} CAD", "Ledger total", tone="good")
        with income_row_2[2]:
            metric_card("Monthly Average", f"{format_money(total_dividends / 12)} CAD", "Received / 12", tone="info")

        with st.expander("💵 Dividend Command Center", expanded=False):
            st.caption("Dividend metrics are based on dividends already entered in the transaction ledger.")
            render_dividend_command_center(active_df)

        with st.expander("💰 Monthly Income Forecast", expanded=True):
            st.caption("Estimated distribution schedule based on ETF forward-yield assumptions and payment frequency.")
            render_monthly_income_forecast(active_df)

    with tab_ledger:
        st.subheader("Transaction Ledger")
        st.caption(
            "Source-of-truth portfolio database. Every BUY, SELL, DIVIDEND, DRIP, INTEREST, CASH_DEPOSIT, and CASH_WITHDRAWAL entered here feeds the dashboard."
        )
        with st.expander(
            "🔧 Transaction Ledger",
            expanded=st.session_state.get("private_portfolio_ledger_open", False),
        ):
            render_transaction_ledger_editor(transactions_df, user_id=current_user_id)

        with st.expander(f"📋 {selected_account} Performance & Income", expanded=False):
            st.caption(
                "Institutional holdings table showing position size, cost basis, market value, dividends, realized gains, unrealized gains, allocation weight, and contribution."
            )
            render_portfolio_table(active_df)

        with st.expander("📊 Raw Portfolio Data", expanded=False):
            st.caption("Audit and troubleshooting view of the calculated holdings engine.")
            st.dataframe(active_df, width="stretch", hide_index=True)

        with st.expander("💾 Saved Transactions", expanded=False):
            st.caption("Permanent transaction history loaded from disk. This is the underlying database used to rebuild the portfolio.")
            st.dataframe(saved_transactions_df, width="stretch", hide_index=True)

        with st.expander("🩺 Private Portfolio Persistence Health", expanded=False):
            health = {
                "Private Portfolio Supabase Loaded": bool(st.session_state.get("private_portfolio_supabase_loaded", False)),
                "Private Portfolio Supabase Saved": bool(st.session_state.get("private_portfolio_supabase_saved", False)),
                "Current User ID Present": bool(str(current_user_id or "").strip()),
                "Record Count": int(st.session_state.get("private_portfolio_record_count", len(saved_transactions_df)) or 0),
                "Last Persistence Error": st.session_state.get("private_portfolio_last_persistence_error", ""),
            }
            health_df = pd.DataFrame(list(health.items()), columns=["Metric", "Value"])
            st.dataframe(health_df, width="stretch", hide_index=True)

    with tab_realized:
        st.subheader("Realized P&L Center")
        st.caption(
            "Profit and loss from completed SELL transactions. Uses average-cost accounting by account and symbol."
        )
        render_realized_pnl_center(realized_trades_df)

    with tab_cash:
        st.subheader("Cash Flow Center")
        st.caption(
            "External deposits and withdrawals. These transactions are tracked separately and power cash-flow-aware return calculations."
        )
        render_cash_flow_center(dashboard_transactions_df)


if __name__ == "__main__":
    run_page()