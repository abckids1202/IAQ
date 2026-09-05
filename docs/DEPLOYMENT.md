# Deployment

## Local

Run `npm install && npm run dev` for the frontend and `uvicorn app.main:app --reload --port 8000` from `backend/` for the API. `docker compose up -d postgres` starts a local Postgres service.

## Production checklist

- Use Python 3.12, a managed PostgreSQL instance, Alembic migrations, and a secret manager.
- Replace `development_demo` auth with verified JWTs and server-side role checks.
- Restrict CORS to deployed origins and enforce TLS.
- Add structured JSON logs without raw personal data.
- Add rate limits to auth, response, export, deletion, and report endpoints.
- Configure backups, retention, deletion workflows, audit review, and monitoring.
- Keep LLM narrative disabled unless an approved provider, minimized payload, schema validation, and fallback template are configured.

The current FastAPI store is a dependency-light demo boundary, not the production persistence implementation.
