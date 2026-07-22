from __future__ import annotations

from types import SimpleNamespace

import app
from pages import SaaS_Core as saas


class _StopCalled(Exception):
    pass


def _fake_saas_streamlit(*, secrets: dict | None = None, session_state: dict | None = None):
    return SimpleNamespace(
        secrets=secrets or {},
        session_state=session_state or {},
    )


def _fake_app_streamlit(session_state: dict | None = None):
    def _stop():
        raise _StopCalled()

    return SimpleNamespace(
        session_state=session_state or {},
        stop=_stop,
        error=lambda *_args, **_kwargs: None,
    )


def test_personal_mode_missing_defaults_false(monkeypatch):
    fake_st = _fake_saas_streamlit(secrets={}, session_state={})
    monkeypatch.setattr(saas, "st", fake_st)
    monkeypatch.delenv("PERSONAL_MODE", raising=False)

    assert saas.personal_mode_enabled() is False


def test_personal_mode_false_keeps_disabled(monkeypatch):
    fake_st = _fake_saas_streamlit(secrets={"PERSONAL_MODE": "false"}, session_state={})
    monkeypatch.setattr(saas, "st", fake_st)
    monkeypatch.delenv("PERSONAL_MODE", raising=False)

    assert saas.personal_mode_enabled() is False


def test_personal_mode_true_value_enables(monkeypatch):
    fake_st = _fake_saas_streamlit(secrets={"PERSONAL_MODE": "true"}, session_state={})
    monkeypatch.setattr(saas, "st", fake_st)
    monkeypatch.delenv("PERSONAL_MODE", raising=False)

    assert saas.personal_mode_enabled() is True


def test_initialize_personal_mode_owner_session_sets_required_state(monkeypatch):
    fake_st = _fake_saas_streamlit(
        secrets={
            "PERSONAL_MODE": "true",
            "PERSONAL_MODE_OWNER_EMAIL": "owner@example.com",
            "PERSONAL_MODE_OWNER_USER_ID": "owner-id-1",
            "PERSONAL_MODE_OWNER_NAME": "Owner Name",
            "PERSONAL_MODE_OWNER_PLAN": saas.PLAN_ELITE,
        },
        session_state={},
    )
    monkeypatch.setattr(saas, "st", fake_st)

    ok, _message = saas.initialize_personal_mode_owner_session()

    assert ok is True
    assert fake_st.session_state.get("saas_logged_in") is True
    assert fake_st.session_state.get("saas_personal_mode_active") is True
    assert fake_st.session_state.get("saas_onboarding_ready") is True
    assert fake_st.session_state.get("saas_auth_session") is None

    user = fake_st.session_state.get("saas_user")
    assert isinstance(user, saas.SaaSUser)
    assert user.email == "owner@example.com"
    assert user.user_id == "owner-id-1"
    assert user.plan == saas.PLAN_ELITE


def test_personal_mode_does_not_fabricate_auth_tokens(monkeypatch):
    fake_st = _fake_saas_streamlit(
        secrets={
            "PERSONAL_MODE": "true",
            "PERSONAL_MODE_OWNER_EMAIL": "owner@example.com",
        },
        session_state={},
    )
    monkeypatch.setattr(saas, "st", fake_st)

    ok, _message = saas.initialize_personal_mode_owner_session()

    assert ok is True
    auth_session = fake_st.session_state.get("saas_auth_session")
    assert auth_session is None


def test_enforce_app_login_disabled_mode_keeps_auth_flow(monkeypatch):
    fake_st = _fake_app_streamlit(session_state={})
    monkeypatch.setattr(app, "st", fake_st)

    called = {"front_door": False}

    monkeypatch.setattr(app, "init_saas_state", lambda: None)
    monkeypatch.setattr(app, "personal_mode_enabled", lambda: False)
    monkeypatch.setattr(app, "get_current_user", lambda: None)

    def _front_door():
        called["front_door"] = True

    monkeypatch.setattr(app, "render_front_door", _front_door)

    try:
        app.enforce_app_login()
        assert False, "Expected st.stop()"
    except _StopCalled:
        pass

    assert called["front_door"] is True


