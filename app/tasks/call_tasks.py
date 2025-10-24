"""
Celery tasks for call operations

Handles async call origination and retry logic.
"""
from celery import Task
from loguru import logger
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.models import CallStatus


class CallbackTask(Task):
    """Base task with callbacks"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(
            "Task failed",
            extra={
                "task_id": task_id,
                "task": self.name,
                "error": str(exc),
                "args": args
            }
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry"""
        logger.warning(
            "Task retrying",
            extra={
                "task_id": task_id,
                "task": self.name,
                "error": str(exc),
                "args": args
            }
        )


@celery_app.task(
    base=CallbackTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes
    retry_jitter=True
)
def retry_failed_call(self, call_id: str):
    """
    Retry a failed call
    
    This task is queued when a call fails due to transient errors.
    """
    from app.database import SessionLocal
    from app.models.call import Call
    from app.services.circuit_breaker import get_asterisk_with_circuit_breaker
    import asyncio
    
    logger.info(f"Retrying failed call: {call_id}")
    
    db = SessionLocal()
    try:
        # Get call record
        call = db.query(Call).filter(Call.call_id == call_id).first()
        if not call:
            logger.error(f"Call not found for retry: {call_id}")
            return {"success": False, "error": "Call not found"}
        
        # Check if call is retryable
        if call.status not in [CallStatus.FAILED, CallStatus.NO_ANSWER]:
            logger.warning(f"Call {call_id} not in retryable state: {call.status}")
            return {"success": False, "error": "Not retryable"}
        
        # Increment attempt number
        call.attempt_number += 1
        call.status = CallStatus.PENDING
        db.commit()
        
        # Originate call via Asterisk
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        asterisk = loop.run_until_complete(get_asterisk_with_circuit_breaker())
        result = loop.run_until_complete(
            asterisk.originate_call(
                phone_number=call.phone_number,
                context=call.context,
                extension=call.extension,
                priority=call.priority,
                timeout=call.timeout,
                caller_id=call.caller_id
            )
        )
        
        loop.close()
        
        if result["success"]:
            call.status = CallStatus.DIALING
            call.channel = result.get("channel")
            call.dialed_at = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"Call retry successful: {call_id}")
            return {"success": True, "call_id": call_id}
        else:
            call.status = CallStatus.FAILED
            call.failure_reason = f"Retry failed: {result.get('error')}"
            db.commit()
            
            logger.error(f"Call retry failed: {call_id}")
            return {"success": False, "error": result.get("error")}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Exception during call retry: {e}")
        raise
    finally:
        db.close()


@celery_app.task(
    base=CallbackTask,
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,)
)
def originate_call_async(
    self,
    phone_number: str,
    context: str,
    extension: str,
    priority: int,
    timeout: int,
    caller_id: str,
    call_id: str
):
    """
    Originate call asynchronously
    
    Used for background call origination without blocking API response.
    """
    from app.database import SessionLocal
    from app.models.call import Call
    from app.services.circuit_breaker import get_asterisk_with_circuit_breaker
    import asyncio
    
    logger.info(f"Originating call async: {call_id}")
    
    db = SessionLocal()
    try:
        # Get call record
        call = db.query(Call).filter(Call.call_id == call_id).first()
        if not call:
            logger.error(f"Call not found: {call_id}")
            return {"success": False, "error": "Call not found"}
        
        # Originate via Asterisk
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        asterisk = loop.run_until_complete(get_asterisk_with_circuit_breaker())
        result = loop.run_until_complete(
            asterisk.originate_call(
                phone_number=phone_number,
                context=context,
                extension=extension,
                priority=priority,
                timeout=timeout,
                caller_id=caller_id
            )
        )
        
        loop.close()
        
        if result["success"]:
            call.status = CallStatus.DIALING
            call.channel = result.get("channel")
            call.dialed_at = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"Async call originated: {call_id}")
            return {"success": True, "call_id": call_id}
        else:
            call.status = CallStatus.FAILED
            call.failure_reason = result.get("error")
            call.ended_at = datetime.now(timezone.utc)
            db.commit()
            
            # Queue for retry if it's a transient error
            if "timeout" in str(result.get("error")).lower():
                retry_failed_call.apply_async(args=[call_id], countdown=60)
            
            return {"success": False, "error": result.get("error")}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Exception during async origination: {e}")
        raise
    finally:
        db.close()
