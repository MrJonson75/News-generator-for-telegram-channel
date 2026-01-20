# app/news_parser/parser_habr.py
from bs4 import BeautifulSoup
from typing import List, Dict
from app.logger import logger
from app.news_parser.load_site import fetch_html
from app.config import settings
from app.utils.rate_limit import random_delay


async def parse_news_habr_site() -> List[Dict]:
    """
    Парсит новости с сайта habr.com и возвращает список словарей.

    Возвращаемая структура:
    [
        {
            "title": str,
            "url": str,
            "summary": str,
            "source": "habr.com",
            "published_at": str,
            "keywords": List[str],
        },
        ...
    ]
    """
    url = settings.habr_url
    html = await fetch_html(url)

    if not html:
        logger.warning(f"⚠️ Пустой HTML для страницы {url}")
        return []

    logger.info(f"Получен HTML код страницы {url}")

    soup = BeautifulSoup(html, "html.parser")
    news_items: List[Dict] = []

    articles = soup.select("article.tm-articles-list__item")
    logger.info(f"Найдено статей: {len(articles)}")

    for item in articles:
        await random_delay(0.8, 2.5)
        try:
            # --- Заголовок и ссылка ---
            title_tag = item.find("a", class_="tm-title__link")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = title_tag.get("href")

            if not title or not href or "/ru/news" not in href:
                continue

            url_full = "https://habr.com" + href

            # --- Краткое описание ---
            summary_tag = item.find("div", class_="article-formatted-body")
            if not summary_tag:
                logger.debug("⚠️ Нет summary-блока у статьи Habr")
                continue

            summary = summary_tag.get_text(strip=True)
            summary = summary[:500] + "..." if len(summary) > 500 else summary
            if not summary:
                continue

            # --- Дата публикации ---
            time_tag = item.find("time")
            published_at = time_tag.get("datetime") if time_tag else None

            news_items.append(
                {
                    "title": title,
                    "url": url_full,
                    "summary": summary,
                    "source": "habr.com",
                    "published_at": published_at,
                }
            )

        except Exception as e:
            logger.exception("❌ Ошибка при разборе статьи Habr")
            continue

    logger.info(f"Успешно спарсено новостей: {len(news_items)}")
    return news_items

# Тестовый запуск
async def main():
    news = await parse_news_habr_site()
    for item in news:
        print(item)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())