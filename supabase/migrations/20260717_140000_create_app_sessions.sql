-- Phase 9A.2 durable session store foundation
-- Authoring only; no deployment in this phase.

BEGIN;

CREATE TABLE IF NOT EXISTS public.app_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_handle_hash text NOT NULL,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    last_seen_at timestamp with time zone NOT NULL DEFAULT now(),
    idle_expires_at timestamp with time zone NOT NULL,
    absolute_expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    revocation_reason text,
    remember_me boolean NOT NULL DEFAULT false,
    user_agent text,
    client_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    rotation_parent_id uuid REFERENCES public.app_sessions(id) ON DELETE SET NULL,
    replaced_by_session_id uuid REFERENCES public.app_sessions(id) ON DELETE SET NULL,
    refresh_material_encrypted text,
    refresh_material_key_version text,
    CONSTRAINT app_sessions_session_handle_hash_non_empty CHECK (length(trim(session_handle_hash)) > 0),
    CONSTRAINT app_sessions_idle_not_after_absolute CHECK (idle_expires_at <= absolute_expires_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS app_sessions_session_handle_hash_uk
    ON public.app_sessions(session_handle_hash);

CREATE INDEX IF NOT EXISTS app_sessions_user_active_idx
    ON public.app_sessions(user_id, created_at ASC)
    WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS app_sessions_idle_expires_idx
    ON public.app_sessions(idle_expires_at);

CREATE INDEX IF NOT EXISTS app_sessions_absolute_expires_idx
    ON public.app_sessions(absolute_expires_at);

CREATE INDEX IF NOT EXISTS app_sessions_revoked_at_idx
    ON public.app_sessions(revoked_at)
    WHERE revoked_at IS NOT NULL;

ALTER TABLE public.app_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_sessions FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.app_sessions FROM PUBLIC;
REVOKE ALL ON TABLE public.app_sessions FROM anon;
REVOKE ALL ON TABLE public.app_sessions FROM authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.app_sessions TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.app_sessions TO postgres;

CREATE OR REPLACE FUNCTION public.app_sessions_create(
    p_user_id uuid,
    p_session_handle_hash text,
    p_created_at timestamp with time zone,
    p_idle_expires_at timestamp with time zone,
    p_absolute_expires_at timestamp with time zone,
    p_remember_me boolean DEFAULT false,
    p_user_agent text DEFAULT NULL,
    p_client_metadata jsonb DEFAULT '{}'::jsonb,
    p_rotation_parent_id uuid DEFAULT NULL,
    p_refresh_material_encrypted text DEFAULT NULL,
    p_refresh_material_key_version text DEFAULT NULL,
    p_max_active_sessions integer DEFAULT 5
)
RETURNS public.app_sessions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    created_row public.app_sessions;
    effective_created_at timestamp with time zone;
BEGIN
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'p_user_id is required';
    END IF;

    IF p_session_handle_hash IS NULL OR length(trim(p_session_handle_hash)) = 0 THEN
        RAISE EXCEPTION 'p_session_handle_hash is required';
    END IF;

    IF p_idle_expires_at IS NULL OR p_absolute_expires_at IS NULL THEN
        RAISE EXCEPTION 'expiration timestamps are required';
    END IF;

    IF p_idle_expires_at > p_absolute_expires_at THEN
        RAISE EXCEPTION 'idle expiration must be <= absolute expiration';
    END IF;

    IF COALESCE(p_max_active_sessions, 0) < 1 THEN
        RAISE EXCEPTION 'p_max_active_sessions must be >= 1';
    END IF;

    effective_created_at := COALESCE(p_created_at, now());

    -- Ensure concurrent login/session creation for one user cannot bypass
    -- maximum active-session policy.
    PERFORM pg_advisory_xact_lock(hashtext(p_user_id::text));

    UPDATE public.app_sessions
    SET
        revoked_at = effective_created_at,
        revocation_reason = 'MAX_CONCURRENT_LIMIT'
    WHERE id IN (
        SELECT id
        FROM public.app_sessions
        WHERE user_id = p_user_id
          AND revoked_at IS NULL
          AND idle_expires_at > effective_created_at
          AND absolute_expires_at > effective_created_at
        ORDER BY created_at ASC
        OFFSET GREATEST(p_max_active_sessions - 1, 0)
    );

    INSERT INTO public.app_sessions (
        session_handle_hash,
        user_id,
        created_at,
        last_seen_at,
        idle_expires_at,
        absolute_expires_at,
        remember_me,
        user_agent,
        client_metadata,
        rotation_parent_id,
        refresh_material_encrypted,
        refresh_material_key_version
    )
    VALUES (
        p_session_handle_hash,
        p_user_id,
        effective_created_at,
        effective_created_at,
        p_idle_expires_at,
        p_absolute_expires_at,
        COALESCE(p_remember_me, false),
        p_user_agent,
        COALESCE(p_client_metadata, '{}'::jsonb),
        p_rotation_parent_id,
        p_refresh_material_encrypted,
        p_refresh_material_key_version
    )
    RETURNING * INTO created_row;

    RETURN created_row;
END;
$$;

REVOKE ALL ON FUNCTION public.app_sessions_create(
    uuid,
    text,
    timestamp with time zone,
    timestamp with time zone,
    timestamp with time zone,
    boolean,
    text,
    jsonb,
    uuid,
    text,
    text,
    integer
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.app_sessions_create(
    uuid,
    text,
    timestamp with time zone,
    timestamp with time zone,
    timestamp with time zone,
    boolean,
    text,
    jsonb,
    uuid,
    text,
    text,
    integer
) TO service_role;
GRANT EXECUTE ON FUNCTION public.app_sessions_create(
    uuid,
    text,
    timestamp with time zone,
    timestamp with time zone,
    timestamp with time zone,
    boolean,
    text,
    jsonb,
    uuid,
    text,
    text,
    integer
) TO postgres;

CREATE OR REPLACE FUNCTION public.app_sessions_cleanup(
    p_now timestamp with time zone DEFAULT now(),
    p_retention interval DEFAULT interval '7 days'
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    deleted_count integer;
BEGIN
    DELETE FROM public.app_sessions
    WHERE
        (revoked_at IS NOT NULL AND revoked_at < (COALESCE(p_now, now()) - p_retention))
        OR (absolute_expires_at < (COALESCE(p_now, now()) - p_retention));

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

REVOKE ALL ON FUNCTION public.app_sessions_cleanup(timestamp with time zone, interval) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.app_sessions_cleanup(timestamp with time zone, interval) TO service_role;
GRANT EXECUTE ON FUNCTION public.app_sessions_cleanup(timestamp with time zone, interval) TO postgres;

COMMENT ON TABLE public.app_sessions IS 'phase9a2_durable_session_store_20260717_140000';

COMMIT;
