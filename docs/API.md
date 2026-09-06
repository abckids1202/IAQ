# API contract

The service exposes resource-oriented endpoints for `/assessments`, `/sessions`, `/results`, `/questionnaires`, `/majors`, `/recommendations`, `/tracker`, `/counselor`, and `/admin`.

`POST /assessments/iaq-cognitive/sessions` defaults to `mode=complete` and creates a balanced randomized form from the 840-item bank: 56 questions, 8 from each domain, with no repeats. `mode=quick` creates 14 questions, 2 from each domain. `GET /assessments` reports the bank and form sizes, and `GET /admin/question-bank/summary` reports safe counts and readiness metadata.

Responses use consistent HTTP errors. `POST /sessions/:id/responses` accepts `Idempotency-Key`, validates the item server-side, stores `data_origin`, and never returns the answer key. `POST /sessions/:id/submit` creates a result with assessment, scoring, confidence, quality, and disclaimer metadata.

This local baseline uses demo identity. Production must validate tokens, enforce role permissions, and persist through the migration contract.
