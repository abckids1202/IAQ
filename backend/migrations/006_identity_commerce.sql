-- IAQ V1 identity, authorization, commerce, and entitlement contract.
-- This migration stores provider-neutral records. Supabase Auth remains the
-- authentication provider; the application owns roles and product access.

ALTER TABLE users ADD COLUMN IF NOT EXISTS account_status text NOT NULL DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at timestamptz;

CREATE TABLE IF NOT EXISTS roles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text UNIQUE NOT NULL CHECK (code IN ('student','guardian','counselor','school_admin','content_reviewer','platform_admin')),
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS permissions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text UNIQUE NOT NULL,
    description text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id uuid NOT NULL REFERENCES roles(id),
    permission_id uuid NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);
CREATE TABLE IF NOT EXISTS user_roles (
    user_id uuid NOT NULL REFERENCES users(id),
    role_id uuid NOT NULL REFERENCES roles(id),
    assigned_by uuid REFERENCES users(id),
    assigned_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS schools (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    slug text UNIQUE NOT NULL,
    status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS school_memberships (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id uuid NOT NULL REFERENCES schools(id),
    user_id uuid NOT NULL REFERENCES users(id),
    membership_role text NOT NULL CHECK (membership_role IN ('student','counselor','school_admin')),
    status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (school_id, user_id, membership_role)
);
CREATE TABLE IF NOT EXISTS school_invitations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id uuid NOT NULL REFERENCES schools(id),
    email text NOT NULL,
    role_code text NOT NULL,
    invited_by uuid NOT NULL REFERENCES users(id),
    token_hash text UNIQUE NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    expires_at timestamptz NOT NULL,
    accepted_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS guardian_relationships (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    guardian_user_id uuid NOT NULL REFERENCES users(id),
    student_user_id uuid NOT NULL REFERENCES users(id),
    status text NOT NULL DEFAULT 'pending',
    consent_scope text NOT NULL DEFAULT 'purchase_only',
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (guardian_user_id, student_user_id)
);
CREATE TABLE IF NOT EXISTS counselor_student_assignments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    counselor_user_id uuid NOT NULL REFERENCES users(id),
    student_user_id uuid NOT NULL REFERENCES users(id),
    school_id uuid NOT NULL REFERENCES schools(id),
    status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (counselor_user_id, student_user_id, school_id)
);
CREATE TABLE IF NOT EXISTS user_consents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id),
    consent_version text NOT NULL,
    purpose text NOT NULL,
    granted boolean NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS account_status_history (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id),
    previous_status text,
    next_status text NOT NULL,
    changed_by uuid REFERENCES users(id),
    reason text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS security_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id),
    event_type text NOT NULL,
    success boolean NOT NULL,
    ip_hash text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS mfa_factors (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id),
    factor_type text NOT NULL DEFAULT 'totp',
    status text NOT NULL DEFAULT 'unverified',
    provider_factor_id text,
    enrolled_at timestamptz,
    verified_at timestamptz,
    UNIQUE (user_id, factor_type)
);
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_code text UNIQUE NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    active boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS prices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id uuid NOT NULL REFERENCES products(id),
    price_code text UNIQUE NOT NULL,
    amount_minor bigint NOT NULL CHECK (amount_minor >= 0),
    currency char(3) NOT NULL DEFAULT 'IDR',
    active boolean NOT NULL DEFAULT false,
    valid_from timestamptz NOT NULL DEFAULT now(),
    valid_to timestamptz
);
CREATE TABLE IF NOT EXISTS orders (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number text UNIQUE NOT NULL,
    purchaser_user_id uuid NOT NULL REFERENCES users(id),
    beneficiary_user_id uuid NOT NULL REFERENCES users(id),
    school_id uuid REFERENCES schools(id),
    currency char(3) NOT NULL DEFAULT 'IDR',
    subtotal_minor bigint NOT NULL CHECK (subtotal_minor >= 0),
    discount_minor bigint NOT NULL DEFAULT 0 CHECK (discount_minor >= 0),
    tax_minor bigint NOT NULL DEFAULT 0 CHECK (tax_minor >= 0),
    total_minor bigint NOT NULL CHECK (total_minor >= 0),
    status text NOT NULL DEFAULT 'draft',
    product_snapshot jsonb NOT NULL,
    price_snapshot jsonb NOT NULL,
    terms_accepted_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS order_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES orders(id),
    product_id uuid NOT NULL REFERENCES products(id),
    price_id uuid NOT NULL REFERENCES prices(id),
    quantity integer NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_amount_minor bigint NOT NULL CHECK (unit_amount_minor >= 0),
    snapshot jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS payment_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES orders(id),
    provider text NOT NULL,
    provider_order_id text,
    checkout_token text,
    redirect_url text,
    amount_minor bigint NOT NULL,
    currency char(3) NOT NULL,
    normalized_status text NOT NULL DEFAULT 'pending',
    provider_status text,
    expires_at timestamptz,
    idempotency_key text UNIQUE NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS payment_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_event_id text UNIQUE,
    payment_attempt_id uuid REFERENCES payment_attempts(id),
    order_id uuid REFERENCES orders(id),
    event_type text NOT NULL,
    signature_valid boolean NOT NULL,
    normalized_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    processing_status text NOT NULL DEFAULT 'received',
    processing_attempts integer NOT NULL DEFAULT 0,
    failure_reason text,
    received_at timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz
);
CREATE TABLE IF NOT EXISTS entitlements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL,
    owner_type text NOT NULL CHECK (owner_type IN ('user','school')),
    owner_id uuid NOT NULL,
    source_type text NOT NULL,
    source_id uuid,
    status text NOT NULL DEFAULT 'pending',
    valid_from timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz,
    quantity integer NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    remaining_quantity integer NOT NULL DEFAULT 1 CHECK (remaining_quantity >= 0),
    granted_by uuid REFERENCES users(id),
    revoked_by uuid REFERENCES users(id),
    revocation_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS entitlement_consumptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entitlement_id uuid NOT NULL REFERENCES entitlements(id),
    assessment_session_id uuid REFERENCES test_sessions(id),
    quantity integer NOT NULL DEFAULT 1 CHECK (quantity > 0),
    consumed_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (entitlement_id, assessment_session_id)
);
CREATE TABLE IF NOT EXISTS billing_profiles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id),
    email text NOT NULL,
    display_name text,
    address jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);
