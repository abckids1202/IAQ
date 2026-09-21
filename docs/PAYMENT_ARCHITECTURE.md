# Payment architecture

V1 products are one-time IDR products. The browser sends only a product identifier. The backend loads the active database price, snapshots product/price data into the order, creates a payment attempt, and waits for a verified provider notification before fulfilling an entitlement.

Manual BCA QRIS is the production pilot path: a student submits proof, and an authorized admin approves it before entitlement creation. `POST /payments/mock/{order_id}/settle` remains only as a development test shortcut. A browser success page never grants access. Duplicate submissions and approvals must be idempotent and obey state precedence.
