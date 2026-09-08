# Deployment

## Local

Run `npm install && npm run dev` for the frontend and `uvicorn app.main:app --reload --port 8000` from `backend/` for the API. `docker compose up -d postgres` starts a local Postgres service.

## Production checklist

- Use Python 3.12, a managed PostgreSQL instance, Alembic migrations, and a secret manager.
- Set `IAQ_ENV=production`, `IAQ_REQUIRE_PERSISTENCE=true`, and `IAQ_REQUIRE_REVIEWED_ITEMS=true`. The API will refuse to create student sessions when these release gates are not satisfied.
- Set `IAQ_ACCESS_STORE=postgres` only after the order, entitlement, guardian-consent, and review repositories are wired to the migration tables. The current local access repository remains memory-backed and `/ready` reports it as a production blocker.
- Replace `development_demo` auth with verified JWTs and server-side role checks.
- Configure `IAQ_AUTH_MODE=supabase`, `SUPABASE_URL` or `SUPABASE_JWKS_URL`, and server-managed roles in Supabase `app_metadata`. Never accept role claims from untrusted user metadata in a production provisioning flow.
- Restrict CORS to deployed origins and enforce TLS.
- Set `IAQ_ALLOWED_ORIGINS` to the exact frontend origin; development localhost origins are not implicitly allowed in production.
- Configure Midtrans production keys and enable `MIDTRANS_IS_PRODUCTION=true` plus `MIDTRANS_LIVE_ENABLED=true` only after merchant verification, refund rehearsal, privacy review, and signed-notification tests.
- Configure Resend with `RESEND_API_KEY`, a verified `EMAIL_FROM_ADDRESS`, and a real `APP_BASE_URL`. Delivery is idempotent by result/email and remains private to the result owner.
- Add structured JSON logs without raw personal data.
- Add rate limits to auth, response, export, deletion, and report endpoints.
- Configure backups, retention, deletion workflows, audit review, and monitoring.
- Keep LLM narrative disabled unless an approved provider, minimized payload, schema validation, and fallback template are configured.

The current FastAPI access/commerce repositories are still dependency-light local repositories. Migration `009_dataset_and_release_readiness.sql` defines the production tables, but a production deployment must complete the repository adapters for orders, entitlements, guardian consent, and admin review before accepting real users. `/ready` is the final preflight check; it is not a substitute for security, privacy, merchant, or psychometric sign-off.
