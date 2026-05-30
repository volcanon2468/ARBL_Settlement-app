from celery import Celery
from app.infrastructure.config import settings

celery_app = Celery(
    "settlement_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.use_cases.run_calculation"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_time_limit=300,
)
