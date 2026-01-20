# app/celery_app.py
from celery import Celery
from app.config import settings

celery_app = Celery(
    "generator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

# Регистрируем все задачи из папки tasks
# Здесь должны быть импортированы все модули с задачами
import app.tasks.news_tasks  # <--- обязательно импортировать
