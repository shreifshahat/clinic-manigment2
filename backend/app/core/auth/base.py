"""Auth abstractions shared by the Supabase verifier and the test doubles."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """The identity proven by a bearer token (no clinic role yet)."""

    auth_user_id: str
    email: str
    token_fingerprint: str
    session_id: str | None = None
    expires_at: datetime | None = None
    claims: dict[str, Any] = field(default_factory=dict, repr=False)


def fingerprint_token(token: str) -> str:
    """Stable, non-reversible identifier for an access token.

    Used to terminate a specific session without storing the token itself.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@runtime_checkable
class TokenVerifier(Protocol):
    """Turns a bearer token into a proven identity."""

    async def verify(self, token: str) -> AuthenticatedUser:  # pragma: no cover - protocol
        ...

    async def close(self) -> None:  # pragma: no cover - protocol
        ...
