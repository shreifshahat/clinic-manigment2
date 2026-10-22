"""Factory that selects the token verifier for the running environment.

Production: Supabase Auth (JWKS).
Development / test: a deterministic local verifier (see ``app.core.auth.dev``).

The choice is made once at start-up and can be overridden per request in tests
through FastAPI's dependency overrides.
"""

from __future__ import annotations

from app.core.auth.base import TokenVerifier
from app.core.auth.dev import DevTokenVerifier
from app.core.auth.supabase import SupabaseJWTVerifier
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger("clinic.auth.factory")

_verifier: TokenVerifier | None = None
_dev_verifier: DevTokenVerifier | None = None


def build_verifier(settings: Settings) -> TokenVerifier:
    """Create the verifier for the configured environment."""
    if settings.supabase_url and settings.jwks_url:
        audiences = ["authenticated"]
        project_ref = settings.supabase_url.rstrip("/").rsplit(".", 1)[-1]
        if project_ref:
            audiences.append(project_ref)
        return SupabaseJWTVerifier(
            settings.jwks_url,
            audience=audiences,
            issuer=settings.supabase_auth_url or None,
        )

    if settings.env not in {"local", "test"}:
        raise RuntimeError(
            "SUPABASE_URL must be configured outside local/test; "
            "development authentication is not permitted there."
        )

    if not settings.dev_auth_enabled:
        raise RuntimeError(
            "No Supabase configuration found. Set SUPABASE_URL, or set "
            "DEV_AUTH_ENABLED=true together with DEV_AUTH_SECRET for local use."
        )

    secret = settings.dev_auth_secret
    if not secret:
        raise RuntimeError(
            "DEV_AUTH_ENABLED is set but DEV_AUTH_SECRET is missing."
        )
    logger.warning(
        "using development authentication - not suitable for production",
        extra={"env": settings.env},
    )
    dev = DevTokenVerifier(secret, env=settings.env)
    globals()["_dev_verifier"] = dev
    return dev


def get_verifier() -> TokenVerifier:
    global _verifier
    if _verifier is None:
        _verifier = build_verifier(get_settings())
    return _verifier


def get_dev_verifier() -> DevTokenVerifier | None:
    """Return the development verifier, building it on first use.

    Building it on demand matters: the development sign-in endpoint is often
    the very first request the server receives, so the verifier must not
    depend on another endpoint having been called first.
    """
    global _dev_verifier
    if _dev_verifier is None:
        try:
            get_verifier()
        except RuntimeError:
            return None
    return _dev_verifier


def reset_verifier() -> None:
    """Used by tests to rebuild the verifier with different settings."""
    global _verifier, _dev_verifier
    _verifier = None
    _dev_verifier = None
