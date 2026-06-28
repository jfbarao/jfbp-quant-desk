# core/portfolio_db.py

from pages.SaaS_Core import get_supabase_client


def _clean_user_id(user_id):
    return str(user_id or "").strip()


def _require_client():
    supabase = get_supabase_client()
    if supabase is None:
        raise RuntimeError("Supabase client unavailable")
    return supabase


def load_positions(user_id):
    user_id = _clean_user_id(user_id)
    if not user_id:
        return []

    supabase = _require_client()

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
    user_id = _clean_user_id(user_id)
    if not user_id:
        raise ValueError("user_id is required")

    symbol = str(symbol or "").upper().strip()
    if not symbol:
        raise ValueError("symbol is required")

    supabase = _require_client()

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
    user_id = _clean_user_id(user_id)
    if not user_id:
        raise ValueError("user_id is required")

    symbol = str(symbol or "").upper().strip()
    if not symbol:
        raise ValueError("symbol is required")

    supabase = _require_client()

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
    user_id = _clean_user_id(user_id)
    if not user_id:
        return []

    supabase = _require_client()

    result = (
        supabase.table("journal_entries")
        .select("*")
        .eq("user_id", user_id)
        .order("timestamp", desc=True)
        .execute()
    )

    return result.data or []


def insert_journal_entry(payload):
    supabase = _require_client()

    return (
        supabase.table("journal_entries")
        .insert(payload)
        .execute()
    )


# =====================================================
# JOURNAL REVIEWS
# =====================================================

def load_journal_reviews(user_id):
    user_id = _clean_user_id(user_id)
    if not user_id:
        return []

    supabase = _require_client()

    result = (
        supabase.table("journal_reviews")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    return result.data or []


def insert_journal_review(payload, dedupe: bool = True):
    supabase = _require_client()

    payload = dict(payload or {})
    user_id = _clean_user_id(payload.get("user_id"))
    if not user_id:
        raise ValueError("user_id is required")

    payload["user_id"] = user_id
    payload["symbol"] = str(payload.get("symbol") or "N/A").upper().strip() or "N/A"
    payload["setup_grade"] = str(payload.get("setup_grade") or "C").upper().strip() or "C"
    payload["execution_grade"] = str(payload.get("execution_grade") or "C").upper().strip() or "C"
    payload["tag"] = str(payload.get("tag") or "Process Review").strip() or "Process Review"
    payload["notes"] = str(payload.get("notes") or "").strip()
    payload["source"] = str(payload.get("source") or "Manual Trade Review").strip() or "Manual Trade Review"

    if dedupe and payload["notes"]:
        recent = (
            supabase.table("journal_reviews")
            .select("id,user_id,symbol,setup_grade,execution_grade,tag,notes,source,created_at")
            .eq("user_id", user_id)
            .eq("symbol", payload["symbol"])
            .eq("setup_grade", payload["setup_grade"])
            .eq("execution_grade", payload["execution_grade"])
            .eq("tag", payload["tag"])
            .eq("notes", payload["notes"])
            .eq("source", payload["source"])
            .limit(1)
            .execute()
        )
        existing = getattr(recent, "data", None) or []
        if existing:
            return {
                "status": "DUPLICATE_SKIPPED",
                "duplicate": True,
                "row": existing[0],
            }

    return (
        supabase.table("journal_reviews")
        .insert(payload)
        .execute()
    )

