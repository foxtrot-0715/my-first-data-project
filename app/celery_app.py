import os
from celery import Celery

# Забираем адреса брокера из переменных окружения (Docker Compose их передаст)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Инициализация Celery-приложения
celery_task_app = Celery(
    "mdm_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Базовые настройки для предотвращения зависаний
celery_task_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1 # Чтобы воркер брал по 1 задаче за раз, актуально для тяжелых ML-моделей
)