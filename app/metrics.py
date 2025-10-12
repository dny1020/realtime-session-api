"""
Prometheus metrics for Contact Center API

Tracks:
- Call origination attempts/success/failures
- Call status distribution
- ARI connection health
- API response times
"""
from prometheus_client import Counter, Gauge, Histogram, Info
from functools import wraps
import time
from typing import Callable

# Application info
app_info = Info('contact_center_api', 'Contact Center API information')
app_info.info({
    'version': '1.0.0',
    'service': 'contact-center-api'
})

# Call Metrics
calls_originated_total = Counter(
    'calls_originated_total',
    'Total number of call origination attempts',
    ['status']  # 'success' or 'failed'
)

calls_by_status = Gauge(
    'calls_by_status',
    'Current number of calls in each status',
    ['status']
)

call_duration_seconds = Histogram(
    'call_duration_seconds',
    'Call duration in seconds',
    buckets=[5, 10, 30, 60, 120, 300, 600, 1800, 3600]
)

call_origination_latency = Histogram(
    'call_origination_latency_seconds',
    'Time to originate call via ARI',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ARI Connection Metrics
ari_http_connected = Gauge(
    'ari_http_connected',
    'ARI HTTP connection status (1=connected, 0=disconnected)'
)

ari_websocket_connected = Gauge(
    'ari_websocket_connected',
    'ARI WebSocket connection status (1=connected, 0=disconnected)'
)

ari_websocket_reconnections = Counter(
    'ari_websocket_reconnections_total',
    'Total WebSocket reconnection attempts'
)

ari_events_received = Counter(
    'ari_events_received_total',
    'Total ARI events received',
    ['event_type']
)

ari_events_processed = Counter(
    'ari_events_processed_total',
    'Total ARI events successfully processed',
    ['event_type']
)

ari_events_failed = Counter(
    'ari_events_failed_total',
    'Total ARI events that failed processing',
    ['event_type']
)

# API Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Database Metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Authentication Metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['result']  # 'success' or 'failed'
)

auth_tokens_issued = Counter(
    'auth_tokens_issued_total',
    'Total JWT tokens issued'
)

rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Total requests rejected due to rate limiting',
    ['endpoint']
)

# State Machine Metrics
state_transitions_total = Counter(
    'call_state_transitions_total',
    'Total call state transitions',
    ['from_state', 'to_state', 'result']  # result: 'success' or 'rejected'
)

invalid_state_transitions = Counter(
    'call_invalid_state_transitions_total',
    'Invalid state transition attempts',
    ['from_state', 'to_state']
)


def track_call_status(status: str, count: int = 1):
    """Update gauge for call status distribution"""
    calls_by_status.labels(status=status).set(count)


def track_call_originated(success: bool):
    """Track call origination attempt"""
    status = 'success' if success else 'failed'
    calls_originated_total.labels(status=status).inc()


def track_call_duration(duration_seconds: float):
    """Track call duration"""
    call_duration_seconds.observe(duration_seconds)


def track_ari_connection(http_connected: bool, ws_connected: bool):
    """Track ARI connection status"""
    ari_http_connected.set(1 if http_connected else 0)
    ari_websocket_connected.set(1 if ws_connected else 0)


def track_ari_event(event_type: str, processed: bool = True, failed: bool = False):
    """Track ARI event processing"""
    ari_events_received.labels(event_type=event_type).inc()
    if processed:
        ari_events_processed.labels(event_type=event_type).inc()
    if failed:
        ari_events_failed.labels(event_type=event_type).inc()


def track_state_transition(from_state: str, to_state: str, success: bool):
    """Track call state transition"""
    result = 'success' if success else 'rejected'
    state_transitions_total.labels(
        from_state=from_state,
        to_state=to_state,
        result=result
    ).inc()
    
    if not success:
        invalid_state_transitions.labels(
            from_state=from_state,
            to_state=to_state
        ).inc()


def track_auth_attempt(success: bool):
    """Track authentication attempt"""
    result = 'success' if success else 'failed'
    auth_attempts_total.labels(result=result).inc()
    if success:
        auth_tokens_issued.inc()


def track_rate_limit_hit(endpoint: str):
    """Track rate limit exceeded"""
    rate_limit_exceeded.labels(endpoint=endpoint).inc()


def time_operation(metric: Histogram, *labels):
    """Decorator to time operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metric.labels(*labels).observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metric.labels(*labels).observe(duration)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
