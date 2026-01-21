# app/news_parser/parser_habr.py
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime

from app.logger import logger
from app.news_parser.load_site import fetch_html
from app.config import settings
from app.utils.rate_limit import random_delay


async def parse_news_habr_site() -> List[Dict]:
    """
    Парсит новости с habr.com и возвращает список словарей
    в унифицированном формате для Pydantic ParsedNewsSchema.

    Формат:
    {
        "title": str,
        "url": str,
        "summary": str,
        "published_at": datetime | None,
        "raw_text": None,
        "source": "habr.com",
        "source_type": "site",
        "source_url": "https://habr.com"
    }
    """
    url = settings.habr_url
    html = await fetch_html(url)

    if not html:
        logger.warning(f"⚠️ Пустой HTML для страницы {url}")
        return []

    logger.info(f"🌐 Получен HTML код страницы {url}")

    soup = BeautifulSoup(html, "html.parser")
    news_items: List[Dict] = []

    articles = soup.select("article.tm-articles-list__item")
    logger.info(f"Найдено статей: {len(articles)}")

    for item in articles:
        await random_delay(0.8, 2.5)

        try:
            title_tag = item.find("a", class_="tm-title__link")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = title_tag.get("href")
            if not title or not href or "/ru/news" not in href:
                continue

            url_full = "https://habr.com" + href

            summary_tag = item.find("div", class_="article-formatted-body")
            if not summary_tag:
                logger.debug("⚠️ Нет summary-блока у статьи Habr")
                continue

            full_text = summary_tag.get_text(strip=True)
            if not full_text or len(full_text) < 50:
                continue

            summary = full_text[:500] + "..." if len(full_text) > 500 else full_text

            # Парсим дату
            time_tag = item.find("time")
            published_at = None
            if time_tag and time_tag.get("datetime"):
                try:
                    published_at = datetime.fromisoformat(
                        time_tag.get("datetime").replace("Z", "+00:00")
                    )
                except Exception:
                    logger.warning(f"⚠️ Не удалось распарсить дату: {time_tag.get('datetime')}")

            news_items.append(
                {
                    "title": title,
                    "url": url_full,
                    "summary": summary,
                    "published_at": published_at,
                    "raw_text": None,
                    "source": "habr.com",
                    "source_type": "site",
                    "source_url": "https://habr.com",
                }
            )

        except Exception:
            logger.exception("❌ Ошибка при разборе статьи Habr")
            continue

    logger.info(f"✅ Успешно спарсено новостей Habr: {len(news_items)}")
    return news_items


# =========================
# Тестовый запуск
# =========================
async def main():
    news = await parse_news_habr_site()
    for item in news:
        print(item)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
