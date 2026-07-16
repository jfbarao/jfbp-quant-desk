-- Schema Recovery Phase 3 - Manual Metadata Queries (READ-ONLY)
-- Guardrail: Run queries one-by-one in Supabase SQL Editor against production project zqzujesufquifrtqnanb.
-- Guardrail: Do not run any CREATE/ALTER/DROP/INSERT/UPDATE/DELETE/GRANT/REVOKE/RPC statements.

-- ============================================================
-- Q1: Target table inventory
-- Export as: q1_target_tables.csv
-- ============================================================
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  c.oid AS table_oid,
  c.relkind,
  c.relpersistence,
  c.relrowsecurity AS rls_enabled,
  c.relforcerowsecurity AS rls_forced
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('user_profiles', 'subscriptions', 'workspaces')
  AND c.relkind = 'r'
ORDER BY c.relname;

-- ============================================================
-- Q2: Column definitions
-- Export as: q2_columns.csv
-- ============================================================
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  a.attnum AS ordinal_position,
  a.attname AS column_name,
  format_type(a.atttypid, a.atttypmod) AS exact_pg_type,
  bt.typname AS underlying_type,
  CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END AS is_nullable,
  pg_get_expr(ad.adbin, ad.adrelid) AS default_expression,
  CASE
    WHEN a.attidentity = 'a' THEN 'ALWAYS'
    WHEN a.attidentity = 'd' THEN 'BY DEFAULT'
    ELSE NULL
  END AS identity_generation,
  CASE
    WHEN a.attgenerated = 's' THEN 'STORED'
    ELSE NULL
  END AS generated_kind,
  coll.collname AS collation_name,
  coll_nsp.nspname AS collation_schema
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_type t ON t.oid = a.atttypid
LEFT JOIN pg_type bt ON bt.oid = t.typbasetype
LEFT JOIN pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
LEFT JOIN pg_collation coll ON coll.oid = a.attcollation AND a.attcollation <> 0
LEFT JOIN pg_namespace coll_nsp ON coll_nsp.oid = coll.collnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('user_profiles', 'subscriptions', 'workspaces')
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY c.relname, a.attnum;

-- ============================================================
-- Q3: Constraints (PK/FK/UNIQUE/CHECK + FK actions + deferrability)
-- Export as: q3_constraints.csv
-- ============================================================
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  con.conname AS constraint_name,
  con.contype AS constraint_type,
  pg_get_constraintdef(con.oid, true) AS constraint_definition,
  con.condeferrable,
  con.condeferred,
  fn.nspname AS referenced_schema,
  fc.relname AS referenced_table,
  CASE con.confupdtype
    WHEN 'a' THEN 'NO ACTION'
    WHEN 'r' THEN 'RESTRICT'
    WHEN 'c' THEN 'CASCADE'
    WHEN 'n' THEN 'SET NULL'
    WHEN 'd' THEN 'SET DEFAULT'
    ELSE NULL
  END AS fk_on_update,
  CASE con.confdeltype
    WHEN 'a' THEN 'NO ACTION'
    WHEN 'r' THEN 'RESTRICT'
    WHEN 'c' THEN 'CASCADE'
    WHEN 'n' THEN 'SET NULL'
    WHEN 'd' THEN 'SET DEFAULT'
    ELSE NULL
  END AS fk_on_delete,
  ARRAY(
    SELECT a.attname
    FROM unnest(con.conkey) WITH ORDINALITY AS ck(attnum, ord)
    JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = ck.attnum
    ORDER BY ck.ord
  ) AS constrained_columns,
  ARRAY(
    SELECT a.attname
    FROM unnest(con.confkey) WITH ORDINALITY AS fk(attnum, ord)
    JOIN pg_attribute a ON a.attrelid = con.confrelid AND a.attnum = fk.attnum
    ORDER BY fk.ord
  ) AS referenced_columns
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_class fc ON fc.oid = con.confrelid
LEFT JOIN pg_namespace fn ON fn.oid = fc.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('user_profiles', 'subscriptions', 'workspaces')
ORDER BY c.relname, con.contype, con.conname;

