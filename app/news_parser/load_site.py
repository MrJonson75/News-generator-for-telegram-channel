# app/news_parser/load_site.py
import httpx
from app.logger import logger


async def fetch_html(url: str) -> str:
    """
    Асинхронно загружает HTML-страницу по URL.

    Возвращает:
        str: HTML-текст страницы или пустую строку при 404.

    Исключения:
        httpx.RequestError: при сетевых ошибках (DNS, таймаут и т.п.)
        httpx.HTTPStatusError: при HTTP-ошибках кроме 404
    """
    logger.info(f"Загрузка страницы: {url}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    except httpx.HTTPStatusError as e:
        # Есть HTTP-ответ (4xx / 5xx)
        status_code = e.response.status_code

        if status_code == 404:
            logger.warning(f"Страница не найдена (404): {url}")
            return ""

        logger.error(
            f"HTTP ошибка при загрузке {url}: "
            f"{status_code} {e.response.reason_phrase}"
        )
        raise

    except httpx.RequestError as e:
        # Ошибки соединения, таймауты, DNS и т.п.
        logger.error(f"Сетевая ошибка при загрузке {url}: {e}")
        raise
