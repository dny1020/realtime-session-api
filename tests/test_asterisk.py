"""Tests for Asterisk service"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.asterisk import AsteriskService


@pytest.fixture
def asterisk_service():
    """Create an Asterisk service instance"""
    return AsteriskService()


@pytest.mark.asyncio
async def test_connect_success(asterisk_service):
    """Test successful connection to Asterisk ARI"""
    with patch.object(asterisk_service, '_build_client') as mock_build:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_build.return_value = mock_client
        
        result = await asterisk_service.connect()
        assert result is True
        assert asterisk_service._connected_ok is True


@pytest.mark.asyncio
async def test_connect_failure(asterisk_service):
    """Test failed connection to Asterisk ARI"""
    with patch.object(asterisk_service, '_build_client') as mock_build:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_build.return_value = mock_client
        
        result = await asterisk_service.connect()
        assert result is False
        assert asterisk_service._connected_ok is False


@pytest.mark.asyncio
async def test_disconnect(asterisk_service):
    """Test disconnection from Asterisk ARI"""
    mock_client = MagicMock()
    mock_client.aclose = AsyncMock()
    asterisk_service._client = mock_client
    asterisk_service._connected_ok = True
    
    await asterisk_service.disconnect()
    
    assert asterisk_service._client is None
    assert asterisk_service._connected_ok is False
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_originate_call_success(asterisk_service):
    """Test successful call origination"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"id": "test-channel"}'
    mock_client.post = AsyncMock(return_value=mock_response)
    
    asterisk_service._client = mock_client
    asterisk_service._connected_ok = True
    
    result = await asterisk_service.originate_call(
        phone_number="1234567890",
        context="outbound-ivr",
        extension="s",
        priority=1,
        timeout=30000,
        caller_id="Test Caller"
    )
    
    assert result["success"] is True
    assert result["phone_number"] == "1234567890"
    assert "channel" in result


@pytest.mark.asyncio
async def test_originate_call_not_connected(asterisk_service):
    """Test call origination when not connected"""
    asterisk_service._client = None
    asterisk_service._connected_ok = False
    
    with patch.object(asterisk_service, 'connect', return_value=False):
        result = await asterisk_service.originate_call(
            phone_number="1234567890"
        )
        
        assert result["success"] is False
        assert "error" in result


@pytest.mark.asyncio
async def test_originate_call_ari_error(asterisk_service):
    """Test call origination with ARI error response"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_client.post = AsyncMock(return_value=mock_response)
    
    asterisk_service._client = mock_client
    asterisk_service._connected_ok = True
    
    result = await asterisk_service.originate_call(
        phone_number="1234567890"
    )
    
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_is_connected(asterisk_service):
    """Test connection status check"""
    asterisk_service._client = None
    asterisk_service._connected_ok = False
    assert await asterisk_service.is_connected() is False
    
    asterisk_service._client = MagicMock()
    asterisk_service._connected_ok = True
    assert await asterisk_service.is_connected() is True
