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

            # Получаем все источники заранее
            result = await session.execute(select(Source))
            sources = result.scalars().all()
            sources_dict = {src.name: src for src in sources}

            for news in news_list:
                source_name = news.source

                # --- Получаем или создаём Source ---
                source_obj = sources_dict.get(source_name)
                if not source_obj:
                    source_obj = Source(
                        name=news.source,
                        type=news.source_type.value,
                        url=news.source_url,
                        enabled=True  # новые источники сразу активны
                    )
                    session.add(source_obj)
                    await session.flush()
                    sources_dict[source_name] = source_obj
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
