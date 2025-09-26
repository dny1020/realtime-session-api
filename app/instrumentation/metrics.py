from prometheus_client import Counter, Histogram

# API request metrics
REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "path", "status"],
)

# NOTE: Keep this legacy histogram for backward compatibility (no labels)
REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "Latency of API requests in seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

# New: latency by method for better breakdown with low cardinality
REQUEST_LATENCY_BY_METHOD = Histogram(
    "api_request_latency_by_method_seconds",
    "Latency of API requests in seconds, split by HTTP method",
    ["method"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

# Outbound call metrics (minimal set requested)
# WARNING: The names below include the "_total" suffix in the metric name string.
# Prometheus adds "_total" automatically when exporting Counters, which results in
# double suffixes. They are kept for backward compatibility only. Prefer the V2
# metrics defined further below and plan to remove these legacy metrics.
CALLS_LAUNCHED = Counter(
    "calls_launched_total",
    "[LEGACY] Total outbound calls launched (enqueued or originate issued)",
)
CALLS_SUCCESS = Counter(
    "calls_success_total",
    "[LEGACY] Total outbound calls successfully launched (accepted by ARI or queue)",
)
CALLS_FAILED = Counter(
    "calls_failed_total",
    "[LEGACY] Total outbound calls failed to launch",
)

# Time to launch a call (enqueue or ARI originate) - used as a proxy for avg duration at launch time
ORIGINATE_LATENCY_SECONDS = Histogram(
    "originate_latency_seconds",
    "Latency to enqueue or originate a call",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

# Requested simple names for Grafana/Prometheus dashboards
# Total call attempts (Counter automatically adds _total suffix to the exported sample)
# LEGACY: Same suffix pitfall as above
CALLS_TOTAL = Counter("calls_total", "[LEGACY] Total outbound call attempts (API-level)")

# Campaign metrics removed (single-call API scope)

# ---------------------------------------------
# V2 METRICS (Preferred)
# ---------------------------------------------

# Correctly named Counters without embedding the _total suffix in the name string.
# Use these going forward. Exported time series will end with _total as expected.
CALLS_LAUNCHED_V2 = Counter(
    "calls_launched",
    "Total outbound calls launched (enqueued or originate issued)",
)
CALLS_SUCCESS_V2 = Counter(
    "calls_success",
    "Total outbound calls successfully launched (accepted by ARI or queue)",
)
CALLS_FAILED_V2 = Counter(
    "calls_failed",
    "Total outbound calls failed to launch",
)
CALLS_V2 = Counter(
    "calls",
    "Total outbound call attempts (API-level)",
)
