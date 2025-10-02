"""Pytest configuration and shared fixtures"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI application"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_asterisk_service():
    """Mock Asterisk service for testing without real ARI connection"""
    service = MagicMock()
    service.originate_call = AsyncMock(return_value={
        "success": True,
        "call_id": "test-call-id-12345",
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
    service.connect = AsyncMock(return_value=True)
    service.disconnect = AsyncMock()
    return service


@pytest.fixture
def mock_db():
    """Mock database session for testing without real database"""
    db = MagicMock()
    db.query = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    db.rollback = MagicMock()
    db.close = MagicMock()
    return db


@pytest.fixture
def sample_call_data():
    """Sample call data for testing"""
    return {
        "phone_number": "1234567890",
        "context": "outbound-ivr",
        "extension": "s",
        "priority": 1,
        "timeout": 30000,
        "caller_id": "Test Caller"
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "TestPass123!"
    }
