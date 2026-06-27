from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None

try:
    from core.responsive import inject_responsive_css
except Exception:  # pragma: no cover
    def inject_responsive_css() -> None:
        return None

try:
    from core.ui_cards import card_grid, hero_card, inject_card_css
except Exception:  # pragma: no cover
    def inject_card_css() -> None:
        return None

    def hero_card(*args, **kwargs) -> None:
        return None

    def card_grid(*args, **kwargs) -> None:
        return None

try:
    from pages.SaaS_Core import (
        ACCOUNT_ACTIVE,
        ACCOUNT_CANCELLED,
        ACCOUNT_EXPIRED,
        ACCOUNT_PAST_DUE,
        ACCOUNT_SUSPENDED,
        ACCOUNT_TRIAL,
        PLAN_ELITE,
        PLAN_LABELS,
        PLAN_MARKET_PULSE,
        PLAN_PRO,
        get_current_user,
        is_admin_email,
        is_admin_user,
    )
except Exception:  # pragma: no cover
    PLAN_MARKET_PULSE = "MARKET_PULSE"
    PLAN_PRO = "PRO"
    PLAN_ELITE = "ELITE"

    ACCOUNT_TRIAL = "TRIAL"
    ACCOUNT_ACTIVE = "ACTIVE"
    ACCOUNT_PAST_DUE = "PAST_DUE"
    ACCOUNT_CANCELLED = "CANCELLED"
    ACCOUNT_EXPIRED = "EXPIRED"
    ACCOUNT_SUSPENDED = "SUSPENDED"

    PLAN_LABELS = {
        PLAN_MARKET_PULSE: "Market Pulse",
        PLAN_PRO: "Quant Desk Pro",
        PLAN_ELITE: "Quant Desk Elite",
    }

    def get_current_user():
        return None

    def is_admin_email(email: str) -> bool:
        raw = str(st.secrets.get("ADMIN_EMAILS", "") or "")
        admin_set = {e.strip().lower() for e in raw.replace(";", ",").split(",") if e.strip()}
        admin_set.add("jfbarao@icloud.com")
        return str(email or "").strip().lower() in admin_set

    def is_admin_user(user: Any) -> bool:
        return bool(user and is_admin_email(getattr(user, "email", "")))


STATUS_OPTIONS = [
    ACCOUNT_TRIAL,
    ACCOUNT_ACTIVE,
    ACCOUNT_PAST_DUE,
    ACCOUNT_CANCELLED,
    ACCOUNT_EXPIRED,
    ACCOUNT_SUSPENDED,
]


def _clean_email(value: Any) -> str:
    return str(value or "").strip().lower()


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _fmt_date(value: Any) -> str:
    dt = _parse_dt(value)
    if not dt:
        return "-"
    return dt.strftime("%Y-%m-%d")


def _response_data(response: Any) -> List[Dict[str, Any]]:
    data = getattr(response, "data", None)
    if data is None:
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _plan_label(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        raw = PLAN_MARKET_PULSE
    return PLAN_LABELS.get(raw, raw)


@st.cache_resource(show_spinner=False)
def get_admin_supabase_client():
    if create_client is None:
        return None

    url = str(st.secrets.get("SUPABASE_URL", "") or "").strip()
    service_key = str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "") or "").strip()
    anon_key = str(st.secrets.get("SUPABASE_ANON_KEY", "") or "").strip()
    key = service_key or anon_key

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


def admin_supabase_ready() -> Tuple[bool, str]:
    if create_client is None:
        return False, "Supabase package is not installed. Add supabase to requirements.txt."
    if not st.secrets.get("SUPABASE_URL", ""):
        return False, "Missing SUPABASE_URL in Streamlit Secrets."
    if not (st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "") or st.secrets.get("SUPABASE_ANON_KEY", "")):
        return False, "Missing SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY in Streamlit Secrets."
    if get_admin_supabase_client() is None:
        return False, "Could not create Supabase admin client."
    if not st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", ""):
        return True, "Connected with anon key. If rows are missing, add SUPABASE_SERVICE_ROLE_KEY for admin visibility."
    return True, "Connected with service role key."


