import asyncio
from sqlalchemy import select
from app.celery_app import celery_app
from app.database import async_session
from app.models import NewsItem, Source
from app.logger import logger
from app.news_parser import news_collector


@celery_app.task(bind=True, name="parse_and_save_news")
def parse_and_save_news(self, limit_telegram: int = 50):
    """
    1️⃣ Сбор новостей с Habr, RBC и Telegram
    2️⃣ Сохранение Source и NewsItem в базу
    """

    async def _main():
        news_list = await news_collector.collect_news(limit_telegram=limit_telegram)
        if not news_list:
            logger.warning("⚠️ Новости не собраны")
            return 0

        logger.info(f"Собрано {len(news_list)} новостей. Сохраняем в базу...")

        async with async_session() as session:
            saved_count = 0

            for news in news_list:
                # --- Source ---
                source_name = news.get("source")
                source_url = news.get("url")
                source_type = "tg" if source_name.lower() == "telegram" else "site"

                result = await session.execute(select(Source).where(Source.name == source_name))
                source_obj = result.scalar()
                if not source_obj:
                    source_obj = Source(name=source_name, type=source_type, url=source_url)
                    session.add(source_obj)
                    await session.commit()
                    await session.refresh(source_obj)

                # --- NewsItem ---
                news_url = news.get("url")
                result = await session.execute(select(NewsItem).where(NewsItem.url == news_url))
                existing_news = result.scalar()
                if existing_news:
                    continue

                news_obj = NewsItem(
                    title=news.get("title") or "Без заголовка",
                    url=news_url,
                    summary=news.get("summary") or "",
                    source_id=source_obj.id,
                    published_at=news.get("published_at"),
                    raw_text=news.get("raw_text"),
                )
                session.add(news_obj)
                saved_count += 1

            await session.commit()
            return saved_count

    count = asyncio.run(_main())
    logger.info(f"✅ Сохранено новостей: {count}")
    return count
