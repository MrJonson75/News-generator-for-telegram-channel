# app/config.py
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Contact(BaseModel):
    name: str
    email: str
    url: str


class AppMeta(BaseModel):
    name: str
    description: str
    version: str
    contact: Contact


APP_META = AppMeta(
    name="AI-генератор постов для Telegram",
    description=(
        "Сервис, который не просто парсит новости, "
        "но использует ИИ для генерации ярких, лаконичных "
        "и интересных постов на основе собранных материалов."
    ),
    version="1.0.0",
    contact=Contact(
        name="MrJonson",
        email="flashh@list.ru",
        url="https://telegram.org/account",
    ),
)


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения и .env файла.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Общие
    debug: bool = Field(False, alias="DEBUG")

    # Telegram
    telegram_api_id: int = Field(0, alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field("", alias="TELEGRAM_API_HASH")
    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    telegram_channel_id: str = Field("", alias="TELEGRAM_CHANNEL_ID")

    # OpenAI
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")

    # Фильтры
    news_keywords: str = Field("python,fastapi,django", alias="NEWS_KEYWORDS")

    # URL источников
    habr_url: str = "https://habr.com/ru/news/"
    rbc_url: str = "https://www.rbc.ru/rubric/technology_and_media?utm_source=topline"

    # Будущие настройки (пока не обязательные)
    redis_url: Optional[str] = Field(None, alias="REDIS_URL")
    celery_broker_url: Optional[str] = Field(None, alias="CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = Field(None, alias="CELERY_RESULT_BACKEND")

    @property
    def keywords_list(self) -> list[str]:
        return [
            word.strip().lower()
            for word in self.news_keywords.split(",")
            if word.strip()
        ]

    def log_config(self):
        from app.logger import logger

        logger.info("⚙️ App configuration:")
        logger.info(f"DEBUG: {self.debug}")
        logger.info(f"Telegram Channel: {self.telegram_channel_id}")
        logger.info(f"News Keywords: {self.keywords_list}")
        logger.info(f"Habr URL: {self.habr_url}")
        logger.info(f"RBC URL: {self.rbc_url}")

        if self.celery_broker_url:
            logger.info(f"Celery Broker: {self.celery_broker_url}")

        if self.redis_url:
            logger.info(f"Redis URL: {self.redis_url}")


settings = Settings()
