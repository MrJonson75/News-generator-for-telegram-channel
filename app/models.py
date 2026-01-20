# app/models.py
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Table,
    Enum,
    Integer,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# =========================
# Enum для статусов поста
# =========================
class PostStatus(enum.Enum):
    new = "new"
    generated = "generated"
    published = "published"
    failed = "failed"


# =========================
# M2M: Post <-> Keyword
# =========================
post_keywords = Table(
    "post_keywords",
    Base.metadata,
    Column("post_id", String, ForeignKey("posts.id"), primary_key=True),
    Column("keyword_id", String, ForeignKey("keywords.id"), primary_key=True),
)


# =========================
# Источники новостей
# =========================
class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False)  # site / tg
    name = Column(String, nullable=False)
    url = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())

    # Связь с новостями
    news_items = relationship("NewsItem", back_populates="source")

    def __repr__(self):
        return f"<Source(name={self.name}, type={self.type}, enabled={self.enabled})>"


# =========================
# Ключевые слова (теги)
# =========================
class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    word = Column(String, unique=True, nullable=False, index=True)

    created_at = Column(DateTime, server_default=func.now())

    posts = relationship("Post", secondary=post_keywords, back_populates="keywords")

    def __repr__(self):
        return f"<Keyword(word={self.word})>"


# =========================
# Новости (результат парсинга)
# =========================
class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    url = Column(String, nullable=True, unique=True, index=True)
    summary = Column(Text, nullable=False)

    source_id = Column(String, ForeignKey("sources.id"), nullable=False)
    published_at = Column(DateTime, nullable=True, index=True)

    raw_text = Column(Text, nullable=True)  # для Telegram
    created_at = Column(DateTime, server_default=func.now())

    source = relationship("Source", back_populates="news_items")
    post = relationship("Post", back_populates="news", uselist=False)

    def __repr__(self):
        return f"<NewsItem(title={self.title[:40]}..., source_id={self.source_id})>"


# =========================
# Сгенерированные посты
# =========================
class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    news_id = Column(String, ForeignKey("news_items.id"), nullable=False, unique=True)

    generated_text = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)

    status = Column(
        Enum(PostStatus, name="post_status_enum"),
        default=PostStatus.new,
        nullable=False,
        index=True,
    )

    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    news = relationship("NewsItem", back_populates="post")
    keywords = relationship("Keyword", secondary=post_keywords, back_populates="posts")

    def __repr__(self):
        return f"<Post(news_id={self.news_id}, status={self.status})>"
