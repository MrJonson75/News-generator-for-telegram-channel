# app/news_parser/load_site.py
import httpx
from app.logger import logger
from app.utils.rate_limit import random_delay


async def fetch_html(url: str, retries: int = 3) -> str:
    """Загружает HTML-страницу с указанного URL с повторением при ошибках."""
    for attempt in range(1, retries + 1):
        try:
            # Пауза между попытками
            await random_delay(1.5, 4.0)

            logger.info(f"🌐 Загрузка страницы: {url} (попытка {attempt})")
            # Отправка запроса с таймаутом 15 секунд
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text

        except httpx.HTTPStatusError as e:
            status = e.response.status_code

            if status == 404:
                logger.error(f"❌ Страница не найдена: {url}")
                return ""

            if status in (429, 500, 502, 503):
                logger.warning(
                    f"⚠️ HTTP {status} для {url}, повтор через паузу"
                )
                # Пауза между повторными попытками
                await random_delay(5, 12)
                continue

            logger.exception(f"❌ HTTP ошибка при загрузке {url}")
            raise

        except httpx.RequestError:
            logger.warning(f"⚠️ Сетевая ошибка при загрузке {url}")
            await random_delay(5, 10)
            continue

    logger.error(f"❌ Не удалось загрузить страницу после {retries} попыток: {url}")
    return ""
