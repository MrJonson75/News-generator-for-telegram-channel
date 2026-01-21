# app/api/sources.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import Optional

from app.database import get_session
from app.models import Post
from app.api.schemas import (
    PostSchema,
    PostStatusUpdateSchema,
    DeleteResponseSchema,
    GenerateResponseSchema,
)
from app.celery_app import celery_app
from app.logger import logger
from app.api.schemas import PostStatus

router = APIRouter(prefix="/api", tags=["posts"])


#======================================================
# Получение всех постов
#======================================================
@router.get("/posts", response_model=list[PostSchema])
async def get_posts(
    status: Optional[PostStatus] = Query(None, description="Фильтр по статусу поста"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получение списка постов.

    Можно:
    - фильтровать по статусу (?status=new)
    - использовать пагинацию (?page=1&size=20)
    """
    try:
        stmt = select(Post).options(selectinload(Post.keywords))

        if status:
            stmt = stmt.where(Post.status == status)

        stmt = (
            stmt.order_by(Post.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )

        result = await session.execute(stmt)
        return result.scalars().all()

    except Exception:
        logger.exception("❌ Ошибка получения постов")
        raise HTTPException(500, "Failed to fetch posts")


#======================================================
# Получение поста по ID
#======================================================
@router.get("/posts/{post_id}", response_model=PostSchema)
async def get_post(post_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    Получение одного поста по ID.
    """
    try:
        result = await session.execute(
            select(Post)
            .options(selectinload(Post.keywords))
            .where(Post.id == str(post_id))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise HTTPException(404, "Post not found")
        return post

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка получения поста {post_id}")
        raise HTTPException(500, "Failed to fetch post")


#======================================================
# Изменение статуса поста
#======================================================
@router.patch("/posts/{post_id}/status", response_model=PostSchema)
async def update_post_status(
    post_id: UUID,
    payload: PostStatusUpdateSchema,
    session: AsyncSession = Depends(get_session)
):
    """
    Ручное изменение статуса поста.
    """
    try:
        result = await session.execute(select(Post).where(Post.id == str(post_id)))
        post = result.scalar_one_or_none()

        if not post:
            raise HTTPException(404, "Post not found")

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
        raise HTTPException(500, "Failed to update status")


#======================================================
# Удаление поста
#======================================================
@router.delete("/posts/{post_id}", response_model=DeleteResponseSchema)
async def delete_post(post_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    Удаление поста по ID.
    """
    try:
        result = await session.execute(select(Post).where(Post.id == str(post_id)))
        post = result.scalar_one_or_none()

        if not post:
            raise HTTPException(404, "Post not found")

        await session.delete(post)
        await session.commit()

        logger.warning(f"🗑 Пост удалён: {post_id}")
        return {"status": "ok", "detail": "Post deleted"}

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка удаления поста {post_id}")
        raise HTTPException(500, "Failed to delete post")


#=======================================================
# Генерация постов вручную
#=======================================================
@router.post("/generate", response_model=GenerateResponseSchema)
async def generate_posts_manual():
    """
    Ручной запуск генерации постов через Celery.
    """
    try:
        task = celery_app.send_task("generate_posts")
        logger.info(f"🚀 Ручной запуск генерации, task_id={task.id}")
        return {"status": "started", "generated_count": 0}
    except Exception:
        logger.exception("❌ Ошибка ручного запуска генерации")
        raise HTTPException(500, "Failed to start generation")


#======================================================
# Публикация поста в Telegram
#======================================================
@router.post("/posts/{post_id}/publish", response_model=PostSchema)
async def publish_post(post_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    Публикация поста в Telegram.

    Меняет статус поста на published.
    В будущем сюда можно подключить реальную отправку в Telegram.
    """
    try:
        result = await session.execute(select(Post).where(Post.id == str(post_id)))
        post = result.scalar_one_or_none()

        if not post:
            raise HTTPException(404, "Post not found")

        if post.status != PostStatus.generated:
            raise HTTPException(400, "Post must be in 'generated' status to publish")

        post.status = PostStatus.published

        await session.commit()
        await session.refresh(post)

        logger.info(f"📢 Пост опубликован: {post_id}")
        return post

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"❌ Ошибка публикации поста {post_id}")
        raise HTTPException(500, "Failed to publish post")

