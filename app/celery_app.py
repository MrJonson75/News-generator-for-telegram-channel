from celery import Celery
from datetime import timedelta
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

# =========================
# Периодические задачи (Beat)
# =========================
celery_app.conf.beat_schedule = {
    "parse-news-every-30-minutes": {
        "task": "parse_and_save_news",
        "schedule": timedelta(minutes=30),
        "args": (50,),  # лимит Telegram сообщений
    },
}

# Регистрируем все задачи из папки tasks
import app.tasks.news_tasks

