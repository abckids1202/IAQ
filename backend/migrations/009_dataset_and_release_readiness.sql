-- IAQ dataset review and release-readiness contract.
-- Research candidates are deliberately separate from items/item_versions. They
-- can be reviewed in batches without making answer keys available to student
-- session queries or accidentally activating generated content.

ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider text NOT NULL DEFAULT 'local';
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_subject text;
CREATE UNIQUE INDEX IF NOT EXISTS users_auth_subject_idx
    ON users (auth_provider, auth_subject)
    WHERE auth_subject IS NOT NULL;

ALTER TABLE report_delivery_requests ADD COLUMN IF NOT EXISTS age_band text;
ALTER TABLE report_delivery_requests ADD COLUMN IF NOT EXISTS guardian_consent_id uuid REFERENCES guardian_consents(id);
ALTER TABLE report_delivery_requests ADD COLUMN IF NOT EXISTS idempotency_key text;
CREATE UNIQUE INDEX IF NOT EXISTS report_delivery_idempotency_idx
    ON report_delivery_requests (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS dataset_candidates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id text UNIQUE NOT NULL,
    source_dataset text NOT NULL,
    source_file text NOT NULL,
    source_id text NOT NULL,
    domain text NOT NULL,
    construct_id text NOT NULL,
    item_family_id text NOT NULL,
    content_version integer NOT NULL DEFAULT 1,
    item_type text NOT NULL,
    prompt text NOT NULL,
    options jsonb NOT NULL,
    answer_key jsonb NOT NULL,
    stimulus jsonb,
    rendering jsonb NOT NULL DEFAULT '{}'::jsonb,
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    license_evidence text,
    difficulty_target text NOT NULL DEFAULT 'medium_hard',
    actual_difficulty numeric,
    language text NOT NULL DEFAULT 'en',
    lifecycle_status text NOT NULL DEFAULT 'DRAFT',
    review_status text NOT NULL DEFAULT 'unreviewed',
    calibrated boolean NOT NULL DEFAULT false,
    commercial_use_approved boolean NOT NULL DEFAULT false,
    production_eligible boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_dataset, source_id, content_version),
    CHECK (lifecycle_status IN ('DRAFT','AUTO_VERIFIED','HUMAN_REVIEWED','PILOT','ACTIVE','RETIRED')),
    CHECK (review_status IN ('unreviewed','in_review','human_reviewed','changes_requested','rejected'))
);

CREATE TABLE IF NOT EXISTS dataset_candidate_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id uuid NOT NULL REFERENCES dataset_candidates(id),
    candidate_version integer NOT NULL,
    reviewer_id uuid NOT NULL REFERENCES users(id),
    reviewer_role text NOT NULL,
    decision text NOT NULL CHECK (decision IN ('approve','reject','changes_requested')),
    checks jsonb NOT NULL DEFAULT '{}'::jsonb,
    notes text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (candidate_id, candidate_version, reviewer_id)
);

CREATE INDEX IF NOT EXISTS dataset_candidates_domain_status_idx
    ON dataset_candidates (domain, lifecycle_status, review_status);
CREATE INDEX IF NOT EXISTS dataset_candidate_reviews_candidate_idx
    ON dataset_candidate_reviews (candidate_id, created_at DESC);

COMMENT ON TABLE dataset_candidates IS
    'Quarantined research candidates. Import and review do not grant student eligibility.';
COMMENT ON COLUMN dataset_candidates.answer_key IS
    'Restricted server-side answer key; never select this column in student payload queries.';
