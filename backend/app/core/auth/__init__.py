"""Authentication layer.

Production authentication is owned **entirely by Supabase Auth**:

* The browser signs in against Supabase (anonymous key).
* The backend verifies the returned JWT against Supabase's JWKS.
* The backend never sees, stores or hashes a password.

The backend adds what the auth provider cannot do for a clinic: a server-side
registry of live sessions so access can be terminated immediately, and a link
between the Supabase identity and the clinic's own staff record (which carries
the role).

Everything in this package is provider-agnostic behind :class:`TokenVerifier`,
so the test-suite can inject a deterministic verifier without adding a
"development backdoor" to the production code path.
"""

from app.core.auth.base import AuthenticatedUser, TokenVerifier
from app.core.auth.supabase import SupabaseAdminClient, SupabaseJWTVerifier

__all__ = [
    "AuthenticatedUser",
    "SupabaseAdminClient",
    "SupabaseJWTVerifier",
    "TokenVerifier",
]
