"""
Tests for the synchronous tool-execution REST endpoint (POST /api/tools/execute).

Verifies (hardware-free):
  * A registered READ_ONLY tool (read_screen) executes and returns a real
    result payload (the endpoint drives the ToolRegistry, which applies the
    security policy + ActionVerifier).
  * An unknown tool name returns HTTP 404.
  * A missing `tool` field returns HTTP 400.

All API routes require auth (require_api_auth), so the tests send the
configured api_token as a Bearer header — mirroring how the real frontend
(wsClient.rest) authenticates.
"""

import pytest
from fastapi.testclient import TestClient

import raphael.tools.screen  # registers read_screen
from raphael.core.configuration import get_config
from raphael.network.api import app

TOKEN = get_config().websocket.api_token
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client():
    return TestClient(app)


def test_execute_read_screen_tool(client):
    res = client.post(
        "/api/tools/execute",
        json={"tool": "read_screen", "args": {"detail": "structural"}},
        headers=AUTH,
    )
    assert res.status_code == 200
    body = res.json()
    # ToolRegistry result shape: action/status/result
    assert body.get("action") == "read_screen"
    assert body.get("status") == "success"
    assert "result" in body


def test_execute_unknown_tool_404(client):
    res = client.post(
        "/api/tools/execute",
        json={"tool": "does_not_exist", "args": {}},
        headers=AUTH,
    )
    assert res.status_code == 404


def test_execute_missing_tool_field_400(client):
    res = client.post("/api/tools/execute", json={"args": {}}, headers=AUTH)
    assert res.status_code == 400
