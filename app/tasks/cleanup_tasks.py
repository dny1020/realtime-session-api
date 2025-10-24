"""
Celery tasks for cleanup and maintenance

Handles data retention, stale record cleanup, and system maintenance.
"""
from celery import Task
from loguru import logger
from datetime import datetime, timedelta, timezone

from app.celery_app import celery_app
from app.models import CallStatus
from config.settings import get_settings

settings = get_settings()


class MaintenanceTask(Task):
    """Base task for maintenance operations"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Maintenance task failed",
            extra={
                "task_id": task_id,
                "task": self.name,
                "error": str(exc)
            }
        )


@celery_app.task(base=MaintenanceTask, bind=True)
def cleanup_stale_calls(self):
    """
    Mark stale calls as failed
    
    Calls stuck in PENDING/DIALING/RINGING for too long are marked as failed.
    """
    from app.database import SessionLocal
    from app.models.call import Call
    
    if settings.disable_db:
        return {"success": True, "message": "Database disabled"}
    
    db = SessionLocal()
    try:
        # Find stale calls (older than 1 hour in non-terminal state)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        stale_calls = db.query(Call).filter(
            Call.status.in_([CallStatus.PENDING, CallStatus.DIALING, CallStatus.RINGING]),
            Call.created_at < cutoff
        ).all()
        
        if not stale_calls:
            logger.debug("No stale calls found")
            return {"success": True, "cleaned": 0}
        
        # Mark as failed
        count = 0
        for call in stale_calls:
            call.status = CallStatus.FAILED
            call.failure_reason = "Timeout: No response from Asterisk"
            call.ended_at = datetime.now(timezone.utc)
            count += 1
        
        db.commit()
        
        logger.info(
            "Cleaned up stale calls",
            extra={"count": count}
        )
        
        return {"success": True, "cleaned": count}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to cleanup stale calls: {e}")
        raise
    finally:
        db.close()


@celery_app.task(base=MaintenanceTask, bind=True)
def cleanup_old_calls(self):
    """
    Delete old call records based on retention policy
    
    Keeps database size manageable by removing old data.
    """
    from app.database import SessionLocal
    from app.models.call import Call
    
    if settings.disable_db:
        return {"success": True, "message": "Database disabled"}
    
    db = SessionLocal()
    try:
        # Calculate retention cutoff
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.call_retention_days)
        
        # Delete old completed calls
        old_calls = db.query(Call).filter(
            Call.ended_at < cutoff,
            Call.status.in_([
                CallStatus.COMPLETED,
                CallStatus.FAILED,
                CallStatus.BUSY,
                CallStatus.NO_ANSWER
            ])
        )
        
        count = old_calls.count()
        
        if count > 0:
            old_calls.delete()
            db.commit()
            
            logger.info(
                "Deleted old call records",
                extra={
                    "count": count,
                    "retention_days": settings.call_retention_days
                }
            )
        else:
            logger.debug("No old calls to delete")
        
        return {"success": True, "deleted": count}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to cleanup old calls: {e}")
        raise
    finally:
        db.close()


@celery_app.task(base=MaintenanceTask, bind=True)
def check_asterisk_health(self):
    """
    Periodic health check for Asterisk connection
    
    Logs warnings if Asterisk is degraded.
    """
    from app.services.asterisk import get_asterisk_service
    import asyncio
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        asterisk = loop.run_until_complete(get_asterisk_service())
        is_connected = loop.run_until_complete(asterisk.is_connected())
        
        loop.close()
        
        if not is_connected:
            logger.warning("Asterisk health check failed - service degraded")
            return {"success": False, "status": "degraded"}
        
        return {"success": True, "status": "healthy"}
        
    except Exception as e:
        logger.error(f"Asterisk health check error: {e}")
        return {"success": False, "status": "error", "error": str(e)}


@celery_app.task(base=MaintenanceTask, bind=True)
def vacuum_database(self):
    """
    Run database vacuum for PostgreSQL optimization
    
    Scheduled to run during low-traffic periods.
    """
    from app.database import SessionLocal
    from sqlalchemy import text
    
    if settings.disable_db:
        return {"success": True, "message": "Database disabled"}
    
    db = SessionLocal()
    try:
        # Run VACUUM ANALYZE on calls table
        db.execute(text("VACUUM ANALYZE calls"))
        db.commit()
        
        logger.info("Database vacuum completed")
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Database vacuum failed: {e}")
        raise
    finally:
        db.close()
