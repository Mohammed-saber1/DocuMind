from celery import Celery

from core.config import get_settings

settings = get_settings()
redis_url = settings.redis.url

celery_app = Celery(
    "worker_knowledge_base",
    broker=redis_url,
    backend=redis_url,
    include=["worker.tasks"],  # Where your tasks live
)

celery_app.conf.update(
    # Worker settings
    worker_concurrency=settings.worker.concurrency,  # Number of concurrent workers
    # Task settings
    task_track_started=settings.worker.track_started,
    task_serializer=settings.worker.serializer,
    result_serializer=settings.worker.serializer,
    # Optional: Task time limits
    task_soft_time_limit=settings.worker.soft_time_limit,  # 1 hour soft limit (warning)
    task_time_limit=settings.worker.time_limit,  # 1 hour + 1 min hard limit (kill)
    # Optional: Retry settings
    task_acks_late=settings.worker.acks_late,  # Acknowledge after task completes
    # Retry if worker crashes
    task_reject_on_worker_lost=settings.worker.reject_on_worker_lost,
)
