"""Tests for consultation router endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Fixture for FastAPI test client."""
    from src.main import app

    return TestClient(app)


def test_health_endpoint(client):
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_cron_endpoint(client):
    """Test GET /cron endpoint."""
    response = client.get("/cron")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_dashboard_endpoint(client):
    """Test GET /dashboard endpoint."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_root_redirect(client):
    """Test GET / redirects to /dashboard."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307


def test_router_module_exists():
    """Test that router module imports successfully."""
    from src.modules.consultations.router import router

    assert router is not None
    assert hasattr(router, "routes")
