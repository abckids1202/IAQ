# IAQ private-pilot runbook

This repository is ready for a local private pilot, but it is not a public launch. The score is a provisional IAQ Cognitive Profile, not an official IQ score, diagnosis, percentile, or selection tool.

## Start locally

From `C:\Users\charl\OneDrive\Desktop\IAQ`:

```powershell
npm.cmd install
python -m pip install -r backend/requirements.txt

# terminal 1
cd backend
python -m uvicorn app.main:app --reload --port 8000

# terminal 2
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. Development sign-in is available at `/auth/login`; it is deliberately not production authentication.

## Server-only OpenAI configuration

Copy `.env.example` to a root `.env` and set:

```dotenv
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini
IAQ_AI_ENABLED=true
```

The key belongs in the backend/deployment environment only. Do not use `VITE_OPENAI_API_KEY`, do not put the key in React code, local storage, screenshots, or Git. The backend sends only aggregate scores, quality/timing summaries, curated direction candidates, and the interest check-in. OpenAI output is optional, cached by an input hash, labeled `AI_ASSISTED`, and cannot change scoring or activate content.

## Pilot question-bank gate

The local preview currently contains 120 candidates per domain: 20 original pilot-baseline items and 100 deterministic generated candidates. Generated candidates are marked `AUTO_VERIFIED` in the authoritative lifecycle and are not human-reviewed production content.

Before a real pilot, complete two independent reviews for at least 100 items per domain, then enable:

```dotenv
IAQ_REQUIRE_REVIEWED_ITEMS=true
```

With that flag enabled, the API refuses forms until the review gate is met. The default local preview may use the legacy `status=PILOT` compatibility flag so the 56-question UI can be exercised before the review queue is complete; this fallback must not be used for real student data.

Run the seed idempotently after applying migrations:

```powershell
cd backend
python -m app.seed
```

The seed reports candidate counts, reviewed counts, and whether the 100-per-domain gate is ready. It does not turn generated content into `ACTIVE` content.

## Payment, email, and minors

- Payment defaults to mock settlement. Midtrans is configuration-gated and should remain sandbox-only until merchant verification, amount/signature/replay tests, refunds, and webhook rehearsal are complete.
- Email defaults to a development queue. Add `RESEND_API_KEY` only in a controlled environment and keep report delivery idempotent.
- Ages 15–17 require a guardian email and a separate consent record before minor report delivery. Legal policy and operational review are still required before collecting real minor data.
- Keep report visibility private. Do not create public result links or public score cards.

## Production checklist

Before production, configure separate Supabase projects for local/staging/production, use `IAQ_AUTH_MODE=supabase`, run the migrations against Postgres, connect Vercel to the frontend and Render to the API, configure Resend and Midtrans, add monitoring and deletion/de-identification jobs, rehearse incident response, and complete privacy/legal review.

The current implementation intentionally leaves the following as release gates: 100 reviewed eligible items per domain, real 200–500 participant pilot data, psychometric review, live provider credentials, production authentication, guardian policy approval, payment reconciliation, and security review.
