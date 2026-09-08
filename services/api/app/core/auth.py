"""Verifies Clerk session tokens sent by the dashboard as `Authorization: Bearer <jwt>`.
Clerk signs these RS256 with a key published at CLERK_JWKS_URL — we verify the signature
and hand back the `sub` claim (Clerk's user id), which every bot-scoped route uses to
enforce ownership. No cookies, no session store on our side — this API stays stateless.
"""

from __future__ import annotations

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from app.core.config import get_settings

_jwks_client: PyJWKClient | None = None


class AuthError(HTTPException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status_code=401, detail=detail)


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        if not settings.clerk_jwks_url:
            raise RuntimeError("CLERK_JWKS_URL is not set.")
        _jwks_client = PyJWKClient(settings.clerk_jwks_url)
    return _jwks_client


async def get_current_clerk_user_id(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency. Raises 401 on any missing/invalid/expired token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError("Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk session tokens don't set aud
        )
    except jwt.PyJWTError as exc:
        raise AuthError(f"Invalid token: {exc}") from exc

    sub = payload.get("sub")
    if not sub:
        raise AuthError("Token missing sub claim")
    return sub