def load_profiles() -> List[Dict[str, Any]]:
    client = get_admin_supabase_client()
    if client is None:
        return []

    response = (
        client.table("user_profiles")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return _response_data(response)


def load_subscriptions() -> List[Dict[str, Any]]:
    client = get_admin_supabase_client()
    if client is None:
        return []

    response = (
        client.table("subscriptions")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return _response_data(response)


def _latest_by_key(rows: List[Dict[str, Any]], key_name: str) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        key = str(row.get(key_name, "") or "").strip()
        if not key:
            continue

        current_dt = _parse_dt(row.get("created_at"))
        prev = latest.get(key)
        if prev is None:
            latest[key] = row
            continue

        prev_dt = _parse_dt(prev.get("created_at"))
        if (current_dt or datetime.min.replace(tzinfo=timezone.utc)) >= (
            prev_dt or datetime.min.replace(tzinfo=timezone.utc)
        ):
            latest[key] = row
    return latest


def merge_customer_rows(profiles: List[Dict[str, Any]], subscriptions: List[Dict[str, Any]]) -> pd.DataFrame:
    latest_sub_by_user_id = _latest_by_key(subscriptions, "user_id")
    latest_sub_by_email = _latest_by_key(subscriptions, "email")

    rows: List[Dict[str, Any]] = []
    seen_customer_keys: set[str] = set()

    for profile in profiles:
        user_id = str(profile.get("user_id", "") or "").strip()
        profile_email = _clean_email(profile.get("email"))

        sub = latest_sub_by_user_id.get(user_id) if user_id else None
        if sub is None and profile_email:
            sub = latest_sub_by_email.get(profile_email)
        sub = sub or {}

        email = _clean_email(_first_non_empty(profile_email, sub.get("email")))
        customer_key = user_id or email
        if not customer_key or customer_key in seen_customer_keys:
            continue
        seen_customer_keys.add(customer_key)

        plan = str(_first_non_empty(profile.get("plan"), sub.get("plan"), PLAN_MARKET_PULSE) or PLAN_MARKET_PULSE)
        status = str(_first_non_empty(profile.get("account_status"), sub.get("status"), ACCOUNT_TRIAL) or ACCOUNT_TRIAL)
        created_at = _first_non_empty(profile.get("created_at"), sub.get("created_at"))
        role = str(_first_non_empty(profile.get("role"), "admin" if is_admin_email(email) else "user") or "user")

        rows.append(
            {
                "Customer Key": customer_key,
                "Display Name": str(
                    _first_non_empty(profile.get("display_name"), profile.get("full_name"), profile.get("name"), "JFBP User")
                ),
                "Email": email,
                "Plan": _plan_label(plan),
                "Plan Key": plan,
                "Account Status": status,
                "Status Key": status,
                "Trial End Date": _fmt_date(_first_non_empty(profile.get("trial_end"), sub.get("trial_end"))),
                "Role": "Admin" if role.lower() == "admin" or is_admin_email(email) else "User",
                "Created Date": _fmt_date(created_at),
                "Created DT": _parse_dt(created_at),
            }
        )

    # Include subscription-only customers that are missing from user_profiles.
    for sub in subscriptions:
        user_id = str(sub.get("user_id", "") or "").strip()
        email = _clean_email(sub.get("email"))
        customer_key = user_id or email
        if not customer_key or customer_key in seen_customer_keys:
            continue
        seen_customer_keys.add(customer_key)

        plan = str(_first_non_empty(sub.get("plan"), PLAN_MARKET_PULSE) or PLAN_MARKET_PULSE)
        status = str(_first_non_empty(sub.get("status"), ACCOUNT_TRIAL) or ACCOUNT_TRIAL)
        created_at = sub.get("created_at")

        rows.append(
            {
                "Customer Key": customer_key,
                "Display Name": "JFBP User",
                "Email": email,
                "Plan": _plan_label(plan),
                "Plan Key": plan,
                "Account Status": status,
                "Status Key": status,
                "Trial End Date": _fmt_date(sub.get("trial_end")),
                "Role": "Admin" if is_admin_email(email) else "User",
                "Created Date": _fmt_date(created_at),
                "Created DT": _parse_dt(created_at),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "Display Name",
                "Email",
                "Plan",
                "Account Status",
                "Trial End Date",
                "Role",
                "Created Date",
                "Plan Key",
                "Status Key",
                "Created DT",
            ]
        )
    return df


def render_admin_gate() -> bool:
    user = get_current_user()
    if is_admin_user(user):
        return True

    st.error("Admin access required. Sign in with an authorized founder/admin account.")
    return False


def render_overview_cards(df: pd.DataFrame) -> None:
    if df.empty:
        card_grid(
            [
                {"label": "Customers", "value": 0, "detail": "No rows found", "tone": "warning"},
                {"label": "Plans", "value": 0, "detail": "No plan data", "tone": "neutral"},
                {"label": "Statuses", "value": 0, "detail": "No status data", "tone": "neutral"},
            ],
            columns=3,
        )
        return

    customers = len(df)
    plans = int(df["Plan Key"].nunique())
    statuses = int(df["Status Key"].nunique())
    active = int((df["Status Key"] == ACCOUNT_ACTIVE).sum())

    card_grid(
        [
            {"label": "Customers", "value": customers, "detail": "One row per customer", "tone": "info"},
            {"label": "Active", "value": active, "detail": "Account status ACTIVE", "tone": "good"},
            {"label": "Plans", "value": plans, "detail": "Distinct plan tiers", "tone": "neutral"},
            {"label": "Statuses", "value": statuses, "detail": "Distinct account statuses", "tone": "neutral"},
        ],
        columns=4,
    )


def filter_and_sort_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    c1, c2, c3, c4 = st.columns([0.42, 0.2, 0.2, 0.18], gap="medium")
    with c1:
        query = st.text_input("Search by name or email", placeholder="Type display name or email")
    with c2:
        plan_options = ["All"] + sorted(df["Plan Key"].dropna().astype(str).unique().tolist())
        selected_plan = st.selectbox(
            "Filter by Plan",
            plan_options,
            format_func=lambda p: "All" if p == "All" else PLAN_LABELS.get(p, p),
        )
    with c3:
        status_options = ["All"] + sorted(df["Status Key"].dropna().astype(str).unique().tolist())
        selected_status = st.selectbox("Filter by Status", status_options)
    with c4:
        sort_order = st.selectbox("Sort by Created", ["Newest", "Oldest"])

    out = df.copy()

    if query:
        q = query.strip().lower()
        name_match = out["Display Name"].astype(str).str.lower().str.contains(q, na=False)
        email_match = out["Email"].astype(str).str.lower().str.contains(q, na=False)
        out = out[name_match | email_match]

    if selected_plan != "All":
        out = out[out["Plan Key"].astype(str) == selected_plan]

    if selected_status != "All":
        out = out[out["Status Key"].astype(str) == selected_status]

    out = out.sort_values("Created DT", ascending=(sort_order == "Oldest"), na_position="last")
    return out


def render_customer_table(df: pd.DataFrame) -> None:
    st.subheader("Customer Directory")
    filtered = filter_and_sort_df(df)

    display_cols = [
        "Display Name",
        "Email",
        "Plan",
        "Account Status",
        "Trial End Date",
        "Role",
    ]

    st.dataframe(
        filtered[display_cols] if not filtered.empty else pd.DataFrame(columns=display_cols),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Showing {len(filtered)} of {len(df)} customers.")


def render_admin_control_center() -> None:
    inject_responsive_css()
    inject_card_css()

    hero_card(
        title="Admin Control Center",
        subtitle="Supabase customer command view across user profiles and subscriptions.",
        action="Read-only customer operations with search, filters, and created-date sorting.",
        kicker="JFBP Quant Desk Internal Command",
        tone="info",
    )

    if not render_admin_gate():
        return

    ready, message = admin_supabase_ready()
    if not ready:
        st.error(message)
        return

    if "anon key" in message.lower():
        st.warning(message)
    else:
        st.success(message)

    try:
        profiles = load_profiles()
        subscriptions = load_subscriptions()
        df = merge_customer_rows(profiles, subscriptions)
    except Exception as exc:
        st.error(f"Could not load admin customer data: {exc}")
        return

    render_overview_cards(df)
    render_customer_table(df)


def run_page() -> None:
    render_admin_control_center()


def page() -> None:
    run_page()


if __name__ == "__main__":
    run_page()
