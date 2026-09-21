-- Durable guest ownership and manual QRIS records.
-- Run after 012_experimental_iq_score.sql.

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS result_id uuid REFERENCES assessment_results(id);
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS purchaser_external_user_id text;
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS beneficiary_external_user_id text;

CREATE UNIQUE INDEX IF NOT EXISTS profiles_user_id_unique ON profiles(user_id);

CREATE TABLE IF NOT EXISTS guest_sessions (
    token_hash text PRIMARY KEY,
    external_user_id text UNIQUE NOT NULL,
    user_id uuid NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz
);

CREATE INDEX IF NOT EXISTS guest_sessions_user_idx ON guest_sessions(user_id, expires_at);

CREATE TABLE IF NOT EXISTS guest_result_identities (
    result_id uuid PRIMARY KEY REFERENCES assessment_results(id),
    external_guest_user_id text NOT NULL,
    email text NOT NULL,
    display_name text NOT NULL,
    age_band text NOT NULL,
    consent_version text NOT NULL,
    token_hash text NOT NULL,
    captured_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS guest_result_identities_token_idx ON guest_result_identities(token_hash, expires_at);

CREATE TABLE IF NOT EXISTS payment_proofs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES orders(id),
    user_id uuid NOT NULL REFERENCES users(id),
    idempotency_key text UNIQUE,
    filename text NOT NULL,
    content_type text NOT NULL,
    content bytea NOT NULL,
    size_bytes integer NOT NULL CHECK (size_bytes > 0),
    transaction_ref text,
    status text NOT NULL DEFAULT 'under_review',
    note text NOT NULL DEFAULT '',
    reviewed_by uuid REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS payment_proofs_order_idx ON payment_proofs(order_id, created_at DESC);

CREATE TABLE IF NOT EXISTS qris_settings (
    id text PRIMARY KEY,
    merchant_name text NOT NULL,
    instructions text NOT NULL,
    image_filename text,
    image bytea,
    image_content_type text,
    updated_by uuid REFERENCES users(id),
    updated_at timestamptz NOT NULL DEFAULT now()
);
