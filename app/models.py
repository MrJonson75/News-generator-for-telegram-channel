import datetime
import uuid
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime,
    ForeignKey, Text, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base, validates
from sqlalchemy.sql import func

Base = declarative_base()


# =========================
# Enum для статусов постов
# =========================
class PostStatus(Enum):
    """Возможные статусы публикации поста"""
    NEW = "new"
    GENERATED = "generated"
    PUBLISHED = "published"
    FAILED = "failed"


# =========================
# Enum для типов источников
# =========================
class SourceType(Enum):
    """Тип источника новостей: сайт или Telegram-канал"""
    SITE = "site"
    TELEGRAM = "tg"


# =========================
# Модель новости
# =========================
class NewsItem(Base):
    """
    Модель для хранения новостей, полученных с сайтов или Telegram-каналов.

    Атрибуты:
        news_id (str)          - UUID новости
        title (str)            - заголовок новости
        url (str)              - ссылка на оригинал
        summary (str)          - краткое содержание
        source (str)           - источник новости
        published_at (datetime) - дата публикации
        created_at / updated_at - даты создания и последнего обновления записи
        posts (Post[])         - список связанных постов
    """
    __tablename__ = "news_items"
    __table_args__ = (
        Index('idx_news_published', 'published_at'),
        Index('idx_news_source', 'source'),
    )

    news_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Связь с Post
    posts = relationship(
        "Post",
        back_populates="news_item",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    @validates('url')
    def validate_url(self, key, url):
        """Проверка корректности URL: http(s):// или t.me/"""
        if url and not url.startswith(('http://', 'https://', 't.me/')):
            raise ValueError("Invalid URL format. Must start with http://, https:// or t.me/")
        return url

    def __repr__(self):
        return f"<NewsItem(title='{self.title[:30]}', source='{self.source}')>"



# Модель поста
class Post(Base):
    """
    Модель для хранения сгенерированных постов на основе новости.

    Атрибуты:
        id (int)              - первичный ключ
        news_id (str)         - внешний ключ на NewsItem
        generated_text (str)  - текст поста
        status (PostStatus)   - статус поста: new, generated, published, failed
        published_at (datetime) - дата публикации
        created_at / updated_at - даты создания и обновления записи
    """
    __tablename__ = "posts"
    __table_args__ = (
        Index('idx_post_status', 'status'),
        Index('idx_post_published', 'published_at'),
        Index('idx_post_news_id', 'news_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    news_id = Column(String(36), ForeignKey("news_items.news_id"), nullable=False, index=True)
    generated_text = Column(Text, nullable=False)
    status = Column(SQLEnum(PostStatus, native_enum=False), nullable=False, default=PostStatus.NEW)
    published_at = Column(DateTime, nullable=True, index=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Связь с NewsItem
    news_item = relationship("NewsItem", back_populates="posts")

    def __repr__(self):
        return f"<Post(news_id='{self.news_id}', status='{self.status.value}')>"


# Модель источника новостей
class Source(Base):
    """
    Модель для хранения источников новостей (сайты или Telegram-каналы).

    Атрибуты:
        id (int)           - первичный ключ
        type (SourceType)  - тип источника
        name (str)         - название источника
        url (str)          - URL сайта или username TG
        enabled (bool)     - активность источника
        created_at / updated_at - даты создания и обновления записи
    """
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(SQLEnum(SourceType, native_enum=False), nullable=False)
    name = Column(String(100), nullable=False)
    url = Column(String(300), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    @validates('url')
    def validate_source_url(self, key, url):
        """Проверка корректности URL источника в зависимости от типа"""
        if self.type == SourceType.SITE and url and not url.startswith(('http://', 'https://')):
            raise ValueError("URL-адрес веб-сайта должен начинаться с http:// or https://")
        elif self.type == SourceType.TELEGRAM and url and not url.startswith('@'):
            raise ValueError("Канал Telegram должен начинаться с @")
        return url

    def __repr__(self):
        return f"<Source(name='{self.name}', type='{self.type.value}')>"



# Модель ключевого слова
class Keyword(Base):
    """
    Модель для хранения ключевых слов (тегов) для фильтрации новостей.

    Атрибуты:
        id (int)           - первичный ключ
        word (str)         - ключевое слово
        created_at / updated_at - даты создания и обновления записи
    """
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(50), nullable=False, unique=True, index=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Keyword(word='{self.word}')>"
