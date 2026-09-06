-- IAQ results-first assessment contract.
-- Generated content remains pilot content until human review and real response analysis.

ALTER TABLE items DROP CONSTRAINT IF EXISTS items_data_origin_check;
ALTER TABLE items ADD CONSTRAINT items_data_origin_check
    CHECK (data_origin IN ('REVIEWED_CONTENT', 'ORIGINAL_GENERATED', 'SYNTHETIC'));

ALTER TABLE items ADD COLUMN IF NOT EXISTS construct_id text;
ALTER TABLE items ADD COLUMN IF NOT EXISTS language text NOT NULL DEFAULT 'en';
ALTER TABLE items ADD COLUMN IF NOT EXISTS generation_run_id text;
ALTER TABLE items ADD COLUMN IF NOT EXISTS provenance text;
ALTER TABLE item_versions ADD COLUMN IF NOT EXISTS difficulty_target text DEFAULT 'medium_hard';
ALTER TABLE item_versions ADD COLUMN IF NOT EXISTS difficulty_estimate numeric;
ALTER TABLE item_versions ADD COLUMN IF NOT EXISTS render_type text DEFAULT 'choice';
ALTER TABLE item_versions ADD COLUMN IF NOT EXISTS generation_parameters jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS item_generation_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id text UNIQUE NOT NULL,
    factory text NOT NULL,
    seed text NOT NULL,
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    item_count integer NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'COMPLETED',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS item_options (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    item_version_id uuid NOT NULL REFERENCES item_versions(id),
    option_order integer NOT NULL,
    option_text text NOT NULL,
    UNIQUE(item_version_id, option_order)
);

CREATE TABLE IF NOT EXISTS item_assets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    item_version_id uuid NOT NULL REFERENCES item_versions(id),
    asset_type text NOT NULL,
    asset_uri text NOT NULL,
    alt_text text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS session_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES test_sessions(id),
    event_type text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(session_id, id)
);

CREATE TABLE IF NOT EXISTS assessment_sections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_version_id uuid NOT NULL REFERENCES assessment_versions(id),
    domain text NOT NULL,
    position integer NOT NULL,
    item_quota integer NOT NULL,
    duration_seconds integer,
    UNIQUE(assessment_version_id, domain)
);

CREATE TABLE IF NOT EXISTS assessment_form_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES test_sessions(id),
    item_version_id uuid NOT NULL REFERENCES item_versions(id),
    domain text NOT NULL,
    presented_order integer NOT NULL,
    UNIQUE(session_id, presented_order),
    UNIQUE(session_id, item_version_id)
);

ALTER TABLE test_sessions ADD COLUMN IF NOT EXISTS deadline_at timestamptz;
ALTER TABLE test_sessions ADD COLUMN IF NOT EXISTS duration_seconds integer NOT NULL DEFAULT 2100;
ALTER TABLE test_sessions ADD COLUMN IF NOT EXISTS result_id uuid;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS question_count integer NOT NULL DEFAULT 0;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS answered_count integer NOT NULL DEFAULT 0;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS domain_metrics jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS quality jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS completed_at timestamptz;

CREATE INDEX IF NOT EXISTS item_versions_render_type_idx ON item_versions(render_type);
CREATE INDEX IF NOT EXISTS assessment_form_items_session_domain_idx ON assessment_form_items(session_id, domain);
CREATE INDEX IF NOT EXISTS test_sessions_deadline_idx ON test_sessions(deadline_at);
