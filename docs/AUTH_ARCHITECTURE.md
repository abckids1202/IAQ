# Authentication and access architecture

IAQ separates four decisions: authentication (who is signed in), authorization (what their roles permit), payment (whether a provider verified an order), and entitlement (which feature the beneficiary may use).

The current local workflow uses an explicit development provider with seeded accounts. The first visit is public and unsigned-in; `POST /auth/guest` creates a short-lived browser-scoped guest token with assessment-only permissions. `POST /auth/dev/login` creates a development session token, while email OTP creates or reopens a student account. Tokens are sent as `X-IAQ-Session`; these local flows are not production authentication. A production adapter must validate Supabase JWTs server-side, link guest results to the signed-in account, and map the Supabase user UUID to the local `profiles` and `user_roles` records before enabling anonymous assessment access.

No browser claim, email address, payment-success URL, or `premium` flag grants access. The assessment service checks an active entitlement before creating a session. Staff routes additionally require the assigned role and AAL2/MFA state.

The development accounts are student, guardian, counselor, school admin, and platform admin. They exist only to exercise workflows locally.
