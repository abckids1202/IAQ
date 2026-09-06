# Entitlement model

Entitlements are explicit records such as `assessment.complete.start`, `assessment.complete.report`, `assessment.retake`, `report.download`, and `school.seat.complete`. They have an owner, source, status, quantity, remaining quantity, and audit trail. A verified payment, approved school seat, or authorized manual grant can be a source. Refunded, revoked, expired, or consumed records do not grant access.

Consumable use must be checked and consumed in one database transaction with row locking in the PostgreSQL implementation.
