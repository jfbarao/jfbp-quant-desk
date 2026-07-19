from __future__ import annotations

from types import SimpleNamespace

from pages import SaaS_Core as saas


class _FakeSecrets(dict):
    pass


def _set_fake_streamlit(monkeypatch, secrets: dict):
    fake_st = SimpleNamespace(secrets=_FakeSecrets(secrets), session_state={})
    monkeypatch.setattr(saas, "st", fake_st)


def test_redirect_source_prefers_streamlit_secrets(monkeypatch):
    _set_fake_streamlit(monkeypatch, {"SUPABASE_EMAIL_REDIRECT_TO": "https://www.jfbpquantdesk.com"})
    monkeypatch.setenv("SUPABASE_EMAIL_REDIRECT_TO", "https://jfbp-quant-desk-sw9qbylj9ywd9hglnadzqk.streamlit.app")

    resolved = saas._resolve_secret_value_with_source("SUPABASE_EMAIL_REDIRECT_TO", "")

    assert resolved["selected_source"] == "ST_SECRETS"
    assert resolved["secret_exists"] is True
    assert resolved["environment_exists"] is True
    assert resolved["value"] == "https://www.jfbpquantdesk.com"


def test_redirect_source_uses_environment_when_secret_absent(monkeypatch):
    _set_fake_streamlit(monkeypatch, {})
    monkeypatch.setenv("SUPABASE_EMAIL_REDIRECT_TO", "https://jfbp-quant-desk-sw9qbylj9ywd9hglnadzqk.streamlit.app")

    resolved = saas._resolve_secret_value_with_source("SUPABASE_EMAIL_REDIRECT_TO", "")

    assert resolved["selected_source"] == "ENVIRONMENT"
    assert resolved["secret_exists"] is False
    assert resolved["environment_exists"] is True
    assert resolved["value"] == "https://jfbp-quant-desk-sw9qbylj9ywd9hglnadzqk.streamlit.app"


def test_redirect_source_falls_back_only_when_both_absent(monkeypatch):
    _set_fake_streamlit(monkeypatch, {})
    monkeypatch.delenv("SUPABASE_EMAIL_REDIRECT_TO", raising=False)

    resolved = saas._resolve_secret_value_with_source("SUPABASE_EMAIL_REDIRECT_TO", "https://jfbpquantdesk.com")

    assert resolved["selected_source"] == "FALLBACK"
    assert resolved["secret_exists"] is False
    assert resolved["environment_exists"] is False
    assert resolved["value"] == "https://jfbpquantdesk.com"


def test_signup_redirect_diagnostic_logs_are_sanitized(monkeypatch):
    captured: list[str] = []

    def _capture(fmt: str, *args):
        captured.append(fmt % args)

    _set_fake_streamlit(monkeypatch, {"SUPABASE_EMAIL_REDIRECT_TO": "https://www.jfbpquantdesk.com"})
    monkeypatch.delenv("SUPABASE_EMAIL_REDIRECT_TO", raising=False)
    monkeypatch.setattr(saas.logger, "info", _capture)
    monkeypatch.setattr(saas, "_phase10b_redirect_diagnostic_enabled", lambda: True)
    monkeypatch.setattr(saas, "_runtime_commit_hash", lambda: "abcdef1")
    monkeypatch.setattr(saas, "_runtime_app_hostname", lambda: "jfbp-quant-desk-sw9qbylj9ywd9hglnadzqk.streamlit.app")

    value = saas._signup_email_redirect_to()

    assert value == "https://www.jfbpquantdesk.com"
    assert captured, "Expected at least one diagnostic log line"
    log_line = "\n".join(captured)
    assert "PHASE10B_REDIRECT_DIAGNOSTIC" in log_line
    assert "MARKETING_HOST_WWW" in log_line
    assert "ST_SECRETS" in log_line
    assert "https://www.jfbpquantdesk.com" not in log_line
    assert "SUPABASE_EMAIL_REDIRECT_TO" not in log_line
