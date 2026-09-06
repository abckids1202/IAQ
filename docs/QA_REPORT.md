# IAQ QA report — local release

Date: 2026-09-06

## Automated checks

| Check | Result |
| --- | --- |
| `npm.cmd run typecheck` | Passed |
| `npm.cmd run build` | Passed; Vite reports a non-blocking large-chunk warning |
| `npm.cmd test -- --run` | Passed: 2 tests |
| `python -m pytest -q` from `backend` | Passed: 19 tests |
| `python -m compileall -q app` | Passed |
| `git diff --check` | Passed |

## Product checks covered

- One-item domains no longer become flattering scores; they remain insufficient evidence.
- Empty `/results` does not display seeded score data.
- A stale assessment ID in browser session storage is cleared and retried as a new session.
- Interest responses are stored per current development user and carry explicit provisional metadata.
- Certificate issuance is tied to a submitted result; public verification omits score data.
- Report delivery is consent-gated, age-gated for minors, and idempotent by result/email.

## Manual checks still required before real deployment

- Run migrations 001–007 against an empty PostgreSQL database and repeat the seed.
- Exercise real Supabase/Google/Midtrans/transactional-email adapters in a staging environment.
- Review `/`, `/assess`, `/assess/session`, `/results`, `/interests`, `/certificates`, and `/verify` at 1440px, 1024px, and 390px.
- Test refresh/resume, timeout auto-submit, network loss, reduced motion, keyboard-only navigation, and screen-reader announcements.
- Have assessment reviewers inspect every item family and have a psychometric reviewer approve pilot criteria.
