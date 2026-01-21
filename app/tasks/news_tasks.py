# app/tasks/news_tasks.py
import asyncio
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
                # news теперь ParsedNewsSchema, а не dict

                # --- Получаем или создаём Source ---
                result = await session.execute(
                    select(Source).where(Source.name == news.source)
                )
                source_obj = result.scalar_one_or_none()

                if not source_obj:
                    source_obj = Source(
                        name=news.source,
                        type=news.source_type.value,
                        url=news.source_url,
                    )
                    session.add(source_obj)
                    await session.flush()
                    logger.info(f"🆕 Создан новый источник: {source_obj.name} ({source_obj.type})")

                # --- Проверка дубликата по URL ---
                result = await session.execute(
                    select(NewsItem).where(NewsItem.url == str(news.url))
                )
                existing_news = result.scalar_one_or_none()
                if existing_news:
                    continue

                # --- Создание NewsItem ---
                news_obj = NewsItem(
                    title=news.title or "Без заголовка",
                    url=str(news.url),
                    summary=news.summary or "",
                    source_id=source_obj.id,
                    published_at=news.published_at,
                    raw_text=news.raw_text,
                )

                session.add(news_obj)
                saved_count += 1

            await session.commit()
            return saved_count

    count = asyncio.run(_main())
    logger.info(f"✅ Сохранено новостей: {count}")
    return count
