"""Integration tests for /bots — runs against the real (dev) Atlas cluster, since
ownership filtering baked into Mongo queries is exactly what's under test. clerk_user_id is
supplied via FastAPI dependency_overrides (standard pattern), not a real Clerk token —
app/core/auth.py itself is unit-tested separately in test_auth.py.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_clerk_user_id
from app.main import app
from tests.integration_helpers import purge_test_data, reset_db_client

USER_A = "pytest_bots_user_a"
USER_B = "pytest_bots_user_b"


@pytest.fixture(autouse=True)
async def _clean():
    reset_db_client()
    await purge_test_data()
    yield
    await purge_test_data()
    app.dependency_overrides.pop(get_current_clerk_user_id, None)


def _client_as(clerk_user_id: str) -> AsyncClient:
    app.dependency_overrides[get_current_clerk_user_id] = lambda: clerk_user_id
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_create_and_list_bot():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "Support Bot"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Support Bot"
        assert body["site_key"].startswith("sk_pub_")
        assert body["config"]["model_tier"] == "haiku"

        resp = await client.get("/bots")
        assert resp.status_code == 200
        assert [b["name"] for b in resp.json()] == ["Support Bot"]


async def test_get_nonexistent_bot_returns_404():
    async with _client_as(USER_A) as client:
        resp = await client.get("/bots/000000000000000000000000")
        assert resp.status_code == 404


async def test_delete_bot():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "Temp"})
        bot_id = resp.json()["id"]

        resp = await client.delete(f"/bots/{bot_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/bots/{bot_id}")
        assert resp.status_code == 404


async def test_bots_are_scoped_to_owner():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "Mine"})
        bot_id = resp.json()["id"]

    async with _client_as(USER_B) as client:
        resp = await client.get(f"/bots/{bot_id}")
        assert resp.status_code == 404

        resp = await client.get("/bots")
        assert resp.json() == []


async def test_missing_auth_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/bots")
    assert resp.status_code == 401
