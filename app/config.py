from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# =========================
# Метаданные приложения
# =========================

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


# =========================
# Настройки окружения
# =========================

class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения и .env файла.
    ВАЖНО: здесь ТОЛЬКО то, что реально приходит из env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Общие
    debug: bool = Field(False, alias="DEBUG")

    # Redis / Celery
    redis_url: str = Field(..., alias="REDIS_URL")
    celery_broker_url: str = Field(..., alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., alias="CELERY_RESULT_BACKEND")

    # Telegram
    telegram_api_id: int = Field(0, alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field("", alias="TELEGRAM_API_HASH")
    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    telegram_channel_id: str = Field("", alias="TELEGRAM_CHANNEL_ID")

    # OpenAI
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")

    # Фильтры
    news_keywords: str = Field("python,fastapi,django", alias="NEWS_KEYWORDS")

    # Путь к базе
    database_url: str = Field(..., alias="DATABASE_URL")

    @property
    def keywords_list(self) -> list[str]:
        """
        Преобразует строку ключевых слов в список.
        """
        return [
            word.strip().lower()
            for word in self.news_keywords.split(",")
            if word.strip()
        ]


# =========================
# Глобальные экземпляры
# =========================

settings = Settings()
