# Phase 9A.2 Session Schema Reference

Status: Implemented migration reference.

## Migration
- [supabase/migrations/20260717_140000_create_app_sessions.sql](supabase/migrations/20260717_140000_create_app_sessions.sql)

## Table
- `public.app_sessions`

## Columns
- `id uuid primary key default gen_random_uuid()`
- `session_handle_hash text not null`
- `user_id uuid not null references auth.users(id) on delete cascade`
- `created_at timestamptz not null default now()`
- `last_seen_at timestamptz not null default now()`
- `idle_expires_at timestamptz not null`
- `absolute_expires_at timestamptz not null`
- `revoked_at timestamptz null`
- `revocation_reason text null`
- `remember_me boolean not null default false`
- `user_agent text null`
- `client_metadata jsonb not null default '{}'::jsonb`
- `rotation_parent_id uuid null references public.app_sessions(id) on delete set null`
- `replaced_by_session_id uuid null references public.app_sessions(id) on delete set null`
- `refresh_material_encrypted text null`
- `refresh_material_key_version text null`

## Constraints and Indexes
- Unique: `app_sessions_session_handle_hash_uk`
- Check: non-empty `session_handle_hash`
- Check: `idle_expires_at <= absolute_expires_at`
- Active-user index: `app_sessions_user_active_idx`
- Cleanup indexes: `app_sessions_idle_expires_idx`, `app_sessions_absolute_expires_idx`
- Revocation index: `app_sessions_revoked_at_idx`

## Security Model
- RLS enabled and forced.
- Direct table access revoked from `anon` and `authenticated`.
- Table privileges granted to `service_role` and `postgres` only.
- Controlled mutation path via `SECURITY DEFINER` function `public.app_sessions_create(...)`.

## Concurrency and Cleanup Functions
- `public.app_sessions_create(...)`
  - Uses transaction advisory lock on user key.
  - Applies deterministic oldest-session revocation when max active sessions would be exceeded.
- `public.app_sessions_cleanup(...)`
  - Opportunistic retention cleanup for expired/revoked rows.
