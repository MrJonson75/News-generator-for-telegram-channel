# app/ai/openai_client.py
import aiohttp
import asyncio
from app.config import settings
from app.logger import logger


class OpenAIClient:
    """
    Асинхронный клиент для OpenAI API (GPT‑4o‑mini) с поддержкой прокси через aiohttp.
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

    async def generate_text(
        self,
        news_text: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 300,
        temperature: float = 0.7,
    ) -> str:
        """
        Асинхронная генерация текста через OpenAI GPT‑4o‑mini.
        """
        if not self.api_key:
            logger.error("❌ Не задан API ключ для OpenAI.")
            return ""

        prompt = f"{settings.openai_prompt}\n\n{news_text}"
        proxy_url = self._format_proxy()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"❌ OpenAI API returned {response.status}: {text}")
                        return ""
                    data = await response.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.exception(f"❌ Ошибка при генерации текста OpenAI: {e}")
            return ""

    async def health_client(self) -> dict:
        """
        Проверяет доступность OpenAI API через прокси (если задан) и возвращает статус.
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


# Синглтон клиент
openai_client = OpenAIClient()


# Тестовый запуск
async def main():
    print(await openai_client.health_client())
    text = await openai_client.generate_text("Напиши короткий пост о Python")
    print(text)


if __name__ == "__main__":
    asyncio.run(main())
