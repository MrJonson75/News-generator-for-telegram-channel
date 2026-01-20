# app/news_parser/news_collector.py
import asyncio
from typing import List, Dict
from app.logger import logger
from app.config import settings
from app.news_parser import parser_habr, parser_rbk, parser_telegram


async def collect_news(limit_telegram: int = 50) -> List[Dict]:
    """
    Сбор новостей с Habr, RBC и Telegram.

    :param limit_telegram: сколько сообщений Telegram парсить
    :return: Список новостей после дедупликации и фильтрации
    """
    logger.info("🚀 Старт сбора новостей со всех источников")

    # Параллельный сбор новостей
    tasks = [
        parser_habr.parse_news_habr_site(),
        parser_rbk.parse_news_rbk_site(),
        parser_telegram.parse_telegram_channel(limit=limit_telegram),
    ]

    # Запуск парсеров в асинхронном режиме
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Объединяем все источники
    all_news: List[Dict] = []
    for source_news in results:
        if isinstance(source_news, Exception):
            logger.error(f"❌ Ошибка источника: {source_news}")
            continue
        all_news.extend(source_news)

    logger.info(f"Собрано всего новостей (до фильтрации/дедупликации): {len(all_news)}")

    # Дедупликация по URL
    seen_urls = set()
    unique_news = []
    for news in all_news:
        url = news.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        unique_news.append(news)

    logger.info(f"После дедупликации: {len(unique_news)} новостей")

    # Фильтрация по ключевым словам
    keywords = settings.news_keywords
    if keywords:
        filtered_news = []
        for news in unique_news:
            text = f"{news.get('title','')} {news.get('summary','')}".lower()
            if any(word in text for word in keywords):
                filtered_news.append(news)
        logger.info(f"После фильтрации по ключевым словам: {len(filtered_news)} новостей")
    else:
        filtered_news = unique_news

    # Сортировка по дате публикации (сначала новые)
    filtered_news.sort(key=lambda x: x.get("published_at") or "", reverse=True)

    return filtered_news


# Тестовый запуск
async def main():
    news = await collect_news(limit_telegram=20)
    for idx, item in enumerate(news, 1):
        print(f"{idx}. [{item['source']}] {item['title']} ({item['published_at']})")
        print(f"   {item['url']}\n")
        print(f"Краткое описание: {item['summary']}\n")


if __name__ == "__main__":
    asyncio.run(main())
