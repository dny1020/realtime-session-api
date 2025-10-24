"""Test configuration and fixtures"""
import pytest
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Set test environment variables BEFORE importing app
os.environ["DEBUG"] = "true"
os.environ["DISABLE_DB"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters-long-for-testing"
os.environ["ARI_HTTP_URL"] = "http://test-asterisk:8088/ari"
os.environ["ARI_USERNAME"] = "test"
os.environ["ARI_PASSWORD"] = "test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Test database
os.environ["CIRCUIT_BREAKER_ENABLED"] = "false"  # Disable for tests
os.environ["OTEL_ENABLED"] = "false"  # Disable tracing for tests
os.environ["CACHE_ENABLED"] = "false"  # Disable caching for tests


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """Mock Redis service"""
    mock = AsyncMock()
    mock.is_connected.return_value = True
    mock.check_rate_limit.return_value = (True, 10)  # Allowed, 10 remaining
    mock.is_token_blacklisted.return_value = False
    mock.track_failed_login.return_value = 0
    mock.get.return_value = None
    mock.set.return_value = True
    return mock


@pytest.fixture
def mock_asterisk():
    """Mock Asterisk service"""
    mock = AsyncMock()
    mock._connected_ok = True
    mock._ws_connected = True
    mock.is_connected.return_value = True
    mock.connect.return_value = True
    mock.originate_call.return_value = {
        "success": True,
        "call_id": "test-call-id",
        "channel": "test-channel",
        "message": "Call originated"
    }
    return mock


@pytest.fixture(autouse=True)
def mock_services(mock_redis, mock_asterisk):
    """Auto-mock external services for all tests"""
    with patch('app.services.redis_service.get_redis_service', return_value=mock_redis), \
         patch('app.services.asterisk.get_asterisk_service', return_value=mock_asterisk), \
         patch('app.main.get_redis_service', return_value=mock_redis), \
         patch('app.main.get_asterisk_service', return_value=mock_asterisk):
        yield
