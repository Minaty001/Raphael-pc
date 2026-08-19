"""
Tests for browser automation tools (ROADMAP: real browser automation gap).

Hardware/network-free, deterministic:
  * _TextExtractor (stdlib) correctly pulls title, visible text, and links
    from synthetic HTML with script/style stripped.
  * read_webpage via a local stub HTTP server (stdlib) -> real extraction, no
    external deps or network.
  * Playwright-backed DOM tools return an honest "engine not available" result
    when Playwright is not installed (never fake success).
"""

import threading
import http.server
import socketserver
from urllib.parse import urlparse

import pytest

from raphael.tools.browser_automation import (
    _TextExtractor,
    read_webpage,
    browser_navigate,
    browser_click,
    browser_fill,
    browser_extract,
)


_HTML = """<!DOCTYPE html><html><head><title>Test Page</title>
<style>.x{color:red}</style>
<script>var secret=1;</script></head>
<body><h1>Hello World</h1><p>This is a <a href="https://example.com/a">link A</a>
and <a href="/b">link B</a>.</p></body></html>"""


def test_text_extractor_strips_scripts_and_pulls_links():
    ex = _TextExtractor()
    ex.feed(_HTML)
    assert ex.title.strip() == "Test Page"
    # script content must NOT leak into visible text
    assert "secret" not in ex.text
    assert "Hello World" in ex.text
    assert "link A" in ex.text
    # both links captured
    assert "https://example.com/a" in ex.links
    assert "/b" in ex.links
    assert len(ex.links) == 2


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = _HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence test server logs
        pass


@pytest.fixture
def local_server():
    with socketserver.TCPServer(("127.0.0.1", 0), _Handler) as httpd:
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        yield f"http://127.0.0.1:{port}/"
        httpd.shutdown()


def test_read_webpage_real_extraction(local_server):
    res = read_webpage(local_server)
    assert res["status"] == "success"
    r = res["result"]
    assert r["title"] == "Test Page"
    assert "Hello World" in r["text"]
    assert r["engine"] == "stdlib"
    assert len(r["links"]) == 2
    # Prepend missing scheme path (read_webpage should keep valid URLs).
    assert r["url"].startswith("http")


def test_playwright_tools_graceful_when_absent():
    # In this environment Playwright is not installed -> honest failure,
    # never a false success. Args still supplied so the call reaches the
    # engine-availability check.
    res_nav = browser_navigate("https://example.com")
    assert res_nav["status"] == "failed"
    assert "Playwright" in res_nav.get("error", "")

    res_click = browser_click("https://example.com", "button#go")
    assert res_click["status"] == "failed"
    assert "Playwright" in res_click.get("error", "")

    res_fill = browser_fill("https://example.com", "input#q", "hello")
    assert res_fill["status"] == "failed"
    assert "Playwright" in res_fill.get("error", "")

    res_ext = browser_extract("https://example.com")
    assert res_ext["status"] == "failed"
    assert "Playwright" in res_ext.get("error", "")
