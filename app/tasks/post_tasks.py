# app/tasks/post_tasks.py

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.celery_app import celery_app
from app.database import async_session
from app.models import NewsItem, Post, PostStatus, Keyword
from app.logger import logger
from app.ai.openai_client import openai_client, RateLimitError
from app.utils.rate_limit import CyclicRateLimiter

MAX_RETRIES = 3
MAX_PER_RUN = 3
MAX_DELETE_PER_RUN = 20
MIN_TEXT_LENGTH = 20  # минимальная длина сгенерированного текста


# =========================
# Генерация постов
# =========================
@celery_app.task(name="generate_posts")
def generate_posts():
    async def _main():
        async with async_session() as session:
            news_list = (await session.execute(
                select(NewsItem).limit(MAX_PER_RUN * 5)
            )).scalars().all()

            generated_count = 0
            rate_limiter = CyclicRateLimiter(burst=3, interval=20, cooldown=60)

            for news in news_list:
                if generated_count >= MAX_PER_RUN:
                    break

                post = (await session.execute(
                    select(Post).where(Post.news_id == news.id)
                )).scalar_one_or_none()

                # Пропускаем опубликованные
                if post and post.status == PostStatus.published:
                    continue

                # Архивируем failed, если превышен лимит retry
                if post and post.status == PostStatus.failed and post.retry_count >= MAX_RETRIES:
                    logger.info(f"📦 Архивирован failed пост: {news.id}")
                    post.status = PostStatus.archived
                    continue

                # Проверка источника текста
                text_source = (news.raw_text or news.summary or "").strip()
                if not text_source:
                    logger.warning(f"🟡 Пропущена пустая новость {news.id}")
                    continue

                try:
                    await rate_limiter.wait()
                    generated_text = await openai_client.generate_text(text_source)

                except RateLimitError as e:
                    logger.warning(f"⏳ Rate limit для {news.id}: {e}, ждём 60 сек")
                    await asyncio.sleep(60)
                    continue

                except Exception as e:
                    logger.warning(f"⚠️ Ошибка генерации для {news.id}: {e}")
                    if post:
                        post.retry_count += 1
                        post.error_message = str(e)
                        if post.retry_count >= MAX_RETRIES:
                            post.status = PostStatus.failed
                    else:
                        session.add(Post(
                            news_id=news.id,
                            status=PostStatus.failed,
                            retry_count=1,
                            error_message=str(e)
                        ))
                    continue

                # Проверка качества ответа
                clean_text = (generated_text or "").strip()
                if not clean_text or len(clean_text) < MIN_TEXT_LENGTH:
                    logger.warning(f"⚠️ Слишком короткий или пустой ответ OpenAI для {news.id}")
                    if post:
                        post.retry_count += 1
                        post.error_message = "Too short or empty OpenAI response"
                        if post.retry_count >= MAX_RETRIES:
                            post.status = PostStatus.failed
                    else:
                        session.add(Post(
                            news_id=news.id,
                            status=PostStatus.failed,
                            retry_count=1,
                            error_message="Too short or empty OpenAI response"
                        ))
                    continue

                # Успешная генерация
                if post:
                    post.generated_text = clean_text
                    post.status = PostStatus.new
                    post.retry_count = 0
                    post.error_message = None
                    logger.info(f"♻️ Обновлён пост для {news.id}")
                else:
                    session.add(Post(
                        news_id=news.id,
                        generated_text=clean_text,
                        status=PostStatus.new,
                        retry_count=0,
                        error_message=None
                    ))
                    logger.info(f"🆕 Создан пост для {news.id}")

                generated_count += 1

            await session.commit()
            return generated_count

    return asyncio.run(_main())


# =========================
# Очистка старых failed постов
# =========================
@celery_app.task(name="cleanup_old_failed_posts")
def cleanup_old_failed_posts(days: int = 7):
    async def _main():
        async with async_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            posts = (await session.execute(
                select(Post).where(
                    Post.status == PostStatus.failed,
                    Post.created_at < cutoff
                )
            )).scalars().all()

            deleted_count = 0
            for post in posts[:MAX_DELETE_PER_RUN]:
                await session.delete(post)
                deleted_count += 1

            await session.commit()
            return deleted_count

    return asyncio.run(_main())


# =========================
# Генерация ключевых слов
# =========================
@celery_app.task(name="generate_post_keywords")
def generate_post_keywords():
    async def _main():
        async with async_session() as session:
            posts = (await session.execute(
                select(Post)
                .options(selectinload(Post.keywords))
                .where(Post.status.in_([PostStatus.new, PostStatus.generated]))
            )).scalars().all()

            updated_count = 0
            rate_limiter = CyclicRateLimiter(burst=3, interval=20, cooldown=60)

            for post in posts:
                if post.keywords:
                    continue

                text = (post.generated_text or "").strip()
                if not text:
                    logger.warning(f"🟡 Пропущен пост {post.id}, пустой текст")
                    continue

                keywords = []
                for attempt in range(MAX_RETRIES):
                    try:
                        await rate_limiter.wait()
                        keywords = await openai_client.generate_keywords(text)
                        if keywords:
                            break
                    except RateLimitError:
                        logger.warning("⏳ Rate limit при генерации тегов, ждём 60 сек")
                        await asyncio.sleep(60)
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка генерации тегов для {post.id}: {e}")

                if not keywords:
                    logger.error(f"❌ Не удалось сгенерировать теги для поста {post.id}")
                    continue

                for word in keywords:
                    try:
                        keyword_obj = (await session.execute(
                            select(Keyword).where(Keyword.word == word)
                        )).scalar_one_or_none()

                        if not keyword_obj:
                            keyword_obj = Keyword(word=word)
                            session.add(keyword_obj)
                            await session.flush()

                        if keyword_obj not in post.keywords:
                            post.keywords.append(keyword_obj)

                    except IntegrityError:
                        await session.rollback()

                updated_count += 1
                logger.info(f"🏷 Теги для поста {post.id}: {keywords}")

            await session.commit()
            return updated_count

    return asyncio.run(_main())
