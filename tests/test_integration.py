"""
Integration tests for Contact Center API with mocked Asterisk ARI

Tests cover:
- Call origination success/failure scenarios
- WebSocket event processing
- State machine validation
- Timeout handling
- Error conditions
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta
import json
import uuid

from fastapi.testclient import TestClient
from httpx import Response

from app.models import CallStatus


@pytest.fixture
def client():
    """Create test client with mocked dependencies"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


class TestCallOrigination:
    """Test call origination scenarios"""
    
    @pytest.mark.asyncio
    async def test_successful_call_origination(self):
        """Test successful call origination with valid parameters"""
        from app.services.asterisk import AsteriskService
        
        service = AsteriskService()
        
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test-channel-123"}
        mock_client.post.return_value = mock_response
        
        service._client = mock_client
        service._connected_ok = True
        
        result = await service.originate_call(
            phone_number="+1234567890",
            context="outbound-ivr",
            extension="s",
            priority=1,
            timeout=30000,
            caller_id="Test Caller"
        )
        
        assert result["success"] is True
        assert "call_id" in result
        assert result["phone_number"] == "+1234567890"
        
    @pytest.mark.asyncio
    async def test_failed_call_origination_ari_down(self):
        """Test call origination when ARI is unavailable"""
        from app.services.asterisk import AsteriskService
        
        service = AsteriskService()
        service._client = None
        service._connected_ok = False
        
        result = await service.originate_call(
            phone_number="+1234567890",
            context="outbound-ivr",
            extension="s",
            priority=1,
            timeout=30000,
            caller_id="Test Caller"
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "Unable to connect" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_origination_timeout(self):
        """Test call origination with ARI timeout"""
        from app.services.asterisk import AsteriskService
        import httpx
        
        service = AsteriskService()
        
        # Mock client that times out
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ReadTimeout("Request timed out")
        
        service._client = mock_client
        service._connected_ok = True
        
        result = await service.originate_call(
            phone_number="+1234567890",
            context="outbound-ivr",
            extension="s",
            priority=1,
            timeout=30000,
            caller_id="Test Caller"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_call_origination_ari_error(self):
        """Test call origination when ARI returns error"""
        from app.services.asterisk import AsteriskService
        
        service = AsteriskService()
        
        # Mock 503 response
        mock_client = AsyncMock()
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 503
        mock_response.text = "Service temporarily unavailable"
        mock_client.post.return_value = mock_response
        
        service._client = mock_client
        service._connected_ok = True
        
        result = await service.originate_call(
            phone_number="+1234567890",
            context="outbound-ivr",
            extension="s",
            priority=1,
            timeout=30000,
            caller_id="Test Caller"
        )
        
        assert result["success"] is False


class TestWebSocketReconnection:
    """Test WebSocket reconnection logic"""
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_on_close(self):
        """Test that WebSocket reconnects after connection closed"""
        from app.services.asterisk import AsteriskService
        from websockets.exceptions import ConnectionClosed
        
        service = AsteriskService()
        service._should_reconnect = True
        
        # Create a properly mocked async iterator
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                
            def __aiter__(self):
                return self
                
            async def __anext__(self):
                # Immediately raise ConnectionClosed to simulate disconnect
                raise ConnectionClosed(None, None)
        
        mock_ws = MockWebSocket()
        
        # Track reconnection attempts
        reconnect_attempts = []
        
        async def tracked_reconnect():
            reconnect_attempts.append(1)
            return False  # Fail to prevent infinite loop
        
        service._ensure_ws_connection = tracked_reconnect
        service._ws = mock_ws
        service._ws_connected = True
        
        # Start listener (will attempt reconnect)
        task = asyncio.create_task(service._listen_events_with_reconnect())
        
        # Let it try once
        await asyncio.sleep(0.2)
        service._should_reconnect = False
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Should have attempted reconnection
        assert len(reconnect_attempts) > 0
    
    @pytest.mark.asyncio
    async def test_websocket_exponential_backoff(self):
        """Test that WebSocket uses exponential backoff"""
        from app.services.asterisk import AsteriskService
        import time
        
        service = AsteriskService()
        
        # Mock websockets.connect to always fail
        with patch('websockets.connect', side_effect=Exception("Connection refused")):
            start_time = time.time()
            result = await service._ensure_ws_connection()
            elapsed = time.time() - start_time
            
            # Should have tried multiple times with backoff (1+2+5+10+30 = 48s minimum)
            assert result is False
            assert elapsed >= 48  # At least waited through backoff delays


class TestStateMachine:
    """Test call state machine validation"""
    
    def test_valid_state_transitions(self):
        """Test that valid state transitions are allowed"""
        from app.services.call_state_machine import CallStateMachine
        
        machine = CallStateMachine()
        
        # Valid transitions
        assert machine.is_valid_transition(CallStatus.PENDING, CallStatus.DIALING) is True
        assert machine.is_valid_transition(CallStatus.DIALING, CallStatus.RINGING) is True
        assert machine.is_valid_transition(CallStatus.RINGING, CallStatus.ANSWERED) is True
        assert machine.is_valid_transition(CallStatus.ANSWERED, CallStatus.COMPLETED) is True
    
    def test_invalid_state_transitions(self):
        """Test that invalid state transitions are rejected"""
        from app.services.call_state_machine import CallStateMachine
        
        machine = CallStateMachine()
        
        # Invalid transitions
        assert machine.is_valid_transition(CallStatus.PENDING, CallStatus.ANSWERED) is False
        assert machine.is_valid_transition(CallStatus.COMPLETED, CallStatus.DIALING) is False
        assert machine.is_valid_transition(CallStatus.FAILED, CallStatus.RINGING) is False
    
    def test_terminal_state_enforcement(self):
        """Test that terminal states cannot transition"""
        from app.services.call_state_machine import CallStateMachine
        
        machine = CallStateMachine()
        
        # Terminal states
        terminal = [CallStatus.COMPLETED, CallStatus.BUSY, CallStatus.NO_ANSWER, CallStatus.FAILED]
        
        for status in terminal:
            is_valid, error = machine.can_transition(status, CallStatus.DIALING)
            assert is_valid is False
            assert "terminal state" in error.lower()
    
    def test_idempotent_transitions(self):
        """Test that same-state transitions are allowed (idempotent)"""
        from app.services.call_state_machine import CallStateMachine
        
        machine = CallStateMachine()
        
        # Same state should always be valid
        for status in CallStatus:
            assert machine.is_valid_transition(status, status) is True
    
    def test_transition_with_mock_call(self):
        """Test state transition with mock call object"""
        from app.services.call_state_machine import transition_call_status
        
        # Create mock call
        mock_call = Mock()
        mock_call.call_id = str(uuid.uuid4())
        mock_call.status = CallStatus.PENDING
        
        # Valid transition
        result = transition_call_status(mock_call, CallStatus.DIALING, context="test")
        assert result is True
        assert mock_call.status == CallStatus.DIALING
        
        # Invalid transition
        result = transition_call_status(mock_call, CallStatus.COMPLETED, context="test")
        assert result is False
        assert mock_call.status == CallStatus.DIALING  # Unchanged


class TestARIEventProcessing:
    """Test ARI event processing and state updates"""
    
    @pytest.mark.asyncio
    async def test_stasis_start_event(self, mock_db_session):
        """Test processing of StasisStart event"""
        from app.main import handle_ari_event
        from app.models.call import Call
        
        # Create mock call
        mock_call = Mock(spec=Call)
        mock_call.call_id = str(uuid.uuid4())
        mock_call.status = CallStatus.PENDING
        mock_call.dialed_at = None
        
        # Setup mock query
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_call
        
        event = {
            "type": "StasisStart",
            "channel": {
                "id": "test-channel-123",
                "state": "Ring"
            }
        }
        
        with patch('app.database.SessionLocal', return_value=mock_db_session):
            with patch('app.main.settings.disable_db', False):
                await handle_ari_event(event)
        
        # Should have transitioned to DIALING and set dialed_at
        assert mock_call.dialed_at is not None
        mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_channel_answered_event(self, mock_db_session):
        """Test processing of channel answered event"""
        from app.main import handle_ari_event
        from app.models.call import Call
        
        mock_call = Mock(spec=Call)
        mock_call.call_id = str(uuid.uuid4())
        mock_call.status = CallStatus.RINGING
        mock_call.answered_at = None
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_call
        
        event = {
            "type": "ChannelStateChange",
            "channel": {
                "id": "test-channel-123",
                "state": "Up"
            }
        }
        
        with patch('app.database.SessionLocal', return_value=mock_db_session):
            with patch('app.main.settings.disable_db', False):
                await handle_ari_event(event)
        
        assert mock_call.answered_at is not None
        mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_channel_destroyed_completed(self, mock_db_session):
        """Test call completion on channel destroyed"""
        from app.main import handle_ari_event
        from app.models.call import Call
        
        mock_call = Mock(spec=Call)
        mock_call.call_id = str(uuid.uuid4())
        mock_call.status = CallStatus.ANSWERED
        mock_call.answered_at = datetime.utcnow() - timedelta(seconds=30)
        mock_call.ended_at = None
        mock_call.duration = None
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_call
        
        event = {
            "type": "ChannelDestroyed",
            "channel": {
                "id": "test-channel-123",
                "cause": 16,
                "cause_txt": "Normal Clearing"
            }
        }
        
        with patch('app.database.SessionLocal', return_value=mock_db_session):
            with patch('app.main.settings.disable_db', False):
                await handle_ari_event(event)
        
        assert mock_call.ended_at is not None
        assert mock_call.duration is not None
        assert mock_call.duration == 30
        mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_channel_destroyed_busy(self, mock_db_session):
        """Test busy status on channel destroyed"""
        from app.main import handle_ari_event
        from app.models.call import Call
        
        mock_call = Mock(spec=Call)
        mock_call.call_id = str(uuid.uuid4())
        mock_call.status = CallStatus.DIALING
        mock_call.ended_at = None
        mock_call.answered_at = None
        mock_call.failure_reason = None
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_call
        
        event = {
            "type": "ChannelDestroyed",
            "channel": {
                "id": "test-channel-123",
                "cause": 17,
                "cause_txt": "User busy"
            }
        }
        
        with patch('app.database.SessionLocal', return_value=mock_db_session):
            with patch('app.main.settings.disable_db', False):
                await handle_ari_event(event)
        
        assert mock_call.ended_at is not None
        mock_db_session.commit.assert_called()


class TestMetrics:
    """Test Prometheus metrics tracking"""
    
    def test_call_origination_metrics(self):
        """Test that call origination is tracked"""
        from app.services.metrics import track_call_originated, calls_originated_total
        
        # Get initial value
        initial_success = calls_originated_total.labels(status='success')._value.get()
        initial_failed = calls_originated_total.labels(status='failed')._value.get()
        
        # Track successful call
        track_call_originated(True)
        assert calls_originated_total.labels(status='success')._value.get() == initial_success + 1
        
        # Track failed call
        track_call_originated(False)
        assert calls_originated_total.labels(status='failed')._value.get() == initial_failed + 1
    
    def test_state_transition_metrics(self):
        """Test that state transitions are tracked"""
        from app.services.metrics import track_state_transition, call_state_transitions
        
        # Track successful transition
        track_state_transition('pending', 'dialing', True)
        
        # Track rejected transition
        track_state_transition('completed', 'dialing', False)
        
        # Metrics should be incremented
        assert call_state_transitions.labels(
            from_state='pending',
            to_state='dialing',
            result='success'
        )._value.get() > 0
    
    def test_ari_connection_metrics(self):
        """Test ARI connection status tracking"""
        from app.services.metrics import track_ari_connection, ari_http_connected, ari_websocket_connected
        
        # Both connected
        track_ari_connection(True, True)
        assert ari_http_connected._value.get() == 1
        assert ari_websocket_connected._value.get() == 1
        
        # HTTP connected, WS disconnected
        track_ari_connection(True, False)
        assert ari_http_connected._value.get() == 1
        assert ari_websocket_connected._value.get() == 0
        
        # Both disconnected
        track_ari_connection(False, False)
        assert ari_http_connected._value.get() == 0
        assert ari_websocket_connected._value.get() == 0


class TestAPIEndpoints:
    """Test API endpoints with authentication"""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "database" in data
        assert "asterisk" in data
    
    def test_originate_without_auth(self, client):
        """Test that origination requires authentication"""
        response = client.post("/api/v1/interaction/1234567890")
        assert response.status_code == 401
    
    def test_status_without_auth(self, client):
        """Test that status check requires authentication"""
        response = client.get("/api/v1/status/test-call-id")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
