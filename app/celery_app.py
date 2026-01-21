# app/celery_app.py
from celery import Celery
from celery.schedules import crontab
from app.config import settings

# ================================
# Инициализация Celery
# ================================
celery_app = Celery(
    "generator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# ================================
# Конфигурация Celery
# ================================
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

celery_app.conf.timezone = "Europe/Moscow"
celery_app.conf.enable_utc = False

# ================================
# Расписание Celery Beat
# ================================
celery_app.conf.beat_schedule = {
    # Парсинг новостей каждые 30 минут
    "parse-news-every-30-minutes": {
        "task": "parse_and_save_news",
        "schedule": crontab(minute="*/30"),
    },
    # Генерация постов каждые 10 минут
    "generate-posts-every-10-minutes": {
        "task": "generate_posts",
        "schedule": crontab(minute="*/10"),
    },
    # Очистка старых failed постов каждый день в 03:00
    "cleanup-old-failed-posts-daily": {
        "task": "cleanup_old_failed_posts",
        "schedule": crontab(hour=3, minute=0),
        "args": (7,),  # по умолчанию удаляем посты старше 7 дней
    },
}

# ================================
# Импорт всех задач
# ================================
import app.tasks.news_tasks
import app.tasks.post_tasks
