import httpx
import pytest

from app.services import web_fetch
from app.services.web_fetch import (
    FetchError,
    SsrfError,
    _assert_public_host,
    _page_title,
    fetch_url,
)

# --- SSRF guard -------------------------------------------------------------


@pytest.mark.parametrize("host", ["127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254", "0.0.0.0"])
def test_assert_public_host_rejects_internal_addresses(host):
    with pytest.raises(SsrfError):
        _assert_public_host(host)


def test_assert_public_host_allows_a_public_address():
    _assert_public_host("1.1.1.1")  # no raise


async def test_fetch_url_rejects_non_http_schemes():
    for bad in ("ftp://example.com/x", "file:///etc/passwd", "gopher://example.com"):
        with pytest.raises(FetchError):
            await fetch_url(bad)


async def test_validate_url_allow_private_skips_the_host_check(monkeypatch):
    checked: list[str] = []

    def boom(host):
        checked.append(host)
        raise SsrfError("blocked")

    monkeypatch.setattr(web_fetch, "_assert_public_host", boom)

    with pytest.raises(SsrfError):
        await web_fetch._validate_url("http://127.0.0.1:5500/demo/")
    await web_fetch._validate_url("http://127.0.0.1:5500/demo/", allow_private=True)  # no raise

    assert checked == ["127.0.0.1"]  # host check runs only when allow_private is False


# --- fetch_url -------------------------------------------------------------

_HTML = "<html><head><title>Fiddle Leaf &amp; Fig Care</title></head><body>...</body></html>"


@pytest.fixture(autouse=True)
def _no_dns_and_fake_extractor(monkeypatch):
    monkeypatch.setattr(web_fetch, "_assert_public_host", lambda host: None)
    monkeypatch.setattr(web_fetch, "_extract_main_text", lambda page_html: "water it weekly. " * 40)


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


async def test_fetch_url_returns_title_and_extracted_text():
    def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_HTML)

    title, text = await fetch_url("https://plants.example/care", client=_client(handler))
    assert title == "Fiddle Leaf & Fig Care"
    assert "water it weekly" in text


async def test_fetch_url_follows_redirects_and_revalidates():
    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(301, headers={"location": "https://plants.example/final"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_HTML)

    title, text = await fetch_url("https://plants.example/start", client=_client(handler))
    assert "water it weekly" in text


async def test_fetch_url_rejects_non_html_content():
    def handler(request):
        return httpx.Response(200, headers={"content-type": "application/json"}, text="{}")

    with pytest.raises(FetchError):
        await fetch_url("https://plants.example/api", client=_client(handler))


async def test_fetch_url_raises_when_page_has_no_readable_text(monkeypatch):
    monkeypatch.setattr(web_fetch, "_extract_main_text", lambda page_html: "too short")

    def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_HTML)

    with pytest.raises(FetchError, match="JavaScript"):
        await fetch_url("https://spa.example/", client=_client(handler))


async def test_fetch_url_raises_on_http_error():
    def handler(request):
        return httpx.Response(404, headers={"content-type": "text/html"}, text="nope")

    with pytest.raises(FetchError, match="404"):
        await fetch_url("https://plants.example/missing", client=_client(handler))


def test_page_title_collapses_whitespace_and_unescapes():
    assert _page_title("<title>  Hello\n  &amp; welcome  </title>") == "Hello & welcome"
    assert _page_title("<html>no title here</html>") is None
