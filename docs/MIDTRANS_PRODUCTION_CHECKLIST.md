# Midtrans production checklist

Production is disabled by default. Before enabling it, verify merchant ownership, approved business identity, production keys, HTTPS webhook delivery, signature tests, amount/currency validation, event replay handling, refund rules, alerting, and a tested reconciliation run. Remove development auth and mock settlement. This requires a verified merchant/business owner; do not bypass Midtrans verification.
