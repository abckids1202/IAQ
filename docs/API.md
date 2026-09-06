# API contract

The service exposes resource-oriented endpoints for `/assessments`, `/sessions`, `/results`, `/questionnaires`, `/majors`, `/recommendations`, `/tracker`, `/counselor`, and `/admin`.

`POST /assessments/iaq-cognitive/sessions` defaults to `mode=complete` and creates a balanced randomized form from the 840-item bank: 56 questions, 8 from each domain, with no repeats. `mode=quick` creates 14 questions, 2 from each domain. `GET /assessments` reports the bank and form sizes, and `GET /admin/question-bank/summary` reports safe counts and readiness metadata.

Responses use consistent HTTP errors. `POST /sessions/:id/responses` accepts `Idempotency-Key`, validates the item server-side, stores `data_origin`, and never returns the answer key. `POST /sessions/:id/submit` creates a result with assessment, scoring, confidence, quality, and disclaimer metadata.

This local baseline uses demo identity. Production must validate tokens, enforce role permissions, and persist through the migration contract.
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
