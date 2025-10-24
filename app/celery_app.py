"""
Celery configuration for async task processing

Handles retry queues, scheduled tasks, and long-running operations.
"""
from celery import Celery
from celery.schedules import crontab
from loguru import logger

from config.settings import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "contactcenter",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.call_tasks",
        "app.tasks.cleanup_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "retry_on_timeout": True,
    },
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    
    # Task routing
    task_routes={
        "app.tasks.call_tasks.retry_failed_call": {"queue": "retry"},
        "app.tasks.cleanup_tasks.*": {"queue": "maintenance"},
    },
    
    # Rate limits
    task_annotations={
        "app.tasks.call_tasks.originate_call_async": {"rate_limit": "100/m"},
    },
    
    # Retry policy
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-stale-calls": {
        "task": "app.tasks.cleanup_tasks.cleanup_stale_calls",
        "schedule": crontab(minute=f"*/{settings.cleanup_interval_minutes}"),
    },
    "cleanup-old-calls": {
        "task": "app.tasks.cleanup_tasks.cleanup_old_calls",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
    "health-check-asterisk": {
        "task": "app.tasks.maintenance_tasks.check_asterisk_health",
        "schedule": 60.0,  # Every minute
    },
}


# Task error handler
@celery_app.task(bind=True)
def error_handler(self, uuid):
    """Handle task errors"""
    result = self.app.AsyncResult(uuid)
    logger.error(
        "Task failed",
        extra={
            "task_id": uuid,
            "task": result.task_name,
            "error": str(result.info)
        }
    )


logger.info("Celery configured", extra={"broker": settings.redis_url})
