# API contract

The service exposes resource-oriented endpoints for `/assessments`, `/sessions`, `/results`, `/questionnaires`, `/majors`, `/recommendations`, `/tracker`, `/counselor`, and `/admin`.

Responses use consistent HTTP errors. `POST /sessions/:id/responses` accepts `Idempotency-Key`, validates the item server-side, stores `data_origin`, and never returns the answer key. `POST /sessions/:id/submit` creates a result with assessment, scoring, confidence, quality, and disclaimer metadata.

This local baseline uses demo identity. Production must validate tokens, enforce role permissions, and persist through the migration contract.
