"""
Redis-based distributed rate limiter
Replaces in-memory rate limiter for multi-instance deployments
"""
import time
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
from loguru import logger
from config.settings import get_settings

settings = get_settings()


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed rate limiter using Redis
    
    Features:
    - Works across multiple API instances
    - Sliding window algorithm
    - Per-IP rate limiting
    - Configurable limits per endpoint
    """
    
    def __init__(
        self, 
        app, 
        limit: int = None, 
        window: int = None,
        redis_url: str = None
    ):
        super().__init__(app)
        self.limit = limit if limit is not None else settings.rate_limit_requests
        self.window = window if window is not None else settings.rate_limit_window
        self.redis: Optional[redis.Redis] = None
        self.redis_url = redis_url or settings.redis_url
        
        # Endpoints to protect (add more as needed)
        self.protected_paths = {
            "/api/v1/token": {"limit": 10, "window": 60},  # 10 req/min for auth
            "/api/v1/interaction": {"limit": 100, "window": 60},  # 100 req/min for calls
        }
    
    async def startup(self):
        """Initialize Redis connection on startup"""
        try:
            self.redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            await self.redis.ping()
            logger.info("Redis rate limiter initialized")
        except Exception as e:
            logger.error(f"Redis rate limiter connection failed: {e}")
            self.redis = None
    
    async def shutdown(self):
        """Close Redis connection on shutdown"""
        if self.redis:
            await self.redis.close()
            self.redis = None
    
    def _get_rate_limit_config(self, path: str) -> dict:
        """Get rate limit configuration for specific path"""
        # Check for exact match
        if path in self.protected_paths:
            return self.protected_paths[path]
        
        # Check for prefix match (e.g., /api/v1/interaction/+123456789)
        for protected_path, config in self.protected_paths.items():
            if path.startswith(protected_path):
                return config
        
        # Default limits
        return {"limit": self.limit, "window": self.window}
    
    async def dispatch(self, request: Request, call_next):
        """
        Check rate limit before processing request
        
        Uses sliding window algorithm with Redis:
        1. Use sorted set with timestamps as scores
        2. Remove old entries outside window
        3. Count remaining entries
        4. Allow if under limit
        """
        path = request.url.path
        
        # Only rate limit protected paths
        should_limit = any(
            path.startswith(protected) for protected in self.protected_paths.keys()
        )
        
        if not should_limit:
            return await call_next(request)
        
        # Check if Redis is available
        if not self.redis:
            # Fail open: allow request if Redis is unavailable
            logger.warning("Redis unavailable, rate limiting disabled")
            return await call_next(request)
        
        # Get client IP
        ip = request.client.host if request.client else "unknown"
        
        # Build rate limit key
        config = self._get_rate_limit_config(path)
        limit = config["limit"]
        window = config["window"]
        key = f"ratelimit:{path}:{ip}"
        
        try:
            now = time.time()
            window_start = now - window
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # 1. Remove entries older than window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # 2. Count current entries
            pipe.zcard(key)
            
            # 3. Add current request
            pipe.zadd(key, {str(now): now})
            
            # 4. Set expiry to window duration
            pipe.expire(key, window + 10)  # +10s buffer
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]  # Result of zcard
            
            if current_count >= limit:
                # Rate limit exceeded
                ttl = await self.redis.ttl(key)
                
                # Track metric
                from app.services.metrics import track_rate_limit_exceeded
                track_rate_limit_exceeded(path)
                
                logger.warning(
                    f"Rate limit exceeded for {ip} on {path}: "
                    f"{current_count}/{limit} in {window}s window"
                )
                
                return Response(
                    status_code=429,
                    content='{"error": "Too Many Requests", "detail": "Rate limit exceeded"}',
                    media_type="application/json",
                    headers={
                        "Retry-After": str(ttl if ttl > 0 else window),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(now + ttl)) if ttl > 0 else str(int(now + window)),
                    }
                )
            
            # Allow request and add rate limit headers
            response = await call_next(request)
            
            # Add rate limit info to response headers
            remaining = max(0, limit - current_count - 1)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(now + window))
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open: allow request on error
            return await call_next(request)


# Global instance
_rate_limiter: Optional[RedisRateLimitMiddleware] = None


def get_rate_limiter(app) -> RedisRateLimitMiddleware:
    """Get or create global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimitMiddleware(app)
    return _rate_limiter
