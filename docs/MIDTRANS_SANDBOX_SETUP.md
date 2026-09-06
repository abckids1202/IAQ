# Midtrans Sandbox setup

Status: notification verification and checkout state contract are prepared; no merchant credentials are committed.

Set `MIDTRANS_SERVER_KEY`, `MIDTRANS_MERCHANT_ID`, `MIDTRANS_IS_PRODUCTION=false`, `MIDTRANS_SANDBOX_ONLY=true`, and the public `WEBHOOK_BASE_URL`. Configure the Midtrans notification URL to `/payments/midtrans/notification`. Test settlement, pending, expire, cancel, amount mismatch, invalid signature, duplicate, and out-of-order notifications.

The hosted Snap checkout must be used. IAQ must never receive raw card data.