def test_enforce_app_login_true_bypasses_secure_access_ui(monkeypatch):
    fake_st = _fake_app_streamlit(session_state={})
    monkeypatch.setattr(app, "st", fake_st)

    monkeypatch.setattr(app, "init_saas_state", lambda: None)
    monkeypatch.setattr(app, "personal_mode_enabled", lambda: True)
    monkeypatch.setattr(app, "initialize_personal_mode_owner_session", lambda: (True, "ok"))
    monkeypatch.setattr(app, "get_current_user", lambda: None)

    called = {"front_door": False}

    def _front_door():
        called["front_door"] = True

    monkeypatch.setattr(app, "render_front_door", _front_door)

    assert app.enforce_app_login() is True
    assert called["front_door"] is False


def test_personal_mode_does_not_invoke_password_login_transport(monkeypatch):
    fake_st = _fake_app_streamlit(session_state={})
    monkeypatch.setattr(app, "st", fake_st)

    monkeypatch.setattr(app, "init_saas_state", lambda: None)
    monkeypatch.setattr(app, "personal_mode_enabled", lambda: True)
    monkeypatch.setattr(app, "initialize_personal_mode_owner_session", lambda: (True, "ok"))
    monkeypatch.setattr(app, "get_current_user", lambda: None)

    def _unexpected_transport(*_args, **_kwargs):
        raise AssertionError("password login transport must not run in Personal Mode")

    monkeypatch.setattr(saas, "_supabase_rest_password_login", _unexpected_transport)

    assert app.enforce_app_login() is True


def test_personal_mode_blocks_customer_onboarding_surfaces(monkeypatch):
    fake_st = _fake_app_streamlit(session_state={})
    monkeypatch.setattr(app, "st", fake_st)

    monkeypatch.setattr(app, "init_saas_state", lambda: None)
    monkeypatch.setattr(app, "personal_mode_enabled", lambda: True)
    monkeypatch.setattr(app, "initialize_personal_mode_owner_session", lambda: (True, "ok"))
    monkeypatch.setattr(app, "get_current_user", lambda: None)

    called = {"front_door": False}

    def _front_door():
        called["front_door"] = True

    monkeypatch.setattr(app, "render_front_door", _front_door)

    assert app.enforce_app_login() is True
    assert called["front_door"] is False


def test_personal_mode_blocks_signup_and_reset_actions(monkeypatch):
    fake_st = _fake_saas_streamlit(
        secrets={"PERSONAL_MODE": "true", "PERSONAL_MODE_OWNER_EMAIL": "owner@example.com"},
        session_state={"saas_personal_mode_active": True},
    )
    monkeypatch.setattr(saas, "st", fake_st)

    signup_ok, signup_msg = saas.supabase_sign_up(
        email="new@example.com",
        password="password-123",
        full_name="New User",
        plan=saas.PLAN_MARKET_PULSE,
    )
    reset_ok, reset_msg, reset_meta = saas.supabase_reset_password("new@example.com")

    assert signup_ok is False
    assert "Personal Mode" in signup_msg
    assert reset_ok is False
    assert "Personal Mode" in reset_msg
    assert reset_meta.get("error_code") == "personal_mode_disabled"


def test_personal_mode_blocks_checkout_session_creation(monkeypatch):
    fake_st = _fake_saas_streamlit(
        secrets={"PERSONAL_MODE": "true", "PERSONAL_MODE_OWNER_EMAIL": "owner@example.com"},
        session_state={"saas_personal_mode_active": True},
    )
    monkeypatch.setattr(saas, "st", fake_st)

    user = saas.SaaSUser(
        user_id="owner-id-1",
        email="owner@example.com",
        full_name="Owner",
        plan=saas.PLAN_ELITE,
        account_status=saas.ACCOUNT_ACTIVE,
        trial_start=saas._utc_now(),
        trial_end=saas._utc_now(),
        created_at=saas._utc_now(),
        source="personal_mode",
        role="user",
        subscription_status=saas.ACCOUNT_ACTIVE,
        provisioning_required=False,
    )

    ok, message = saas.create_stripe_checkout_session(user, saas.PLAN_PRO)
    assert ok is False
    assert "Personal Mode" in message
