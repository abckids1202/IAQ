"""Minimal Supabase JWT validation boundary.

Development auth remains available only when IAQ_AUTH_MODE=development. In
Supabase mode, an absent or invalid bearer token is a hard authentication
failure and never falls back to the demo student.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict


class SupabaseAuthError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _jwks_client():
    try:
        from jwt import PyJWKClient
    except ImportError as error:
        raise SupabaseAuthError("PyJWT is required when IAQ_AUTH_MODE=supabase") from error
    jwks_url = os.getenv("SUPABASE_JWKS_URL", "").strip()
    if not jwks_url:
        supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json" if supabase_url else ""
    if not jwks_url:
        raise SupabaseAuthError("SUPABASE_JWKS_URL or SUPABASE_URL must be configured")
    return PyJWKClient(jwks_url)


def user_from_token(token: str) -> Dict[str, Any]:
    if not token:
        raise SupabaseAuthError("A Supabase access token is required")
    try:
        import jwt
        signing_key = _jwks_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, signing_key, algorithms=["RS256", "ES256"], audience=os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated"))
    except Exception as error:
        raise SupabaseAuthError("The Supabase access token is invalid or expired") from error
    subject = str(claims.get("sub", "")).strip()
    if not subject:
        raise SupabaseAuthError("The Supabase token has no subject")
    user_metadata = claims.get("user_metadata") or {}
    app_metadata = claims.get("app_metadata") or {}
    allowed_roles = {"student", "guardian", "counselor", "school_admin", "content_reviewer", "platform_admin"}
    # Roles are authorization data. Only server-managed app_metadata is
    # trusted; user-editable metadata must never be able to grant staff access.
    raw_roles = app_metadata.get("roles") or ["student"]
    roles = [role for role in raw_roles if role in allowed_roles] if isinstance(raw_roles, list) else ["student"]
    return {
        "id": subject,
        "email": str(claims.get("email", "")).lower(),
        "display_name": str(user_metadata.get("display_name") or claims.get("email", "IAQ student")).strip(),
        "roles": roles or ["student"],
        "account_status": "active",
        "age_band": str(user_metadata.get("age_band", "unknown")),
        "school_id": user_metadata.get("school_id"),
        "mfa_verified": bool(claims.get("aal") in {"aal2", "aal3"}),
        "provider": "supabase",
    }
