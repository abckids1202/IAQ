# Google OAuth setup

Create a separate OAuth web client for each environment. Register only the exact Supabase callback URL and application origin required by that environment. Do not request Drive, Calendar, Classroom, Gmail, or other scopes.

Required manual configuration: Google Cloud consent screen, authorized redirect URIs in Supabase, and `AUTH_GOOGLE_ENABLED=true` only after the callback is tested. Never commit client secrets. An unsafe `returnTo` must be rejected; only internal paths or configured origins are accepted.
