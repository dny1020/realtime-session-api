"""
Redis service for distributed caching, locking, and rate limiting
"""
import json
from typing import Optional, Any
from datetime import timedelta
from contextlib import asynccontextmanager
import redis.asyncio as redis
from loguru import logger

from config.settings import get_settings

settings = get_settings()


class RedisService:
    """Redis service for distributed operations"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self._pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=50,
                decode_responses=True,
                socket_keepalive=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._client.ping()
            logger.info("Connected to Redis", extra={"url": settings.redis_url})
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        logger.info("Disconnected from Redis")
    
    async def is_connected(self) -> bool:
        """Check if Redis is connected"""
        try:
            if self._client:
                await self._client.ping()
                return True
        except Exception:
            pass
        return False
    
    # ==================== CACHING ====================
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(f"Redis GET failed: {e}")
            return None
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from cache"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode JSON for key: {key}")
        return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL (seconds)"""
        try:
            if ttl:
                await self._client.setex(key, ttl, value)
            else:
                await self._client.set(key, value)
            return True
        except Exception as e:
            logger.warning(f"Redis SET failed: {e}")
            return False
    
    async def set_json(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set JSON value in cache"""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, ttl)
        except Exception as e:
            logger.warning(f"Redis SET JSON failed: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DELETE failed: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self._client.exists(key) > 0
        except Exception:
            return False
    
    # ==================== DISTRIBUTED LOCKING ====================
    
    @asynccontextmanager
    async def lock(
        self, 
        resource: str, 
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: Optional[float] = None
    ):
        """
        Distributed lock context manager
        
        Usage:
            async with redis_service.lock("call:123", timeout=5):
                # Critical section - only one process executes this
                ...
        """
        lock = self._client.lock(
            f"lock:{resource}",
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout
        )
        
        acquired = False
        try:
            acquired = await lock.acquire()
            if not acquired:
                raise LockError(f"Failed to acquire lock for: {resource}")
            
            logger.debug(f"Acquired lock: {resource}")
            yield lock
            
        finally:
            if acquired:
                try:
                    await lock.release()
                    logger.debug(f"Released lock: {resource}")
                except Exception as e:
                    logger.warning(f"Failed to release lock {resource}: {e}")
    
    # ==================== RATE LIMITING ====================
    
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window: int
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded using sliding window
        
        Args:
            key: Rate limit key (e.g., "rate:token:/api/v1/token:192.168.1.1")
            limit: Max requests allowed
            window: Time window in seconds
            
        Returns:
            (allowed, remaining): Whether request is allowed and remaining quota
        """
        try:
            # Use Redis pipeline for atomic operations
            pipe = self._client.pipeline()
            now = await self._client.time()
            current_time = now[0]  # Unix timestamp
            
            window_start = current_time - window
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            # Count current requests in window
            pipe.zcard(key)
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            # Set expiry
            pipe.expire(key, window + 1)
            
            results = await pipe.execute()
            current_count = results[1]  # Count after removing old entries
            
            allowed = current_count < limit
            remaining = max(0, limit - current_count - 1)
            
            return allowed, remaining
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if Redis is down
            return True, limit
    
    # ==================== JWT BLACKLIST ====================
    
    async def blacklist_token(self, jti: str, exp: int) -> bool:
        """
        Blacklist a JWT token
        
        Args:
            jti: JWT ID (unique token identifier)
            exp: Token expiration timestamp
            
        Returns:
            True if blacklisted successfully
        """
        try:
            # Calculate TTL until token expires
            import time
            ttl = max(1, exp - int(time.time()))
            
            await self._client.setex(
                f"blacklist:jwt:{jti}",
                ttl,
                "revoked"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False
    
    async def is_token_blacklisted(self, jti: str) -> bool:
        """Check if JWT token is blacklisted"""
        try:
            return await self._client.exists(f"blacklist:jwt:{jti}") > 0
        except Exception:
            # Fail closed - if Redis is down, assume token is blacklisted for safety
            return True
    
    # ==================== AUTH TRACKING ====================
    
    async def track_failed_login(self, username: str, ip: str) -> int:
        """
        Track failed login attempt
        
        Returns:
            Number of failed attempts in the last hour
        """
        try:
            key = f"auth:failed:{username}:{ip}"
            pipe = self._client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 3600)  # 1 hour
            results = await pipe.execute()
            return results[0]
        except Exception as e:
            logger.error(f"Failed to track login: {e}")
            return 0
    
    async def reset_failed_logins(self, username: str, ip: str) -> bool:
        """Reset failed login counter after successful login"""
        try:
            await self._client.delete(f"auth:failed:{username}:{ip}")
            return True
        except Exception:
            return False


class LockError(Exception):
    """Raised when distributed lock cannot be acquired"""
    pass


# Global Redis service instance
_redis_service: Optional[RedisService] = None


async def get_redis_service() -> RedisService:
    """Get Redis service instance (dependency injection)"""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
        await _redis_service.connect()
    return _redis_service


async def init_redis_service():
    """Initialize Redis service at startup"""
    global _redis_service
    _redis_service = RedisService()
    await _redis_service.connect()
    return _redis_service


async def close_redis_service():
    """Close Redis service at shutdown"""
    global _redis_service
    if _redis_service:
        await _redis_service.disconnect()
        _redis_service = None