-- ============================================================
-- Q4: Indexes (definition, uniqueness, predicate)
-- Export as: q4_indexes.csv
-- ============================================================
SELECT
  ns.nspname AS schema_name,
  tbl.relname AS table_name,
  idx.relname AS index_name,
  i.indisunique AS is_unique,
  i.indisprimary AS is_primary,
  pg_get_indexdef(i.indexrelid) AS index_definition,
  pg_get_expr(i.indpred, i.indrelid) AS predicate_expression,
  pg_get_expr(i.indexprs, i.indrelid) AS index_expressions,
  ARRAY(
    SELECT a.attname
    FROM unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord)
    LEFT JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum
    WHERE k.attnum > 0
    ORDER BY k.ord
  ) AS indexed_columns
FROM pg_index i
JOIN pg_class idx ON idx.oid = i.indexrelid
JOIN pg_class tbl ON tbl.oid = i.indrelid
JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
WHERE ns.nspname = 'public'
  AND tbl.relname IN ('user_profiles', 'subscriptions', 'workspaces')
ORDER BY tbl.relname, idx.relname;

-- ============================================================
-- Q5: RLS policies
-- Export as: q5_rls_policies.csv
-- ============================================================
SELECT
  p.schemaname,
  p.tablename,
  p.policyname,
  p.permissive,
  p.roles,
  p.cmd,
  p.qual AS using_expression,
  p.with_check AS with_check_expression
FROM pg_policies p
WHERE p.schemaname = 'public'
  AND p.tablename IN ('user_profiles', 'subscriptions', 'workspaces')
ORDER BY p.tablename, p.policyname;

-- ============================================================
-- Q6: Table and sequence grants
-- Export as: q6_table_sequence_grants.csv
-- ============================================================
SELECT
  g.table_schema,
  g.table_name,
  g.grantee,
  g.privilege_type,
  g.is_grantable,
  CASE WHEN c.relkind = 'S' THEN 'SEQUENCE' ELSE 'TABLE' END AS object_kind
FROM information_schema.role_table_grants g
JOIN pg_class c ON c.relname = g.table_name
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = g.table_schema
WHERE g.table_schema = 'public'
  AND (
    g.table_name IN ('user_profiles', 'subscriptions', 'workspaces')
    OR g.table_name IN (
      SELECT relname
      FROM pg_class s
      JOIN pg_namespace sn ON sn.oid = s.relnamespace
      WHERE sn.nspname = 'public' AND s.relkind = 'S'
    )
  )
ORDER BY g.table_name, g.grantee, g.privilege_type;

-- ============================================================
-- Q7: Triggers (full trigger definition + referenced function)
-- Export as: q7_triggers.csv
-- ============================================================
SELECT
  n.nspname AS table_schema,
  c.relname AS table_name,
  t.tgname AS trigger_name,
  t.tgenabled,
  pg_get_triggerdef(t.oid, true) AS trigger_definition,
  fn.nspname AS function_schema,
  p.proname AS function_name,
  p.oid AS function_oid,
  pg_get_function_identity_arguments(p.oid) AS function_arguments,
  l.lanname AS function_language,
  p.prosecdef AS security_definer,
  p.provolatile AS volatility
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_proc p ON p.oid = t.tgfoid
JOIN pg_namespace fn ON fn.oid = p.pronamespace
JOIN pg_language l ON l.oid = p.prolang
WHERE n.nspname = 'public'
  AND c.relname IN ('user_profiles', 'subscriptions', 'workspaces')
  AND NOT t.tgisinternal
ORDER BY c.relname, t.tgname;

-- ============================================================
-- Q8: Functions referenced by triggers and direct dependencies
-- Export as: q8_referenced_functions.csv
-- ============================================================
WITH target_tables AS (
  SELECT c.oid AS relid
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname IN ('user_profiles', 'subscriptions', 'workspaces')
),
trigger_functions AS (
  SELECT DISTINCT t.tgfoid AS func_oid
  FROM pg_trigger t
  WHERE t.tgrelid IN (SELECT relid FROM target_tables)
    AND NOT t.tgisinternal
),
object_dependencies AS (
  SELECT DISTINCT d.refobjid AS func_oid
  FROM pg_depend d
  WHERE d.refclassid = 'pg_proc'::regclass
    AND d.classid IN ('pg_attrdef'::regclass, 'pg_constraint'::regclass, 'pg_rewrite'::regclass)
    AND d.objid IN (
      SELECT ad.oid FROM pg_attrdef ad WHERE ad.adrelid IN (SELECT relid FROM target_tables)
      UNION
      SELECT con.oid FROM pg_constraint con WHERE con.conrelid IN (SELECT relid FROM target_tables)
      UNION
      SELECT r.oid
      FROM pg_rewrite r
      JOIN pg_class c ON c.oid = r.ev_class
      WHERE c.oid IN (SELECT relid FROM target_tables)
    )
),
all_funcs AS (
  SELECT func_oid FROM trigger_functions
  UNION
  SELECT func_oid FROM object_dependencies
)
SELECT
  pn.nspname AS function_schema,
  p.proname AS function_name,
  p.oid AS function_oid,
  pg_get_function_identity_arguments(p.oid) AS function_arguments,
  pg_get_function_result(p.oid) AS return_type,
  l.lanname AS language,
  p.prosecdef AS security_definer,
  p.provolatile AS volatility,
  pg_get_functiondef(p.oid) AS function_definition
