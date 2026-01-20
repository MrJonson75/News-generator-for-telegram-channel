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
    :return: Список новостей в формате Dict с полями title, url, summary, source, published_at
    :raises: Exception при ошибке парсинга или загрузки HTML.
    :example: [{'title': '...', 'url': '...', 'summary': '...', 'source': 'rbk.ru', 'published_at': '...'}, ...]
    """
    # Проверка на включение парсинга
    url = settings.rbc_url
    html = await fetch_html(url)

    # Проверка на пустой HTML
    if not html:
        logger.warning(f"⚠️ Пустой HTML для страницы {url}")
        return []

    logger.info(f"Получен HTML код страницы {url}")

    # Парсинг HTML
    soup = BeautifulSoup(html, "html.parser")
    news_items: List[Dict] = []

    # Поиск основного контейнера
    main_content = soup.select_one(".l-col-main")
    if not main_content:
        logger.warning("⚠️ Не найден основной контейнер RBC")
        return []

    # Поиск статей
    articles = main_content.find_all("div", class_="item__wrap l-col-center")
    logger.info(f"Найдено статей: {len(articles)}")

    for item in articles:
        await random_delay(2.0, 5.0)
        try:
            title_tag = item.find("a", class_="item__link")
            if not title_tag:
                continue

            # --- Заголовок и ссылка ---
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href")
            if not title or not href:
                continue

            # --- Содержание статьи ---
            html_article = await fetch_html(href)
            if not html_article:
                continue

            # --- Парсинг статьи ---
            sample_soup = BeautifulSoup(html_article, "html.parser")

            content_tag = sample_soup.find("div", class_="l-col-center-590 article__content")
            if not content_tag:
                continue

            text_block = content_tag.find("div", class_="article__text")
            if not text_block:
                logger.debug("⚠️ Нет article__text у статьи RBC")
                continue

            summary_text = text_block.get_text(strip=True)
            if not summary_text:
                continue
            # --- Краткое описание ---
            summary = summary_text[:400] + "..." if len(summary_text) > 400 else summary_text

            # --- Дата публикации ---
            time_tag = content_tag.find("time")
            published_at = time_tag.get("datetime") if time_tag else None

            news_items.append(
                {
                    "title": title,
                    "url": href,
                    "summary": summary,
                    "source": "rbc.ru",
                    "published_at": published_at,
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