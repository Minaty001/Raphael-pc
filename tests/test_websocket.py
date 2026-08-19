import pytest
from fastapi.testclient import TestClient
from raphael.core.configuration import get_config
from raphael.network.api import app

TOKEN = get_config().websocket.api_token
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def test_api_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["core"] == "ok"


def test_api_tools_list_endpoint():
    client = TestClient(app)
    response = client.get("/api/tools", headers=AUTH)
    assert response.status_code == 200
    tools = response.json()
    assert isinstance(tools, list)
    assert len(tools) > 0
