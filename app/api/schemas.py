from pydantic import BaseModel, Field, AnyHttpUrl
from datetime import datetime
from typing import List
from uuid import UUID


# Модель данных для новости
class NewsItem(BaseModel):
    """
    Схема данных для представления одной новости.

    Используется для валидации и документирования входящих/исходящих данных,
    связанных с новостями из внешних источников.
    """

    news_id: str = Field(
        ...,
        description="Уникальный идентификатор новости в формате UUID или хеша",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Заголовок новости",
        examples=["Вышла новая версия Django", "Что вышло нового за декабрь 2025 года."]
    )
    url: AnyHttpUrl = Field(
        ...,
        description="URL оригинальной статьи",
        examples=["https://news.yandex.ru"]
    )
    summary: str = Field(
        default=None,
        description="Краткое содержание новости. Может отсутствовать.",
        examples=["Вышла новая версия Django 5.0 с поддержкой асинхронных миграций.", "За декабрь 2025 года представлено несколько обновлений в экосистеме Python."]
    )
    source: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Источник новости (например, название сайта или платформы)",
        examples=["Telegram", "Habr", "VC.ru", "Lenta.ru"]
    )
    published_at: datetime = Field(
        ...,
        description="Дата и время публикации новости в формате ISO 8601",
        examples=["2025-02-20T10:30:00Z", "2025-02-19T14:15:30+03:00"]
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Список ключевых слов или тегов, связанных с новостью. Может быть пустым.",
        examples=[["Python", "Django", "Web development"], ["новости", "технологии", "IT"]]
    )


class Post(BaseModel):
    """
    Схема данных для поста, сгенерированного на основе новости.

    Представляет запись в базе данных, связанную с обработанной новостью.
    Содержит статус публикации и сгенерированный текст.
    """

    id: int = Field(
        ...,
        description="Первичный ключ записи в базе данных",
        examples=[1, 42]
    )
    news_id: str = Field(
        ...,
        description="Идентификатор связанной новости",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    generated_text: str = Field(
        ...,
        description="Сгенерированный текст публикации",
        examples=["Сегодня вышла новая версия Django 5.0 с поддержкой асинхронных миграций."]
    )
    published_at: datetime = Field(
        default=None,
        description="Дата и время публикации поста в формате ISO 8601. Может быть не задано.",
        examples=["2025-02-20T12:00:00Z"]
    )
    status: str = Field(
        ...,
        pattern="^(new|generated|published|failed)$",
        description="Статус поста: new — создан, generated — текст сгенерирован, published — опубликован, failed — ошибка",
        examples=["new", "published", "failed"]
    )


class Keyword(BaseModel):
    """
    Схема данных для ключевого слова.

    Используется для управления тегами, связанными с новостями.
    """

    id: int = Field(
        ...,
        description="Первичный ключ записи в базе данных",
        examples=[1, 2]
    )
    word: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Ключевое слово или тег",
        examples=["Python", "Django", "Web development"]
    )


class Source(BaseModel):
    """
    Схема данных для источника новостей.

    Поддерживает два типа источников: веб-сайты и Telegram-каналы.
    Используется для настройки парсинга и фильтрации новостей.
    """

    id: int = Field(
        ...,
        description="Первичный ключ записи в базе данных",
        examples=[1, 2]
    )
    type: str = Field(
        ...,
        pattern="^(site|tg)$",
        description="Тип источника: site — веб-сайт, tg — Telegram канал",
        examples=["site", "tg"]
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Название источника (например, название сайта или Telegram канала)",
        examples=["Habr", "VC.ru", "Python News TG"]
    )
    url: str = Field(
        ...,
        description="Ссылка на сайт или username Telegram-канала (без @)",
        examples=["https://habr.com", "python_news"]
    )
    enabled: bool = Field(
        ...,
        description="Флаг активности источника: True — активен, False — отключен",
        examples=[True, False]
    )