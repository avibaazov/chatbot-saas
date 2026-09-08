"""Integration tests for /bots — runs against the real (dev) Atlas cluster, since
ownership filtering baked into Mongo queries is exactly what's under test. clerk_user_id is
supplied via FastAPI dependency_overrides (standard pattern), not a real Clerk token —
app/core/auth.py itself is unit-tested separately in test_auth.py.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_clerk_user_id
from app.main import dashboard_app
from tests.integration_helpers import purge_test_data, reset_db_client

USER_A = "pytest_bots_user_a"
USER_B = "pytest_bots_user_b"

# Port 9 (discard) on loopback: connection is refused instantly, so the auto-ingestion
# kicked off by create_bot fails fast with no external network call. Bot creation still
# succeeds — the seed document just lands on status=failed.
WEBSITE_URL = "http://127.0.0.1:9/"


@pytest.fixture(autouse=True)
async def _clean():
    reset_db_client()
    await purge_test_data()
    yield
    await purge_test_data()
    dashboard_app.dependency_overrides.pop(get_current_clerk_user_id, None)


def _client_as(clerk_user_id: str) -> AsyncClient:
    dashboard_app.dependency_overrides[get_current_clerk_user_id] = lambda: clerk_user_id
    return AsyncClient(transport=ASGITransport(app=dashboard_app), base_url="http://test")


async def _create_bot(client: AsyncClient, name: str, website_url: str = WEBSITE_URL):
    return await client.post("/bots", json={"name": name, "website_url": website_url})


async def test_create_and_list_bot():
    async with _client_as(USER_A) as client:
        resp = await _create_bot(client, "Support Bot")
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Support Bot"
        assert body["website_url"] == WEBSITE_URL
        assert body["site_key"].startswith("sk_pub_")
        assert body["config"]["model_tier"] == "haiku"

        resp = await client.get("/bots")
        assert resp.status_code == 200
        assert [b["name"] for b in resp.json()] == ["Support Bot"]


async def test_create_bot_requires_a_website_url():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "No URL"})
        assert resp.status_code == 422  # missing required field

        resp = await client.post("/bots", json={"name": "Bad URL", "website_url": "not-a-url"})
        assert resp.status_code == 400


async def test_create_bot_seeds_allowed_domain_and_a_url_document():
    async with _client_as(USER_A) as client:
        resp = await _create_bot(client, "Seeded", website_url="https://docs.example.com/faq")
        bot = resp.json()
        assert bot["allowed_domains"] == ["docs.example.com"]

        resp = await client.get(f"/bots/{bot['id']}/documents")
        docs = resp.json()
        assert [d["url"] for d in docs] == ["https://docs.example.com/faq"]


async def test_get_nonexistent_bot_returns_404():
    async with _client_as(USER_A) as client:
        resp = await client.get("/bots/000000000000000000000000")
        assert resp.status_code == 404


async def test_delete_bot():
    async with _client_as(USER_A) as client:
        resp = await _create_bot(client, "Temp")
        bot_id = resp.json()["id"]

        resp = await client.delete(f"/bots/{bot_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/bots/{bot_id}")
        assert resp.status_code == 404


async def test_bots_are_scoped_to_owner():
    async with _client_as(USER_A) as client:
        resp = await _create_bot(client, "Mine")
        bot_id = resp.json()["id"]

    async with _client_as(USER_B) as client:
        resp = await client.get(f"/bots/{bot_id}")
        assert resp.status_code == 404

        resp = await client.get("/bots")
        assert resp.json() == []


async def test_missing_auth_returns_401():
    transport = ASGITransport(app=dashboard_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/bots")
    assert resp.status_code == 401


async def test_allowed_domains_are_normalized_from_pasted_urls():
    """Regression test: a user pasting a full URL copied from their browser's address
    bar (e.g. "http://127.0.0.1:5500/demo/") must be stored as just the hostname[:port]
    — the format a real Origin header takes — or the widget's origin check can never match.
    """
    async with _client_as(USER_A) as client:
        resp = await _create_bot(client, "Domain Bot")
        bot_id = resp.json()["id"]

        resp = await client.put(
            f"/bots/{bot_id}/allowed-domains",
            json={"allowed_domains": ["http://127.0.0.1:5500/demo/", "example.com"]},
        )
        assert resp.status_code == 200
        assert resp.json()["allowed_domains"] == ["127.0.0.1:5500", "example.com"]


async def test_invalid_allowed_domain_returns_400():
    async with _client_as(USER_A) as client:
        resp = await _create_bot(client, "Domain Bot")
        bot_id = resp.json()["id"]

        resp = await client.put(
            f"/bots/{bot_id}/allowed-domains", json={"allowed_domains": [""]}
        )
        assert resp.status_code == 400


async def test_update_appearance_persists_to_config():
    async with _client_as(USER_A) as client:
        bot_id = (await _create_bot(client, "Look Bot")).json()["id"]

        resp = await client.put(
            f"/bots/{bot_id}/appearance",
            json={"display_name": "  Ada  ", "primary_color": "#4f46e5", "font_size": "large"},
        )
        assert resp.status_code == 200
        config = resp.json()["config"]
        assert config["display_name"] == "Ada"  # trimmed
        assert config["primary_color"] == "#4f46e5"
        assert config["font_size"] == "large"
        # behavior fields untouched
        assert config["system_prompt"] == "You are a helpful assistant."

        # and it's actually stored, not just echoed
        assert (await client.get(f"/bots/{bot_id}")).json()["config"]["font_size"] == "large"


async def test_update_appearance_rejects_bad_values():
    async with _client_as(USER_A) as client:
        bot_id = (await _create_bot(client, "Look Bot")).json()["id"]
        good = {"display_name": "Ada", "primary_color": "#4f46e5", "font_size": "medium"}

        assert (
            await client.put(f"/bots/{bot_id}/appearance", json={**good, "primary_color": "blue"})
        ).status_code == 400
        assert (
            await client.put(f"/bots/{bot_id}/appearance", json={**good, "font_size": "huge"})
        ).status_code == 400
        assert (
            await client.put(f"/bots/{bot_id}/appearance", json={**good, "display_name": "  "})
        ).status_code == 400


async def test_update_appearance_respects_ownership():
    async with _client_as(USER_A) as client:
        bot_id = (await _create_bot(client, "Look Bot")).json()["id"]

    async with _client_as(USER_B) as client:
        resp = await client.put(
            f"/bots/{bot_id}/appearance",
            json={"display_name": "Hacked", "primary_color": "#000000", "font_size": "small"},
        )
        assert resp.status_code == 404
