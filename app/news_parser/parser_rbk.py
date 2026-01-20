# app/news_parser/parser_rbk.py
from bs4 import BeautifulSoup
from typing import List, Dict
from app.logger import logger
from app.news_parser.load_site import fetch_html
from app.config import settings


async def parse_news_rbk_site() -> List[Dict]:
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
                continue

            summary_text = text_block.get_text(strip=True)
            if not summary_text:
                continue

            summary = summary_text[:400] + "..."

            time_tag = content_tag.find("time")
            published_at = time_tag.get("datetime") if time_tag else None

            keywords: List[str] = []
            for key in content_tag.find_all("a", class_="article__tags__item"):
                kw = key.get_text(strip=True)
                if kw:
                    keywords.append(kw.lower())

            news_items.append(
                {
                    "title": title,
                    "url": href,
                    "summary": summary,
                    "source": "rbc.ru",
                    "published_at": published_at,
                    "keywords": keywords,
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