FROM all_funcs af
JOIN pg_proc p ON p.oid = af.func_oid
JOIN pg_namespace pn ON pn.oid = p.pronamespace
JOIN pg_language l ON l.oid = p.prolang
ORDER BY pn.nspname, p.proname, function_arguments;

-- ============================================================
-- Q9: Function grants for referenced functions
-- Export as: q9_function_grants.csv
-- ============================================================
WITH referenced_functions AS (
  SELECT DISTINCT p.oid,
    pn.nspname AS function_schema,
    p.proname,
    pg_get_function_identity_arguments(p.oid) AS function_arguments
  FROM pg_proc p
  JOIN pg_namespace pn ON pn.oid = p.pronamespace
  WHERE p.oid IN (
    WITH target_tables AS (
      SELECT c.oid AS relid
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public'
        AND c.relname IN ('user_profiles', 'subscriptions', 'workspaces')
    )
    SELECT DISTINCT t.tgfoid
    FROM pg_trigger t
    WHERE t.tgrelid IN (SELECT relid FROM target_tables)
      AND NOT t.tgisinternal
  )
)
SELECT
  rf.function_schema,
  rf.proname AS function_name,
  rf.function_arguments,
  grantee.rolname AS grantee,
  priv.privilege_type,
  priv.is_grantable
FROM referenced_functions rf
JOIN LATERAL aclexplode(COALESCE((SELECT p.proacl FROM pg_proc p WHERE p.oid = rf.oid), acldefault('f', (SELECT p.proowner FROM pg_proc p WHERE p.oid = rf.oid)))) priv ON true
JOIN pg_roles grantee ON grantee.oid = priv.grantee
ORDER BY rf.function_schema, rf.proname, rf.function_arguments, grantee.rolname;

-- ============================================================
-- Q10: Policy/default/constraint expression text for function reference review
-- Export as: q10_expression_sources.csv
-- ============================================================
SELECT
  src_type,
  schema_name,
  table_name,
  object_name,
  expression_text
FROM (
  SELECT
    'DEFAULT'::text AS src_type,
    n.nspname AS schema_name,
    c.relname AS table_name,
    a.attname AS object_name,
    pg_get_expr(ad.adbin, ad.adrelid) AS expression_text
  FROM pg_attrdef ad
  JOIN pg_attribute a ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
  JOIN pg_class c ON c.oid = ad.adrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relname IN ('user_profiles', 'subscriptions', 'workspaces')

  UNION ALL

  SELECT
    'CHECK'::text,
    n.nspname,
    c.relname,
    con.conname,
    pg_get_constraintdef(con.oid, true)
  FROM pg_constraint con
  JOIN pg_class c ON c.oid = con.conrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname IN ('user_profiles', 'subscriptions', 'workspaces')
    AND con.contype = 'c'

  UNION ALL

  SELECT
    'POLICY_USING'::text,
    p.schemaname,
    p.tablename,
    p.policyname,
    COALESCE(p.qual, '')
  FROM pg_policies p
  WHERE p.schemaname = 'public'
    AND p.tablename IN ('user_profiles', 'subscriptions', 'workspaces')

  UNION ALL

  SELECT
    'POLICY_WITH_CHECK'::text,
    p.schemaname,
    p.tablename,
    p.policyname,
    COALESCE(p.with_check, '')
  FROM pg_policies p
  WHERE p.schemaname = 'public'
    AND p.tablename IN ('user_profiles', 'subscriptions', 'workspaces')
) x
ORDER BY table_name, src_type, object_name;
