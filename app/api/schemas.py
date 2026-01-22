# app/api/schemas.py
from pydantic import BaseModel, Field, AnyHttpUrl
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from enum import Enum


# =========================
# Enum под Source.type
# =========================
class SourceType(str, Enum):
    site = "site"
    tg = "tg"


# =========================
# Enum под Post.status
# =========================
class PostStatus(str, Enum):
    new = "new"
    generated = "generated"
    published = "published"
    failed = "failed"


# =========================
# Схема источника
# =========================
class SourceSchema(BaseModel):
    id: UUID = Field(..., description="UUID источника")
    type: SourceType = Field(..., description="Тип источника: site / tg")
    name: str = Field(..., min_length=1, max_length=100)
    url: Optional[str] = Field(None, description="URL сайта или ссылка на TG")
    enabled: bool = Field(True)

    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =========================
# Схема новости (под БД)
# =========================
class NewsItemSchema(BaseModel):
    id: UUID = Field(..., description="UUID новости")
    title: str = Field(..., min_length=3, max_length=300)
    url: Optional[AnyHttpUrl]
    summary: str
    published_at: Optional[datetime]
    raw_text: Optional[str]

    source_id: UUID
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# =========================
# Входная схема для news_collector
# (до сохранения в БД)
# =========================
class ParsedNewsSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    url: Optional[AnyHttpUrl]
    summary: str
    published_at: Optional[datetime]
    raw_text: Optional[str]

    source: str = Field(..., description="Имя источника")
    source_type: SourceType = Field(..., description="site / tg")
    source_url: Optional[str]

    class Config:
        extra = "forbid"  # запрещает лишние поля


# =========================
# Ключевое слово
# =========================
class KeywordSchema(BaseModel):
    id: UUID
    word: str = Field(..., min_length=1, max_length=50)
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# =========================
# Пост
# =========================
class PostSchema(BaseModel):
    id: UUID
    news_id: UUID

    generated_text: Optional[str]
    published_at: Optional[datetime]

    status: PostStatus
    retry_count: int
    error_message: Optional[str]
    created_at: Optional[datetime]

    keywords: List[KeywordSchema] = []

    class Config:
        from_attributes = True


# =========================
# Обновление статуса поста
# =========================
class PostStatusUpdateSchema(BaseModel):
    status: PostStatus = Field(..., description="Новый статус поста")


# =========================
# Ответ при удалении
# =========================
class DeleteResponseSchema(BaseModel):
    status: str
    detail: str


# =========================
# Ответ генерации
# =========================
class GenerateResponseSchema(BaseModel):
    status: str
    generated_count: int


# =========================
# Входная схема для управления источниками Новостей (вкл/выкл)
# =========================
class SourceToggleSchema(BaseModel):
    enabled: bool = Field(..., description="Включён ли источник")


# =========================
# Создание тега
# =========================
class KeywordCreateSchema(BaseModel):
    word: str = Field(..., min_length=1, max_length=50, description="Ключевое слово")


# =========================
# Обновление тега
# =========================
class KeywordUpdateSchema(BaseModel):
    word: str = Field(..., min_length=1, max_length=50, description="Новое ключевое слово")


# =========================
# Привязка тегов к посту
# =========================
class PostKeywordAttachSchema(BaseModel):
    keywords: list[str] = Field(..., description="Список тегов для привязки")
