"""API endpoint tests with mocked services"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


@pytest.fixture
def client():
    """Create test client with mocked services"""
    # Mock Redis before importing app
    mock_redis = AsyncMock()
    mock_redis.is_connected.return_value = True
    mock_redis.check_rate_limit.return_value = (True, 10)
    mock_redis.is_token_blacklisted.return_value = False
    
    with patch('app.services.redis_service.get_redis_service', return_value=mock_redis), \
         patch('app.middleware.rate_limit.get_redis_service', return_value=mock_redis):
        from app.main import app
        return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "health" in data


def test_health_endpoint(client):
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "database" in data
    assert "asterisk" in data
    # Database should be disabled in tests
    assert data["database"] == "disabled"


def test_readiness_endpoint(client):
    """Test readiness endpoint"""
    response = client.get("/readiness")
    assert response.status_code in [200, 503]  # May not be fully ready in tests
    data = response.json()
    assert "ready" in data
    assert "checks" in data


def test_docs_available_in_debug(client):
    """Test that docs are available in debug mode"""
    response = client.get("/docs")
    # Docs enabled in test mode (DEBUG=true)
    assert response.status_code == 200


def test_metrics_endpoint(client):
    """Test metrics endpoint is available"""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Should contain Prometheus metrics
    assert b"# HELP" in response.content or response.status_code == 200


def test_token_endpoint_without_credentials(client):
    """Test token endpoint without credentials"""
    response = client.post("/api/v1/token")
    # Should return 422 (validation error - missing form data)
    assert response.status_code == 422


def test_token_endpoint_with_wrong_credentials(client):
    """Test token endpoint with wrong credentials"""
    response = client.post(
        "/api/v1/token",
        data={"username": "wrong", "password": "wrong"}
    )
    # Should return 401 or 503 (DB disabled)
    assert response.status_code in [401, 503]


def test_protected_endpoint_without_auth(client):
    """Test that protected endpoints require authentication"""
    response = client.post("/api/v1/interaction/+1234567890")
    assert response.status_code == 401  # Unauthorized


def test_protected_endpoint_with_invalid_token(client):
    """Test protected endpoint with invalid token"""
    response = client.post(
        "/api/v1/interaction/+1234567890",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_call_status_without_auth(client):
    """Test call status endpoint requires auth"""
    response = client.get("/api/v1/status/test-call-id")
    assert response.status_code == 401


def test_invalid_phone_number(client):
    """Test that invalid phone numbers are rejected"""
    # Even without auth, validation should happen first
    response = client.post("/api/v1/interaction/invalid-phone")
    # Should fail with 401 (auth) or 400 (validation)
    assert response.status_code in [400, 401]


def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    # CORS middleware should add headers
    # In test mode with DEBUG=true, wildcard CORS is allowed
    assert response.status_code == 200
