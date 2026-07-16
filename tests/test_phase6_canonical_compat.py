from __future__ import annotations

from types import SimpleNamespace

from core.canonical_schema import CANONICAL_TABLE_COLUMNS, filter_canonical_payload
from pages import Admin_Control_Center as admin
from pages import SaaS_Core as saas


class _FakeQuery:
    def __init__(self, table_name: str, store: dict):
        self.table_name = table_name
        self.store = store
        self.operation = "select"
        self.payload = None

    def select(self, _expr):
        self.operation = "select"
        return self

    def eq(self, _key, _value):
        return self

    def limit(self, _value):
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = dict(payload)
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = dict(payload)
        return self

    def execute(self):
        table_store = self.store.setdefault(self.table_name, {"insert": [], "update": [], "select": []})
        if self.operation == "insert":
            table_store["insert"].append(dict(self.payload or {}))
            return SimpleNamespace(data=[dict(self.payload or {})])
        if self.operation == "update":
            table_store["update"].append(dict(self.payload or {}))
            return SimpleNamespace(data=[dict(self.payload or {})])
        return SimpleNamespace(data=list(table_store.get("select", [])))


class _FakeClient:
    def __init__(self):
        self.store = {}

    def table(self, table_name: str):
        return _FakeQuery(table_name, self.store)


def test_canonical_allowlist_is_explicit():
    assert CANONICAL_TABLE_COLUMNS["user_profiles"] == {
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
    }
    assert CANONICAL_TABLE_COLUMNS["subscriptions"] == {
        "id",
        "user_id",
        "plan",
        "status",
        "stripe_customer_id",
        "stripe_subscription_id",
        "created_at",
    }
    assert CANONICAL_TABLE_COLUMNS["workspaces"] == {
        "id",
        "user_id",
        "workspace_name",
        "created_at",
    }


