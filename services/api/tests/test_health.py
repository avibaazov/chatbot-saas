from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


async def test_openapi_json_exposes_dashboard_app_routes_through_the_mount():
    """Regression test: `app` (the top-level ASGI entrypoint uvicorn actually serves)
    used to auto-register its own /openapi.json at construction time, which — since
    Starlette matches routes in registration order — silently shadowed dashboard_app's
    real one instead of erroring. main.py now disables docs/openapi on the bare `app`
    so this path falls through to the "/" mount. Without that, this would come back
    as {"paths": {}} instead of the real route list.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/health" in paths
    assert "/bots" in paths
