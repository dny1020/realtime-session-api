"""Simple API endpoint tests"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client"""
    from app.main import app
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_endpoint(client):
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data


def test_docs_available(client):
    """Test that docs are available"""
    response = client.get("/docs")
    assert response.status_code == 200


def test_token_endpoint_exists(client):
    """Test token endpoint exists (will fail without credentials)"""
    response = client.post("/api/v2/token")
    # Should return 422 (validation error) or 503 (DB disabled)
    assert response.status_code in [422, 503]


def test_protected_endpoint_without_auth(client):
    """Test that protected endpoints require authentication"""
    response = client.post("/api/v2/interaction/1234567890")
    assert response.status_code == 401  # Unauthorized
