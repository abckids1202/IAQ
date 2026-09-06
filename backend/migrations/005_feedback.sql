-- Lightweight product feedback inbox. PII remains optional and should follow
-- the application's retention policy in production.

CREATE TABLE IF NOT EXISTS feedback_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message text NOT NULL,
    page text NOT NULL,
    email text,
    status text NOT NULL DEFAULT 'NEW',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS feedback_messages_created_idx ON feedback_messages(created_at DESC);
