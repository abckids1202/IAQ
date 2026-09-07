# IAQ whole-product audit — 2026-09-07

## Executive assessment

IAQ is a strong local pilot baseline, not a production assessment service yet. The main product loop is present: a student can start a timed randomized assessment, submit real responses, receive a results-first visual report, complete a separate interest check-in, explore deterministic directions, request development-mode report delivery, and issue a private completion certificate.

The highest-risk gap is not the UI. It is production identity/provider activation and validation: stable external identities now map to database users, but there is no real provider auth in this checkout, and no real pilot data exists to support difficulty, fairness, reliability, or norm claims.

## Progress by product area

| Area | Status | What exists | Important gap |
| --- | --- | --- | --- |
| Home and public pages | Strong pilot | Compact IAQ entry point, start-test CTA, public information routes, pricing/access surfaces, responsive navbar | Needs real content review, analytics, SEO, and production hosting checks |
| Assessment UX | Strong pilot | 35-minute server deadline, 56-question balanced form, refresh/resume, timeout handling, no app nav during testing, stale-session recovery | Manual browser QA still required at mobile widths; production auth/DB ownership is incomplete |
| Question bank | Pilot-ready software contract | 840 bank records, 120 per domain, lifecycle/provenance fields, family deduplication per form, answer keys server-side | Candidate quality is not the same as psychometric validation; two-reviewer and real-pilot evidence still required |
| Scoring and results | Strong provisional baseline | Persisted result shape, seven domain bars, confidence/quality context, no demo result on empty state, insufficient evidence remains null | Simple accuracy transform is not normed; no IRT, reliability, DIF, test-retest, or population calibration |
| Interest check-in | Functional pilot | Separate RIASEC-style storage, explicit provisional version, real UI and API | Current instrument is exploratory, not a validated vocational inventory; Compass still needs broader evidence inputs |
| Deterministic directions | Functional pilot | Candidate majors, transparent weighted fit, actual result/interest inputs, practical next-step framing | More academic/project evidence and explainable audit trails are needed before high-stakes use |
| Optional OpenAI layer | Ready but disabled until configured | Server-only key boundary, Responses API adapter, result interpretation, bounded direction context, output validation, provider status, AI-assisted labeling | No API call has been run in this environment; rate limits, cost controls, consent/retention, evals, and real user-ID persistence remain |
| Auth and roles | Development workflow | Role permission map, seeded student/guardian/counselor/admin flows, backend permission checks on protected areas | Demo fallback is not production auth; Supabase/Google/MFA/guardian consent must be activated and tested |
| School/counselor workflows | UI and access baseline | Separate counselor workspace, consent-aware roster language, cohort summary | Report access, notes, follow-ups, exports, audit trails, and data minimisation need real DB/provider wiring |
| Commerce | Sandbox baseline | Product catalog, backend price snapshots, orders, entitlements, mock settlement, Midtrans signature boundary | No live merchant credentials/webhook rehearsal/refund reconciliation in this environment |
| Report email | Development queue | Consent and minor age gate, idempotent result/email key, explicit `QUEUED_DEV` status | No transactional provider sends mail; guardian/minor workflow needs legal and operational review |
| Certificates | Functional pilot | Private issuance and minimal public verification without score disclosure | Needs durable identity-aware storage, PDF/document delivery, revocation process, and institutional policy |
| PostgreSQL | Migration contract plus adapter | Migrations 001–008, stable external-user mapping, sessions/responses/results support, versioned AI output storage | Requires an empty-database rehearsal, Supabase identity mapping, backups, and production operations |
| Accessibility/performance | Good baseline | ARIA labels, mobile navigation, reduced-motion CSS, loading/error states, lazy-safe UI patterns | Manual screen-reader/keyboard pass and code-splitting remain; Vite warns about a large JS chunk |
| QA and operations | Documented local gate | 22 backend tests, frontend typecheck/tests, build path, QA report, implementation status, audit | Need staging smoke tests, database rehearsal, provider failures, observability, backups, incident drills |

## AI boundary and setup

The key goes in the ignored root file:

```text
C:\Users\charl\OneDrive\Desktop\IAQ\.env
```

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini
IAQ_AI_ENABLED=true
```

Restart the backend. The frontend never receives the key. `GET /ai/status` reports only whether the capability is configured. The AI receives aggregate scores, quality context, interest scores, and the existing deterministic candidate list. It does not receive answer keys, report-email fields, or a write path to scores. The deterministic scorer remains the assessor of record.

## Nuances that matter

1. “AI assessor” must not mean AI scoring. If a model changes correctness, difficulty, item activation, or a student’s score, IAQ would lose reproducibility and make scientific validation impossible.
2. Interest results are context, not evidence of ability. A high interest score should not inflate a cognitive score or produce a guaranteed career claim.
3. Null is better than a flattering number. A domain with one or two answers cannot support a meaningful within-profile interpretation.
4. The current AI output is generated on demand, cached by an aggregate input hash, and stored in `ai_result_outputs` when Postgres is configured. Local development remains process-local by design.
5. Report email is a privacy boundary, not just a form. Names, emails, age, consent version, provider delivery state, retention, and minor/guardian policy must be treated as separate records.
6. A certificate proves that IAQ issued a completion record. It must never be presented as proof of IQ, diagnosis, school admission, or professional qualification.
7. The current question quantity is a software readiness milestone, not validation. “120 per domain” does not prove medium-hard difficulty or fairness.
8. The model alias is configurable because model behavior can change. Pin a snapshot and run evaluations before using AI output in a consequential workflow.

## Recommended next release order

1. Replace development identity with real authenticated user IDs throughout sessions, results, interests, certificates, delivery, and PostgreSQL queries.
2. Run migration and seed rehearsals on an empty PostgreSQL database; verify rollback/backup and idempotency.
3. Add an AI evaluation fixture set covering incomplete evidence, low confidence, rapid guessing, no interests, and conflicting interest/cognitive signals.
4. Add rate limiting, cost limits, request-ID logging, provider error telemetry, and an admin kill switch for AI endpoints.
5. Complete content review and start a real pilot with a preregistered psychometric analysis plan.
6. Perform manual 1440px/1024px/390px, keyboard, screen-reader, reduced-motion, timeout, refresh, network-loss, and consent tests.
7. Activate email/payment/auth providers only after legal, minor-consent, privacy, refund, and incident-response review.
