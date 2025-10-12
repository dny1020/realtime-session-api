"""
Prometheus metrics tracking service for Contact Center API
"""
from prometheus_client import Counter, Gauge, Histogram
from loguru import logger


# Call lifecycle metrics
calls_originated_total = Counter(
    'calls_originated_total',
    'Total call origination attempts',
    ['status']  # success, failed
)

call_origination_latency = Histogram(
    'call_origination_latency_seconds',
    'Time to originate call via ARI',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

call_duration_seconds = Histogram(
    'call_duration_seconds',
    'Call duration distribution',
    buckets=[5, 10, 30, 60, 120, 300, 600, 1800, 3600]
)

call_state_transitions = Counter(
    'call_state_transitions_total',
    'Call state transitions',
    ['from_state', 'to_state', 'result']  # result: success, rejected
)

# ARI connection metrics
ari_http_connected = Gauge(
    'ari_http_connected',
    'ARI HTTP connection status (1=connected)'
)

ari_websocket_connected = Gauge(
    'ari_websocket_connected',
    'ARI WebSocket connection status (1=connected)'
)

ari_events_received = Counter(
    'ari_events_received_total',
    'ARI events received by type',
    ['event_type', 'processed', 'failed']
)

# Rate limiting
rate_limit_exceeded_total = Counter(
    'rate_limit_exceeded_total',
    'Requests rejected by rate limiter',
    ['endpoint']
)

# Authentication metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Authentication attempts',
    ['result']  # success, failed
)


def track_call_originated(success: bool):
    """Track call origination attempt"""
    calls_originated_total.labels(status='success' if success else 'failed').inc()


def track_auth_attempt(success: bool):
    """Track authentication attempt"""
    auth_attempts_total.labels(result='success' if success else 'failed').inc()


def track_call_duration(duration: float):
    """Track completed call duration"""
    call_duration_seconds.observe(duration)


def track_state_transition(from_state: str, to_state: str, success: bool):
    """Track call state machine transition"""
    call_state_transitions.labels(
        from_state=from_state,
        to_state=to_state,
        result='success' if success else 'rejected'
    ).inc()


def track_ari_connection(http_ok: bool, ws_ok: bool):
    """Update ARI connection status gauges"""
    ari_http_connected.set(1 if http_ok else 0)
    ari_websocket_connected.set(1 if ws_ok else 0)


def track_ari_event(event_type: str, processed: bool = False, failed: bool = False):
    """Track ARI event processing"""
    ari_events_received.labels(
        event_type=event_type,
        processed=str(processed).lower(),
        failed=str(failed).lower()
    ).inc()


def track_rate_limit_exceeded(endpoint: str):
    """Track rate limit hit"""
    rate_limit_exceeded_total.labels(endpoint=endpoint).inc()
