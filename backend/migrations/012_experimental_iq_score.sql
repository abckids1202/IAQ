-- Experimental IQ-style display score.
--
-- This nullable field is intentionally separate from the observed composite
-- profile signal. It must remain null until the complete seven-domain form
-- has enough evidence. It is not a normed or official IQ score.

ALTER TABLE assessment_results
    ADD COLUMN IF NOT EXISTS iq_score numeric;

COMMENT ON COLUMN assessment_results.iq_score IS
    'Experimental IAQ IQ-style reference score only; not population-normed, official, clinical, or diagnostic.';
