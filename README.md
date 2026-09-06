# IAQ — Intelligence Assessment Quotient

> Understand how you think. Discover where you could thrive.

IAQ is a V1.0 baseline for a cognitive, aptitude, interest, and academic-direction assessment platform for high-school students. It is intentionally cautious: results are an **Experimental IAQ Composite**, not a clinical diagnosis or officially normed IQ score.

## What is included

- React + TypeScript + Vite product shell with editorial dashboard UI.
- Student flow: a results-first seven-domain cognitive session, a server-enforced 35-minute timer, Compass, Tracker, evidence prompts, saved majors, and a private printable report.
- Question bank: 840 pilot items, with 120 deterministic/reviewable candidates in each intelligence aspect. A complete test selects 8 items per aspect (56 total), avoids duplicate item families within a session, and randomizes the order for every session.
- Counselor workspace with consent-aware student states and anonymized cohort summaries.
- Administrator item studio with lifecycle states, item health flags, response counts, and protected answer-key preview.
- FastAPI service boundary with server-side response scoring, idempotent response submission, session events, RIASEC scoring, transparent major matching, tracker endpoints, and role-oriented endpoints.
- PostgreSQL-backed assessment/session/result persistence when `IAQ_DATABASE_URL` is configured, plus dependency-light local demo behavior.
- Provider-neutral identity and commerce workflow: development sign-in for each role, server-side permission maps, backend-driven IDR products, order snapshots, mock hosted-checkout state, verified sandbox settlement, and explicit entitlements.
- Optional account, pricing, checkout, payment-status, billing, and settings routes. Production Supabase/Google/Midtrans activation remains disabled until credentials, merchant approval, MFA, consent, and legal review are complete.
- Results integrity workflow: an empty results state (no demo score), incomplete domains remain “not assessed,” optional interest check-in persistence, private completion certificates with a minimal public verification response, and development-only report-delivery status.
- Product, assessment, privacy, pilot, deployment, and data dictionary documentation in `docs/`.

## Run the frontend

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Run the backend

Python 3.12 is recommended. The current local environment also supports the code on Python 3.9.

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

For the local access workflow, copy `.env.example` to `.env` if desired and keep `IAQ_AUTH_MODE=development`. Open `/auth/login` and choose a seeded role. The student account has development assessment access; the guardian account can create a sandbox purchase for `demo-student`. Payment access is granted only after clicking the sandbox settlement action and receiving the server-confirmed `fulfilled` state.

PostgreSQL (recommended for durable sessions and results):

```bash
docker compose up -d postgres
psql postgresql://iaq:iaq@localhost:5432/iaq -f backend/migrations/001_initial.sql
psql postgresql://iaq:iaq@localhost:5432/iaq -f backend/migrations/002_question_bank_contract.sql
psql postgresql://iaq:iaq@localhost:5432/iaq -f backend/migrations/003_results_first_assessment.sql
psql postgresql://iaq:iaq@localhost:5432/iaq -f backend/migrations/006_identity_commerce.sql
psql postgresql://iaq:iaq@localhost:5432/iaq -f backend/migrations/007_reports_interests_certificates.sql
cd backend
$env:IAQ_DATABASE_URL = 'postgresql+psycopg://iaq:iaq@localhost:5432/iaq'  # PowerShell
python -m app.seed
```

The seed command is idempotent. It creates the 840 reviewed/generated pilot item
records and their version-1 answer keys in PostgreSQL; version conflicts are not
silently overwritten. Without `IAQ_DATABASE_URL`, `python -m app.seed` prints the
bank summary used by the dependency-light local API.

The frontend requires the backend for assessment sessions and real result data.
Configure `VITE_API_BASE_URL` when connecting the UI to a different service.

## Verify

```bash
npm run typecheck
npm run build
npm test
cd backend
pytest
python -m app.seed
```

## Demo roles

The local UI includes seeded views rather than production authentication:

| Role | Demo view | Purpose |
| --- | --- | --- |
| Student | Ari Pratama | Assessment, Compass, Tracker, report |
| Counselor | `/school` | Authorized follow-up and anonymized cohort view |
| Administrator | `/admin` | Item review and health dashboard |

Additional workflow routes are `/auth/login`, `/pricing`, `/checkout/iaq-complete`, `/app/billing`, `/app/settings/profile`, `/interests`, `/certificates`, and `/verify`. The local development provider is intentionally not a production auth system. See [docs/AUTH_ARCHITECTURE.md](docs/AUTH_ARCHITECTURE.md), [docs/PAYMENT_ARCHITECTURE.md](docs/PAYMENT_ARCHITECTURE.md), and [docs/ENTITLEMENT_MODEL.md](docs/ENTITLEMENT_MODEL.md).

Production must replace demo mode with token validation and server-side role checks. No demo credentials should be used for real student data.

## Scientific boundary

Question candidates and synthetic responses can help test software. They cannot establish difficulty, discrimination, fairness, reliability, predictive validity, or population norms. Real pilot data and psychometric review are required before making stronger claims. See [docs/PILOT_PLAN.md](docs/PILOT_PLAN.md) and [docs/SCORING_V1.md](docs/SCORING_V1.md).
