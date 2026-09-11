# API contract

The service exposes resource-oriented endpoints for `/assessments`, `/sessions`, `/results`, `/questionnaires`, `/majors`, `/recommendations`, `/ai`, `/certificates`, `/tracker`, `/counselor`, and `/admin`.

`POST /assessments/iaq-cognitive/sessions` defaults to `mode=complete` and creates a balanced randomized form from the 840-item bank: 56 questions, 8 from each domain, with no repeats. `mode=quick` creates 14 questions, 2 from each domain. `GET /assessments` reports the bank and form sizes, and `GET /admin/question-bank/summary` reports safe counts and readiness metadata.

Responses use consistent HTTP errors. `POST /sessions/:id/responses` accepts `Idempotency-Key`, validates the item server-side, stores `data_origin`, and never returns the answer key. `POST /sessions/:id/submit` creates a result with assessment, scoring, confidence, quality, and disclaimer metadata.

The first visit is public and unsigned-in. `POST /auth/guest` creates a limited browser-scoped guest identity with free assessment access; it cannot create orders or access paid report/direction features. Email OTP promotes a new or returning student to an account. With `IAQ_ASSESSMENT_SOURCE=staged` and `IAQ_ALLOW_STAGED_ITEMS=true` in local development, sessions use the same imported Dataset Lab records and assets; those QA sessions/results remain process-local because their external item IDs are not yet in the authored Postgres item tables. Production must validate Supabase tokens, enforce role permissions, link any guest result to the signed-in account, and persist through the migration contract before enabling guest assessment access publicly.

Optional AI endpoints never return answer keys and never write score fields. They require an owned result, use the configured server-side OpenAI adapter, mark output as `AI_ASSISTED`, and return `503` when `OPENAI_API_KEY` is not configured.
# Access and commerce workflow

The local development workflow exposes these provider-neutral endpoints:

- `POST /auth/dev/login`, `POST /auth/otp/request`, `POST /auth/otp/verify`, `POST /auth/logout`
- `GET /me`, `/me/roles`, `/me/permissions`, `/me/entitlements`, `/me/orders`
- `GET /products`, `GET /products/{product_id}`
- `POST /orders`, `GET /orders/{order_id}`, `POST /orders/{order_id}/checkout`, `GET /orders/{order_id}/status`
- `POST /payments/mock/{order_id}/settle` (development only)
- `POST /payments/midtrans/notification` (requires a configured server key and signature validation)
- `GET /schools/{school_id}/seats`, `POST /schools/{school_id}/seats/allocate`

The browser supplies only a product identifier and optional verified beneficiary. The backend snapshots the active price and creates an order. A payment success redirect does not grant access; only a verified settlement fulfills the order and creates an entitlement.
