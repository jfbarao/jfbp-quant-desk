from __future__ import annotations

from types import SimpleNamespace

import app
from pages import Admin_Control_Center as admin_page
from pages import SaaS_Core as saas


class _FakeSecrets(dict):
    pass


class _FakeAuthClient:
    def __init__(self, user_id: str, email: str):
        self._user = SimpleNamespace(id=user_id, email=email)
        self.auth = SimpleNamespace(get_user=lambda: SimpleNamespace(user=self._user))


def _make_saas_user(role: str, user_id: str = "u-1", email: str = "user@example.com") -> saas.SaaSUser:
    now = saas._utc_now()
    return saas.SaaSUser(
        user_id=user_id,
        email=email,
        full_name="Test User",
        plan=saas.PLAN_MARKET_PULSE,
        account_status=saas.ACCOUNT_TRIAL,
        trial_start=now,
        trial_end=now,
        created_at=now,
        role=role,
    )


def _set_fake_streamlit_for_saas(monkeypatch):
    fake_st = SimpleNamespace(secrets=_FakeSecrets({}), session_state={})
    monkeypatch.setattr(saas, "st", fake_st)
    return fake_st


def test_roles_fail_closed_for_admin_access(monkeypatch):
    _set_fake_streamlit_for_saas(monkeypatch)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: _FakeAuthClient("u-1", "user@example.com"))

    for role_value in ["", "user", "trial", "elite", "unknown", None]:
        user = _make_saas_user(str(role_value or ""), user_id="u-1", email="user@example.com")
        allowed, _reason = saas.admin_access_allowed(user)
        assert allowed is False


def test_explicit_admin_requires_identity_match(monkeypatch):
    _set_fake_streamlit_for_saas(monkeypatch)
    user = _make_saas_user("admin", user_id="u-expected", email="admin@example.com")

    monkeypatch.setattr(saas, "get_supabase_client", lambda: _FakeAuthClient("u-other", "admin@example.com"))
    allowed, reason = saas.admin_access_allowed(user)
    assert allowed is False
    assert reason == "authenticated_identity_mismatch"


def test_explicit_admin_with_matching_identity_is_allowed(monkeypatch):
    _set_fake_streamlit_for_saas(monkeypatch)
    user = _make_saas_user("admin", user_id="u-admin", email="admin@example.com")

    monkeypatch.setattr(saas, "get_supabase_client", lambda: _FakeAuthClient("u-admin", "admin@example.com"))
    allowed, reason = saas.admin_access_allowed(user)
    assert allowed is True
    assert reason == "ok"


def test_plan_tiers_do_not_imply_admin(monkeypatch):
    _set_fake_streamlit_for_saas(monkeypatch)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: _FakeAuthClient("u-1", "user@example.com"))

    for plan in [saas.PLAN_MARKET_PULSE, saas.PLAN_PRO, saas.PLAN_ELITE]:
        user = _make_saas_user("user", user_id="u-1", email="user@example.com")
        user.plan = plan
        allowed, _reason = saas.admin_access_allowed(user)
        assert allowed is False


def test_build_saas_user_uses_app_metadata_role_only(monkeypatch):
    _set_fake_streamlit_for_saas(monkeypatch)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: None)
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(saas, "_verified_user_row", lambda *_args, **_kwargs: [])

    auth_user = SimpleNamespace(
        id="u-2",
        email="ordinary@example.com",
        created_at=saas._utc_now().isoformat(),
        user_metadata={"role": "admin", "plan": saas.PLAN_ELITE},
        app_metadata={},
    )
    built = saas.build_saas_user_from_auth(auth_user)
    assert built.role == "user"


def test_clear_authenticated_session_clears_admin_override(monkeypatch):
    fake_st = _set_fake_streamlit_for_saas(monkeypatch)
    fake_st.session_state.update(
        {
            "saas_logged_in": True,
            "saas_user": _make_saas_user("admin", user_id="u-admin", email="admin@example.com"),
            "saas_auth_session": {"access_token": "tok", "refresh_token": "ref"},
            "saas_admin_override": True,
        }
    )

    monkeypatch.setattr(saas, "_clear_cached_authenticated_session", lambda: None)
    monkeypatch.setattr(saas, "_clear_session_cookie", lambda: None)
    monkeypatch.setattr(saas, "_clear_cookie_readiness_state", lambda: None)
    monkeypatch.setattr(saas, "clear_active_page_cache", lambda: None)
    monkeypatch.setattr(saas, "clear_stripe_checkout_state", lambda: None)

    ok, _detail = saas.clear_authenticated_session(revoke_current=False)
    assert ok is True
    assert fake_st.session_state["saas_logged_in"] is False
    assert fake_st.session_state["saas_user"] is None
    assert fake_st.session_state["saas_admin_override"] is False