CREATE TABLE IF NOT EXISTS invoices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number text UNIQUE NOT NULL,
    school_id uuid REFERENCES schools(id),
    order_id uuid REFERENCES orders(id),
    status text NOT NULL DEFAULT 'issued',
    total_minor bigint NOT NULL,
    currency char(3) NOT NULL DEFAULT 'IDR',
    due_at timestamptz,
    paid_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS invoice_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id uuid NOT NULL REFERENCES invoices(id),
    description text NOT NULL,
    quantity integer NOT NULL,
    amount_minor bigint NOT NULL
);
CREATE TABLE IF NOT EXISTS refunds (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES orders(id),
    payment_attempt_id uuid REFERENCES payment_attempts(id),
    amount_minor bigint NOT NULL,
    currency char(3) NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    reason text,
    created_by uuid REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS discount_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text UNIQUE NOT NULL,
    product_id uuid REFERENCES products(id),
    amount_minor bigint NOT NULL DEFAULT 0,
    active boolean NOT NULL DEFAULT true,
    valid_from timestamptz NOT NULL DEFAULT now(),
    valid_to timestamptz
);
CREATE TABLE IF NOT EXISTS school_licences (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id uuid NOT NULL REFERENCES schools(id),
    source_invoice_id uuid REFERENCES invoices(id),
    product_id uuid NOT NULL REFERENCES products(id),
    seat_quantity integer NOT NULL CHECK (seat_quantity > 0),
    status text NOT NULL DEFAULT 'active',
    valid_from timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz
);
CREATE TABLE IF NOT EXISTS school_seat_allocations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    licence_id uuid NOT NULL REFERENCES school_licences(id),
    school_id uuid NOT NULL REFERENCES schools(id),
    student_user_id uuid NOT NULL REFERENCES users(id),
    entitlement_id uuid REFERENCES entitlements(id),
    status text NOT NULL DEFAULT 'active',
    allocated_by uuid NOT NULL REFERENCES users(id),
    revoked_by uuid REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    UNIQUE (licence_id, student_user_id)
);
CREATE TABLE IF NOT EXISTS reconciliation_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    status text NOT NULL DEFAULT 'started',
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);

CREATE UNIQUE INDEX IF NOT EXISTS active_entitlement_source_idx ON entitlements (code, owner_type, owner_id, source_type, source_id) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS orders_purchaser_idx ON orders (purchaser_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS orders_beneficiary_idx ON orders (beneficiary_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS payment_events_status_idx ON payment_events (processing_status, received_at);
CREATE INDEX IF NOT EXISTS entitlements_owner_idx ON entitlements (owner_type, owner_id, status);
CREATE INDEX IF NOT EXISTS school_seat_school_idx ON school_seat_allocations (school_id, status);

INSERT INTO roles (code, name) VALUES
    ('student', 'Student'), ('guardian', 'Guardian'), ('counselor', 'Counselor'),
    ('school_admin', 'School administrator'), ('content_reviewer', 'Content reviewer'),
    ('platform_admin', 'Platform administrator')
ON CONFLICT (code) DO NOTHING;