def test_profile_provisioning_payload_is_canonical_only(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(saas, "_verified_user_row", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(saas, "_verified_row_by_email", lambda *_args, **_kwargs: [])

    saas._create_profile_record(
        client=fake,
        user_id="u1",
        email="u@example.com",
        full_name="User One",
        plan=saas.PLAN_MARKET_PULSE,
        account_status=saas.ACCOUNT_TRIAL,
        trial_start=saas._utc_now(),
        trial_end=saas._utc_now(),
        trial_metadata={
            "signup_ip": "1.1.1.1",
            "trial_attempts": 3,
            "risk_score": 80,
            "trial_notes": "note",
        },
    )

    payload = fake.store["user_profiles"]["insert"][0]
    assert set(payload.keys()).issubset(CANONICAL_TABLE_COLUMNS["user_profiles"])


def test_login_metadata_telemetry_is_non_blocking_when_noncanonical(monkeypatch):
    fake = _FakeClient()
    ok, message, payload, _response = saas._save_login_metadata(
        client=fake,
        user_id="u1",
        profile_row={},
        login_metadata={
            "timestamp": saas._utc_now().isoformat(),
            "last_login_ip": "1.1.1.1",
            "last_login_country": "US",
            "last_login_city": "Austin",
        },
    )

    assert ok is True
    assert "skipped" in message.lower()
    assert payload == {}
    assert fake.store.get("user_profiles", {}).get("update", []) == []


def test_trial_payload_filter_keeps_required_trial_fields():
    payload, dropped = filter_canonical_payload(
        "user_profiles",
        {
            "user_id": "u1",
            "trial_start": "2026-01-01T00:00:00+00:00",
            "trial_end": "2026-01-31T00:00:00+00:00",
            "trial_attempts": 9,
            "risk_score": 99,
        },
    )

    assert set(payload.keys()) == {"user_id", "trial_start", "trial_end"}
    assert dropped == {"trial_attempts", "risk_score"}


def test_workspace_payload_is_canonical_only(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(saas, "_verified_user_row", lambda *_args, **_kwargs: [])

    saas._create_workspace_record(fake, "u1", "Personal Workspace")

    payload = fake.store["workspaces"]["insert"][0]
    assert set(payload.keys()) == {"user_id", "workspace_name"}


def test_subscription_reconciliation_prefers_user_id(monkeypatch):
    monkeypatch.setattr(
        saas,
        "_profile_row_for_auth_user",
        lambda *_args, **_kwargs: {
            "full_name": "U",
            "plan": saas.PLAN_MARKET_PULSE,
            "account_status": saas.ACCOUNT_TRIAL,
            "trial_start": saas._utc_now().isoformat(),
            "trial_end": saas._utc_now().isoformat(),
        },
    )

    def _fake_verified(client, table_name, user_id):
        if table_name == "subscriptions":
            return [{"user_id": user_id, "plan": saas.PLAN_PRO, "status": saas.ACCOUNT_ACTIVE}]
        return []

    monkeypatch.setattr(saas, "_verified_user_row", _fake_verified)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: object())

    auth_user = SimpleNamespace(id="u1", email="u@example.com", user_metadata={})
    built = saas.build_saas_user_from_auth(auth_user)

    assert built.plan == saas.PLAN_PRO
    assert built.subscription_status == saas.ACCOUNT_ACTIVE


def test_create_subscription_record_does_not_lookup_by_email(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(saas, "_verified_user_row", lambda *_args, **_kwargs: [])

    def _boom(*_args, **_kwargs):
        raise AssertionError("email lookup should not be used for subscriptions")

    monkeypatch.setattr(saas, "_verified_row_by_email", _boom)

    saas._create_subscription_record(fake, "u1", saas.PLAN_PRO, saas.ACCOUNT_ACTIVE, email="u@example.com")
    payload = fake.store["subscriptions"]["insert"][0]
    assert set(payload.keys()) == {"user_id", "plan", "status"}


def test_admin_rest_first_row_skips_subscriptions_email_query(monkeypatch):
    captured = []

    def _fake_rest_select(table_name, order_expr="created_at.desc", extra_params=None):
        captured.append((table_name, dict(extra_params or {})))
        return []

    monkeypatch.setattr(admin, "_rest_select", _fake_rest_select)

    admin._rest_first_row("subscriptions", user_id="", email="u@example.com")
    assert captured == []


def test_admin_reporting_handles_absent_telemetry():
    row = admin._build_customer_record(
        profile={
            "user_id": "u1",
            "email": "u@example.com",
            "plan": saas.PLAN_MARKET_PULSE,
            "account_status": saas.ACCOUNT_TRIAL,
            "trial_start": saas._utc_now().isoformat(),
            "trial_end": saas._utc_now().isoformat(),
        },
        sub={"user_id": "u1", "plan": saas.PLAN_MARKET_PULSE, "status": saas.ACCOUNT_TRIAL},
        login_rows=[],
        audit_user_rows=[],
        all_profiles=[],
        auth_user={"id": "u1", "email": "u@example.com"},
    )

    assert "Risk Score" in row
    assert "Trial Notes" in row


def test_required_canonical_write_failure_is_surfaced(monkeypatch):
    class _FailingQuery(_FakeQuery):
        def execute(self):
            if self.operation in {"insert", "update"}:
                raise RuntimeError("write failed")
            return SimpleNamespace(data=[])

    class _FailingClient(_FakeClient):
        def table(self, table_name: str):
            return _FailingQuery(table_name, self.store)

    client = _FailingClient()
    monkeypatch.setattr(saas, "_verified_user_row", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(saas, "_verified_row_by_email", lambda *_args, **_kwargs: [])

    raised = False
    try:
        saas._create_profile_record(
            client=client,
            user_id="u1",
            email="u@example.com",
            full_name="User One",
            plan=saas.PLAN_MARKET_PULSE,
            account_status=saas.ACCOUNT_TRIAL,
            trial_start=saas._utc_now(),
            trial_end=saas._utc_now(),
        )
    except RuntimeError:
        raised = True

    assert raised is True
