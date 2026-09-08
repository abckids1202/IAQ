-- Production hardening follow-up.
-- Keeps the legacy role column compatible with the canonical role tables and
-- records the session completion timestamp used by reporting/retention jobs.

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check
    CHECK (role IN ('student','guardian','counselor','school_admin','content_reviewer','platform_admin','reviewer','admin'));

CREATE UNIQUE INDEX IF NOT EXISTS profiles_user_id_unique_idx ON profiles (user_id);
ALTER TABLE test_sessions ADD COLUMN IF NOT EXISTS completed_at timestamptz;

CREATE INDEX IF NOT EXISTS test_sessions_completed_idx
    ON test_sessions (user_id, completed_at DESC);

COMMENT ON COLUMN users.role IS
    'Compatibility role only. Production authorization uses user_roles and server-managed Supabase app_metadata.';
