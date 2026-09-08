"""Integration tests for the public /widget/{site_key} routes — real Atlas, since the
thing under test (origin vs. allowed_domains matching, CORS header correctness) needs to
run against the real bot document. Dashboard-side calls (create bot, set allowed domains)
still go through the regular app with auth overridden; widget calls go through widget_app
directly via its own ASGI transport, with NO auth override — that's the point, it's public.

Most tests below hit widget_app directly (isolated), which is deliberate for speed and
focus — but that isolation is exactly what let a real bug slip past this suite once
already: widget_app worked fine alone, yet real browser requests through the fully
mounted `app` got rejected, because Starlette middleware on a parent app wraps mounted
sub-apps too (add_middleware() isn't escaped by mount()) — the dashboard's CORSMiddleware
was intercepting /widget/* before this router ever ran. test_widget_ask_works_through_the_
actual_mounted_app below hits `app` itself for that reason: it's the one test that would
have caught it.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_clerk_user_id
from app.main import app, dashboard_app
from app.routes.widget import widget_app
from app.services.rate_limit import _buckets
from tests.integration_helpers import purge_test_data, reset_db_client

USER_A = "pytest_widget_user_a"


@pytest.fixture(autouse=True)
async def _clean():
    reset_db_client()
    await purge_test_data()
    _buckets.clear()
    yield
    await purge_test_data()
    dashboard_app.dependency_overrides.pop(get_current_clerk_user_id, None)


def _dashboard_client_as(clerk_user_id: str) -> AsyncClient:
    dashboard_app.dependency_overrides[get_current_clerk_user_id] = lambda: clerk_user_id
    return AsyncClient(transport=ASGITransport(app=dashboard_app), base_url="http://test")


def _widget_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=widget_app), base_url="http://widget-test")


async def _create_bot_with_allowed_domain(domain: str) -> dict:
    async with _dashboard_client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "Widget Bot"})
        bot = resp.json()
        resp = await client.put(
            f"/bots/{bot['id']}/allowed-domains", json={"allowed_domains": [domain]}
        )
        return resp.json()


async def test_ask_from_allowed_origin_succeeds():
    bot = await _create_bot_with_allowed_domain("example.com")

    async with _widget_client() as client:
        resp = await client.post(
            f"/{bot['site_key']}/ask",
            json={"question": "hi"},
            headers={"Origin": "https://example.com"},
        )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "https://example.com"


async def test_ask_from_disallowed_origin_is_rejected():
    bot = await _create_bot_with_allowed_domain("example.com")

    async with _widget_client() as client:
        resp = await client.post(
            f"/{bot['site_key']}/ask",
            json={"question": "hi"},
            headers={"Origin": "https://evil.com"},
        )
    assert resp.status_code == 403
    assert "access-control-allow-origin" not in resp.headers


async def test_ask_with_no_allowed_domains_configured_is_rejected():
    async with _dashboard_client_as(USER_A) as client:
        resp = await client.post("/bots", json={"name": "No Domains Bot"})
        bot = resp.json()

    async with _widget_client() as client:
        resp = await client.post(
            f"/{bot['site_key']}/ask",
            json={"question": "hi"},
            headers={"Origin": "https://example.com"},
        )
    assert resp.status_code == 403


async def test_wildcard_allowed_domain_permits_any_origin():
    bot = await _create_bot_with_allowed_domain("*")

    async with _widget_client() as client:
        resp = await client.post(
            f"/{bot['site_key']}/ask",
            json={"question": "hi"},
            headers={"Origin": "https://anything-at-all.example"},
        )
    assert resp.status_code == 200


async def test_widget_preflight_and_ask_work_through_the_actual_mounted_app():
    """Regression test for the mount/middleware bug: goes through `app` itself (the real
    ASGI entrypoint uvicorn serves), not the isolated widget_app the other tests use.
    A third-party origin, not in the dashboard's allowed CORS_ORIGINS, must still work here.
    """
    bot = await _create_bot_with_allowed_domain("example.com")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        preflight = await client.options(
            f"/widget/{bot['site_key']}/ask",
            headers={"Origin": "https://example.com", "Access-Control-Request-Method": "POST"},
        )
        assert preflight.status_code == 204
        assert preflight.headers["access-control-allow-origin"] == "https://example.com"

        resp = await client.post(
            f"/widget/{bot['site_key']}/ask",
            json={"question": "hi"},
            headers={"Origin": "https://example.com"},
        )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "https://example.com"


async def test_unknown_site_key_returns_404():
    async with _widget_client() as client:
        resp = await client.post(
            "/sk_pub_does_not_exist/ask",
            json={"question": "hi"},
            headers={"Origin": "https://example.com"},
        )
    assert resp.status_code == 404


async def test_preflight_options_returns_cors_headers_for_allowed_origin():
    bot = await _create_bot_with_allowed_domain("example.com")

    async with _widget_client() as client:
        resp = await client.options(
            f"/{bot['site_key']}/ask",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert resp.status_code == 204
    assert resp.headers["access-control-allow-origin"] == "https://example.com"
    assert "POST" in resp.headers["access-control-allow-methods"]


async def test_widget_config_returns_display_settings():
    bot = await _create_bot_with_allowed_domain("example.com")

    async with _widget_client() as client:
        resp = await client.get(
            f"/{bot['site_key']}/config", headers={"Origin": "https://example.com"}
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Assistant"  # BotConfig default


async def test_rate_limit_kicks_in_after_threshold():
    bot = await _create_bot_with_allowed_domain("*")

    async with _widget_client() as client:
        statuses = []
        for _ in range(25):
            resp = await client.post(
                f"/{bot['site_key']}/ask",
                json={"question": "hi"},
                headers={"Origin": "https://example.com"},
            )
            statuses.append(resp.status_code)

    assert 429 in statuses
    assert statuses.count(429) < len(statuses)  # some succeeded before the limit hit
