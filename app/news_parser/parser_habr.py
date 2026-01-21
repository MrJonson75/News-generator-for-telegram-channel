# app/news_parser/parser_habr.py
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime

from app.logger import logger
from app.news_parser.load_site import fetch_html
from app.config import settings
from app.utils.rate_limit import random_delay


async def parse_news_habr_site(url: str = None, source_name: str = "habr.com") -> List[Dict]:
    """
    Парсинг новостей с Habr. Поддерживает динамическое указание URL.

    :param url: URL сайта для парсинга. Если None, берется из настроек.
    :param source_name: Название источника (для заполнения source)
    """
    url = url or settings.habr_url
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

            title = title_tag.get_text(strip=True)[:300]
            href = title_tag.get("href")
            if not title or not href or not href.startswith("/ru/news"):
                continue

            url_full = "https://habr.com" + href

            summary_tag = item.find("div", class_="article-formatted-body")
            if not summary_tag:
                continue

            full_text = summary_tag.get_text(strip=True)
            if not full_text or len(full_text) < 50:
                continue

            summary = full_text[:500] + "..." if len(full_text) > 500 else full_text

            # Парсинг даты публикации
            published_at = None
            time_tag = item.find("time")
            if time_tag and time_tag.get("datetime"):
                try:
                    published_at = datetime.fromisoformat(time_tag.get("datetime").replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"⚠️ Не удалось распарсить дату: {time_tag.get('datetime')}")

            news_items.append(
                {
                    "title": title,
                    "url": url_full,
                    "summary": summary,
                    "published_at": published_at,
                    "source": source_name,
                    "source_type": "site",
                    "source_url": url,
                }
            )

        except Exception:
            logger.exception("❌ Ошибка при разборе статьи Habr")
            continue

    logger.info(f"✅ Успешно спарсено новостей {source_name}: {len(news_items)}")
    return news_items

