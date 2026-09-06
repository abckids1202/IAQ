-- Results delivery and exploration foundation.
-- Experimental results remain provisional; certificate validity proves
-- completion/issuance, not scientific or institutional recognition.

ALTER TABLE assessment_results ALTER COLUMN composite DROP NOT NULL;
ALTER TABLE domain_scores ALTER COLUMN score DROP NOT NULL;

CREATE TABLE IF NOT EXISTS interest_instruments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text UNIQUE NOT NULL,
    version text NOT NULL,
    language text NOT NULL DEFAULT 'id',
    status text NOT NULL DEFAULT 'PILOT',
    scoring_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS interest_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id uuid NOT NULL REFERENCES interest_instruments(id),
    code text NOT NULL,
    dimension char(1) NOT NULL CHECK (dimension IN ('R','I','A','S','E','C')),
    prompt text NOT NULL,
    version integer NOT NULL DEFAULT 1,
    UNIQUE (instrument_id, code, version)
);
CREATE TABLE IF NOT EXISTS interest_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id),
    instrument_id uuid NOT NULL REFERENCES interest_instruments(id),
    status text NOT NULL DEFAULT 'IN_PROGRESS',
    language text NOT NULL DEFAULT 'id',
    response_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
    result_snapshot jsonb,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);
CREATE TABLE IF NOT EXISTS interest_responses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id uuid NOT NULL REFERENCES interest_attempts(id),
    item_id uuid NOT NULL REFERENCES interest_items(id),
    value integer,
    response_state text NOT NULL DEFAULT 'answered',
    revision integer NOT NULL DEFAULT 1,
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (attempt_id, item_id, revision)
);

CREATE TABLE IF NOT EXISTS report_grants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id uuid NOT NULL REFERENCES assessment_results(id),
    owner_user_id uuid NOT NULL REFERENCES users(id),
    grantee_type text NOT NULL CHECK (grantee_type IN ('guardian','counselor','school')),
    grantee_id uuid NOT NULL,
    scope text NOT NULL,
    status text NOT NULL DEFAULT 'active',
    granted_by uuid NOT NULL REFERENCES users(id),
    granted_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    UNIQUE (result_id, grantee_type, grantee_id, scope)
);
CREATE TABLE IF NOT EXISTS certificates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id uuid NOT NULL REFERENCES assessment_results(id),
    user_id uuid NOT NULL REFERENCES users(id),
    certificate_identifier text UNIQUE NOT NULL,
    document_revision integer NOT NULL DEFAULT 1,
    status text NOT NULL DEFAULT 'issued',
    title text NOT NULL,
    language text NOT NULL DEFAULT 'id',
    audience text NOT NULL,
    assessment_version text NOT NULL,
    scoring_version text NOT NULL,
    certificate_hash text,
    private_object_key text,
    issued_at timestamptz NOT NULL DEFAULT now(),
    supersedes_id uuid REFERENCES certificates(id),
    revoked_at timestamptz,
    revocation_reason text,
    UNIQUE (result_id, document_revision)
);
CREATE TABLE IF NOT EXISTS certificate_verification_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    certificate_id uuid NOT NULL REFERENCES certificates(id),
    accessed_at timestamptz NOT NULL DEFAULT now(),
    result_state text NOT NULL
);
CREATE TABLE IF NOT EXISTS report_delivery_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_request_id uuid NOT NULL REFERENCES report_delivery_requests(id),
    provider_event_id text UNIQUE,
    status text NOT NULL,
    provider_message_id text,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    received_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS data_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id),
    request_type text NOT NULL CHECK (request_type IN ('export','correction','deletion')),
    status text NOT NULL DEFAULT 'requested',
    reason text,
    requested_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);
CREATE TABLE IF NOT EXISTS source_registry (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type text NOT NULL,
    title text NOT NULL,
    owner_or_author text,
    source_url text,
    acquired_version text,
    acquired_at timestamptz,
    license_evidence text,
    commercial_use_allowed boolean NOT NULL DEFAULT false,
    review_status text NOT NULL DEFAULT 'rights_review_required',
    notes text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS certificates_user_idx ON certificates(user_id, issued_at DESC);
CREATE INDEX IF NOT EXISTS report_grants_result_idx ON report_grants(result_id, status);
CREATE INDEX IF NOT EXISTS interest_attempts_user_idx ON interest_attempts(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS data_requests_user_idx ON data_requests(user_id, status);
