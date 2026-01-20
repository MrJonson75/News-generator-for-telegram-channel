# app/news_parser/parser_rbk.py
from bs4 import BeautifulSoup
from typing import List, Dict
from app.logger import logger
from app.news_parser.load_site import fetch_html
from app.config import settings
from app.utils.rate_limit import random_delay


async def parse_news_rbk_site() -> List[Dict]:
    """
    Парсинг новостей с сайта rbk.ru
    Возвращаем формат Dict для NewsItem:
    {
        "title": str,
        "url": str,
        "summary": str,
        "source": str,
        "published_at": str,
        "raw_text": str
    }
    """
    url = settings.rbc_url
    html = await fetch_html(url)

    if not html:
        logger.warning(f"⚠️ Пустой HTML для страницы {url}")
        return []

    logger.info(f"Получен HTML код страницы {url}")

    soup = BeautifulSoup(html, "html.parser")
    news_items: List[Dict] = []

    main_content = soup.select_one(".l-col-main")
    if not main_content:
        logger.warning("⚠️ Не найден основной контейнер RBC")
        return []

    articles = main_content.find_all("div", class_="item__wrap l-col-center")
    logger.info(f"Найдено статей: {len(articles)}")

    for item in articles:
        await random_delay(2.0, 5.0)
        try:
            title_tag = item.find("a", class_="item__link")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = title_tag.get("href")
            if not title or not href:
                continue

            html_article = await fetch_html(href)
            if not html_article:
                continue

            sample_soup = BeautifulSoup(html_article, "html.parser")
            content_tag = sample_soup.find("div", class_="l-col-center-590 article__content")
            if not content_tag:
                continue

            text_block = content_tag.find("div", class_="article__text")
            if not text_block:
                logger.debug("⚠️ Нет article__text у статьи RBC")
                continue

            full_text = text_block.get_text(strip=True)
            if not full_text:
                continue

            summary = full_text[:400] + "..." if len(full_text) > 400 else full_text

            time_tag = content_tag.find("time")
            published_at = time_tag.get("datetime") if time_tag else None

            news_items.append(
                {
                    "title": title,
                    "url": href,
                    "summary": summary,
                    "source": "rbc.ru",
                    "published_at": published_at,
                    "raw_text": full_text,  # полный текст статьи
                }
            )

        except Exception:
            logger.exception("❌ Ошибка при разборе статьи RBC")
            continue

    logger.info(f"Успешно спарсено новостей: {len(news_items)}")
    return news_items


# Тестовый запуск
async def main():
    news = await parse_news_rbk_site()
    for item in news:
        print(item)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
