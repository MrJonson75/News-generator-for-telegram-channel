# app/api/keywords.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import Optional
from sqlalchemy import func

from app.database import get_session
from app.models import Keyword, post_keywords
from app.api.schemas import (
    KeywordSchema,
    KeywordCreateSchema,
    KeywordUpdateSchema,
    DeleteResponseSchema,
)
from app.logger import logger

router = APIRouter(prefix="/api/keywords", tags=["keywords"])


# ======================================================
# Получение всех тегов + фильтрация
# ======================================================
@router.get("/", response_model=list[KeywordSchema], summary="Получить список тегов")
async def get_keywords(
    search: Optional[str] = Query(None, description="Поиск по слову"),
    session: AsyncSession = Depends(get_session),
):
    """
    Получение списка всех тегов.

    Можно фильтровать по части слова:
    `/api/keywords?search=python`
    """
    try:
        stmt = select(Keyword)
        if search:
            stmt = stmt.where(Keyword.word.ilike(f"%{search}%"))

        result = await session.execute(stmt.order_by(Keyword.word))
        return result.scalars().all()
    except Exception:
        logger.exception("❌ Ошибка получения тегов")
        raise HTTPException(500, "Не удалось получить теги")


# ======================================================
# Статистика по тегам
# ======================================================
@router.get("/stats", summary="Статистика по тегам")
async def keyword_stats(session: AsyncSession = Depends(get_session)):
    """
    Возвращает статистику по тегам:
    сколько постов связано с каждым тегом.
    """
    try:
        stmt = (
            select(
                Keyword.word,
                func.count(post_keywords.c.post_id).label("posts_count")
            )
            .outerjoin(post_keywords, Keyword.id == post_keywords.c.keyword_id)
            .group_by(Keyword.id)
            .order_by(func.count(post_keywords.c.post_id).desc())
        )

        result = await session.execute(stmt)
        rows = result.all()

        return [
            {"keyword": word, "posts_count": count}
            for word, count in rows
        ]
    except Exception:
        logger.exception("❌ Ошибка получения статистики по тегам")
        raise HTTPException(500, "Не удалось получить статистику по тегам")


# ======================================================
# Получение тега по ID
# ======================================================
@router.get("/{keyword_id}", response_model=KeywordSchema, summary="Получить тег по ID")
async def get_keyword(
    keyword_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        result = await session.execute(
            select(Keyword).where(Keyword.id == str(keyword_id))
        )
        keyword = result.scalar_one_or_none()

        if not keyword:
            raise HTTPException(404, "Тег не найден")

        return keyword
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка получения тега {keyword_id}")
        raise HTTPException(500, "Не удалось получить тег")


# ======================================================
# Создание нового тега
# ======================================================
@router.post("/", response_model=KeywordSchema, summary="Создать тег")
async def create_keyword(
    payload: KeywordCreateSchema,
    session: AsyncSession = Depends(get_session)
):
    try:
        # Проверка уникальности
        exists = await session.execute(
            select(Keyword).where(Keyword.word == payload.word)
        )
        if exists.scalar_one_or_none():
            raise HTTPException(400, "Тег с таким словом уже существует")

        keyword = Keyword(word=payload.word)
        session.add(keyword)
        await session.commit()
        await session.refresh(keyword)

        logger.info(f"🏷 Создан тег: {payload.word}")
        return keyword
    except HTTPException:
        raise
    except Exception:
        logger.exception("❌ Ошибка создания тега")
        raise HTTPException(500, "Не удалось создать тег")


# ======================================================
# Обновление тега
# ======================================================
@router.patch("/{keyword_id}", response_model=KeywordSchema, summary="Обновить тег")
async def update_keyword(
    keyword_id: UUID,
    payload: KeywordUpdateSchema,
    session: AsyncSession = Depends(get_session)
):
    try:
        result = await session.execute(
            select(Keyword).where(Keyword.id == str(keyword_id))
        )
        keyword = result.scalar_one_or_none()

        if not keyword:
            raise HTTPException(404, "Тег не найден")

        # Проверка уникальности нового слова
        exists = await session.execute(
            select(Keyword).where(Keyword.word == payload.word)
        )
        if exists.scalar_one_or_none():
            raise HTTPException(400, "Тег с таким словом уже существует")

        old_word = keyword.word
        keyword.word = payload.word

        await session.commit()
        await session.refresh(keyword)

        logger.info(f"✏️ Тег изменён: {old_word} → {payload.word}")
        return keyword
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка обновления тега {keyword_id}")
        raise HTTPException(500, "Не удалось обновить тег")


# ======================================================
# Удаление тега
# ======================================================
@router.delete("/{keyword_id}", response_model=DeleteResponseSchema, summary="Удалить тег")
async def delete_keyword(
    keyword_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        result = await session.execute(
            select(Keyword).where(Keyword.id == str(keyword_id))
        )
        keyword = result.scalar_one_or_none()

        if not keyword:
            raise HTTPException(404, "Тег не найден")

        await session.delete(keyword)
        await session.commit()

        logger.warning(f"🗑 Удалён тег: {keyword.word}")
        return {"status": "ok", "detail": "Тег удалён"}
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка удаления тега {keyword_id}")
        raise HTTPException(500, "Не удалось удалить тег")


