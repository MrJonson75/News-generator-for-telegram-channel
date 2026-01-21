# app/news_parser/parser_rbk.py
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime

from app.logger import logger
from app.news_parser.load_site import fetch_html
from app.config import settings
from app.utils.rate_limit import random_delay


async def parse_news_rbk_site(url: str = None, source_name: str = "rbc.ru") -> List[Dict]:
    """
    Парсинг новостей с RBC. Поддерживает динамическое указание URL и source_name.

    :param url: URL сайта для парсинга. Если None, берется из настроек.
    :param source_name: Название источника (для заполнения source)
    :return: Список словарей в формате ParsedNewsSchema
    """
    url = url or settings.rbc_url
    html = await fetch_html(url)

    if not html:
        logger.warning(f"⚠️ Пустой HTML для страницы {url}")
        return []

    logger.info(f"🌐 Получен HTML код страницы {url}")

    soup = BeautifulSoup(html, "html.parser")
    news_items: List[Dict] = []

    main_content = soup.select_one(".l-col-main")
    if not main_content:
        logger.warning(f"⚠️ Не найден основной контейнер {source_name}")
        return []

    articles = main_content.find_all("div", class_="item__wrap l-col-center")
    logger.info(f"Найдено статей {source_name}: {len(articles)}")

    for item in articles:
        await random_delay(2.0, 5.0)

        try:
            title_tag = item.find("a", class_="item__link")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)[:300]
            href = title_tag.get("href")
            if not title or not href or not href.startswith("http"):
                continue

            html_article = await fetch_html(href)
            if not html_article:
                continue

            article_soup = BeautifulSoup(html_article, "html.parser")
            content_tag = article_soup.find("div", class_="l-col-center-590 article__content")
            if not content_tag:
                continue

            text_block = content_tag.find("div", class_="article__text")
            if not text_block:
                continue

            full_text = text_block.get_text(strip=True)
            if not full_text or len(full_text) < 50:
                continue

            summary = full_text[:400] + "..." if len(full_text) > 400 else full_text

            # Парсинг даты публикации
            published_at = None
            time_tag = content_tag.find("time")
            if time_tag and time_tag.get("datetime"):
                try:
                    published_at = datetime.fromisoformat(time_tag.get("datetime").replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"⚠️ Не удалось распарсить дату {source_name}: {time_tag.get('datetime')}")

            news_items.append(
                {
                    "title": title,
                    "url": href,
                    "summary": summary,
                    "published_at": published_at,
                    "raw_text": full_text,
                    "source": source_name,
                    "source_type": "site",
                    "source_url": url,
                }
            )

        except Exception:
            logger.exception(f"❌ Ошибка при разборе статьи {source_name}")
            continue

    logger.info(f"✅ Успешно спарсено новостей {source_name}: {len(news_items)}")
    return news_items

