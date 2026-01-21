# app/tasks/post_tasks.py
import asyncio
from datetime import datetime, timedelta
from app.celery_app import celery_app
from sqlalchemy import select
from app.database import async_session
from app.models import NewsItem, Post, PostStatus
from app.logger import logger
from app.ai.openai_client import openai_client

MAX_RETRIES = 3
MAX_PER_RUN = 3
MAX_DELETE_PER_RUN = 20  # лимит на очистку за один прогон


@celery_app.task(name="generate_posts")
def generate_posts():
    """
    Генерация постов на основе новостей через OpenAI GPT-4o-mini.

    Логика:
    - published → не трогаем
    - failed → перегенерация если retry < MAX_RETRIES
    - retry_count >= MAX_RETRIES → failed
    - generated → перегенерация
    """

    async def _main():
        async with async_session() as session:
            result = await session.execute(select(NewsItem))
            news_list = result.scalars().all()
            generated_count = 0

            for news in news_list:
                if generated_count >= MAX_PER_RUN:
                    break

                result_post = await session.execute(
                    select(Post).where(Post.news_id == news.id)
                )
                post = result_post.scalar_one_or_none()

                # Не трогаем опубликованные
                if post and post.status == PostStatus.published:
                    continue

                # Удаляем failed, если превышен лимит retry
                if post and post.status == PostStatus.failed and post.retry_count >= MAX_RETRIES:
                    logger.info(f"🗑 Удаляем failed пост и новость: {news.id}")
                    await session.delete(post)
                    await session.delete(news)
                    continue

                source_text = news.raw_text or news.summary

                try:
                    generated_text = await openai_client.generate_text(source_text)
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка генерации для {news.id}: {e}")
                    if post:
                        post.retry_count += 1
                        post.error_message = str(e)
                        if post.retry_count >= MAX_RETRIES:
                            post.status = PostStatus.failed
                    else:
                        post = Post(
                            news_id=news.id,
                            status=PostStatus.failed,
                            retry_count=1,
                            error_message=str(e),
                        )
                        session.add(post)
                    continue

                if not generated_text or not generated_text.strip():
                    logger.warning(f"⚠️ Пустой ответ OpenAI для {news.id}")
                    if post:
                        post.retry_count += 1
                        post.error_message = "Empty OpenAI response"
                        if post.retry_count >= MAX_RETRIES:
                            post.status = PostStatus.failed
                    else:
                        post = Post(
                            news_id=news.id,
                            status=PostStatus.failed,
                            retry_count=1,
                            error_message="Empty OpenAI response",
                        )
                        session.add(post)
                    continue

                # Успешная генерация
                if post:
                    post.generated_text = generated_text
                    post.status = PostStatus.new
                    post.retry_count = 0
                    post.error_message = None
                    logger.info(f"♻️ Обновлён пост для {news.id}")
                else:
                    new_post = Post(
                        news_id=news.id,
                        generated_text=generated_text,
                        status=PostStatus.new,
                        retry_count=0,
                        error_message=None,
                    )
                    session.add(new_post)
                    logger.info(f"🆕 Создан пост для {news.id}")

                generated_count += 1
                # Небольшая пауза между запросами к OpenAI
                await asyncio.sleep(0.5)

            await session.commit()
            return generated_count

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    count = loop.run_until_complete(_main())
    logger.info(f"✅ Сгенерировано постов: {count}")
    return count


@celery_app.task(name="cleanup_old_failed_posts")
def cleanup_old_failed_posts(days: int = 7):
    """
    Автоочистка старых failed постов и связанных новостей.
    Удаляются посты со статусом failed и которые старше `days`.
    Лимит на удаление за один прогон: MAX_DELETE_PER_RUN
    """

    async def _main():
        async with async_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)

            result = await session.execute(
                select(Post).where(
                    Post.status == PostStatus.failed,
                    Post.created_at < cutoff
                )
            )
            old_failed_posts = result.scalars().all()

            deleted_count = 0
            for i, post in enumerate(old_failed_posts):
                if i >= MAX_DELETE_PER_RUN:
                    break
                if post.news:
                    await session.delete(post.news)
                await session.delete(post)
                deleted_count += 1

            await session.commit()
            return deleted_count

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    count = loop.run_until_complete(_main())
    logger.info(f"🗑 Очистка старых failed постов: {count} удалено")
    return count
