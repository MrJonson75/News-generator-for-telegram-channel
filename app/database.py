import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from app.config import settings
import os



# Создаем асинхронный движок SQLAlchemy для SQLite
# DATABASE_URL = settings.database_url
DATABASE_URL = "sqlite+aiosqlite:///./aibot.db"

# Создаём асинхронный движок SQLAlchemy
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # True для логирования SQL-запросов
    future=True,
)

# Создаём асинхронную сессию
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency для FastAPI
async def get_session() -> AsyncSession:
    """
    Dependency для FastAPI: возвращает асинхронную сессию SQLAlchemy.

    Использование:
        async with get_session() as session:
            # работа с базой
    """
    async with async_session() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


# Вспомогательная функция для теста подключения
async def test_connection():
    """
    Проверяет подключение к базе данных.
    Если база и таблицы доступны, возвращает 1.
    """
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            return f"✅ Database connection OK: {result.scalar()}"
    except Exception as e:
        print("❌ Database connection failed:", e)



