from __future__ import annotations

from pathlib import Path


MIGRATION_PATH = Path("supabase/migrations/20260717_140000_create_app_sessions.sql")


def _text() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_migration_file_exists():
    assert MIGRATION_PATH.exists()


def test_table_and_required_columns_present():
    text = _text()
    assert "CREATE TABLE IF NOT EXISTS public.app_sessions" in text
    assert "session_handle_hash text NOT NULL" in text
    assert "user_id uuid NOT NULL REFERENCES auth.users(id)" in text
    assert "idle_expires_at timestamp with time zone NOT NULL" in text
    assert "absolute_expires_at timestamp with time zone NOT NULL" in text
    assert "revoked_at timestamp with time zone" in text
    assert "revocation_reason text" in text
    assert "refresh_material_encrypted text" in text
    assert "refresh_material_key_version text" in text


def test_unique_hash_and_indexes_present():
    text = _text()
    assert "CREATE UNIQUE INDEX IF NOT EXISTS app_sessions_session_handle_hash_uk" in text
    assert "ON public.app_sessions(session_handle_hash)" in text
    assert "CREATE INDEX IF NOT EXISTS app_sessions_user_active_idx" in text
    assert "CREATE INDEX IF NOT EXISTS app_sessions_idle_expires_idx" in text
    assert "CREATE INDEX IF NOT EXISTS app_sessions_absolute_expires_idx" in text


def test_rls_and_restricted_grants_present():
    text = _text()
    assert "ALTER TABLE public.app_sessions ENABLE ROW LEVEL SECURITY" in text
    assert "ALTER TABLE public.app_sessions FORCE ROW LEVEL SECURITY" in text
    assert "REVOKE ALL ON TABLE public.app_sessions FROM anon" in text
    assert "REVOKE ALL ON TABLE public.app_sessions FROM authenticated" in text
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.app_sessions TO service_role" in text


def test_concurrency_and_cleanup_functions_present():
    text = _text()
    assert "CREATE OR REPLACE FUNCTION public.app_sessions_create" in text
    assert "pg_advisory_xact_lock" in text
    assert "MAX_CONCURRENT_LIMIT" in text
    assert "CREATE OR REPLACE FUNCTION public.app_sessions_cleanup" in text
