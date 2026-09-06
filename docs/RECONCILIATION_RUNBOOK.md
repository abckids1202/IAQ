# Reconciliation runbook

The reconciliation job should report: paid orders without active entitlements, active entitlements without a valid source, repeatedly failed payment events, stale pending payments, and refunded orders with active access. Resolve by replaying a verified event, revoking an invalid entitlement with a reason, or escalating to the merchant/provider. Never rewrite transaction history.
