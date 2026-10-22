"""Development-only token issuer.

Purpose: let the application be run and demoed end-to-end **without** a
Supabase project, and let the test-suite exercise the real request pipeline
(verify token → resolve staff → apply RLS context) with deterministic
identities.

Safety rules (all enforced, not just documented):

* The provider refuses to initialise when ``ENV=production``.
* It only issues tokens for staff rows that already exist; it cannot create
  accounts and it does not store or check passwords.
* The issuing endpoint is mounted **only** when ``DEV_AUTH_ENABLED=true``.
* Every issued token is short-lived and signed with ``DEV_AUTH_SECRET``.

This is a development affordance, not an authentication system: production
authentication is Supabase Auth only.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.auth.base import AuthenticatedUser, fingerprint_token
from app.core.errors import InvalidTokenError
from app.core.logging import get_logger

logger = get_logger("clinic.auth.dev")


class DevAuthDisabledError(RuntimeError):
    """Raised when development authentication is used in a non-dev environment."""


class DevTokenVerifier:
    """Verify (and mint) short-lived HS256 development tokens."""

    def __init__(self, secret: str, *, env: str, ttl_minutes: int = 60) -> None:
        if env not in {"local", "test"}:
            # A staging deployment must never fall back to development tokens:
            # anyone knowing the secret would get a full account.
            raise DevAuthDisabledError(
                f"Development authentication is not allowed in the '{env}' environment."
            )
        if len(secret) < 32:
            raise DevAuthDisabledError(
                "DEV_AUTH_SECRET must be at least 32 characters long."
            )
        self._secret = secret
        self._ttl_minutes = ttl_minutes

    def issue(
        self,
        *,
        auth_user_id: str,
        email: str,
        ttl_minutes: int | None = None,
        extra_claims: dict[str, object] | None = None,
    ) -> str:
        now = datetime.now(UTC)
        expires = now + timedelta(minutes=ttl_minutes or self._ttl_minutes)
        payload: dict[str, object] = {
            "sub": auth_user_id,
            "email": email,
            "role": "authenticated",
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "session_id": str(uuid.uuid4()),
            "dev": True,
        }
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, self._secret, algorithm="HS256")

    async def verify(self, token: str) -> AuthenticatedUser:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
                leeway=5,
            )
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError("رمز الدخول غير صالح.") from exc
        subject = claims.get("sub")
        if not subject:
            raise InvalidTokenError("رمز الدخول لا يحمل هوية مستخدم.")
        return AuthenticatedUser(
            auth_user_id=str(subject),
            email=str(claims.get("email") or ""),
            token_fingerprint=fingerprint_token(token),
            session_id=claims.get("session_id"),
            expires_at=(
                datetime.fromtimestamp(claims["exp"], tz=UTC) if claims.get("exp") else None
            ),
            claims=claims,
        )

    async def close(self) -> None:
        return None
