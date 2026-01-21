# app/news_parser/news_collector.py
import asyncio
from typing import List
from datetime import datetime

from sqlalchemy import select

from app.logger import logger
from app.config import settings
from app.news_parser import parser_habr, parser_rbk, parser_telegram
from app.api.schemas import ParsedNewsSchema
from app.database import async_session
from app.models import Source


async def collect_news(limit_telegram: int = 50) -> List[ParsedNewsSchema]:
    """
    Сбор, валидация и фильтрация новостей с активных источников.
    Поддерживает динамическое создание источников из конфигурации, если база пуста.
    """

    logger.info("🚀 Старт сбора новостей с активных источников")

    # -------------------------
    # Получаем активные источники из базы
    # -------------------------
    async with async_session() as session:
        result = await session.execute(select(Source).where(Source.enabled == True))
        sources = result.scalars().all()

        # Если база пуста — создаём записи из config
        if not sources:
            logger.info("⚠️ Нет источников в базе, создаём из config")
            default_sources = [
                {
                    "name": "habr.com",
                    "type": "site",
                    "url": settings.habr_url,
                    "enabled": True,
                },
                {
                    "name": "rbc.ru",
                    "type": "site",
                    "url": settings.rbc_url,
                    "enabled": True,
                },
                {
                    "name": settings.telegram_news_channel,
                    "type": "tg",
                    "url": f"https://t.me/{settings.telegram_news_channel}",
                    "enabled": True,
                },
            ]
            for src in default_sources:
                session.add(Source(**src))
            await session.commit()

            # перечитываем созданные источники
            result = await session.execute(select(Source).where(Source.enabled == True))
            sources = result.scalars().all()

    if not sources:
        logger.warning("⚠️ Нет активных источников для парсинга")
        return []

    # -------------------------
    # Формируем задачи парсеров динамически
    # -------------------------
    tasks = []
    for src in sources:
        if not src.enabled:
            continue
        if src.type == "site" and "habr" in src.name.lower():
            tasks.append(parser_habr.parse_news_habr_site())
        elif src.type == "site" and "rbc" in src.name.lower():
            tasks.append(parser_rbk.parse_news_rbk_site())
        elif src.type == "tg":
            tasks.append(parser_telegram.parse_telegram_channel(limit=limit_telegram))

    if not tasks:
        logger.warning("⚠️ Нет задач для парсеров")
        return []

    # -------------------------
    # Запуск парсеров параллельно
    # -------------------------
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # -------------------------
    # Объединяем результаты
    # -------------------------
    raw_news = []
    for source_news in results:
        if isinstance(source_news, Exception):
            logger.error(f"❌ Ошибка источника: {source_news}")
            continue
        raw_news.extend(source_news)

    logger.info(f"Собрано всего новостей (до валидации): {len(raw_news)}")

    # -------------------------
    # Валидация через Pydantic
    # -------------------------
    validated_news: List[ParsedNewsSchema] = []
    for item in raw_news:
        try:
            validated = ParsedNewsSchema.model_validate(item)
            validated_news.append(validated)
        except Exception as e:
            logger.warning(f"⚠️ Новость пропущена (не прошла валидацию): {e}")

    logger.info(f"После валидации: {len(validated_news)} новостей")

    # -------------------------
    # Дедупликация по URL
    # -------------------------
    seen_urls = set()
    unique_news: List[ParsedNewsSchema] = []
    for news in validated_news:
        if news.url in seen_urls:
            continue
        seen_urls.add(news.url)
        unique_news.append(news)

    logger.info(f"После дедупликации: {len(unique_news)} новостей")

    # -------------------------
    # Фильтрация по ключевым словам
    # -------------------------
    keywords = [kw.lower() for kw in settings.keywords_list] if settings.keywords_list else []
    if keywords:
        filtered_news = [
            news for news in unique_news
            if any(word in f"{news.title} {news.summary}".lower() for word in keywords)
        ]
        logger.info(f"После фильтрации по ключевым словам: {len(filtered_news)} новостей")
    else:
        filtered_news = unique_news

    # -------------------------
    # Сортировка по дате публикации (новые первыми)
    # -------------------------
    filtered_news.sort(key=lambda x: x.published_at or datetime.min, reverse=True)

    return filtered_news


# =========================
# Тестовый запуск
# =========================
async def main():
    news = await collect_news(limit_telegram=20)
    for idx, item in enumerate(news, 1):
        print(f"{idx}. [{item.source_type}] {item.title} ({item.published_at})")
        print(f"   {item.url}\n")
        print(f"Кратко: {item.summary}\n")


if __name__ == "__main__":
    asyncio.run(main())
