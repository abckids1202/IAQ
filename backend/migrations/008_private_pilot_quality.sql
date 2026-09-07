-- IAQ private-pilot quality, ownership, consent, and AI output contract.
-- This migration adds auditability without making generated candidates
-- eligible for student forms automatically.

ALTER TABLE test_sessions ADD COLUMN IF NOT EXISTS external_user_id text;
ALTER TABLE test_sessions ADD COLUMN IF NOT EXISTS consent_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS access_tier text NOT NULL DEFAULT 'summary';
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS data_origin text NOT NULL DEFAULT 'REAL_PILOT';

ALTER TABLE items ADD COLUMN IF NOT EXISTS review_required boolean NOT NULL DEFAULT true;
ALTER TABLE items ADD COLUMN IF NOT EXISTS reviewed_at timestamptz;
ALTER TABLE items ADD COLUMN IF NOT EXISTS license_evidence text;
ALTER TABLE items ADD COLUMN IF NOT EXISTS source_registry_id uuid REFERENCES source_registry(id);

ALTER TABLE item_versions ADD COLUMN IF NOT EXISTS actual_difficulty numeric;
ALTER TABLE item_versions ADD COLUMN IF NOT EXISTS reading_level text;
ALTER TABLE item_versions ADD COLUMN IF NOT EXISTS independent_answer text;
ALTER TABLE item_versions ADD COLUMN IF NOT EXISTS render_parameters jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE item_versions ADD COLUMN IF NOT EXISTS license_evidence text;
ALTER TABLE item_versions ADD COLUMN IF NOT EXISTS frozen_at timestamptz;

ALTER TABLE item_reviews ADD COLUMN IF NOT EXISTS reviewer_role text;
ALTER TABLE item_reviews ADD COLUMN IF NOT EXISTS decision text;
ALTER TABLE item_reviews ADD COLUMN IF NOT EXISTS review_round integer NOT NULL DEFAULT 1;
ALTER TABLE item_reviews ADD COLUMN IF NOT EXISTS reviewed_at timestamptz;

CREATE TABLE IF NOT EXISTS item_health_metrics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    item_version_id uuid NOT NULL REFERENCES item_versions(id),
    data_origin text NOT NULL CHECK (data_origin IN ('REAL_PILOT','SYNTHETIC')),
    sample_size integer NOT NULL DEFAULT 0,
    answered_count integer NOT NULL DEFAULT 0,
    correct_rate numeric,
    discrimination numeric,
    median_response_time_ms integer,
    response_time_p25_ms integer,
    response_time_p75_ms integer,
    omission_rate numeric,
    timeout_rate numeric,
    flags jsonb NOT NULL DEFAULT '[]'::jsonb,
    calculated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(item_version_id, data_origin)
);

CREATE TABLE IF NOT EXISTS guardian_consents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_user_id uuid NOT NULL REFERENCES users(id),
    guardian_user_id uuid,
    guardian_email text NOT NULL,
    consent_version text NOT NULL,
    scope text NOT NULL DEFAULT 'assessment_and_pilot_data',
    token_hash text UNIQUE NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    requested_at timestamptz NOT NULL DEFAULT now(),
    granted_at timestamptz,
    expires_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_result_outputs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id uuid NOT NULL REFERENCES assessment_results(id),
    user_id uuid REFERENCES users(id),
    kind text NOT NULL,
    status text NOT NULL,
    data_origin text NOT NULL DEFAULT 'AI_ASSISTED',
    provider text NOT NULL,
    model text NOT NULL,
    prompt_version text NOT NULL,
    input_hash text NOT NULL,
    output jsonb,
    fallback_used boolean NOT NULL DEFAULT false,
    provider_request_id text,
    error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(result_id, kind, input_hash)
);

CREATE TABLE IF NOT EXISTS pilot_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name text NOT NULL,
    user_external_id text,
    session_id uuid REFERENCES test_sessions(id),
    properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    data_origin text NOT NULL DEFAULT 'REAL_PILOT',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS test_sessions_external_user_idx ON test_sessions(external_user_id);
CREATE INDEX IF NOT EXISTS item_health_flags_idx ON item_health_metrics USING gin(flags);
CREATE INDEX IF NOT EXISTS ai_result_outputs_result_idx ON ai_result_outputs(result_id, kind, created_at DESC);
CREATE INDEX IF NOT EXISTS pilot_events_name_idx ON pilot_events(event_name, created_at DESC);

COMMENT ON TABLE item_health_metrics IS 'Descriptive pilot metrics only; never activates an item automatically.';
COMMENT ON TABLE ai_result_outputs IS 'Versioned, entitlement-protected AI direction outputs; never authoritative scoring.';

CREATE OR REPLACE FUNCTION prevent_scored_item_version_edit()
RETURNS trigger AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM assessment_form_items afi
        JOIN test_sessions ts ON ts.id = afi.session_id
        WHERE afi.item_version_id = OLD.id
          AND ts.result_id IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'Scored item versions are immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS item_versions_scored_immutable ON item_versions;
CREATE TRIGGER item_versions_scored_immutable
    BEFORE UPDATE ON item_versions
    FOR EACH ROW EXECUTE FUNCTION prevent_scored_item_version_edit();
