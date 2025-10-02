from fastapi import FastAPI, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import uvicorn
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from typing import Optional

from config.settings import get_settings
from app.services.asterisk import get_asterisk_service, AsteriskService
from app.database import get_db, engine
from app.models import Base
from app.routes import interaction
from app.routes import auth as auth_routes
from app.middleware.logging_middleware import JSONLoggingMiddleware
from loguru import logger
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time
from collections import defaultdict, deque

settings = get_settings()


PLACEHOLDER_SECRET_VALUES = {"your-secret-key-change-in-production", "CHANGE_ME_STRONG_HEX_64"}
if settings.secret_key in PLACEHOLDER_SECRET_VALUES and not settings.debug:
    raise RuntimeError("SECRET_KEY is a placeholder; set a strong value before running in production.")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        # Attach to state for access in routes/logging
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """Very simple in-memory rate limiter for sensitive endpoints like /api/v2/token.
    Not distributed; for multi-instance deployments replace with Redis or Traefik plugin.
    """

    def __init__(self, app, limit: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds
        self.buckets: defaultdict[str, deque] = defaultdict(deque)
        self.protected_paths = {"/api/v2/token"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.protected_paths:
            ip = request.client.host if request.client else "unknown"
            now = time.time()
            bucket = self.buckets[ip]
            # purge old
            while bucket and now - bucket[0] > self.window:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return Response(status_code=429, content="Too Many Requests")
            bucket.append(now)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manager life cycle of the application"""
    # Startup
    logger.info("Starting Contact Center API...")

    # Create tables only in debug mode; in production use Alembic migrations
    if settings.debug and not settings.disable_db and engine is not None:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized (debug)")

    # Connect to Asterisk ARI (not critical in test/dev)
    asterisk_service = await get_asterisk_service()
    try:
        connected = await asterisk_service.connect()
        if connected:
            logger.info("Connected to Asterisk ARI")
        else:
            logger.warning("Asterisk ARI connection not established (test/dev mode or error)")
    except Exception as e:
        logger.error(f"Error connecting to ARI: {e}")

    yield
    
    # Shutdown
    logger.info("Shutting down Contact Center API...")

    # Disconnect from Asterisk ARI
    try:
        await asterisk_service.disconnect()
        logger.info("Disconnected from Asterisk ARI")
    except Exception:
        pass


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API REST for Contact Center with Asterisk - Outbound Call",
    docs_url=("/docs" if settings.docs_enabled else None),
    redoc_url=("/redoc" if settings.docs_enabled else None),
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware (structured JSON)
app.add_middleware(JSONLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SimpleRateLimitMiddleware)

# Include routes
app.include_router(interaction.router, prefix="/api/v2", tags=["Interaction"])
app.include_router(auth_routes.router, prefix="/api/v2", tags=["Auth"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Contact Center API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "auth_token": "/api/v2/token"
    }


@app.get("/metrics")
async def metrics():
    """Endpoint for Prometheus metrics"""
    if not settings.metrics_enabled:
        return Response(status_code=404)
    data = generate_latest()
    resp = Response(content=data, media_type=CONTENT_TYPE_LATEST)
    # Avoid caching metrics
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/health")
async def health_check(
    asterisk_service: AsteriskService = Depends(get_asterisk_service),
    db: Optional[Session] = Depends(get_db)
):
    """System health check endpoint"""
    # Check database connection
    if settings.disable_db or db is None:
        db_status = "disabled"
    else:
        try:
            db.execute("SELECT 1")
            db_status = "ok"
        except Exception as e:
            db_status = f"error: {str(e)}"

    # Check connection to Asterisk (ARI)
    asterisk_status = "ok" if await asterisk_service.is_connected() else "disconnected"
    
    return {
        "status": "ok",
        "version": settings.app_version,
        "database": db_status,
        "asterisk": asterisk_status,
        "services": {
            "api": "running",
            "database": db_status,
            "asterisk_ari": asterisk_status
        }
    }


if __name__ == "__main__":
    # Basic Loguru configuration; in production, route to file or stdout for Loki/ELK
    logger.remove()
    logger.add(lambda msg: print(msg, end=""))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )