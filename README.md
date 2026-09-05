# IAQ — Intelligence Assessment Quotient

> Understand how you think. Discover where you could thrive.

IAQ is a V1.0 baseline for a cognitive, aptitude, interest, and academic-direction assessment platform for high-school students. It is intentionally cautious: results are an **Experimental IAQ Composite**, not a clinical diagnosis or officially normed IQ score.

## What is included

- React + TypeScript + Vite product shell with editorial dashboard UI.
- Student flow: a resumable seven-domain cognitive session, results, Compass, Tracker, evidence prompts, saved majors, and printable report.
- Question bank: 140 original medium-hard pilot items, with 20 items in each intelligence aspect. A complete test selects 8 fresh items per aspect (56 total) and randomizes their order for every session; the quick mode selects 2 per aspect (14 total).
- Counselor workspace with consent-aware student states and anonymized cohort summaries.
- Administrator item studio with lifecycle states, item health flags, response counts, and protected answer-key preview.
- FastAPI service boundary with server-side response scoring, idempotent response submission, session events, RIASEC scoring, transparent major matching, tracker endpoints, and role-oriented endpoints.
- PostgreSQL-oriented SQL migration contract plus dependency-light local demo behavior.
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

Optional PostgreSQL:

```bash
docker compose up -d postgres
psql postgresql://iaq:iaq@localhost:5432/iaq -f backend/migrations/001_initial.sql
```

The frontend connects to the backend for randomized question sessions. If the API is unavailable, it falls back to the small local demo set so the interface remains previewable. Configure `VITE_API_BASE_URL` when connecting the UI to a different service.

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

Production must replace demo mode with token validation and server-side role checks. No demo credentials should be used for real student data.

## Scientific boundary

Question candidates and synthetic responses can help test software. They cannot establish difficulty, discrimination, fairness, reliability, predictive validity, or population norms. Real pilot data and psychometric review are required before making stronger claims. See [docs/PILOT_PLAN.md](docs/PILOT_PLAN.md) and [docs/SCORING_V1.md](docs/SCORING_V1.md).
