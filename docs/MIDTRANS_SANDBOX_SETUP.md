# Midtrans Sandbox setup

Status: notification verification and checkout state contract are prepared; no merchant credentials are committed.

Deprecated: IAQ no longer uses Midtrans for checkout or entitlement fulfillment. The current release uses manually reviewed BCA QRIS payment proofs. Keep this document only as historical migration context; `/payments/midtrans/notification` intentionally returns `410 Gone`.

The hosted Snap checkout must be used. IAQ must never receive raw card data.
