# Supabase Auth setup

Status: interface prepared; live Supabase is not configured in this repository.

1. Create separate Supabase projects for local/staging/production.
2. Enable Google and email OTP providers.
3. Configure the callback URL as `/auth/callback` on each approved origin.
4. Set `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `SUPABASE_URL`, `SUPABASE_JWKS_URL`, and `SUPABASE_JWT_AUDIENCE`.
5. Keep the service-role key server-side only.
6. Map the Supabase `auth.users.id` to `users.id` and assign roles through an invite/admin workflow.

Google should request only `openid`, `email`, and `profile`. PKCE and redirect allowlisting must be enabled before staging. Local development can continue with the explicit dev provider.
