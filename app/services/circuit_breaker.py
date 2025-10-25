"""
Circuit breaker wrapper for Asterisk ARI service

Prevents cascading failures when Asterisk is degraded or down.
"""
from typing import Optional
from datetime import timedelta
from aiobreaker import CircuitBreaker, CircuitBreakerError
from loguru import logger

from app.services.asterisk import AsteriskService


class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    FAIL_THRESHOLD = 5  # Open after 5 failures
    SUCCESS_THRESHOLD = 2  # Close after 2 successes
    TIMEOUT = timedelta(seconds=60)  # Try again after 60 seconds
    EXPECTED_EXCEPTIONS = (Exception,)  # All exceptions count as failures


class AsteriskCircuitBreaker:
    """
    Wraps AsteriskService with circuit breaker pattern
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(self, asterisk_service: AsteriskService):
        self.service = asterisk_service
        
        # Create circuit breakers for each operation type
        self.originate_breaker = CircuitBreaker(
            fail_max=CircuitBreakerConfig.FAIL_THRESHOLD,
            timeout_duration=CircuitBreakerConfig.TIMEOUT,
            name="asterisk_originate"
        )
        
        self.hangup_breaker = CircuitBreaker(
            fail_max=CircuitBreakerConfig.FAIL_THRESHOLD,
            timeout_duration=CircuitBreakerConfig.TIMEOUT,
            name="asterisk_hangup"
        )
    
    def _on_breaker_open(self, breaker: CircuitBreaker):
        """Called when circuit opens (too many failures)"""
        logger.warning(
            f"Circuit breaker OPENED for {breaker.name}",
            extra={
                "fail_count": breaker.fail_counter,
                "threshold": breaker.fail_max
            }
        )
    
    def _on_breaker_close(self, breaker: CircuitBreaker):
        """Called when circuit closes (service recovered)"""
        logger.info(f"Circuit breaker CLOSED for {breaker.name}")
    
    async def originate_call(self, *args, **kwargs):
        """
        Originate call with circuit breaker protection
        
        Returns error immediately if circuit is open
        """
        try:
            return await self.originate_breaker.call_async(
                self.service.originate_call,
                *args,
                **kwargs
            )
        except CircuitBreakerError as e:
            # Circuit is open - service is degraded
            logger.error(
                "Circuit breaker OPEN - preventing call origination",
                extra={
                    "state": self.originate_breaker.current_state,
                    "error": str(e)
                }
            )
            
            # Return graceful error response
            return {
                "success": False,
                "error": "Service temporarily unavailable",
                "details": "Asterisk service is degraded, please try again later"
            }
        except Exception as e:
            # Other exceptions - let circuit breaker track and re-raise
            logger.error(
                "Call origination failed",
                extra={
                    "state": self.originate_breaker.current_state,
                    "error": str(e)
                }
            )
            # Return error response but let exception propagate for circuit breaker
            raise
    
    async def hangup_channel(self, *args, **kwargs):
        """
        Hangup channel with circuit breaker protection
        """
        try:
            return await self.hangup_breaker.call_async(
                self.service.hangup_channel,
                *args,
                **kwargs
            )
        except Exception as e:
            logger.error(
                "Circuit breaker prevented hangup",
                extra={
                    "state": self.hangup_breaker.current_state,
                    "error": str(e)
                }
            )
            
            return {
                "success": False,
                "error": "Service temporarily unavailable"
            }
    
    def get_state(self) -> dict:
        """Get current circuit breaker states"""
        return {
            "originate": {
                "state": self.originate_breaker.current_state,
                "fail_count": self.originate_breaker.fail_counter,
                "last_failure": getattr(self.originate_breaker, 'last_failure_time', None)
            },
            "hangup": {
                "state": self.hangup_breaker.current_state,
                "fail_count": self.hangup_breaker.fail_counter,
                "last_failure": getattr(self.hangup_breaker, 'last_failure_time', None)
            }
        }


# Global instance
_circuit_breaker: Optional[AsteriskCircuitBreaker] = None


async def get_asterisk_with_circuit_breaker() -> AsteriskCircuitBreaker:
    """Get Asterisk service wrapped with circuit breaker"""
    global _circuit_breaker
    if _circuit_breaker is None:
        from app.services.asterisk import get_asterisk_service
        asterisk_service = await get_asterisk_service()
        _circuit_breaker = AsteriskCircuitBreaker(asterisk_service)
    return _circuit_breaker
