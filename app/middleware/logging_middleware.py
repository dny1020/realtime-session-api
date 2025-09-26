import json
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger

from app.instrumentation.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    REQUEST_LATENCY_BY_METHOD,
)
from config.settings import get_settings


class JSONLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        start = time.perf_counter()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            # Keep default 500 for unhandled exceptions; re-raise after logging in finally
            raise
        finally:
            elapsed = time.perf_counter() - start
            # Prefer low-cardinality route pattern over raw path
            route = request.scope.get("route")
            path_template = getattr(route, "path", None)
            path = path_template or request.url.path
            method = request.method

            # Update Prometheus metrics when enabled
            if settings.metrics_enabled:
                # Avoid counting internal/infra endpoints to reduce noise/cardinality
                if not (path.startswith("/metrics") or path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi")):
                    try:
                        REQUEST_COUNT.labels(method=method, path=path, status=str(status_code)).inc()
                        REQUEST_LATENCY.observe(elapsed)  # legacy, no labels
                        REQUEST_LATENCY_BY_METHOD.labels(method=method).observe(elapsed)
                    except Exception:
                        # Never break requests due to metrics errors
                        pass

            # Structured JSON log
            log_entry = {
                "message": "http_request",
                "method": method,
                "path": path,
                "status": status_code,
                "duration_ms": round(elapsed * 1000, 2),
            }
            try:
                logger.info(json.dumps(log_entry))
            except Exception:
                # Fallback if logger isn't initialized; print JSON
                print(json.dumps(log_entry))
