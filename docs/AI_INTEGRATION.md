# Optional AI integration

## Where to put the key

Create or edit:

```text
C:\Users\charl\OneDrive\Desktop\IAQ\.env
```

Add:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini
IAQ_AI_ENABLED=true
OPENAI_REQUEST_TIMEOUT_SECONDS=25
```

The root `.env` is ignored by Git. Never place the key in `VITE_OPENAI_API_KEY`, React code, local storage, a screenshot, or a GitHub commit. The backend loads it at startup and the frontend talks only to IAQ endpoints.

## What the AI is allowed to do

- Explain an already-persisted provisional result in student-friendly language.
- Describe what stands out, where more evidence is needed, timing context, and one practical next step.
- Add tentative explanations and small experiments to deterministic direction candidates.

## What it is not allowed to do

- Score answers or access answer keys.
- Change a score, confidence value, question lifecycle, entitlement, or deterministic fit.
- Produce percentiles, diagnoses, official IQ claims, or guaranteed career outcomes.
- Receive report-recipient names/emails or raw response-level secrets.
- Persist an AI narrative until real user-ID propagation and retention controls are complete.

The backend marks returned outputs `data_origin=AI_ASSISTED`, pins a prompt version, validates JSON, whitelists candidate direction slugs, uses `store=False` on Responses API calls, and caches results by a deterministic input hash. When Postgres is configured, the same versioned output is stored in `ai_result_outputs`; local development keeps the cache process-local.

## Endpoints

- `GET /ai/status` — safe capability status; never returns the key.
- `POST /ai/results/{result_id}/interpretation` — optional report explanation after ownership checks.
- `POST /ai/directions` — optional direction context using the existing result, interests, and deterministic candidate list.

If the key is absent, the API returns `503` for AI requests while the rest of IAQ remains usable. A provider error or malformed response is surfaced as an operational error, not converted into a score.

## Before production

Add real authenticated user IDs to every session/result query, rate-limit AI endpoints, add consent and retention controls for AI processing, store provider request IDs without prompts, monitor cost and latency, run prompt/output evaluations, and review minor-safety/privacy terms. Pin a model snapshot when output stability matters; model behavior can change between snapshots.
