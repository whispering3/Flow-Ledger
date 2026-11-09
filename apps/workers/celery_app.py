from celery import Celery

from apps.api.config import get_settings

settings = get_settings()
celery_app = Celery("flowledger", broker=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="flowledger",
    worker_prefetch_multiplier=1,
    beat_schedule={
        "publish-transactional-outbox": {
            "task": "flowledger.outbox.publish_pending",
            "schedule": 1.0,
        },
        "dispatch-due-executions": {
            "task": "flowledger.executions.dispatch_due",
            "schedule": 1.0,
        },
        "recover-stale-executions": {
            "task": "flowledger.executions.recover_stale",
            "schedule": 60.0,
        },
    },
)
celery_app.autodiscover_tasks(["apps.workers"])
