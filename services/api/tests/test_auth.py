"""Unit tests for app/core/auth.py. Verifies real JWT signature checking using a
locally-generated RSA keypair — no network call to Clerk's JWKS endpoint, so this stays a
fast, offline unit test while still exercising the actual verification logic.
"""

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import app.core.auth as auth_module
from app.core.auth import AuthError, get_current_clerk_user_id


def _make_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJWKSClient:
    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey(self._public_key)


async def test_missing_header_raises_401():
    with pytest.raises(AuthError) as exc_info:
        await get_current_clerk_user_id(authorization=None)
    assert exc_info.value.status_code == 401


async def test_non_bearer_header_raises_401():
    with pytest.raises(AuthError):
        await get_current_clerk_user_id(authorization="Basic dXNlcjpwYXNz")


async def test_valid_token_returns_sub(monkeypatch):
    private_key, public_key = _make_keypair()
    monkeypatch.setattr(auth_module, "_get_jwks_client", lambda: _FakeJWKSClient(public_key))

    token = jwt.encode({"sub": "user_abc123"}, private_key, algorithm="RS256")
    user_id = await get_current_clerk_user_id(authorization=f"Bearer {token}")
    assert user_id == "user_abc123"


async def test_token_signed_by_wrong_key_is_rejected(monkeypatch):
    _, real_public_key = _make_keypair()
    attacker_private_key, _ = _make_keypair()
    monkeypatch.setattr(auth_module, "_get_jwks_client", lambda: _FakeJWKSClient(real_public_key))

    forged_token = jwt.encode({"sub": "user_abc123"}, attacker_private_key, algorithm="RS256")
    with pytest.raises(AuthError):
        await get_current_clerk_user_id(authorization=f"Bearer {forged_token}")


async def test_token_missing_sub_claim_is_rejected(monkeypatch):
    private_key, public_key = _make_keypair()
    monkeypatch.setattr(auth_module, "_get_jwks_client", lambda: _FakeJWKSClient(public_key))

    token = jwt.encode({"not_sub": "whatever"}, private_key, algorithm="RS256")
    with pytest.raises(AuthError):
        await get_current_clerk_user_id(authorization=f"Bearer {token}")
