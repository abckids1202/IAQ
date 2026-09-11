# IAQ local accounts and guest testing

The local app now starts as a public, unsigned-in visitor. It must not silently
use the seeded student account.

## Guest smoke test

1. Start the API and frontend.
2. Open `http://127.0.0.1:5173/` in a fresh/private browser window.
3. Choose **Start test**. The browser receives an `iaq-guest-token` and the API
   creates a limited guest identity.
4. Choose an age band. Ages 18–22 can run the complete local pilot; ages 15–17
   are practice-only.
5. The profile menu shows **Guest / Not signed in** while the test is active.
6. After the result, submit the identity/consent card to promote the guest
   identity to a local student account. The API returns a development session
   token and the browser replaces the guest token with it.

Guest access is intentionally limited. It cannot create orders, unlock paid
reports, request directions, or use counselor/admin endpoints.

## Development test accounts

There are no passwords in the local provider. Open `/auth/login` and select an
account:

| Account | Email | Purpose |
| --- | --- | --- |
| Student preview | `student@iaq.local` | Student assessment, result, and sandbox purchase flow |
| Guardian preview | `guardian@iaq.local` | Dependent purchase and guardian-consent preview |
| Counselor preview | `counselor@iaq.local` | Assigned-student counselor workspace |
| School admin preview | `school-admin@iaq.local` | Seats and school administration preview |
| Platform admin preview | `admin@iaq.local` | Item review and protected administration preview |

## New student account

Use the email sign-in form on `/auth/login`:

1. Enter any test email, such as `qa-student+1@example.com`.
2. Select **Send me a code**.
3. Enter `123456` in development.
4. The API creates or reopens a student account with a free assessment start.

Use a different email for each isolated test account. These development users
are memory-backed and are not production identities.

## Production boundary

Render is configured for Supabase authentication and does not enable the local
development accounts. Do not put real personal data into the seeded accounts.
Before enabling `IAQ_GUEST_ASSESSMENT_ENABLED=true` in production, implement
durable guest-session storage and a secure guest-result-to-Supabase-account
linking flow. Otherwise a guest could lose a result on API restart.
