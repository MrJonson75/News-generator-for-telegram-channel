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

    main_content = soup.select(".l-col-main")
    articles = main_content[0].find_all("div", class_="item__wrap l-col-center")
    logger.info(f"Найдено статей: {len(articles)}")
    for item in articles:
        try:
            # --- Заголовок и ссылка ---
            title_tag = item.find("a", {"class": "item__link rm-cm-item-link js-rm-central-column-item-link"})
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = title_tag.get("href")
            if not href or not title:
                continue
            html_article = await fetch_html(href)
            if not html_article:
                continue
            # --- Краткое описание ---
            sample_soup = BeautifulSoup(html_article, "html.parser")
            summary_tag = sample_soup.find("div", {"class": "l-col-center-590 article__content"})
            summary = summary_tag.find(
                "div",
                {"class": "article__text article__text_free"}
                ).get_text(strip=True)[:400] + "..."
            if not summary:
                continue

            # --- Дата публикации ---
            time_tag = summary_tag.find("time")
            published_at = time_tag.get("datetime") if time_tag else None

            # --- Ключевые слова (хабы) ---
            keywords: List[str] = []
            for key in summary_tag.find_all("a", {"class": "article__tags__item"}):
                keywords.append(key.get_text(strip=True))

            # --- Добавляем статью в список ---
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

        except Exception as e:
            logger.exception("❌ Ошибка при разборе статьи Habr")
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
