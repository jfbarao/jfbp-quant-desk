from __future__ import annotations

from pathlib import Path

from pages import SaaS_Core as saas


class _FakeCookieManager:
    def __init__(self, value: str = ""):
        self.value = value

    def get(self, _key):
        return self.value

    def set(self, *_args, **_kwargs):
        return None

    def delete(self, *_args, **_kwargs):
        return None


class _RerunRequested(Exception):
    pass


def test_all_explicit_reruns_flow_through_wrapper():
    source = Path(saas.__file__).read_text(encoding="utf-8")
    assert source.count("st.rerun(") == 1
    assert "def _request_streamlit_rerun" in source


def test_rehydrate_cookie_not_ready_emits_explicit_rerun_marker(monkeypatch):
    traces = []

    def _trace(stage, source_function, **metadata):
        traces.append((stage, source_function, metadata))

    monkeypatch.setattr(saas, "production_auth_trace", _trace)
    monkeypatch.setattr(
        saas,
        "_read_session_cookie_result",
        lambda: saas.CookieReadResult(saas.COOKIE_READINESS_NOT_READY, ""),
    )
    saas.st.session_state.clear()
    saas.st.session_state["saas_login_in_progress"] = False

    result = saas._rehydrate_authenticated_session()

    assert result is None
    assert any(
        stage == "EXPLICIT_STREAMLIT_RERUN_REQUESTED"
        and source_function == "_rehydrate_authenticated_session"
        and metadata.get("call_site_id") == "rehydrate_cookie_not_ready"
        for stage, source_function, metadata in traces
    )


def test_script_execution_enter_uses_distinct_execution_ids(monkeypatch):
    traces = []

    def _trace(stage, source_function, **metadata):
        traces.append((stage, source_function, metadata))

    monkeypatch.setattr(saas, "production_auth_trace", _trace)
    monkeypatch.setattr(saas, "_rehydrate_authenticated_session", lambda: None)

    saas.st.session_state.clear()
    saas.init_saas_state()
    first_enter = next(
        metadata
        for stage, source_function, metadata in traces
        if stage == "SCRIPT_EXECUTION_ENTER" and source_function == "init_saas_state"
    )

    traces.clear()
    saas.init_saas_state()
    second_enter = next(
        metadata
        for stage, source_function, metadata in traces
        if stage == "SCRIPT_EXECUTION_ENTER" and source_function == "init_saas_state"
    )

    assert first_enter["script_execution_id"]
    assert second_enter["script_execution_id"]
    assert first_enter["script_execution_id"] != second_enter["script_execution_id"]
    assert second_enter["previous_script_execution_id"] == first_enter["script_execution_id"]


def test_trace_component_cookie_read_does_not_log_cookie_value(monkeypatch):
    traces = []
    sensitive_cookie = "cookie-super-sensitive-value"

    def _trace(stage, source_function, **metadata):
        traces.append((stage, source_function, metadata))

    monkeypatch.setattr(saas, "production_auth_trace", _trace)
    monkeypatch.setattr(saas, "_cookie_manager", lambda: _FakeCookieManager(value=sensitive_cookie))
    saas.st.session_state.clear()

    result = saas._read_session_cookie_result()

    assert result.state == saas.COOKIE_READINESS_PRESENT
    assert result.value == sensitive_cookie
    rendered = "\n".join(str(item) for item in traces)
    assert sensitive_cookie not in rendered


def test_component_instrumentation_preserves_cookie_read_return(monkeypatch):
    monkeypatch.setattr(saas, "_cookie_manager", lambda: _FakeCookieManager(value="opaque-cookie"))
    saas.st.session_state.clear()

    result = saas._read_session_cookie_result()

    assert result.state == saas.COOKIE_READINESS_PRESENT
    assert result.value == "opaque-cookie"


def test_request_rerun_emits_marker_before_rerun(monkeypatch):
    traces = []

    def _trace(stage, source_function, **metadata):
        traces.append((stage, source_function, metadata))

    def _rerun():
        raise _RerunRequested()

    monkeypatch.setattr(saas, "production_auth_trace", _trace)
    monkeypatch.setattr(saas.st, "rerun", _rerun)

    try:
        saas._request_streamlit_rerun(
            call_site_id="unit_test_callsite",
            source_function="unit_test_source",
            reason="unit_test_reason",
        )
    except _RerunRequested:
        pass

    assert any(
        stage == "EXPLICIT_STREAMLIT_RERUN_REQUESTED"
        and source_function == "unit_test_source"
        and metadata.get("call_site_id") == "unit_test_callsite"
        and metadata.get("reason") == "unit_test_reason"
        for stage, source_function, metadata in traces
    )
