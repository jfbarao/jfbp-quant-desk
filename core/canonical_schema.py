from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional, Set, Tuple

# Canonical production columns derived from Phase 3 normalized catalog.
CANONICAL_TABLE_COLUMNS: Dict[str, Set[str]] = {
    "user_profiles": {
        "id",
        "created_at",
        "email",
        "full_name",
        "plan",
        "account_status",
        "trial_start",
        "trial_end",
        "user_id",
        "stripe_customer_id",
        "stripe_subscription_id",
    },
    "subscriptions": {
        "id",
        "user_id",
        "plan",
        "status",
        "stripe_customer_id",
        "stripe_subscription_id",
        "created_at",
    },
    "workspaces": {
        "id",
        "user_id",
        "workspace_name",
        "created_at",
    },
}


def canonical_columns(table_name: str) -> Set[str]:
    return set(CANONICAL_TABLE_COLUMNS.get(str(table_name or "").strip(), set()))


def canonical_supports_column(table_name: str, column_name: str) -> bool:
    if not column_name:
        return False
    return str(column_name).strip() in canonical_columns(table_name)


def filter_canonical_payload(
    table_name: str,
    payload: Dict[str, Any],
    *,
    context: str = "",
    logger: Optional[Callable[[str], None]] = None,
) -> Tuple[Dict[str, Any], Set[str]]:
    allowed = canonical_columns(table_name)
    if not isinstance(payload, dict):
        return {}, set()

    filtered = {key: value for key, value in payload.items() if key in allowed}
    dropped = set(payload.keys()) - set(filtered.keys())

    if dropped and logger is not None:
        location = f" [{context}]" if context else ""
        logger(
            "CANONICAL_FILTER"
            f" table={table_name}{location}"
            f" dropped={sorted(dropped)}"
        )

    return filtered, dropped


def filter_column_list(table_name: str, columns: Iterable[str]) -> Tuple[list[str], Set[str]]:
    allowed = canonical_columns(table_name)
    normalized = [str(col).strip() for col in columns if str(col).strip()]
    filtered = [col for col in normalized if col in allowed]
    dropped = set(normalized) - set(filtered)
    return filtered, dropped
