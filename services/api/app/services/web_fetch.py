"""Static (no-JavaScript) fetching of a single web page for URL ingestion.

Fetches one page over HTTP, guards against SSRF (only public hosts, only http/https,
redirects re-validated hop by hop), and pulls out the main readable text. Pages that
render their content client-side come back with little or no text — that surfaces as a
FetchError, not a silently empty document.
"""

from __future__ import annotations

import asyncio
import html
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx

MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = 10.0
MIN_CONTENT_CHARS = 200
USER_AGENT = "ChatbotIngestBot/1.0"

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class FetchError(Exception):
    """Any reason a URL could not be turned into ingestible text."""


class SsrfError(FetchError):
    """The URL points somewhere we refuse to fetch from (internal/non-public address)."""


def _assert_public_host(host: str) -> None:
    """Resolve `host` and reject it if any address is loopback/private/link-local/etc.
    Blocking DNS — call via asyncio.to_thread.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise FetchError(f"could not resolve host: {host}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise SsrfError(f"host {host} resolves to a non-public address ({ip})")


async def _validate_url(raw_url: str, *, allow_private: bool = False) -> None:
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError("only http:// and https:// URLs can be ingested")
    if not parsed.hostname:
        raise FetchError("URL has no host")
    if not allow_private:
        await asyncio.to_thread(_assert_public_host, parsed.hostname)


def _extract_main_text(page_html: str) -> str:
    """Main-content extraction. Isolated (and lazily importing trafilatura) so tests can
    monkeypatch it without the dependency or a real page.
    """
    import trafilatura

    return (trafilatura.extract(page_html, include_comments=False, include_tables=True) or "").strip()


def _page_title(page_html: str) -> str | None:
    match = _TITLE_RE.search(page_html)
    if not match:
        return None
    return html.unescape(" ".join(match.group(1).split())) or None


def _decode(response: httpx.Response) -> str:
    if len(response.content) > MAX_BYTES:
        raise FetchError(f"page is larger than {MAX_BYTES // 1_000_000} MB")
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        raise FetchError(f"unsupported content type: {content_type or 'unknown'}")
    return response.content.decode(response.encoding or "utf-8", errors="replace")


async def fetch_url(
    url: str, *, client: httpx.AsyncClient | None = None, allow_private: bool = False
) -> tuple[str, str]:
    """Fetch `url` and return (title, main_text). Raises FetchError / SsrfError on any
    problem, including a page with no extractable text. `allow_private` disables the
    SSRF host check — dev only, for ingesting a demo site on 127.0.0.1.
    """
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
        )

    try:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            await _validate_url(current, allow_private=allow_private)
            try:
                response = await client.get(current)
            except httpx.HTTPError as exc:
                raise FetchError(f"request failed: {exc}") from exc

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise FetchError("got a redirect with no target")
                current = urljoin(current, location)
                continue

            if response.status_code >= 400:
                raise FetchError(f"page returned HTTP {response.status_code}")

            page_html = _decode(response)
            text = _extract_main_text(page_html)
            if len(text) < MIN_CONTENT_CHARS:
                raise FetchError(
                    "no readable text found — the page may need JavaScript to render"
                )
            return _page_title(page_html) or urlparse(current).hostname or current, text

        raise FetchError("too many redirects")
    finally:
        if owns_client:
            await client.aclose()
