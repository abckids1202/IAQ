# Authentication and access architecture

IAQ separates four decisions: authentication (who is signed in), authorization (what their roles permit), payment (whether a provider verified an order), and entitlement (which feature the beneficiary may use).

The current local workflow uses an explicit development provider with seeded accounts. `POST /auth/dev/login` creates a short-lived development session token. The token is sent as `X-IAQ-Session`; this is not production authentication. A production adapter must validate Supabase JWTs server-side and map the Supabase user UUID to the local `profiles` and `user_roles` records.

No browser claim, email address, payment-success URL, or `premium` flag grants access. The assessment service checks an active entitlement before creating a session. Staff routes additionally require the assigned role and AAL2/MFA state.

The development accounts are student, guardian, counselor, school admin, and platform admin. They exist only to exercise workflows locally.
