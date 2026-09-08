"""Integration tests for /bots/{bot_id}/documents — real Atlas, same rationale as
test_bots_api.py. Uses FakeEmbeddingsProvider + InMemoryQueue by default (no
VOYAGE_API_KEY/REDIS_URL in .env), so ingestion runs inline and synchronously.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_clerk_user_id
from app.main import app
from tests.integration_helpers import purge_test_data, reset_db_client

USER_A = "pytest_docs_user_a"
USER_B = "pytest_docs_user_b"


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


async def test_create_document_ingests_synchronously_and_becomes_ready():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "Doc Bot"})
        bot_id = resp.json()["id"]

        resp = await client.post(
            f"/bots/{bot_id}/documents",
            json={"filename": "faq.txt", "text": "We are open 9-5. " * 50},
        )
        assert resp.status_code == 201
        body = resp.json()
        # InMemoryQueue runs the job inline and awaited, so ingestion has already
        # finished by the time this response comes back.
        assert body["status"] == "ready"

        resp = await client.get(f"/bots/{bot_id}/documents/{body['id']}")
        assert resp.json()["status"] == "ready"


async def test_create_document_with_empty_text_marks_failed():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "Doc Bot"})
        bot_id = resp.json()["id"]

        resp = await client.post(
            f"/bots/{bot_id}/documents", json={"filename": "empty.txt", "text": "   "}
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "failed"
        assert resp.json()["error"]


async def test_list_documents_returns_uploaded_docs():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "Doc Bot"})
        bot_id = resp.json()["id"]

        await client.post(
            f"/bots/{bot_id}/documents", json={"filename": "a.txt", "text": "some content here"}
        )
        await client.post(
            f"/bots/{bot_id}/documents", json={"filename": "b.txt", "text": "more content here"}
        )

        resp = await client.get(f"/bots/{bot_id}/documents")
        assert resp.status_code == 200
        filenames = {d["filename"] for d in resp.json()}
        assert filenames == {"a.txt", "b.txt"}


async def test_documents_route_respects_bot_ownership():
    async with _client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "Not yours"})
        bot_id = resp.json()["id"]

    async with _client_as(USER_B) as client:
        resp = await client.post(
            f"/bots/{bot_id}/documents", json={"filename": "x.txt", "text": "hi"}
        )
        assert resp.status_code == 404
