"""Tests for interaction endpoints"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create a test client"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_asterisk_service():
    """Mock Asterisk service"""
    service = MagicMock()
    service.originate_call = AsyncMock(return_value={
        "success": True,
        "call_id": "test-call-id",
        "phone_number": "1234567890",
        "channel": "Local/1234567890@outbound-ivr",
        "context": "outbound-ivr",
        "extension": "s",
        "priority": 1,
        "timeout": 30000,
        "caller_id": "Outbound Call",
        "message": "Call originated via ARI"
    })
    service.is_connected = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = MagicMock()
    return db


@pytest.fixture
def mock_auth_token():
    """Mock authentication token"""
    return "Bearer test-token-12345"


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "services" in data


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Contact Center API"
    assert "version" in data
    assert "docs" in data


def test_originate_call_unauthorized(client):
    """Test originating a call without authentication"""
    response = client.post("/api/v2/interaction/1234567890")
    assert response.status_code == 401


def test_get_call_status_unauthorized(client):
    """Test getting call status without authentication"""
    response = client.get("/api/v2/interaction/test-call-id/status")
    assert response.status_code == 401


def test_invalid_phone_number_format(client, mock_auth_token):
    """Test originating call with invalid phone number format"""
    # Phone number with letters should fail validation
    response = client.post(
        "/api/v2/interaction/abc123",
        headers={"Authorization": mock_auth_token}
    )
    assert response.status_code in (401, 422)  # 401 if auth fails, 422 if validation fails


def test_metrics_endpoint_enabled(client):
    """Test metrics endpoint when enabled"""
    response = client.get("/metrics")
    # Should return metrics or 404 depending on configuration
    assert response.status_code in (200, 404)


def test_docs_endpoint(client):
    """Test OpenAPI docs endpoint"""
    response = client.get("/docs")
    # Should return docs page or 404 if disabled
    assert response.status_code in (200, 404)
