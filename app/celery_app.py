from celery import Celery
from smart_common.core.config import settings

celery_app = Celery(
    "smart_energy",
    broker=f"redis://{settings.REDIS_HOST}:6379/0",
    backend=f"redis://{settings.REDIS_HOST}:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,
)

import app.tasks.email_tasks  # noqa
