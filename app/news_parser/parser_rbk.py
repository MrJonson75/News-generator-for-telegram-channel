# app/news_parser/parser_rbk.py
from bs4 import BeautifulSoup
from typing import List, Dict
from app.logger import logger
from app.news_parser.load_site import fetch_html
from app.config import settings


async def parse_news_rbk_site() -> List[Dict]:
    """
    Парсит новости с сайта rbk.ru и возвращает список словарей.

    Возвращаемая структура:
    [
        {
            "title": str,
            "url": str,
            "summary": str,
            "source": "rbc.ru",
            "published_at": str,
            "keywords": List[str],
        },
        ...
    ]
    """
    url = settings.rbc_url
    html = await fetch_html(url)

    if not html:
        logger.warning(f"⚠️ Пустой HTML для страницы {url}")
        return []

    logger.info(f"Получен HTML код страницы {url}")

    soup = BeautifulSoup(html, "html.parser")
    news_items: List[Dict] = []

    articles = soup.select("l-row js-load-container")
    logger.info(f"Найдено статей: {len(articles)}")

    for item in articles:
        try:
            print(item)
            print()
            # --- Заголовок и ссылка ---
    #         title_tag = item.find("a", class_="tm-title__link")
    #         if not title_tag:
    #             continue
    #
    #         title = title_tag.get_text(strip=True)
    #         href = title_tag.get("href")
    #
    #         if not title or not href or "/ru/news" not in href:
    #             continue
    #
    #         url_full = "https://habr.com" + href

            # # --- Краткое описание ---
            # summary_tag = item.find("div", class_="article-formatted-body")
            # if not summary_tag:
            #     continue
            #
            # summary = summary_tag.get_text(strip=True)
            # if not summary:
            #     continue
            #
            # # --- Дата публикации ---
            # time_tag = item.find("time")
            # published_at = time_tag.get("datetime") if time_tag else None
            #
            # # --- Ключевые слова (хабы) ---
            # keywords: List[str] = []
            # for key in item.select(".tm-publication-hub__link-container"):
            #     keyword = key.get_text(strip=True).replace("*", "")
            #     if keyword:
            #         keywords.append(keyword.lower())
            #
            # news_items.append(
            #     {
            #         "title": title,
            #         "url": url_full,
            #         "summary": summary,
            #         "source": "habr.com",
            #         "published_at": published_at,
            #         "keywords": keywords,
            #     }
            # )

        except Exception as e:
            logger.exception("❌ Ошибка при разборе статьи Habr")
            continue

    logger.info(f"Успешно спарсено новостей: {len(news_items)}")
    return news_items


# Тестовый запуск
async def main():
    news = await parse_news_rbk_site()
    # for item in news:
    #     print(item)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
