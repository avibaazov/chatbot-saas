"""Single source of truth for turning "something a human typed" or "a browser's Origin
header" into the plain hostname[:port] format allowed_domains is stored and compared as.
Used by both bots.py (normalizing what a user pastes into the dashboard — which might be a
full URL, with or without a trailing slash) and widget.py (parsing the real Origin header).
"""

from urllib.parse import urlparse


def extract_hostname(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    if value == "*":
        return "*"

    # urlparse("127.0.0.1:5500") without a scheme misparses it as scheme="127.0.0.1",
    # path="5500" — prefixing with "//" forces it to populate .netloc/.hostname/.port
    # correctly, same as a protocol-relative URL. Real Origin headers always have a
    # scheme already, so this is a no-op for them.
    parsed = urlparse(value if "://" in value else f"//{value}")
    if not parsed.hostname:
        return None
    return parsed.hostname if not parsed.port else f"{parsed.hostname}:{parsed.port}"
