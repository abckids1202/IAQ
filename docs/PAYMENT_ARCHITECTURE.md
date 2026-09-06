# Payment architecture

V1 products are one-time IDR products. The browser sends only a product identifier. The backend loads the active database price, snapshots product/price data into the order, creates a payment attempt, and waits for a verified provider notification before fulfilling an entitlement.

`MockPaymentGateway` behavior is represented by `POST /payments/mock/{order_id}/settle` in development. Midtrans is provider-neutral at the API boundary and remains sandbox/configuration-gated. A browser success page never grants access. Duplicate and out-of-order events must be idempotent and obey state precedence.
