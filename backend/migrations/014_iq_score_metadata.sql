-- Keep the experimental score contract identical after a process restart.
-- These fields describe the display model; they do not make it a normed IQ.

ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS iq_score_kind text;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS iq_score_label text;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS iq_score_version text;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS iq_score_scale text;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS iq_score_method text;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS official_iq_enabled boolean NOT NULL DEFAULT false;
