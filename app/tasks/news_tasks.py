# app/tasks/news_tasks.py
import asyncio
from datetime import datetime
from app.celery_app import celery_app
from sqlalchemy import select
from app.database import async_session
from app.models import NewsItem, Source
from app.logger import logger
from app.news_parser import news_collector


@celery_app.task(name="parse_and_save_news")
def parse_and_save_news(limit_telegram: int = 50):
    async def _main():
        news_list = await news_collector.collect_news(limit_telegram=limit_telegram)
        if not news_list:
            logger.warning("⚠️ Новости не собраны")
            return 0

        async with async_session() as session:
            saved_count = 0
            for news in news_list:
                source_name = news.get("source")
                source_url = news.get("url")

                # --- Получаем или создаём Source ---
                result = await session.execute(select(Source).where(Source.name == source_name))
                source_obj = result.scalar()
                if not source_obj:
                    source_obj = Source(name=source_name, type="site", url=source_url)
                    session.add(source_obj)
                    await session.commit()
                    await session.refresh(source_obj)

                # --- Проверка дубликата по URL ---
                news_url = news.get("url")
                result = await session.execute(select(NewsItem).where(NewsItem.url == news_url))
                existing_news = result.scalar()
                if existing_news:
                    continue

                # --- Конвертация published_at в datetime ---
                published_at = None
                published_str = news.get("published_at")
                if published_str:
                    try:
                        published_at = datetime.fromisoformat(published_str)
                    except ValueError:
                        logger.warning(f"⚠️ Невалидная дата публикации: {published_str}")

                # --- Создание NewsItem ---
                news_obj = NewsItem(
                    title=news.get("title") or "Без заголовка",
                    url=news_url,
                    summary=news.get("summary") or "",
                    source_id=source_obj.id,
                    published_at=published_at,
                    raw_text=news.get("raw_text"),
                )
                session.add(news_obj)
                saved_count += 1

            await session.commit()
            return saved_count

    count = asyncio.run(_main())
    logger.info(f"✅ Сохранено новостей: {count}")
    return count
