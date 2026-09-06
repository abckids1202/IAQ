# Payment security

Authoritative totals, beneficiary relationships, order state, and entitlements are server-side. Amounts use integer minor units. Notification signatures, order references, amount, currency, merchant environment, status, and fraud status must be checked. Events are recorded with processing status and handled idempotently. Secrets and raw card data are not stored or logged.
