"""Tests for the public, loopback-only auth bootstrap endpoint (GET /api/bootstrap).

This endpoint lets the bundled localhost UI obtain the api_token so it can
authenticate against the now-auth-required REST/WS routes. It must:
  * return the configured api_token when called from loopback, and
  * refuse non-loopback clients with 403.

Note: Starlette's TestClient injects the literal host "testclient" (not a real
IP), so we drive `bootstrap_auth` directly with explicit request scopes to
assert both the allow (loopback) and deny (remote) branches.
"""
import asyncio

import pytest
from fastapi import Request
from fastapi import HTTPException as FastAPIHTTPException

from raphael.core.configuration import get_config
from raphael.network.api import app, bootstrap_auth


TOKEN = get_config().websocket.api_token


def _make_request(host: str) -> Request:
    scope = {
        "type": "http",
        "client": (host, 5555),
        "method": "GET",
        "path": "/api/bootstrap",
        "headers": [],
    }
    return Request(scope)


def test_bootstrap_returns_token_on_loopback():
    for host in ("127.0.0.1", "::1", "localhost"):
        req = _make_request(host)
        result = asyncio.run(bootstrap_auth(req))
        assert result == {"token": TOKEN}, f"host={host}"


def test_protected_route_requires_token():
    from fastapi.testclient import TestClient

    client = TestClient(app)
    # Sanity check: a gated route must 401 without the token.
    res = client.get("/api/tools")
    assert res.status_code == 401
    # ...and succeed with it.
    res2 = client.get("/api/tools", headers={"Authorization": f"Bearer {TOKEN}"})
    assert res2.status_code == 200


def test_bootstrap_refuses_non_loopback():
    # TEST-NET-3 (203.0.113.0/24) — a non-loopback address.
    req = _make_request("203.0.113.9")
    with pytest.raises(FastAPIHTTPException) as exc:
        asyncio.run(bootstrap_auth(req))
    assert exc.value.status_code == 403
