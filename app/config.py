from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Класс настроек приложения, основанный на Pydantic BaseSettings.

    Позволяет загружать конфигурацию из переменных окружения и .env файла.
    Все атрибуты класса представляют собой настройки с типами и значениями по умолчанию.
    """

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    # Конфигурация модели: указывает Pydantic искать переменные в файле .env с кодировкой UTF-8

    # Режим отладки — если True, приложение будет выводить подробные логи (по умолчанию выключен)
    debug: bool = False

    # Название приложения, описание
    app_name: str = "AI-генератор постов для Telegram"
    description: str = """
        Сервис, который не просто парсит новости, но использует ИИ для генерации ярких, лаконичных 
        и интересных постов на основе собранных материалов.
    """
    version: str = "1.0.0"
    contact: dict = {
        "email": "flashh@list.ru",
        "url": "https://telegram.org/account",
        "name": "MrJonson",
    }
    
    # URL для подключения к Redis (используется для кэширования и хранения состояний)
    redis_url: str = 'redis://127.0.0.1:6379/0'

    # Идентификатор API Telegram (получается при создании приложения в @my_id_bot)
    telegram_api_id: int = 0
    
    # Хэш API Telegram (секретный ключ, используется вместе с api_id)
    telegram_api_hash: str = ''
    
    # Токен бота Telegram (получается от @BotFather)
    telegram_bot_token: str = ''
    
    # ID канала Telegram, куда бот будет публиковать новости (может быть числом или строкой с @username)
    telegram_channel_id: str = ''

    # Ключевые слова для поиска новостей (разделены запятыми, по умолчанию: python, fastapi, django)
    news_keywords: str = 'python,fastapi,django'

    @property
    def keywords_list(self) -> list[str]:
        """
        Преобразует строку ключевых слов в список.
        Убирает лишние пробелы и фильтрует пустые строки.
        :return: Список очищенных ключевых слов.
        Example: ['python', 'fastapi', 'django']
        :rtype: list[str]
        """
        raw_value = self.news_keywords
        parts = [part.strip() for part in raw_value.split(',') if part.strip()]
        return parts


# Глобальный экземпляр настроек, используемый в приложении
settings = Settings()


if __name__ == '__main__':
    print(settings.debug)
    print(settings.redis_url)
    print(settings.telegram_api_id)
    print(settings.telegram_bot_token)
    print(settings.telegram_channel_id)
    print(settings.news_keywords)
    print(settings.telegram_api_hash)
    print(settings.telegram_bot_token)
    print(settings.telegram_channel_id)
