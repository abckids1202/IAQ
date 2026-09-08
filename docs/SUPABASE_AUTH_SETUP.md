# Supabase Auth setup

Status: interface prepared; live Supabase is not configured in this repository.

1. Create separate Supabase projects for local/staging/production.
2. Enable Google and email OTP providers.
3. Configure the callback URL as `/auth/callback` on each approved origin. The frontend uses a PKCE verifier for Google OAuth and does not store a client secret.
4. Set `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `SUPABASE_URL`, `SUPABASE_JWKS_URL`, and `SUPABASE_JWT_AUDIENCE`.
5. Keep the service-role key server-side only.
6. Map the Supabase `auth.users.id` to `users.id` and assign roles through an invite/admin workflow.

Google should request only `openid`, `email`, and `profile`. Redirect allowlisting must be exact before staging. Local development can continue with the explicit dev provider. The browser stores only the short-lived Supabase access token; IAQ API requests send it to the server for JWT and role validation.
