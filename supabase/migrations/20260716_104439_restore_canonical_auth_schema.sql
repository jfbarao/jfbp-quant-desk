-- Phase 7 canonical development migration (authoring only; not executed)
-- Source: runtime_state/schema_recovery_phase3_20260715_211215/normalized_catalog.json
-- Target project ref (development): qkqexvlprzjqjtsarqbz
-- Guardrail: do not run against production.

BEGIN;

-- 1) Required extensions proven by canonical metadata
-- No extension objects are present in normalized_catalog; none authored.

-- Safety pre-check: fail fast if target canonical tables already exist (detect drift)
DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_profiles') THEN RAISE EXCEPTION 'Expected empty canonical table % but found existing object', 'user_profiles'; END IF; END $$;
DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'subscriptions') THEN RAISE EXCEPTION 'Expected empty canonical table % but found existing object', 'subscriptions'; END IF; END $$;
DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'workspaces') THEN RAISE EXCEPTION 'Expected empty canonical table % but found existing object', 'workspaces'; END IF; END $$;

-- 2) Base tables
CREATE TABLE public.user_profiles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    email text COLLATE pg_catalog."default",
    full_name text COLLATE pg_catalog."default",
    plan text COLLATE pg_catalog."default",
    account_status text COLLATE pg_catalog."default",
    trial_start timestamp with time zone,
    trial_end timestamp with time zone,
    user_id uuid,
    stripe_customer_id text COLLATE pg_catalog."default",
    stripe_subscription_id text COLLATE pg_catalog."default"
);

CREATE TABLE public.subscriptions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    plan text COLLATE pg_catalog."default",
    status text COLLATE pg_catalog."default",
    stripe_customer_id text COLLATE pg_catalog."default",
    stripe_subscription_id text COLLATE pg_catalog."default",
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.workspaces (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    workspace_name text COLLATE pg_catalog."default",
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- 3) Primary keys
ALTER TABLE ONLY public.user_profiles ADD CONSTRAINT user_profiles_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.subscriptions ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.workspaces ADD CONSTRAINT workspaces_pkey PRIMARY KEY (id);

-- 4) Unique and check constraints
-- No canonical unique/check constraints beyond primary keys.

-- 5) Foreign keys
-- No canonical foreign keys for target tables.

-- 6) Indexes
-- Canonical indexes are primary-key backing indexes and are created by PK constraints above.

-- 7) RLS enablement and force settings
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workspaces NO FORCE ROW LEVEL SECURITY;

-- 8) RLS policies
CREATE POLICY "Users can create own profile" ON public.user_profiles AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Users can update own profile" ON public.user_profiles AS PERMISSIVE FOR UPDATE TO authenticated USING ((auth.uid() = user_id)) WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Users can view own profile" ON public.user_profiles AS PERMISSIVE FOR SELECT TO authenticated USING ((auth.uid() = user_id));
CREATE POLICY "Users can create own subscription" ON public.subscriptions AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Users can update own subscription" ON public.subscriptions AS PERMISSIVE FOR UPDATE TO authenticated USING ((auth.uid() = user_id)) WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Users can view own subscription" ON public.subscriptions AS PERMISSIVE FOR SELECT TO authenticated USING ((auth.uid() = user_id));
CREATE POLICY "Users can create own workspace" ON public.workspaces AS PERMISSIVE FOR INSERT TO authenticated WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Users can update own workspace" ON public.workspaces AS PERMISSIVE FOR UPDATE TO authenticated USING ((auth.uid() = user_id)) WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Users can view own workspace" ON public.workspaces AS PERMISSIVE FOR SELECT TO authenticated USING ((auth.uid() = user_id));

-- 9) Grants (canonical Q6 table grants for target tables only)
-- Note: Q6 recovered metadata does not include grantor column; grantee/privilege/grant option are canonical and preserved.
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.subscriptions TO anon;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.subscriptions TO authenticated;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.subscriptions TO postgres WITH GRANT OPTION;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.subscriptions TO service_role;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.user_profiles TO anon;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.user_profiles TO authenticated;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.user_profiles TO postgres WITH GRANT OPTION;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.user_profiles TO service_role;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.workspaces TO anon;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.workspaces TO authenticated;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.workspaces TO postgres WITH GRANT OPTION;
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE public.workspaces TO service_role;

-- 10) Validation metadata marker
COMMENT ON TABLE public.user_profiles IS 'canonical_migration_phase7_20260716_104439';
COMMENT ON TABLE public.subscriptions IS 'canonical_migration_phase7_20260716_104439';
COMMENT ON TABLE public.workspaces IS 'canonical_migration_phase7_20260716_104439';

COMMIT;
