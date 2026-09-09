-- Strict pilot metadata: keep score type, norm version, and session context
-- explicit so provisional results cannot be mistaken for normed IQ scores.

ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS score_kind text NOT NULL DEFAULT 'provisional_domain_signal';
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS norm_version text;
ALTER TABLE test_sessions ADD COLUMN IF NOT EXISTS language text NOT NULL DEFAULT 'en';
ALTER TABLE test_sessions ADD COLUMN IF NOT EXISTS age_band text NOT NULL DEFAULT 'unknown';

-- A timed session may finish with too little evidence for one or more
-- domains. Preserve the result and mark those signals null instead of making
-- the transaction fail or inventing a score.
ALTER TABLE assessment_results ALTER COLUMN composite DROP NOT NULL;
ALTER TABLE domain_scores ALTER COLUMN score DROP NOT NULL;

COMMENT ON COLUMN assessment_results.score_kind IS
    'The measurement type. provisional_domain_signal is not an IQ score.';
COMMENT ON COLUMN assessment_results.norm_version IS
    'Locked norm reference used for a future IAQ IQ estimate; null for provisional results.';
