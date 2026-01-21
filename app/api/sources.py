# app/api/sources.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID

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

router = APIRouter(
    prefix="/api",
    tags=["posts"],
)

#======================================================
# Получение всех постов
#======================================================
@router.get("/posts", response_model=list[PostSchema])
async def get_posts(session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            select(Post)
            .options(selectinload(Post.keywords))
            .order_by(Post.created_at.desc())
        )
        return result.scalars().all()
    except Exception as e:
        logger.exception("❌ Ошибка получения списка постов")
        raise HTTPException(500, "Failed to fetch posts")

#======================================================
# Получение поста по ID
#======================================================
@router.get("/posts/{post_id}", response_model=PostSchema)
async def get_post(post_id: UUID, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            select(Post)
            .options(selectinload(Post.keywords))
            .where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        return post
    except HTTPException:
        raise
    except Exception as e:
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
    try:
        result = await session.execute(select(Post).where(Post.id == post_id))
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
    except Exception as e:
        logger.exception(f"❌ Ошибка обновления статуса поста {post_id}")
        raise HTTPException(500, "Failed to update post status")

#======================================================
# Удаление поста
#======================================================
@router.delete("/posts/{post_id}", response_model=DeleteResponseSchema)
async def delete_post(post_id: UUID, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()

        if not post:
            raise HTTPException(404, "Post not found")

        await session.delete(post)
        await session.commit()

        logger.warning(f"🗑 Пост удалён: {post_id}")
        return {"status": "ok", "detail": "Post deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Ошибка удаления поста {post_id}")
        raise HTTPException(500, "Failed to delete post")

#=======================================================
# Генерация постов вручную
#=======================================================
@router.post("/generate", response_model=GenerateResponseSchema)
async def generate_posts_manual():
    try:
        task = celery_app.send_task("generate_posts")
        logger.info(f"🚀 Ручной запуск генерации, task_id={task.id}")
        return {"status": "started", "generated_count": 0}
    except Exception as e:
        logger.exception("❌ Ошибка ручного запуска генерации")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start generation"
        )
