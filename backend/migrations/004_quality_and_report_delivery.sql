-- Quality review history and optional post-result report delivery.
-- Report delivery remains opt-in and must use a provider adapter in production.

CREATE TABLE IF NOT EXISTS item_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id uuid NOT NULL REFERENCES items(id),
    item_version_id uuid REFERENCES item_versions(id),
    reviewer_id uuid REFERENCES users(id),
    status text NOT NULL,
    notes text NOT NULL DEFAULT '',
    checks jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS item_reviews_item_idx ON item_reviews(item_id, created_at DESC);

CREATE TABLE IF NOT EXISTS report_delivery_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id uuid NOT NULL REFERENCES assessment_results(id),
    name text NOT NULL,
    email text NOT NULL,
    consent_version text NOT NULL,
    status text NOT NULL DEFAULT 'QUEUED',
    provider text NOT NULL DEFAULT 'development_log',
    provider_message_id text,
    error text,
    requested_at timestamptz NOT NULL DEFAULT now(),
    sent_at timestamptz,
    UNIQUE(result_id, email)
);

CREATE INDEX IF NOT EXISTS report_delivery_result_idx ON report_delivery_requests(result_id);
