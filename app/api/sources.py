# app/api/sources.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import Optional

from app.database import get_session
from app.models import Post, Source, Keyword
from app.api.schemas import (
    PostSchema,
    PostStatusUpdateSchema,
    DeleteResponseSchema,
    GenerateResponseSchema,
    PostStatus,
    SourceToggleSchema,
    SourceSchema,
    PostKeywordAttachSchema
)
from app.celery_app import celery_app
from app.logger import logger

router = APIRouter(prefix="/api", tags=["posts"])


# ======================================================
# Получение всех постов
# ======================================================
@router.get("/posts", response_model=list[PostSchema], summary="Получить список постов")
async def get_posts(
    status: Optional[PostStatus] = Query(None, description="Фильтр по статусу поста"),
    keyword: Optional[str] = Query(None, description="Фильтр по тегу"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """
    Получение списка постов с фильтрами:

    - по статусу: `/api/posts?status=new`
    - по тегу: `/api/posts?keyword=python`
    - совместно: `/api/posts?status=published&keyword=ai`
    """
    try:
        stmt = select(Post).options(selectinload(Post.keywords))

        if status:
            stmt = stmt.where(Post.status == status)

        if keyword:
            stmt = stmt.join(Post.keywords).where(Keyword.word == keyword)

        stmt = stmt.order_by(Post.created_at.desc()) \
                   .offset((page - 1) * size) \
                   .limit(size)

        result = await session.execute(stmt)
        return result.scalars().unique().all()
    except Exception:
        logger.exception("❌ Ошибка получения постов")
        raise HTTPException(500, "Не удалось получить посты")



# ======================================================
# Получение поста по ID
# ======================================================
@router.get("/posts/{post_id}", response_model=PostSchema, summary="Получить пост по ID")
async def get_post(post_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    Получение одного поста по ID.

    **Пример запроса:**
    `/api/posts/9250e8ec-9ebf-41bb-a5d7-9287a5380024`
    """
    try:
        result = await session.execute(
            select(Post).options(selectinload(Post.keywords)).where(Post.id == str(post_id))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise HTTPException(404, "Пост не найден")
        return post
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка получения поста {post_id}")
        raise HTTPException(500, "Не удалось получить пост")


# ======================================================
# Ручная привязка тегов к посту
# ======================================================
@router.post("/posts/{post_id}/keywords", response_model=PostSchema, summary="Привязать теги к посту")
async def attach_keywords_to_post(
    post_id: UUID,
    payload: PostKeywordAttachSchema,
    session: AsyncSession = Depends(get_session)
):
    """
    Ручная привязка тегов к посту.

    Пример:
    {
        "keywords": ["python", "ai", "telegram"]
    }
    """
    try:
        result = await session.execute(
            select(Post).options(selectinload(Post.keywords)).where(Post.id == str(post_id))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise HTTPException(404, "Пост не найден")

        attached = []

        for word in payload.keywords:
            word = word.strip().lower()

            result = await session.execute(select(Keyword).where(Keyword.word == word))
            keyword = result.scalar_one_or_none()

            if not keyword:
                keyword = Keyword(word=word)
                session.add(keyword)
                await session.flush()

            if keyword not in post.keywords:
                post.keywords.append(keyword)
                attached.append(word)

        await session.commit()
        await session.refresh(post)

        logger.info(f"🔗 Теги {attached} привязаны к посту {post_id}")
        return post

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка привязки тегов к посту {post_id}")
        raise HTTPException(500, "Не удалось привязать теги")


# ======================================================
# Изменение статуса поста
# ======================================================
@router.patch("/posts/{post_id}/status", response_model=PostSchema, summary="Изменить статус поста")
async def update_post_status(
    post_id: UUID,
    payload: PostStatusUpdateSchema,
    session: AsyncSession = Depends(get_session)
):
    """
    Ручное изменение статуса поста.

    **Доступные статусы:**
    - `new` — новый пост
    - `generated` — отправить в генерацию
    - `published` — опубликован
    - `failed` — ошибка генерации

    **Пример запроса:**
    ```json
    {
      "status": "published"
    }
    ```
    """
    try:
        result = await session.execute(
            select(Post).options(selectinload(Post.keywords)).where(Post.id == str(post_id))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise HTTPException(404, "Пост не найден")

        old_status = post.status
        post.status = payload.status

        await session.commit()
        await session.refresh(post)

        logger.info(f"🔄 Статус поста {post_id}: {old_status} → {payload.status}")
        return post
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка смены статуса поста {post_id}")
        raise HTTPException(500, "Не удалось изменить статус")


# ======================================================
# Удаление поста
# ======================================================
@router.delete("/posts/{post_id}", response_model=DeleteResponseSchema, summary="Удалить пост")
async def delete_post(post_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    Удаление поста по ID.

    **Пример запроса:**
    `/api/posts/9250e8ec-9ebf-41bb-a5d7-9287a5380024`
    """
    try:
        result = await session.execute(
            select(Post).options(selectinload(Post.keywords)).where(Post.id == str(post_id))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise HTTPException(404, "Пост не найден")

        await session.delete(post)
        await session.commit()

        logger.warning(f"🗑 Пост удалён: {post_id}")
        return {"status": "ok", "detail": "Пост удалён"}
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка удаления поста {post_id}")
        raise HTTPException(500, "Не удалось удалить пост")


# ======================================================
# Генерация постов вручную
# ======================================================
@router.post("/generate", response_model=GenerateResponseSchema, summary="Запустить генерацию")
async def generate_posts_manual():
    """
    Ручной запуск генерации постов через Celery.

    **Пример запроса:**
    POST `/api/generate`
    """
    try:
        task = celery_app.send_task("generate_posts")
        logger.info(f"🚀 Ручной запуск генерации, task_id={task.id}")
        return {"status": "started", "generated_count": 0}
    except Exception:
        logger.exception("❌ Ошибка ручного запуска генерации")
        raise HTTPException(500, "Не удалось запустить генерацию")


# ======================================================
# Публикация поста в Telegram
# ======================================================
@router.post("/posts/{post_id}/publish", response_model=PostSchema, summary="Опубликовать пост")
async def publish_post(post_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    Публикация поста в Telegram.

    Меняет статус поста на `published`.
    В будущем сюда можно подключить реальную отправку в Telegram.

    **Пример запроса:**
    POST `/api/posts/9250e8ec-9ebf-41bb-a5d7-9287a5380024/publish`
    """
    try:
        result = await session.execute(
            select(Post).options(selectinload(Post.keywords)).where(Post.id == str(post_id))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise HTTPException(404, "Пост не найден")

        # if post.status != PostStatus.new:
        #     raise HTTPException(400, "Пост должен быть в статусе 'new' для публикации")

        post.status = PostStatus.published

        await session.commit()
        await session.refresh(post)

        logger.info(f"📢 Пост опубликован: {post_id}")
        return post
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка публикации поста {post_id}")
        raise HTTPException(500, "Не удалось опубликовать пост")


# ======================================================
# Получение всех источников новостей
# ======================================================
@router.get(
    "/sources",
    response_model=list[SourceSchema],
    summary="Получить список источников новостей",
)
async def get_sources(session: AsyncSession = Depends(get_session)):
    """
    Возвращает список всех источников новостей.

    Используется для управления парсерами:
    - включение / выключение источников
    - администрирование системы
    """
    try:
        result = await session.execute(select(Source))
        return result.scalars().all()
    except Exception:
        logger.exception("❌ Ошибка получения источников")
        raise HTTPException(500, "Не удалось получить источники")


# ======================================================
# Управление активностью источника
# ======================================================
@router.patch(
    "/sources/{source_id}/enabled",
    response_model=SourceSchema,
    summary="Включить или отключить источник новостей"
)
async def toggle_source_enabled(
    source_id: UUID,
    payload: SourceToggleSchema,
    session: AsyncSession = Depends(get_session)
):
    """
    Управление активностью источника новостей.

    Если `enabled = false` — источник исключается из парсинга
    Если `enabled = true` — источник снова участвует в сборе новостей

    **Пример запроса:**
    ```json
    {
      "enabled": false
    }
    ```
    """
    try:
        result = await session.execute(
            select(Source).where(Source.id == str(source_id))
        )
        source = result.scalar_one_or_none()

        if not source:
            raise HTTPException(404, "Источник не найден")

        old_state = source.enabled
        source.enabled = payload.enabled

        await session.commit()
        await session.refresh(source)

        logger.info(
            f"🔧 Источник '{source.name}' ({source.id}): {old_state} → {payload.enabled}"
        )

        return source

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка изменения состояния источника {source_id}")
        raise HTTPException(500, "Не удалось изменить состояние источника")

