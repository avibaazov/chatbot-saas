from app.services.domains import extract_hostname


def test_bare_host_and_port():
    assert extract_hostname("localhost:3000") == "localhost:3000"


def test_bare_host_no_port():
    assert extract_hostname("example.com") == "example.com"


def test_full_url_with_path_and_trailing_slash():
    assert extract_hostname("http://127.0.0.1:5500/demo/") == "127.0.0.1:5500"


def test_full_url_https_no_port():
    assert extract_hostname("https://example.com/some/path") == "example.com"


def test_wildcard_passes_through():
    assert extract_hostname("*") == "*"


def test_empty_string_returns_none():
    assert extract_hostname("") is None
    assert extract_hostname("   ") is None
