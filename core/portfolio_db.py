# core/portfolio_db.py

from pages.SaaS_Core import get_supabase_client


def load_positions(user_id):
    supabase = get_supabase_client()

    result = (
        supabase.table("portfolio_positions")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    return result.data or []


def upsert_position(
    user_id,
    symbol,
    shares,
    cost_basis,
    market_value,
    avg_price,
    realized_pnl,
):
    supabase = get_supabase_client()

    payload = {
        "user_id": user_id,
        "symbol": symbol,
        "shares": shares,
        "cost_basis": cost_basis,
        "market_value": market_value,
        "avg_price": avg_price,
        "realized_pnl": realized_pnl,
    }

    return (
        supabase.table("portfolio_positions")
        .upsert(
            payload,
            on_conflict="user_id,symbol",
        )
        .execute()
    )


def delete_position(user_id, symbol):
    supabase = get_supabase_client()

    return (
        supabase.table("portfolio_positions")
        .delete()
        .eq("user_id", user_id)
        .eq("symbol", symbol)
        .execute()
    )

# =====================================================
# JOURNAL ENTRIES
# =====================================================

def load_journal_entries(user_id):
    supabase = get_supabase_client()

    result = (
        supabase.table("journal_entries")
        .select("*")
        .eq("user_id", user_id)
        .order("timestamp", desc=True)
        .execute()
    )

    return result.data or []


def insert_journal_entry(payload):
    supabase = get_supabase_client()

    return (
        supabase.table("journal_entries")
        .insert(payload)
        .execute()
    )


# =====================================================
# JOURNAL REVIEWS
# =====================================================

def load_journal_reviews(user_id):
    supabase = get_supabase_client()

    result = (
        supabase.table("journal_reviews")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    return result.data or []


def insert_journal_review(payload):
    supabase = get_supabase_client()

    return (
        supabase.table("journal_reviews")
        .insert(payload)
        .execute()
    )

