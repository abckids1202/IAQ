# IAQ implementation status

This release completes the highest-value product loop in local development: start a timed assessment, persist and score a real session, show a results-first report, add optional interest context, explore directions, request a private report delivery, and issue a minimal completion certificate.

## Implemented

- React/Vite student, public, counselor, administration, access, commerce, results, interest, certificate, and verification routes.
- FastAPI session contract with randomized balanced forms, a server deadline, idempotent response writes, server-side answer keys, and persisted results when PostgreSQL is configured.
- Honest incomplete-result behavior: domains with fewer than four scored items are `null`/“Not assessed,” and a composite is withheld until at least two domains have enough evidence.
- Interest check-in storage is separate from cognitive scoring and marked provisional.
- Direction matching consumes the current user’s latest stored cognitive result and interest check-in when available.
- Certificates prove completion/issuance only and the public verification response intentionally excludes scores.
- Report delivery is idempotent by result/email. Development mode records `QUEUED_DEV` and does not send real mail.
- Stale browser session recovery: a missing or expired local session pointer is cleared before a fresh assessment is created.
- Private-pilot guardrails: 120 candidates per domain, authoritative lifecycle metadata, review queue primitives, item-health calculations, score-only result projection, identity capture, minor guardian-consent records, and paid-report gating.
- Research dataset staging: the supplied five-domain banks, linked assets, and verbal research JSONL are copied under `data/assessment` and exposed only through protected admin inventory/preview/asset endpoints. Staged records are forced to `DRAFT`, `unreviewed`, `calibrated=false`, and `production_eligible=false`; they are not added to student forms.
- Dataset review workspace: administration can filter the staged catalog by domain/source, preview linked stimuli and options, inspect provenance/licensing, and record independent checklist decisions. Review decisions are stored in a local ignored sidecar in development and are still blocked from pilot activation.
- Memory protocol: working-memory items no longer reveal their stimulus in the prompt. The student runner now uses a three-second study screen, automatic hide transition, and recall screen with no replay.
- Runtime release gate: `/ready` reports safe configuration blockers; production mode rejects demo auth, non-persistent assessment sessions, unreviewed forms, mock checkout, and development-only report delivery.
- Database contract: migration `009_dataset_and_release_readiness.sql` adds Supabase subject mapping, delivery idempotency fields, and quarantined candidate/reviewer tables for the production import path.
- Production schema hardening: migration `010_production_hardening.sql` aligns the legacy role constraint with canonical roles, makes profiles one-to-one, and records session completion timestamps.
- Candidate import path: `python -m app.dataset_import` copies the quarantined JSONL catalog into restricted PostgreSQL `dataset_candidates` rows with DRAFT lifecycle and conflict-safe version handling; import alone cannot release an item.

## Explicitly not production-ready

- The local identity fallback, in-memory repositories, mock payment settlement, and development email provider are not suitable for real student data.
- Production auth, provider deployment, live email/payment webhooks, retention/deletion jobs, encryption/key management, and monitoring still require configuration and security review. Guardian consent is implemented as a local workflow but is not yet legally or operationally approved for production.
- The score remains a provisional within-profile educational signal. There are no population norms, percentiles, clinical claims, or validated career predictions.
- Certificates are not academic qualifications and do not establish an official IQ score.
- The staged research banks are intentionally Git-ignored because they contain answer keys. Keep them in private storage or a private repository and verify item-level licensing before deployment.
- The staged catalog currently has enough raw candidates for the target (2,000 each across five generated domains and 24,386 English verbal records), but it has zero production-eligible items until licensing, two-person review, calibration, and release approval are complete.

## Release gate

Before a real pilot, complete provider activation, database migration rehearsal, threat-model review, accessibility review at mobile widths, two-reviewer content approval, consent/legal review for minors, and a psychometric analysis plan. See `docs/PILOT_PLAN.md`, `docs/PRIVACY_MODEL.md`, and `docs/SCORING_V1.md`.
