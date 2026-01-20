# app/utils/rate_limit.py
import asyncio
import random
from app.logger import logger

# Глобальный семафор для ограничения количества одновременных запросов
GLOBAL_SEMAPHORE = asyncio.Semaphore(3)


async def random_delay(min_seconds: float = 1.5, max_seconds: float = 4.0):
    """
    Выполняет асинхронную задержку на случайное время в указанном диапазоне.

    Используется для имитации человеческого поведения между запросами,
    чтобы снизить вероятность блокировки со стороны сервера.

    :param min_seconds: Минимальная задержка в секундах (по умолчанию 1.5)
    :param max_seconds: Максимальная задержка в секундах (по умолчанию 4.0)
    """
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"⏳ Задержка перед следующим запросом: {delay:.2f} сек")
    await asyncio.sleep(delay)


async def limited_request(coro):
    """
    Выполняет асинхронную корутину с учётом глобального ограничения на количество одновременных запросов.

    Использует семафор для контроля параллелизма. Позволяет избежать перегрузки сервера
    и соблюдать лимиты на количество запросов.

    :param coro: Асинхронная функция (корутина), которую нужно выполнить
    :return: Результат выполнения корутины
    """
    async with GLOBAL_SEMAPHORE:
        return await coro