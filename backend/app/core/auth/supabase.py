"""Supabase Auth integration.

Two responsibilities:

* :class:`SupabaseJWTVerifier` — verify an access token issued by Supabase
  against the project's JWKS (asymmetric keys: the backend never holds a
  signing secret).
* :class:`SupabaseAdminClient` — the *only* place allowed to use the
  ``service_role`` key. It is used by the staff-management service to create
  accounts and reset passwords. The key is read from the environment and is
  never returned to the browser.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import httpx
import jwt
from jwt import PyJWKClient, PyJWKClientError

from app.core.auth.base import AuthenticatedUser, fingerprint_token
from app.core.errors import InvalidTokenError
from app.core.logging import get_logger

logger = get_logger("clinic.auth")

_JWKS_REFRESH_SECONDS = 300


class SupabaseJWTVerifier:
    """Verify Supabase-issued access tokens (RS256 / ES256)."""

    def __init__(
        self,
        jwks_url: str,
        *,
        audience: list[str] | None = None,
        issuer: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        if not jwks_url:
            raise ValueError("jwks_url is required")
        self._jwks_url = jwks_url
        self._audience = audience or []
        self._issuer = issuer
        self._timeout = timeout
        self._jwk_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=_JWKS_REFRESH_SECONDS)
        self._last_refresh = 0.0

    async def verify(self, token: str) -> AuthenticatedUser:
        if not token:
            raise InvalidTokenError()
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token)
        except PyJWKClientError:
            # The signing key may have been rotated: force a refresh once.
            self._jwk_client = PyJWKClient(
                self._jwks_url, cache_keys=True, lifespan=_JWKS_REFRESH_SECONDS
            )
            try:
                signing_key = self._jwk_client.get_signing_key_from_jwt(token)
            except PyJWKClientError as exc:
                raise InvalidTokenError("تعذّر التحقق من رمز الدخول.") from exc

        options: dict[str, Any] = {}  # forwarded to jwt.decode
        if self._audience:
            options["audience"] = self._audience
        else:
            options["verify_aud"] = False
        if self._issuer:
            options["issuer"] = self._issuer

        try:
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                options=cast(Any, options),
                leeway=5,
            )
        except jwt.ExpiredSignatureError as exc:
            raise InvalidTokenError("انتهت صلاحية رمز الدخول.") from exc
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


class SupabaseAdminClient:
    """Thin async wrapper over the Supabase Auth Admin API."""

    def __init__(
        self,
        base_url: str,
        service_role_key: str,
        *,
        timeout: float = 15.0,
    ) -> None:
        if not base_url or not service_role_key:
            raise ValueError("Supabase admin client requires base_url and service_role_key")
        self._base_url = base_url.rstrip("/")
        self._service_role_key = service_role_key
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
                "Content-Type": "application/json",
            },
        )

    async def create_user(
        self,
        *,
        email: str,
        password: str | None,
        email_confirm: bool = True,
        user_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"email": email, "email_confirm": email_confirm}
        if password is not None:
            body["password"] = password
        if user_metadata:
            body["user_metadata"] = user_metadata
        return await self._request("POST", "/admin/users", json=body)

    async def invite_user(self, email: str, redirect_to: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"email": email}
        if redirect_to:
            body["redirect_to"] = redirect_to
        return await self._request("POST", "/invite", json=body)

    async def update_user(self, user_id: str, **fields: Any) -> dict[str, Any]:
        return await self._request("PUT", f"/admin/users/{user_id}", json=fields)

    async def delete_user(self, user_id: str) -> None:
        await self._request("DELETE", f"/admin/users/{user_id}")

    async def get_user(self, user_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/admin/users/{user_id}")

    async def verify_password(self, email: str, password: str) -> bool:
        """Check a password against the auth provider (used on password change).

        The provider has no "verify only" endpoint, so we use the sign-in
        endpoint and immediately revoke the session it creates — otherwise every
        password-change attempt would leave an extra live session behind.
        """
        try:
            response = await self._client.post(
                "/token?grant_type=password",
                json={"email": email, "password": password},
            )
        except httpx.HTTPError:
            return False
        if response.status_code != 200:
            return False
        try:
            payload = response.json()
        except ValueError:
            return True
        refresh_token = payload.get("refresh_token") if isinstance(payload, dict) else None
        if refresh_token:
            await self.revoke_refresh_token(str(refresh_token))
        return True

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """Revoke a single refresh token (and the session behind it)."""
        try:
            await self._client.post(
                "/logout",
                headers={
                    "apikey": self._service_role_key,
                    "Authorization": f"Bearer {self._service_role_key}",
                },
                json={"refresh_token": refresh_token},
            )
        except httpx.HTTPError:  # pragma: no cover - best effort
            logger.warning("supabase refresh token revocation failed")

    async def logout_user_session(self, access_token: str) -> bool:
        """Invalidate the provider session behind an access token.

        Used by ``POST /auth/logout`` so that the *refresh* token dies with the
        session instead of silently re-minting a new access token.
        """
        if not access_token:
            return False
        try:
            response = await self._client.post(
                "/logout",
                headers={
                    "apikey": self._service_role_key,
                    "Authorization": f"Bearer {access_token}",
                },
            )
        except httpx.HTTPError:
            return False
        return response.status_code < 400

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            # Log the status only: the body may contain an email address.
            logger.warning(
                "supabase admin request failed",
                extra={"method": method, "path": path, "status": response.status_code},
            )
            raise SupabaseAdminError(
                f"Supabase admin request failed with status {response.status_code}"
            )
        if not response.content:
            return {}
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()


class SupabaseAdminError(RuntimeError):
    """Raised when the Supabase Admin API rejects a request."""
