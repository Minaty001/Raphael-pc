"""
Browser Automation tools for Raphael AI Assistant.

Two layers, following the project's real-impl + graceful-offline-fallback
pattern (same as STT / TTS / OCR / embeddings):

  * ``read_webpage``   -> dependency-free. Uses only the stdlib
    (``urllib`` + ``html.parser``) to fetch a URL and extract a factual
    summary: page title, visible text (tags stripped), and outbound links.
    No external browser engine required — works on any machine with network.
  * Playwright-backed DOM actions (``browser_navigate`` / ``browser_click`` /
    ``browser_fill`` / ``browser_extract``) -> real automation (click buttons,
    fill forms, read live DOM). Activated automatically when the user has
    installed Playwright (``pip install playwright && playwright install``).
    When Playwright is NOT installed these tools return an honest
    "engine not available" result instead of failing silently or faking it.

All tools register with the ToolRegistry and are auto-verified by the
ActionVerifier (ROADMAP L10). Network/headless actions are MODERATE risk.
"""

from __future__ import annotations

import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from raphael.tools.registry import get_tool_registry
from raphael.security.permissions import RiskLevel
from raphael.core.logging import get_logger
from raphael.platform.common import make_action_result

logger = get_logger("tools.browser_automation")
registry = get_tool_registry()

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) RaphaelAssistant/2.0 "
    "(compatible; +https://github.com/Minaty001/Raphael-pc)"
)


# ---------------------------------------------------------------------------
# Dependency-free webpage reading (stdlib only)
# ---------------------------------------------------------------------------
from html.parser import HTMLParser

_VOID = {"script", "style", "meta", "link", "noscript", "template"}
_BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
          "section", "article", "blockquote", "pre", "table"}


class _TextExtractor(HTMLParser):
    """HTML -> title / visible text / links using only the stdlib parser."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.links: List[str] = []
        self._text_parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _VOID:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "a":
            d = dict(attrs)
            href = d.get("href")
            if href:
                self.links.append(href)
        if tag in _BLOCK:
            self._text_parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _VOID and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in _BLOCK:
            self._text_parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if self._in_title:
            self.title += data
        else:
            self._text_parts.append(data)

    @property
    def text(self) -> str:
        raw = " ".join(self._text_parts)
        return " ".join(raw.split())


def _read_webpage_stdlib(url: str, timeout: float = 10.0) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        html = resp.read().decode(charset, errors="replace")

    ex = _TextExtractor()
    ex.feed(html)
    text = ex.text
    return {
        "url": url,
        "title": ex.title.strip(),
        "text": text[:4000],
        "word_count": len(text.split()),
        "links": ex.links[:50],
        "engine": "stdlib",
    }


@registry.register(
    name="read_webpage",
    description="Fetch a URL and extract its title, readable text, and links (no browser needed)",
    risk_level=RiskLevel.LOW_RISK,
)
def read_webpage(url: str, timeout: float = 10.0) -> Dict[str, Any]:
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    try:
        data = _read_webpage_stdlib(url, timeout)
        return make_action_result(
            "read_webpage", "success", 0.0,
            result={
                "url": data["url"],
                "title": data["title"],
                "text": data["text"],
                "word_count": data["word_count"],
                "links": data["links"],
                "engine": data["engine"],
            },
        )
    except urllib.error.HTTPError as e:
        return make_action_result("read_webpage", "failed", 0.0,
                                  error=f"HTTP {e.code}: {e.reason}")
    except Exception as e:
        return make_action_result("read_webpage", "failed", 0.0, error=str(e))


# ---------------------------------------------------------------------------
# Optional Playwright-backed DOM automation (real clicks/fills/reads)
# ---------------------------------------------------------------------------
def _get_playwright_page():
    """Return (playwright, browser, page) or raise if Playwright unavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # pragma: no cover - optional dep
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && "
            "playwright install chromium"
        ) from e

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    return pw, browser, page


def _playwright_unavailable_result(tool_name: str):
    return make_action_result(
        tool_name, "failed", 0.0,
        error=(
            "Browser automation engine (Playwright) not installed. "
            "Install it for DOM interaction: pip install playwright && "
            "playwright install chromium. (read_webpage works without it.)"
        ),
    )


@registry.register(
    name="browser_navigate",
    description="Open a URL in a headless browser and return the live page title/text (requires Playwright)",
    risk_level=RiskLevel.MODERATE,
)
def browser_navigate(url: str) -> Dict[str, Any]:
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    try:
        pw, browser, page = _get_playwright_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return make_action_result(
                "browser_navigate", "success", 0.0,
                result={
                    "url": page.url,
                    "title": page.title(),
                    "text": (page.inner_text("body") or "")[:4000],
                    "engine": "playwright",
                },
            )
        finally:
            browser.close()
            pw.stop()
    except RuntimeError as e:
        return _playwright_unavailable_result("browser_navigate")
    except Exception as e:
        return make_action_result("browser_navigate", "failed", 0.0, error=str(e))


@registry.register(
    name="browser_click",
    description="Click an element on the current/loaded page by CSS selector (requires Playwright)",
    risk_level=RiskLevel.MODERATE,
)
def browser_click(url: str, selector: str) -> Dict[str, Any]:
    try:
        pw, browser, page = _get_playwright_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.click(selector, timeout=5000)
            return make_action_result(
                "browser_click", "success", 0.0,
                result={"url": page.url, "clicked": selector, "engine": "playwright"},
            )
        finally:
            browser.close()
            pw.stop()
    except RuntimeError:
        return _playwright_unavailable_result("browser_click")
    except Exception as e:
        return make_action_result("browser_click", "failed", 0.0, error=str(e))


@registry.register(
    name="browser_fill",
    description="Fill a form field (CSS selector) with text on a loaded page (requires Playwright)",
    risk_level=RiskLevel.MODERATE,
)
def browser_fill(url: str, selector: str, value: str) -> Dict[str, Any]:
    try:
        pw, browser, page = _get_playwright_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.fill(selector, value, timeout=5000)
            return make_action_result(
                "browser_fill", "success", 0.0,
                result={"url": page.url, "filled": selector, "engine": "playwright"},
            )
        finally:
            browser.close()
            pw.stop()
    except RuntimeError:
        return _playwright_unavailable_result("browser_fill")
    except Exception as e:
        return make_action_result("browser_fill", "failed", 0.0, error=str(e))


@registry.register(
    name="browser_extract",
    description="Extract visible text + all links from a live page (requires Playwright)",
    risk_level=RiskLevel.LOW_RISK,
)
def browser_extract(url: str) -> Dict[str, Any]:
    try:
        pw, browser, page = _get_playwright_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return make_action_result(
                "browser_extract", "success", 0.0,
                result={
                    "url": page.url,
                    "title": page.title(),
                    "text": (page.inner_text("body") or "")[:4000],
                    "links": [a.get_attribute("href") for a in page.query_selector_all("a")][:50],
                    "engine": "playwright",
                },
            )
        finally:
            browser.close()
            pw.stop()
    except RuntimeError:
        return _playwright_unavailable_result("browser_extract")
    except Exception as e:
        return make_action_result("browser_extract", "failed", 0.0, error=str(e))
