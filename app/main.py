# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from app.config import settings, APP_META
from app.api.sources import router as sources_router
from app.database import test_connection
from app.ai.openai_client import openai_client
from app.logger import logger
from app.celery_app import celery_app
import redis.asyncio as redis
import asyncio

# =====================================================
# Инициализация FastAPI
# =====================================================
app = FastAPI(
    title=APP_META.name,
    description=APP_META.description,
    version=APP_META.version,
    contact={
        "name": APP_META.contact.name,
        "email": APP_META.contact.email,
        "url": APP_META.contact.url
    },
    openapi_tags=[
        {"name": "posts", "description": "Управление постами: просмотр, генерация, публикация, удаление"},
        {"name": "main", "description": "Общие эндпоинты: здоровье сервиса, корень API"}
    ]
)

# =====================================================
# Настройка CORS
# =====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ограничить список доменов для продакшена
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Подключение роутеров
# =====================================================
app.include_router(sources_router)


# =====================================================
# Корневой эндпоинт
# =====================================================
@app.get("/", tags=["main"], summary="Главная страница API")
async def root():
    """
    Главная страница API.

    Просто возвращает приветственное сообщение.
    """
    return {"message": "📰 Генератор новостей для Telegram"}


# =====================================================
# Health-check с проверкой Celery, Redis и OpenAI
# =====================================================
@app.get("/health", tags=["main"], summary="Проверка состояния системы")
async def health():
    """
    Проверка состояния системы:

    - `database` — статус подключения к базе данных
    - `openai` — статус клиента OpenAI
    - `celery` — проверка очередей Celery
    - `redis` — проверка подключения к Redis
    """
    status_report = {"status": "ok"}
    try:
        # --- База данных ---
        db_status = await test_connection()
        status_report["database"] = db_status

        # --- OpenAI ---
        openai_status = await openai_client.health_client()
        status_report["openai"] = openai_status

        # --- Redis ---
        try:
            redis_url = settings.redis_url
            redis_client = redis.from_url(redis_url)
            pong = await redis_client.ping()
            status_report["redis"] = "ok" if pong else "fail"
            await redis_client.close()
        except Exception as e:
            logger.exception("Redis health-check failed")
            status_report["redis"] = f"fail: {e}"

        # --- Celery ---
        try:
            inspect = celery_app.control.inspect(timeout=2)
            active = inspect.active()  # словарь {worker_name: [...]}
            if active is None:
                status_report["celery"] = "no workers"
            else:
                status_report["celery"] = "ok"
        except Exception as e:
            logger.exception("Celery health-check failed")
            status_report["celery"] = f"fail: {e}"

        logger.info(f"Health-check: {status_report}")
        return status_report

    except Exception as e:
        logger.exception("❌ Health-check failed")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)}
        )


# =====================================================
# Обработка ошибок валидации FastAPI
# =====================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"❌ Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "fail",
            "detail": exc.errors(),
            "body": exc.body
        }
    )


# =====================================================
# Событие старта приложения
# =====================================================
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Приложение запущено")
    # Проверка состояния OpenAI при старте
    try:
        openai_status = await openai_client.health_client()
        logger.info(f"OpenAI client ready: {openai_status}")
    except Exception as e:
        logger.error(f"OpenAI client error: {e}")