def test_admin_sidebar_group_hidden_for_non_admin(monkeypatch):
    fake_st = SimpleNamespace(session_state={"jfbp_main_navigation": "Opportunity Center"})
    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "get_current_user", lambda: SimpleNamespace(user_id="u", email="u@example.com", role="user"))
    monkeypatch.setattr(app, "admin_access_allowed", lambda _user=None: (False, "role_not_admin"))

    seen_titles: list[str] = []
    monkeypatch.setattr(app, "_sidebar_group", lambda title, *_args, **_kwargs: seen_titles.append(title))

    app.workflow_sidebar_navigation()
    assert "🔐 Admin" not in seen_titles


def test_admin_direct_page_blocked_for_non_admin(monkeypatch):
    errors: list[str] = []
    fake_st = SimpleNamespace(session_state={"jfbp_main_navigation": "Admin Control Center"}, error=lambda msg: errors.append(str(msg)))
    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "get_current_user", lambda: SimpleNamespace(user_id="u", email="u@example.com", role="user"))
    monkeypatch.setattr(app, "admin_access_allowed", lambda _user=None: (False, "role_not_admin"))

    remembered: list[str] = []
    monkeypatch.setattr(app, "remember_active_page", lambda page_name: remembered.append(page_name))

    called = {"runner": False}
    app.run_protected_page("Admin Control Center", lambda: called.update({"runner": True}))

    assert called["runner"] is False
    assert fake_st.session_state["jfbp_main_navigation"] == "Opportunity Center"
    assert remembered == ["Opportunity Center"]
    assert errors and "Administrator access is required." in errors[-1]


def test_admin_direct_page_allowed_for_explicit_admin(monkeypatch):
    fake_st = SimpleNamespace(session_state={"jfbp_main_navigation": "Admin Control Center"}, error=lambda _msg: None)
    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "get_current_user", lambda: SimpleNamespace(user_id="u-admin", email="admin@example.com", role="admin"))
    monkeypatch.setattr(app, "admin_access_allowed", lambda _user=None: (True, "ok"))
    monkeypatch.setattr(app, "require_page_access", lambda _access_name: True)

    called = {"runner": False}
    app.run_protected_page("Admin Control Center", lambda: called.update({"runner": True}))
    assert called["runner"] is True


def test_sensitive_admin_queries_fail_closed_for_non_admin(monkeypatch):
    monkeypatch.setattr(admin_page, "_require_admin_authorization", lambda: (False, "role_not_admin"))
    called = {"requests": False}

    def _unexpected(*_args, **_kwargs):
        called["requests"] = True
        raise AssertionError("requests.get should not be called for non-admin users")

    monkeypatch.setattr(admin_page.requests, "get", _unexpected)

    raised = False
    try:
        admin_page._rest_select("user_profiles")
    except PermissionError:
        raised = True

    assert raised is True
    assert called["requests"] is False


def test_sensitive_admin_write_rejects_non_admin(monkeypatch):
    monkeypatch.setattr(admin_page, "_require_admin_authorization", lambda: (False, "role_not_admin"))
    monkeypatch.setattr(admin_page, "_rest_patch_by_user_id", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("write should not execute")))

    ok, message = admin_page.update_customer_plan_status("u-1", saas.PLAN_PRO, saas.ACCOUNT_ACTIVE)
    assert ok is False
    assert "Administrator access is required" in message


def test_regression_admin_not_inherited_after_user_change(monkeypatch):
    _set_fake_streamlit_for_saas(monkeypatch)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: _FakeAuthClient("u-user", "user@example.com"))

    previous_admin = _make_saas_user("admin", user_id="u-admin", email="admin@example.com")
    current_user = _make_saas_user("user", user_id="u-user", email="user@example.com")

    assert saas.is_admin_user(previous_admin) is False
    assert saas.is_admin_user(current_user) is False