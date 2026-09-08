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


WEBSITE_URL = "http://127.0.0.1:9/"


async def _create_bot_with_allowed_domain(domain: str) -> dict:
    async with _dashboard_client_as(USER_A) as client:
        resp = await client.post(
            "/bots", json={"name": "Widget Bot", "website_url": WEBSITE_URL}
        )
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


async def test_ask_from_a_subdomain_of_the_allowed_domain_succeeds():
    bot = await _create_bot_with_allowed_domain("acme.com")

    async with _widget_client() as client:
        resp = await client.post(
            f"/{bot['site_key']}/ask",
            json={"question": "hi"},
            headers={"Origin": "https://help.acme.com"},
        )
    assert resp.status_code == 200


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


async def test_ask_from_origin_not_in_allowlist_is_rejected():
    bot = await _create_bot_with_allowed_domain("example.com")

    async with _widget_client() as client:
        resp = await client.post(
            f"/{bot['site_key']}/ask",
            json={"question": "hi"},
            headers={"Origin": "https://not-listed.com"},
        )
    assert resp.status_code == 403


async def test_ask_from_first_party_dashboard_origin_is_always_allowed():
    """The dashboard embeds the real widget as a live preview on the bot detail page, so
    its own origin is accepted regardless of the bot's allow-list (see widget.py)."""
    from app.core.config import get_settings

    dashboard_origin = get_settings().cors_origins[0]
    bot = await _create_bot_with_allowed_domain("example.com")  # dashboard origin NOT listed

    async with _widget_client() as client:
        resp = await client.post(
            f"/{bot['site_key']}/ask",
            json={"question": "hi"},
            headers={"Origin": dashboard_origin},
        )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == dashboard_origin


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
    assert body["font_size"] == "medium"  # BotConfig default


async def test_widget_config_reflects_saved_appearance():
    async with _dashboard_client_as(USER_A) as client:
        bot = (
            await client.post(
                "/bots", json={"name": "Styled Bot", "website_url": WEBSITE_URL}
            )
        ).json()
        await client.put(f"/bots/{bot['id']}/allowed-domains", json={"allowed_domains": ["example.com"]})
        await client.put(
            f"/bots/{bot['id']}/appearance",
            json={"display_name": "Support", "primary_color": "#ff0066", "font_size": "large"},
        )

    async with _widget_client() as client:
        resp = await client.get(
            f"/{bot['site_key']}/config", headers={"Origin": "https://example.com"}
        )
    body = resp.json()
    assert body["display_name"] == "Support"
    assert body["primary_color"] == "#ff0066"
    assert body["font_size"] == "large"


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
