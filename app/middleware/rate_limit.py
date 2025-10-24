"""
Distributed rate limiting middleware using Redis

Replaces in-memory rate limiter with production-ready distributed solution.
"""
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from typing import Optional

from config.settings import get_settings
from app.services.metrics import track_rate_limit_exceeded

settings = get_settings()


class DistributedRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed rate limiter for distributed deployments
    
    Uses sliding window algorithm for accurate rate limiting across multiple instances.
    """
    
    def __init__(
        self, 
        app,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None
    ):
        super().__init__(app)
        self.limit = limit if limit is not None else settings.rate_limit_requests
        self.window = window_seconds if window_seconds is not None else settings.rate_limit_window
        
        # Endpoints that require rate limiting
        self.protected_paths = {
            "/api/v1/token",  # Authentication endpoint
            "/api/v1/interaction",  # Call origination (partial match)
            "/api/v1/calls",  # RESTful call endpoint
        }
        
        # More aggressive limits for sensitive endpoints
        self.endpoint_limits = {
            "/api/v1/token": (5, 60),  # 5 requests per minute
            "/api/v1/interaction": (30, 60),  # 30 calls per minute
            "/api/v1/calls": (30, 60),
        }
    
    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for client (IP + User-Agent hash)
        
        Using both IP and User-Agent provides better identification while
        avoiding issues with shared IPs (NAT, proxies).
        """
        # Check for real IP from proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        # Add user agent hash for better identification
        user_agent = request.headers.get("User-Agent", "")
        ua_hash = str(hash(user_agent))[:8]
        
        return f"{ip}:{ua_hash}"
    
    def _should_rate_limit(self, path: str) -> Optional[tuple[int, int]]:
        """
        Check if path should be rate limited
        
        Returns:
            (limit, window) tuple or None if no rate limit
        """
        # Exact match
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Prefix match for dynamic paths
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return self.endpoint_limits.get(protected_path, (self.limit, self.window))
        
        return None
    
    async def dispatch(self, request: Request, call_next):
        """
        Check rate limit before processing request
        """
        # Check if this endpoint requires rate limiting
        rate_limit_config = self._should_rate_limit(request.url.path)
        
        if rate_limit_config:
            limit, window = rate_limit_config
            
            try:
                # Get Redis service
                from app.services.redis_service import get_redis_service
                redis = await get_redis_service()
                
                # Check rate limit
                client_id = self._get_client_identifier(request)
                key = f"rate:{request.url.path}:{client_id}"
                
                allowed, remaining = await redis.check_rate_limit(key, limit, window)
                
                if not allowed:
                    # Rate limit exceeded
                    logger.warning(
                        "Rate limit exceeded",
                        extra={
                            "client": client_id,
                            "path": request.url.path,
                            "limit": limit,
                            "window": window
                        }
                    )
                    
                    track_rate_limit_exceeded(request.url.path)
                    
                    return Response(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content="Rate limit exceeded. Please try again later.",
                        headers={
                            "X-RateLimit-Limit": str(limit),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(window),
                            "Retry-After": str(window)
                        }
                    )
                
                # Continue to endpoint
                response = await call_next(request)
                
                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(window)
                
                return response
                
            except Exception as e:
                # If Redis is down, log error and fail open (allow request)
                logger.error(
                    "Rate limit check failed, allowing request",
                    extra={"error": str(e), "path": request.url.path}
                )
                # Continue without rate limiting
                return await call_next(request)
        
        # No rate limiting for this endpoint
        return await call_next(request)


class BruteForceProtectionMiddleware(BaseHTTPMiddleware):
    """
    Protect authentication endpoints from brute force attacks
    
    Tracks failed login attempts and temporarily locks out offending IPs.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.max_attempts = settings.max_failed_login_attempts
        self.lockout_duration = settings.login_lockout_duration
    
    async def dispatch(self, request: Request, call_next):
        """
        Check if IP is locked out before processing login attempts
        """
        # Only protect authentication endpoint
        if request.url.path != "/api/v1/token":
            return await call_next(request)
        
        try:
            from app.services.redis_service import get_redis_service
            redis = await get_redis_service()
            
            # Get client IP
            ip = request.client.host if request.client else "unknown"
            
            # Check if IP is locked out
            lockout_key = f"auth:lockout:{ip}"
            if await redis.exists(lockout_key):
                remaining_ttl = await redis._client.ttl(lockout_key)
                
                logger.warning(
                    "Locked out IP attempted login",
                    extra={"ip": ip, "remaining_seconds": remaining_ttl}
                )
                
                return Response(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=f"Too many failed login attempts. Try again in {remaining_ttl} seconds.",
                    headers={"Retry-After": str(remaining_ttl)}
                )
            
            # Process request
            response = await call_next(request)
            
            # If login failed (401), track attempt
            if response.status_code == 401:
                # Extract username from form data if available
                username = "unknown"
                if request.method == "POST":
                    try:
                        form = await request.form()
                        username = form.get("username", "unknown")
                    except Exception:
                        pass
                
                # Track failed attempt
                failed_count = await redis.track_failed_login(username, ip)
                
                logger.info(
                    "Failed login attempt",
                    extra={
                        "username": username,
                        "ip": ip,
                        "failed_count": failed_count,
                        "max_attempts": self.max_attempts
                    }
                )
                
                # Lock out if threshold exceeded
                if failed_count >= self.max_attempts:
                    await redis._client.setex(
                        lockout_key,
                        self.lockout_duration,
                        "locked"
                    )
                    
                    logger.warning(
                        "IP locked out due to excessive failed login attempts",
                        extra={
                            "ip": ip,
                            "failed_count": failed_count,
                            "lockout_duration": self.lockout_duration
                        }
                    )
                    
                    return Response(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content=f"Too many failed login attempts. Locked out for {self.lockout_duration} seconds.",
                        headers={"Retry-After": str(self.lockout_duration)}
                    )
            
            # If login succeeded (200), reset failed attempts
            elif response.status_code == 200:
                try:
                    form = await request.form()
                    username = form.get("username", "unknown")
                    await redis.reset_failed_logins(username, ip)
                except Exception:
                    pass
            
            return response
            
        except Exception as e:
            logger.error(f"Brute force protection failed: {e}")
            # Fail open - allow request
            return await call_next(request)
