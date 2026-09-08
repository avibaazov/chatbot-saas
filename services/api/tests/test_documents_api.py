"""Integration tests for /bots/{bot_id}/documents — real Atlas, same rationale as
test_bots_api.py. Uses FakeEmbeddingsProvider + InMemoryQueue by default (no
VOYAGE_API_KEY/REDIS_URL in .env), so ingestion runs inline and synchronously.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_clerk_user_id
from app.main import dashboard_app
from tests.integration_helpers import purge_test_data, reset_db_client

USER_A = "pytest_docs_user_a"
USER_B = "pytest_docs_user_b"

# See test_bots_api.WEBSITE_URL — loopback discard port, so the create_bot auto-ingestion
# fails fast and doesn't reach the network. Tests that monkeypatch fetch_url override that
# too, which is harmless (the seed document just succeeds/fails alongside the real one).
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


async def _create_bot(client: AsyncClient, name: str):
    resp = await client.post("/bots", json={"name": name, "website_url": WEBSITE_URL})
    return resp.json()["id"]


async def test_create_document_ingests_synchronously_and_becomes_ready():
    async with _client_as(USER_A) as client:
        bot_id = await _create_bot(client, "Doc Bot")

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


async def test_create_document_from_url_ingests_and_uses_page_title(monkeypatch):
    async def fake_fetch(url, *args, **kwargs):
        return "Fig Care Guide", "water it weekly. " * 100

    monkeypatch.setattr("app.services.ingestion_jobs.fetch_url", fake_fetch)

    async with _client_as(USER_A) as client:
        bot_id = await _create_bot(client, "URL Bot")

        resp = await client.post(
            f"/bots/{bot_id}/documents/url", json={"url": "https://plants.example/care"}
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "ready"
        assert body["url"] == "https://plants.example/care"
        assert body["filename"] == "Fig Care Guide"


async def test_create_document_from_url_marks_failed_on_fetch_error(monkeypatch):
    async def bad_fetch(url, *args, **kwargs):
        raise Exception("host resolves to a non-public address")

    monkeypatch.setattr("app.services.ingestion_jobs.fetch_url", bad_fetch)

    async with _client_as(USER_A) as client:
        bot_id = await _create_bot(client, "URL Bot")

        resp = await client.post(
            f"/bots/{bot_id}/documents/url", json={"url": "http://169.254.169.254/latest/meta-data"}
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "failed"
        assert resp.json()["error"]


async def test_create_document_with_empty_text_marks_failed():
    async with _client_as(USER_A) as client:
        bot_id = await _create_bot(client, "Doc Bot")

        resp = await client.post(
            f"/bots/{bot_id}/documents", json={"filename": "empty.txt", "text": "   "}
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "failed"
        assert resp.json()["error"]


async def test_list_documents_returns_uploaded_docs():
    async with _client_as(USER_A) as client:
        bot_id = await _create_bot(client, "Doc Bot")

        await client.post(
            f"/bots/{bot_id}/documents", json={"filename": "a.txt", "text": "some content here"}
        )
        await client.post(
            f"/bots/{bot_id}/documents", json={"filename": "b.txt", "text": "more content here"}
        )

        resp = await client.get(f"/bots/{bot_id}/documents")
        assert resp.status_code == 200
        filenames = {d["filename"] for d in resp.json()}
        # plus the URL seed document create_bot adds
        assert {"a.txt", "b.txt"} <= filenames


async def test_reload_document_rechunks_a_url_document(monkeypatch):
    text_versions = iter(["first revision. " * 80, "second revision, longer now. " * 80])

    async def fake_fetch(url, *args, **kwargs):
        return "Care Guide", next(text_versions)

    monkeypatch.setattr("app.services.ingestion_jobs.fetch_url", fake_fetch)

    async with _client_as(USER_A) as client:
        bot_id = await _create_bot(client, "Reload Bot")

        docs = (await client.get(f"/bots/{bot_id}/documents")).json()
        seed = next(d for d in docs if d["url"])
        assert seed["status"] == "ready"

        resp = await client.post(f"/bots/{bot_id}/documents/{seed['id']}/reload")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


async def test_reload_rejects_a_non_url_document():
    async with _client_as(USER_A) as client:
        bot_id = await _create_bot(client, "Reload Bot")
        text_doc = (
            await client.post(
                f"/bots/{bot_id}/documents", json={"filename": "a.txt", "text": "hello there"}
            )
        ).json()

        resp = await client.post(f"/bots/{bot_id}/documents/{text_doc['id']}/reload")
        assert resp.status_code == 400


async def test_documents_route_respects_bot_ownership():
    async with _client_as(USER_A) as client:
        bot_id = await _create_bot(client, "Not yours")

    async with _client_as(USER_B) as client:
        resp = await client.post(
            f"/bots/{bot_id}/documents", json={"filename": "x.txt", "text": "hi"}
        )
        assert resp.status_code == 404
