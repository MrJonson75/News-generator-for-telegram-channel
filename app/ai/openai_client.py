# app/ai/openai_client.py
import aiohttp
import asyncio
from typing import List
from app.config import settings
from app.logger import logger


class RateLimitError(Exception):
    """Исключение для обработки rate limit OpenAI (HTTP 429)"""
    pass


class OpenAIClient:
    """
    Асинхронный клиент для OpenAI API (GPT-4o-mini) с поддержкой прокси через aiohttp.
    """

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key: str = None, proxy: str = None):
        self.api_key = api_key or settings.openai_api_key
        self.proxy = proxy or settings.openai_proxy

        if not self.api_key:
            logger.error("❌ OPENAI_API_KEY не задан!")
        else:
            logger.info("🤖 OpenAI клиент инициализирован")
            if self.proxy:
                logger.info(f"🌐 Прокси задан: {self.proxy}")

    def _format_proxy(self) -> str | None:
        """
        Преобразует прокси в формат aiohttp: http://user:pass@host:port
        """
        if not self.proxy:
            return None
        try:
            if "@" in self.proxy:
                auth, hostport = self.proxy.split("@")
                user, password = auth.split(":")
                host, port = hostport.split(":")
                return f"http://{user}:{password}@{host}:{port}"
            else:
                return f"http://{self.proxy}"
        except Exception as e:
            logger.error(f"❌ Ошибка разбора прокси {self.proxy}: {e}")
            return None

    async def _request(self, endpoint: str, payload: dict, timeout: int = 30) -> dict:
        """
        Универсальный метод запроса к OpenAI API
        """
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY не задан")

        proxy_url = self._format_proxy()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}{endpoint}",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:

                text = await response.text()

                if response.status == 429:
                    logger.warning(f"⏳ OpenAI rate limit: {text}")
                    raise RateLimitError(text)

                if response.status != 200:
                    logger.error(f"❌ OpenAI API {response.status}: {text}")
                    raise RuntimeError(f"OpenAI error {response.status}: {text}")

                return await response.json()

    async def generate_text(
        self,
        news_text: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 300,
        temperature: float = 0.7,
    ) -> str:
        """
        Асинхронная генерация текста через OpenAI GPT-4o-mini.
        """
        prompt = f"{settings.openai_prompt}\n\n{news_text}"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            data = await self._request("/chat/completions", payload)
            return data["choices"][0]["message"]["content"].strip()
        except RateLimitError:
            raise
        except Exception as e:
            logger.exception(f"❌ Ошибка генерации текста OpenAI: {e}")
            raise

    async def generate_keywords(self, text: str, max_keywords: int = 4) -> List[str]:
        """
        Генерация ключевых слов из текста через OpenAI.
        """
        prompt = (
            "Проанализируй предоставленный текст и составь список релевантных ключевых слов-тегов "
            f"не больше {max_keywords}. "
            "Теги должны отражать основные темы, сущности и концепции.\n\n"
            f"{text}\n\n"
            "Предоставь только теги через запятую."
        )

        response = await self.generate_text(prompt, max_tokens=100, temperature=0.3)

        keywords = [word.strip() for word in response.split(",") if word.strip()]
        return keywords[:max_keywords]

    async def health_client(self) -> dict:
        """
        Проверяет доступность OpenAI API через прокси (если задан).
        """
        if not self.api_key:
            return {"status": "error", "detail": "OPENAI_API_KEY не задан"}

        proxy_url = self._format_proxy()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        return {"status": "ok"}
                    else:
                        text = await response.text()
                        return {"status": "error", "detail": f"HTTP {response.status}: {text}"}
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к OpenAI: {e}")
            return {"status": "error", "detail": str(e)}


# Глобальный клиент
openai_client = OpenAIClient()
