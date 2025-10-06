import json
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger


class JSONLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
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
