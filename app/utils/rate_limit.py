# app/utils/rate_limit.py
import asyncio
import time
from app.logger import logger


class CyclicRateLimiter:
    """
    Лимитер: burst запросов с интервалом, затем cooldown пауза.

    Пример:
        burst=3, interval=20, cooldown=60
        → 3 запроса каждые 20 сек
        → затем пауза 60 сек
    """

    def __init__(self, burst: int = 3, interval: float = 20.0, cooldown: float = 60.0):
        self.burst = burst
        self.interval = interval
        self.cooldown = cooldown

        self._counter = 0
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    async def wait(self):
        async with self._lock:
            now = time.monotonic()

            # Интервал между запросами внутри burst
            if self._counter > 0:
                delta = now - self._last_call
                if delta < self.interval:
                    sleep_time = self.interval - delta
                    logger.debug(f"⏳ Ждём {sleep_time:.2f} сек перед следующим запросом")
                    await asyncio.sleep(sleep_time)

            # Если burst исчерпан — cooldown
            if self._counter >= self.burst:
                logger.info(f"🛑 Достигнут лимит {self.burst} запросов, пауза {self.cooldown} сек")
                await asyncio.sleep(self.cooldown)
                self._counter = 0

            self._last_call = time.monotonic()
            self._counter += 1

            logger.debug(f"📤 Запрос {self._counter}/{self.burst}")


async def random_delay(min_seconds: float = 1.5, max_seconds: float = 4.0):
    import random, asyncio
    from app.logger import logger
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"⏳ Задержка перед следующим запросом: {delay:.2f} сек")
    await asyncio.sleep(delay)