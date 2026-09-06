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

## Explicitly not production-ready

- The local identity fallback, in-memory repositories, mock payment settlement, and development email provider are not suitable for real student data.
- Production auth, database migrations, email provider, payment webhooks, guardian consent, retention/deletion jobs, encryption/key management, and monitoring still require deployment configuration and security review.
- The score remains a provisional within-profile educational signal. There are no population norms, percentiles, clinical claims, or validated career predictions.
- Certificates are not academic qualifications and do not establish an official IQ score.

## Release gate

Before a real pilot, complete provider activation, database migration rehearsal, threat-model review, accessibility review at mobile widths, two-reviewer content approval, consent/legal review for minors, and a psychometric analysis plan. See `docs/PILOT_PLAN.md`, `docs/PRIVACY_MODEL.md`, and `docs/SCORING_V1.md`.
