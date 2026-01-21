# app/news_parser/news_collector.py
import asyncio
from typing import List

from app.logger import logger
from app.config import settings
from app.news_parser import parser_habr, parser_rbk, parser_telegram
from app.api.schemas import ParsedNewsSchema


async def collect_news(limit_telegram: int = 50) -> List[ParsedNewsSchema]:
    """
    Сбор и валидация новостей с Habr, RBK и Telegram.
    """

    logger.info("🚀 Старт сбора новостей со всех источников")

    tasks = [
        parser_habr.parse_news_habr_site(),
        parser_rbk.parse_news_rbk_site(),
        parser_telegram.parse_telegram_channel(limit=limit_telegram),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    raw_news = []
    for source_news in results:
        if isinstance(source_news, Exception):
            logger.error(f"❌ Ошибка источника: {source_news}")
            continue
        raw_news.extend(source_news)

    logger.info(f"Собрано всего новостей (до валидации): {len(raw_news)}")

    # =========================
    # Валидация через Pydantic
    # =========================
    validated_news: List[ParsedNewsSchema] = []
    for item in raw_news:
        try:
            validated = ParsedNewsSchema.model_validate(item)
            validated_news.append(validated)
        except Exception as e:
            logger.warning(f"⚠️ Новость пропущена (не прошла валидацию): {e}")

    logger.info(f"После валидации: {len(validated_news)} новостей")

    # =========================
    # Дедупликация по URL
    # =========================
    seen_urls = set()
    unique_news: List[ParsedNewsSchema] = []
    for news in validated_news:
        if news.url in seen_urls:
            continue
        seen_urls.add(news.url)
        unique_news.append(news)

    logger.info(f"После дедупликации: {len(unique_news)} новостей")

    # =========================
    # Фильтрация по ключевым словам
    # =========================
    keywords = settings.keywords_list
    if keywords:
        filtered_news = []
        for news in unique_news:
            text = f"{news.title} {news.summary}".lower()
            if any(word.lower() in text for word in keywords):
                filtered_news.append(news)
        logger.info(f"После фильтрации по ключевым словам: {len(filtered_news)} новостей")
    else:
        filtered_news = unique_news

    # =========================
    # Сортировка по дате
    # =========================
    filtered_news.sort(
        key=lambda x: x.published_at or "",
        reverse=True
    )

    return filtered_news
