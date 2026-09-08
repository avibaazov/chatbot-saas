"""Integration test for /bots/{bot_id}/ask — the full loop: create bot, ingest a real
document into Mongo, ask a question, and confirm MongoBruteForceVectorStore actually found
the chunk (not just that the endpoint returns 200).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_clerk_user_id
from app.main import dashboard_app
from tests.integration_helpers import purge_test_data, reset_db_client

USER_A = "pytest_chat_user_a"
USER_B = "pytest_chat_user_b"


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


async def test_ask_retrieves_ingested_content():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "Ask Bot"})
        bot_id = resp.json()["id"]

        resp = await client.post(
            f"/bots/{bot_id}/documents",
            json={"filename": "hours.txt", "text": "We are open 9am to 5pm, Monday to Friday."},
        )
        assert resp.json()["status"] == "ready"

        resp = await client.post(f"/bots/{bot_id}/ask", json={"question": "hours?"})
        assert resp.status_code == 200
        answer = resp.json()["answer"]
        # FakeLLMProvider echoes how many context chunks it received — proves retrieval
        # actually pulled something back from the real Mongo chunks collection.
        assert "context_chunks=0" not in answer


async def test_ask_respects_bot_ownership():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "Not yours"})
        bot_id = resp.json()["id"]

    async with _client_as(USER_B) as client:
        resp = await client.post(f"/bots/{bot_id}/ask", json={"question": "hi"})
        assert resp.status_code == 404


async def test_ask_nonexistent_bot_returns_404():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots/000000000000000000000000/ask", json={"question": "hi"})
        assert resp.status_code == 404
