"""
Distributed locking using Redis

Ensures only one instance runs background tasks in multi-instance deployments.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from loguru import logger

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class DistributedLock:
    """Redis-based distributed lock for coordinating background tasks"""
    
    def __init__(self, redis_url: str):
        self.redis: Optional[redis.Redis] = None
        self.redis_url = redis_url
        self._redis_available = REDIS_AVAILABLE
    
    async def connect(self):
        """Initialize Redis connection"""
        if not self._redis_available:
            logger.warning("Redis not available - distributed locking disabled")
            return False
        
        if not self.redis:
            try:
                self.redis = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis.ping()
                logger.info("Redis distributed lock initialized")
                return True
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self.redis = None
                return False
        return True
    
    @asynccontextmanager
    async def acquire(
        self,
        lock_name: str,
        timeout: int = 300,
        blocking_timeout: int = 10
    ):
        """
        Acquire distributed lock
        
        Args:
            lock_name: Unique lock identifier
            timeout: Lock expiry in seconds (prevents deadlock)
            blocking_timeout: Max time to wait for lock acquisition
            
        Yields:
            None when lock is acquired
            
        Raises:
            TimeoutError: If lock cannot be acquired within blocking_timeout
        """
        if not await self.connect():
            # Redis unavailable - proceed without lock (fail-open)
            logger.warning(f"Redis unavailable, proceeding without lock: {lock_name}")
            yield
            return
        
        lock_key = f"lock:{lock_name}"
        acquired = False
        
        try:
            # Try to acquire lock with SET NX EX (atomic operation)
            acquired = await self.redis.set(
                lock_key,
                "locked",
                nx=True,  # Only set if not exists
                ex=timeout  # Auto-expire to prevent deadlock
            )
            
            if not acquired:
                # Wait for lock to be released
                start = asyncio.get_event_loop().time()
                while not acquired and (asyncio.get_event_loop().time() - start) < blocking_timeout:
                    await asyncio.sleep(1)
                    acquired = await self.redis.set(lock_key, "locked", nx=True, ex=timeout)
            
            if not acquired:
                raise TimeoutError(
                    f"Could not acquire lock '{lock_name}' within {blocking_timeout}s"
                )
            
            logger.debug(f"Acquired distributed lock: {lock_name}")
            yield
            
        finally:
            if acquired and self.redis:
                try:
                    await self.redis.delete(lock_key)
                    logger.debug(f"Released distributed lock: {lock_name}")
                except Exception as e:
                    logger.error(f"Failed to release lock {lock_name}: {e}")
    
    async def shutdown(self):
        """Close Redis connection"""
        if self.redis:
            try:
                await self.redis.close()
                logger.info("Redis distributed lock connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")


def get_distributed_lock(redis_url: Optional[str] = None) -> DistributedLock:
    """
    Get distributed lock instance
    
    Args:
        redis_url: Redis connection URL (defaults to settings)
        
    Returns:
        DistributedLock instance
    """
    if redis_url is None:
        try:
            from config.settings import get_settings
            settings = get_settings()
            redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')
        except Exception:
            redis_url = 'redis://localhost:6379/0'
    
    return DistributedLock(redis_url)
