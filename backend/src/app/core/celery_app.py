from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "ai_support_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.document_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    result_expires=3600,
    result_compression="gzip",
    task_routes={
        "app.tasks.document_tasks.*": {"queue": "documents"},
    },
    beat_schedule={
        "cleanup-expired-tokens": {
            "task": "app.tasks.document_tasks.cleanup_expired_tokens",
            "schedule": crontab(hour=3, minute=0),
        },
        "cleanup-old-conversations": {
            "task": "app.tasks.document_tasks.cleanup_old_conversations",
            "schedule": crontab(hour=4, minute=0),
        },
        "process-pending-documents": {
            "task": "app.tasks.document_tasks.process_pending_documents",
            "schedule": crontab(minute="*/5"),
        },
    },
)

celery_app.autodiscover_tasks()


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
