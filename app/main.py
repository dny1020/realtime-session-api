from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import uvicorn
from typing import Optional
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from prometheus_client import make_asgi_app
import asyncio
import json

from config.settings import get_settings
from app.services.asterisk import get_asterisk_service, AsteriskService
from app.services.redis_service import init_redis_service, close_redis_service, get_redis_service
from app.services.circuit_breaker import get_asterisk_with_circuit_breaker
from app.services.tracing import setup_tracing
from app.database import get_db, engine
from app.models import Base, CallStatus
from app.routes import interaction
from app.routes import auth as auth_routes
from app.middleware.logging_middleware import JSONLoggingMiddleware
from app.middleware.rate_limit import DistributedRateLimitMiddleware, BruteForceProtectionMiddleware
from app.services.call_state_machine import transition_call_status
from app.services.metrics import (
    track_ari_event,
    track_ari_connection,
)
from loguru import logger

settings = get_settings()


PLACEHOLDER_SECRET_VALUES = {"your-secret-key-change-in-production", "CHANGE_ME_STRONG_HEX_64"}
if settings.secret_key in PLACEHOLDER_SECRET_VALUES and not settings.debug:
    raise RuntimeError("SECRET_KEY is a placeholder; set a strong value before running in production.")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Prevent large request DoS"""
    def __init__(self, app, max_size: int = 1_000_000):  # 1MB
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            size = int(request.headers["content-length"])
            if size > self.max_size:
                return Response(
                    status_code=413,
                    content="Request too large"
                )
        return await call_next(request)


async def handle_ari_event(event: dict):
    """Handle ARI events and update call status in database with distributed locking"""
    from app.database import SessionLocal
    from app.models.call import Call
    
    event_type = event.get("type")
    
    # Track event received
    if event_type:
        track_ari_event(event_type, processed=False)
    
    if settings.disable_db:
        return
    
    channel = event.get("channel", {})
    channel_id = channel.get("id")
    
    if not channel_id:
        return
    
    # Use distributed lock to prevent race conditions
    try:
        redis = await get_redis_service()
        
        async with redis.lock(f"call:channel:{channel_id}", timeout=5, blocking_timeout=2):
            db = SessionLocal()
            try:
                call = db.query(Call).filter(Call.channel == channel_id).first()
                if not call:
                    return
                
                logger.info(f"Processing ARI event {event_type} for call {call.call_id}")
                
                # Store current version for optimistic locking check
                current_version = call.version
                
                # Update call status based on event using state machine validation
                if event_type == "StasisStart":
                    if transition_call_status(call, CallStatus.DIALING, context=f"ARI: {event_type}"):
                        call.dialed_at = datetime.now(timezone.utc)
                        call.version += 1
                        
                elif event_type == "ChannelStateChange":
                    state = channel.get("state")
                    if state == "Ringing":
                        if transition_call_status(call, CallStatus.RINGING, context=f"ARI: {event_type}"):
                            call.version += 1
                    elif state == "Up":
                        if transition_call_status(call, CallStatus.ANSWERED, context=f"ARI: {event_type}"):
                            if not call.answered_at:
                                call.answered_at = datetime.now(timezone.utc)
                            call.version += 1
                            
                elif event_type == "ChannelDestroyed":
                    cause = channel.get("cause")
                    cause_txt = channel.get("cause_txt", "")
                    
                    # Determine appropriate terminal status
                    if call.status == CallStatus.ANSWERED:
                        new_status = CallStatus.COMPLETED
                    elif "BUSY" in cause_txt.upper() or cause == 17:
                        new_status = CallStatus.BUSY
                    elif "NO_ANSWER" in cause_txt.upper() or cause == 19:
                        new_status = CallStatus.NO_ANSWER
                    else:
                        new_status = CallStatus.FAILED
                        call.failure_reason = cause_txt or f"Cause {cause}"
                    
                    if transition_call_status(call, new_status, context=f"ARI: {event_type}"):
                        call.ended_at = datetime.now(timezone.utc)
                        if call.answered_at:
                            call.duration = int((call.ended_at - call.answered_at).total_seconds())
                        call.version += 1
                
                # Optimistic locking: only commit if version hasn't changed
                db.commit()
                logger.info(f"Updated call {call.call_id} to status {call.status.value} (version {call.version})")
                
                # Mark event as successfully processed
                if event_type:
                    track_ari_event(event_type, processed=True, failed=False)
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error handling ARI event: {e}")
                
                # Mark event as failed
                if event_type:
                    track_ari_event(event_type, processed=False, failed=True)
            finally:
                db.close()
                
    except Exception as e:
        logger.error(f"Failed to acquire lock for ARI event processing: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Contact Center API...")

    # Initialize Redis service
    await init_redis_service()
    logger.info("Redis service initialized")

    # Create tables in debug mode only (production uses Alembic)
    if settings.debug and not settings.disable_db and engine:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized (debug mode)")
    
    # Check migrations (production only)
    if not settings.disable_db and not settings.debug:
        try:
            from alembic.config import Config
            from alembic.script import ScriptDirectory
            from alembic.runtime.migration import MigrationContext
            
            alembic_cfg = Config("alembic.ini")
            script = ScriptDirectory.from_config(alembic_cfg)
            
            with engine.begin() as conn:
                context = MigrationContext.configure(conn)
                current = context.get_current_revision()
                head = script.get_current_head()
                
                if current != head:
                    logger.error(
                        f"Migration mismatch! Current: {current}, Expected: {head}"
                    )
                    raise RuntimeError(
                        "Run migrations: docker-compose run --rm api alembic upgrade head"
                    )
                
                logger.info(f"Migrations OK (rev: {current})")
        except ImportError:
            logger.warning("Alembic not installed, skipping check")

    # Connect to Asterisk ARI
    asterisk_service = await get_asterisk_service()
    try:
        if await asterisk_service.connect():
            logger.info("Connected to Asterisk ARI (HTTP + WebSocket)")
            asterisk_service.register_event_handler("*", handle_ari_event)
        else:
            logger.warning("Asterisk ARI connection not established")
    except Exception as e:
        logger.error(f"Error connecting to ARI: {e}")

    yield
    
    logger.info("Shutting down Contact Center API...")
    
    # Disconnect services
    try:
        await asterisk_service.disconnect()
        logger.info("Disconnected from Asterisk ARI")
    except Exception:
        pass
    
    try:
        await close_redis_service()
        logger.info("Disconnected from Redis")
    except Exception:
        pass


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-Ready Contact Center API with Asterisk ARI",
    docs_url=("/docs" if settings.docs_enabled else None),
    redoc_url=("/redoc" if settings.docs_enabled else None),
    lifespan=lifespan,
)

# Setup OpenTelemetry tracing
setup_tracing(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Additional middleware (order matters - first added = outermost = executed first)
from starlette.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestSizeLimitMiddleware, max_size=1_000_000)

# Logging middleware (structured JSON)
app.add_middleware(JSONLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

# Distributed rate limiting (replaces in-memory version)
app.add_middleware(DistributedRateLimitMiddleware)
app.add_middleware(BruteForceProtectionMiddleware)

# Include routes
app.include_router(interaction.router, prefix="/api/v1", tags=["Interaction"])
app.include_router(auth_routes.router, prefix="/api/v1", tags=["Auth"])

# Mount Prometheus metrics endpoint
if settings.metrics_enabled:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Contact Center API",
        "version": settings.app_version,
        "docs": "/docs" if settings.docs_enabled else "disabled",
        "health": "/health",
        "readiness": "/readiness",
        "auth_token": "/api/v1/token"
    }


@app.get("/health")
async def health_check(
    asterisk_service: AsteriskService = Depends(get_asterisk_service),
    db: Optional[Session] = Depends(get_db)
):
    """System health check endpoint"""
    db_status = "disabled" if not db else "ok"
    if db:
        try:
            db.execute("SELECT 1")
        except Exception as e:
            db_status = f"error: {str(e)}"

    http_ok = asterisk_service._connected_ok
    ws_ok = asterisk_service._ws_connected
    asterisk_status = "ok" if http_ok and ws_ok else "degraded"
    
    # Check Redis
    redis_status = "ok"
    try:
        redis = await get_redis_service()
        if not await redis.is_connected():
            redis_status = "degraded"
    except Exception as e:
        redis_status = f"error: {str(e)[:30]}"
    
    # Update metrics
    track_ari_connection(http_ok, ws_ok)
    
    # Get circuit breaker state
    circuit_state = {}
    if settings.circuit_breaker_enabled:
        try:
            cb = await get_asterisk_with_circuit_breaker()
            circuit_state = cb.get_state()
        except Exception:
            pass
    
    return {
        "status": "ok" if all([
            db_status in ("ok", "disabled"),
            asterisk_status == "ok",
            redis_status == "ok"
        ]) else "degraded",
        "version": settings.app_version,
        "database": db_status,
        "redis": redis_status,
        "asterisk": {
            "status": asterisk_status,
            "http": "connected" if http_ok else "disconnected",
            "websocket": "connected" if ws_ok else "disconnected"
        },
        "circuit_breakers": circuit_state if settings.circuit_breaker_enabled else "disabled"
    }


@app.get("/readiness")
async def readiness(
    asterisk_service: AsteriskService = Depends(get_asterisk_service),
    db: Optional[Session] = Depends(get_db)
):
    """Kubernetes readiness probe - checks if ready to serve traffic"""
    checks = {}
    ready = True
    
    # Database
    if db:
        try:
            db.execute("SELECT 1")
            checks["database"] = "ready"
        except Exception as e:
            checks["database"] = f"error: {str(e)[:30]}"
            ready = False
    else:
        checks["database"] = "disabled"
    
    # Redis
    try:
        redis = await get_redis_service()
        if await redis.is_connected():
            checks["redis"] = "ready"
        else:
            checks["redis"] = "not_connected"
            ready = False
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:30]}"
        ready = False
    
    # Asterisk HTTP (required)
    if asterisk_service._connected_ok:
        checks["asterisk_http"] = "ready"
    else:
        checks["asterisk_http"] = "not_connected"
        ready = False
    
    # Asterisk WebSocket (don't fail on this - it will reconnect)
    checks["asterisk_websocket"] = "connected" if asterisk_service._ws_connected else "reconnecting"
    
    return Response(
        content=json.dumps({"ready": ready, "checks": checks}, indent=2),
        status_code=200 if ready else 503,
        media_type="application/json"
    )


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
