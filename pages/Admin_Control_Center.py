# =========================================================
# 🚢 JFBP QUANT DESK — Admin Control Center v1.0
# Customer Management Console
# ---------------------------------------------------------
# Purpose:
# - Internal admin dashboard for SaaS users, plans, trials, and status.
# - Reads from public.user_profiles and public.subscriptions.
# - Optional writes for plan/status updates.
#
# Recommended Streamlit Secrets:
# SUPABASE_URL = "https://..."
# SUPABASE_SERVICE_ROLE_KEY = "..."   # preferred for admin console
# SUPABASE_ANON_KEY = "..."           # fallback read client
# ADMIN_EMAILS = "jfbarao@icloud.com"
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import os
import requests

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
    from core.ui_cards import inject_card_css
except Exception:  # pragma: no cover
    def inject_card_css() -> None:
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
        PLAN_PRICES,
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
    PLAN_PRICES = {
        PLAN_MARKET_PULSE: "$39/month",
        PLAN_PRO: "$99/month",
        PLAN_ELITE: "$199/month",
    }

    def get_current_user():
        return None

    def is_admin_email(email: str) -> bool:
        raw = str(st.secrets.get("ADMIN_EMAILS", "") or "")
        emails = {e.strip().lower() for e in raw.replace(";", ",").split(",") if e.strip()}
        emails.add("jfbarao@icloud.com")
        return str(email or "").strip().lower() in emails

    def is_admin_user(user: Any) -> bool:
        return bool(user and is_admin_email(getattr(user, "email", "")))


PLAN_OPTIONS = [PLAN_MARKET_PULSE, PLAN_PRO, PLAN_ELITE]
STATUS_OPTIONS = [
    ACCOUNT_TRIAL,
    ACCOUNT_ACTIVE,
    ACCOUNT_PAST_DUE,
    ACCOUNT_CANCELLED,
    ACCOUNT_EXPIRED,
    ACCOUNT_SUSPENDED,
]

PLAN_BADGES = {
    PLAN_MARKET_PULSE: "⚪ Market Pulse",
    PLAN_PRO: "🔵 Pro",
    PLAN_ELITE: "🟣 Elite",
}

STATUS_BADGES = {
    ACCOUNT_TRIAL: "🟢 Trial",
    ACCOUNT_ACTIVE: "✅ Active",
    ACCOUNT_PAST_DUE: "🟡 Past Due",
    ACCOUNT_CANCELLED: "🟠 Cancelled",
    ACCOUNT_EXPIRED: "🔴 Expired",
    ACCOUNT_SUSPENDED: "⛔ Suspended",
}


# =========================================================
# BASIC HELPERS
# =========================================================

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
        return "—"
    return dt.strftime("%Y-%m-%d")


def _days_until(value: Any) -> str:
    dt = _parse_dt(value)
    if not dt:
        return "—"
    days = (dt - _utc_now()).days
    if days < 0:
        return f"Expired {abs(days)}d ago"
    if days == 0:
        return "Ends today"
    return f"{days}d left"


def _clean_email(value: Any) -> str:
    return str(value or "").strip().lower()


def _response_data(response: Any) -> List[Dict[str, Any]]:
    data = getattr(response, "data", None)
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return [data] if isinstance(data, dict) else []


# =========================================================
# SUPABASE REST ADMIN CLIENT
# =========================================================
#
# Why REST instead of create_client here:
# Some Supabase projects now expose service-role keys as sb_secret_...
# and older supabase-py / gotrue versions may reject that key format while
# direct PostgREST calls work correctly. This admin page only needs table
# reads/writes, so REST is simpler and more reliable for the control center.

def _secret_value(name: str, default: str = "") -> str:
    value = ""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""

    if value is None or str(value).strip() == "":
        value = os.environ.get(name, default)

    return str(value or default).strip()


def _admin_rest_config() -> Tuple[str, str, str]:
    url = _secret_value("SUPABASE_URL")
    service_key = _secret_value("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = _secret_value("SUPABASE_ANON_KEY")
    key = service_key or anon_key
    key_type = "service_role" if service_key else "anon"
    return url.rstrip("/"), key, key_type


def _admin_rest_headers() -> Dict[str, str]:
    _, key, _ = _admin_rest_config()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def admin_supabase_ready() -> Tuple[bool, str]:
    url, key, key_type = _admin_rest_config()

    if not url:
        return False, "Missing SUPABASE_URL in Streamlit Secrets."
    if not key:
        return False, "Missing SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY in Streamlit Secrets."
    if not url.startswith("https://") or ".supabase." not in url:
        return False, "SUPABASE_URL does not look like a valid Supabase project URL."

    if key_type == "anon":
        return True, "Connected with anon key. If rows are missing, add SUPABASE_SERVICE_ROLE_KEY for the admin console."

    return True, "Connected with service role key."


def _rest_select(table_name: str, order_col: str = "created_at") -> List[Dict[str, Any]]:
    url, key, _ = _admin_rest_config()
    if not url or not key:
        return []

    endpoint = f"{url}/rest/v1/{table_name}"
    params = {
        "select": "*",
        "order": f"{order_col}.desc",
    }

    response = requests.get(
        endpoint,
        headers=_admin_rest_headers(),
        params=params,
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    return data if isinstance(data, list) else []


def _rest_patch_by_user_id(table_name: str, user_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    url, key, _ = _admin_rest_config()
    if not url or not key:
        return []

    endpoint = f"{url}/rest/v1/{table_name}"
    response = requests.patch(
        endpoint,
        headers=_admin_rest_headers(),
        params={"user_id": f"eq.{user_id}"},
        json=payload,
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    return data if isinstance(data, list) else []

# =========================================================
# DATA LOADERS
# =========================================================

def load_profiles() -> List[Dict[str, Any]]:
    return _rest_select("user_profiles")


def load_subscriptions() -> List[Dict[str, Any]]:
    try:
        return _rest_select("subscriptions")
    except Exception:
        return []


def merge_customer_rows(profiles: List[Dict[str, Any]], subscriptions: List[Dict[str, Any]]) -> pd.DataFrame:
    sub_by_user_id = {str(row.get("user_id", "")): row for row in subscriptions if row.get("user_id")}

    rows: List[Dict[str, Any]] = []
    for profile in profiles:
        user_id = str(profile.get("user_id", "") or "")
        sub = sub_by_user_id.get(user_id, {})
        email = _clean_email(profile.get("email") or sub.get("email"))
        plan = str(profile.get("plan") or sub.get("plan") or PLAN_MARKET_PULSE)
        status = str(profile.get("account_status") or sub.get("status") or ACCOUNT_TRIAL)
        role = str(profile.get("role") or "admin" if is_admin_email(email) else "user").lower()

        trial_end = profile.get("trial_end") or sub.get("trial_end")
        renewal = (
            sub.get("current_period_end")
            or sub.get("renewal_date")
            or sub.get("period_end")
            or profile.get("renewal_date")
        )

        rows.append(
            {
                "User ID": user_id,
                "Name": str(profile.get("full_name") or profile.get("display_name") or "JFBP User"),
                "Email": email,
                "Plan": PLAN_BADGES.get(plan, plan),
                "Plan Key": plan,
                "Status": STATUS_BADGES.get(status, status),
                "Status Key": status,
                "Trial Ends": _fmt_date(trial_end),
                "Trial": _days_until(trial_end),
                "Renewal Date": _fmt_date(renewal),
                "Role": "Admin" if role == "admin" or is_admin_email(email) else "User",
                "Stripe Customer": str(sub.get("stripe_customer_id") or profile.get("stripe_customer_id") or "—"),
                "Stripe Subscription": str(sub.get("stripe_subscription_id") or profile.get("stripe_subscription_id") or "—"),
                "Created": _fmt_date(profile.get("created_at") or sub.get("created_at")),
                "Last Login": _fmt_date(profile.get("last_sign_in_at") or profile.get("last_login_at")),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "User ID",
                "Name",
                "Email",
                "Plan",
                "Plan Key",
                "Status",
                "Status Key",
                "Trial Ends",
                "Trial",
                "Renewal Date",
                "Role",
                "Stripe Customer",
                "Stripe Subscription",
                "Created",
                "Last Login",
            ]
        )
    return df


# =========================================================
# WRITE ACTIONS
# =========================================================

def update_customer_plan_status(user_id: str, plan: str, status: str) -> Tuple[bool, str]:
    if not user_id:
        return False, "Missing user_id for selected customer."

    try:
        _rest_patch_by_user_id(
            "user_profiles",
            user_id,
            {
                "plan": plan,
                "account_status": status,
            },
        )

        try:
            _rest_patch_by_user_id(
                "subscriptions",
                user_id,
                {
                    "plan": plan,
                    "status": status,
                },
            )
        except Exception:
            # Some accounts may not have a subscription row yet.
            pass

        return True, "Customer plan/status updated."
    except Exception as exc:
        return False, f"Update failed: {exc}"


# =========================================================
# UI
# =========================================================

def inject_admin_css() -> None:
    st.markdown(
        """
        <style>
            .admin-hero {
                border:1px solid #dbeafe;
                background:#eff6ff;
                border-radius:18px;
                padding:1.05rem 1.15rem;
                margin:0.3rem 0 1rem 0;
            }
            .admin-kicker {
                color:#475569;
                font-size:0.74rem;
                text-transform:uppercase;
                letter-spacing:0.07em;
                font-weight:850;
                margin-bottom:0.22rem;
            }
            .admin-title {
                color:#0f172a;
                font-size:1.62rem;
                line-height:1.12;
                font-weight:900;
                margin-bottom:0.32rem;
            }
            .admin-text {
                color:#334155;
                font-size:0.95rem;
                line-height:1.42;
                font-weight:650;
            }
            .admin-card-grid {
                display:grid;
                grid-template-columns:repeat(auto-fit,minmax(165px,1fr));
                gap:0.78rem;
                margin:0.8rem 0 1rem 0;
            }
            .admin-card {
                border:1px solid #e2e8f0;
                background:#f8fafc;
                border-radius:16px;
                padding:0.82rem 0.92rem;
            }
            .admin-card-label {
                color:#64748b;
                font-size:0.70rem;
                text-transform:uppercase;
                letter-spacing:0.06em;
                font-weight:850;
                margin-bottom:0.22rem;
            }
            .admin-card-value {
                color:#111827;
                font-size:1.32rem;
                font-weight:900;
                line-height:1.12;
            }
            .admin-card-detail {
                color:#475569;
                font-size:0.78rem;
                margin-top:0.18rem;
            }
            .admin-lock {
                border:1px solid #fecaca;
                background:#fef2f2;
                border-radius:18px;
                padding:1rem;
                color:#7f1d1d;
                font-weight:800;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: Any, detail: str = "") -> str:
    return (
        '<div class="admin-card">'
        f'<div class="admin-card-label">{label}</div>'
        f'<div class="admin-card-value">{value}</div>'
        f'<div class="admin-card-detail">{detail}</div>'
        '</div>'
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="admin-hero">
            <div class="admin-kicker">JFBP Quant Desk · Internal Command</div>
            <div class="admin-title">Admin Control Center</div>
            <div class="admin-text">Customer management console for plans, trials, account status, and subscription visibility.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_admin_gate() -> bool:
    user = get_current_user()
    if is_admin_user(user):
        return True

    st.markdown(
        """
        <div class="admin-lock">
            Admin access required. Please sign in with an authorized founder/admin account.
        </div>
        """,
        unsafe_allow_html=True,
    )
    return False


def render_overview_cards(df: pd.DataFrame) -> None:
    total = len(df)
    trial = int((df.get("Status Key", pd.Series(dtype=str)) == ACCOUNT_TRIAL).sum()) if not df.empty else 0
    active = int((df.get("Status Key", pd.Series(dtype=str)) == ACCOUNT_ACTIVE).sum()) if not df.empty else 0
    pro = int((df.get("Plan Key", pd.Series(dtype=str)) == PLAN_PRO).sum()) if not df.empty else 0
    elite = int((df.get("Plan Key", pd.Series(dtype=str)) == PLAN_ELITE).sum()) if not df.empty else 0
    market_pulse = int((df.get("Plan Key", pd.Series(dtype=str)) == PLAN_MARKET_PULSE).sum()) if not df.empty else 0

    monthly = 0
    for _, row in df.iterrows():
        if row.get("Status Key") not in {ACCOUNT_ACTIVE, ACCOUNT_TRIAL}:
            continue
        plan = row.get("Plan Key")
        if plan == PLAN_MARKET_PULSE:
            monthly += 39
        elif plan == PLAN_PRO:
            monthly += 99
        elif plan == PLAN_ELITE:
            monthly += 199

    cards = [
        metric_card("Total Users", total, "All profile rows"),
        metric_card("Trials", trial, "Trial accounts"),
        metric_card("Active", active, "Paid or manually active"),
        metric_card("Market Pulse", market_pulse, PLAN_PRICES.get(PLAN_MARKET_PULSE, "")),
        metric_card("Pro", pro, PLAN_PRICES.get(PLAN_PRO, "")),
        metric_card("Elite", elite, PLAN_PRICES.get(PLAN_ELITE, "")),
        metric_card("MRR", f"${monthly:,}", "Estimated from current rows"),
        metric_card("ARR", f"${monthly * 12:,}", "Estimated annual run rate"),
    ]
    st.markdown('<div class="admin-card-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def filter_customer_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    c1, c2, c3 = st.columns([0.44, 0.28, 0.28], gap="medium")
    with c1:
        query = st.text_input("Search customers", placeholder="Name, email, plan, status…")
    with c2:
        plan_filter = st.selectbox("Plan", ["All"] + PLAN_OPTIONS, format_func=lambda p: "All" if p == "All" else PLAN_LABELS.get(p, p))
    with c3:
        status_filter = st.selectbox("Status", ["All"] + STATUS_OPTIONS)

    out = df.copy()
    if query:
        q = query.strip().lower()
        mask = out.apply(lambda row: q in " ".join(str(v).lower() for v in row.values), axis=1)
        out = out[mask]
    if plan_filter != "All":
        out = out[out["Plan Key"] == plan_filter]
    if status_filter != "All":
        out = out[out["Status Key"] == status_filter]
    return out


def render_customer_table(df: pd.DataFrame) -> None:
    st.subheader("👥 Customer Table")
    filtered = filter_customer_df(df)

    display_cols = [
        "Name",
        "Email",
        "Plan",
        "Status",
        "Trial Ends",
        "Trial",
        "Renewal Date",
        "Last Login",
        "Role",
        "Created",
    ]
    st.dataframe(
        filtered[display_cols] if not filtered.empty else filtered,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(f"Showing {len(filtered)} of {len(df)} customers.")


def render_customer_actions(df: pd.DataFrame) -> None:
    st.subheader("🛠 Customer Actions")

    if df.empty:
        st.info("No customer rows found yet.")
        return

    options = [f"{row['Name']} · {row['Email']}" for _, row in df.iterrows()]
    selected_label = st.selectbox("Select customer", options)
    selected_index = options.index(selected_label)
    selected = df.iloc[selected_index]

    with st.form("admin_customer_update_form"):
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            new_plan = st.selectbox(
                "Plan",
                PLAN_OPTIONS,
                index=PLAN_OPTIONS.index(selected["Plan Key"]) if selected["Plan Key"] in PLAN_OPTIONS else 0,
                format_func=lambda p: PLAN_LABELS.get(p, p),
            )
        with c2:
            new_status = st.selectbox(
                "Status",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(selected["Status Key"]) if selected["Status Key"] in STATUS_OPTIONS else 0,
            )

        submitted = st.form_submit_button("Update Customer", use_container_width=True)

    if submitted:
        ok, message = update_customer_plan_status(
            user_id=str(selected["User ID"]),
            plan=new_plan,
            status=new_status,
        )
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    with st.expander("Selected customer details", expanded=False):
        st.json(selected.to_dict())


def render_admin_control_center() -> None:
    inject_responsive_css()
    inject_card_css()
    inject_admin_css()
    render_hero()

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
        st.caption("Check SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, table names, and RLS/API permissions.")
        return

    render_overview_cards(df)

    tabs = st.tabs(["Customers", "Manage", "Raw Data", "Setup Notes"])

    with tabs[0]:
        render_customer_table(df)

    with tabs[1]:
        render_customer_actions(df)

    with tabs[2]:
        st.subheader("Raw Customer Rows")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("Secret keys and tokens are never displayed here.")

    with tabs[3]:
        st.markdown(
            """
            ### Recommended Supabase Tables

            This page expects:

            - `user_profiles`: `user_id`, `email`, `full_name`, `plan`, `account_status`, `trial_start`, `trial_end`, `role`, `created_at`
            - `subscriptions`: `user_id`, `plan`, `status`, `stripe_customer_id`, `stripe_subscription_id`, `current_period_end`, `created_at`

            ### Recommended Secret

            Add `SUPABASE_SERVICE_ROLE_KEY` to Streamlit Secrets for this admin-only page so the console can read all customer rows despite RLS.

            Keep this page available only to founder/admin emails.
            """
        )


def run_page() -> None:
    render_admin_control_center()


def page() -> None:
    run_page()


if __name__ == "__main__":
    run_page()
