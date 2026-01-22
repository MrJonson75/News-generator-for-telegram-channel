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
from app.ai.openai_client import openai_client

MAX_RETRIES = 3
MAX_PER_RUN = 3
MAX_DELETE_PER_RUN = 20
OPENAI_DELAY = 0.5  # задержка между запросами к OpenAI
OPENAI_KEYWORD_DELAY = 20  # секунда, чтобы не превысить rate limit (RPM)


# =========================
# Генерация постов
# =========================
@celery_app.task(name="generate_posts")
def generate_posts():
    """
    Генерация постов на основе новостей и сохранение их в базе данных.
    Возвращает количество сгенерированных постов.

    """
    async def _main():
        async with async_session() as session:
            news_list = (await session.execute(select(NewsItem))).scalars().all()
            generated_count = 0

            for news in news_list:
                if generated_count >= MAX_PER_RUN:
                    break

                post = (await session.execute(select(Post).where(Post.news_id == news.id))).scalar_one_or_none()

                # Пропускаем уже опубликованные
                if post and post.status == PostStatus.published:
                    continue

                # Удаляем failed посты, если превышен лимит retry
                if post and post.status == PostStatus.failed and post.retry_count >= MAX_RETRIES:
                    logger.info(f"🗑 Удаляем failed пост и новость: {news.id}")
                    await session.delete(post)
                    await session.delete(news)
                    continue

                text_source = news.raw_text or news.summary
                try:
                    generated_text = await openai_client.generate_text(text_source)
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
                            error_message=str(e)
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
                            error_message="Empty OpenAI response"
                        )
                        session.add(post)
                    continue

                # Сохраняем успешную генерацию
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
                        error_message=None
                    )
                    session.add(new_post)
                    logger.info(f"🆕 Создан пост для {news.id}")

                generated_count += 1
                await asyncio.sleep(OPENAI_DELAY)

            await session.commit()
            return generated_count

    try:
        count = asyncio.run(_main())
    except RuntimeError:
        # fallback для Windows
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        count = loop.run_until_complete(_main())

    logger.info(f"✅ Сгенерировано постов: {count}")
    return count


# =========================
# Очистка старых failed постов
# =========================
@celery_app.task(name="cleanup_old_failed_posts")
def cleanup_old_failed_posts(days: int = 7):
    """
    Очистка старых failed постов, которые не удалось сгенерировать.

    """
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
            for i, post in enumerate(posts):
                if i >= MAX_DELETE_PER_RUN:
                    break
                if post.news:
                    await session.delete(post.news)
                await session.delete(post)
                deleted_count += 1

            await session.commit()
            return deleted_count

    try:
        count = asyncio.run(_main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        count = loop.run_until_complete(_main())

    logger.info(f"🗑 Очистка старых failed постов: {count} удалено")
    return count


# =========================
# Генерация ключевых слов (тегов) для постов
# =========================
@celery_app.task(name="generate_post_keywords")
def generate_post_keywords():
    """
    Генерация ключевых слов для постов на основе их текста.

    """
    async def _main():
        async with async_session() as session:
            # Загружаем посты и их keywords заранее (selectinload)
            posts = (await session.execute(
                select(Post)
                .options(selectinload(Post.keywords))
                .where(Post.status.in_([PostStatus.new, PostStatus.generated]))
            )).scalars().all()

            updated_count = 0

            for post in posts:
                if post.keywords:
                    logger.info(f"🟡 Пропущен пост {post.id}, теги уже есть")
                    continue

                text_for_analysis = post.generated_text or (post.news.summary if post.news else "")
                if not text_for_analysis.strip():
                    logger.info(f"🟡 Пропущен пост {post.id}, пустой текст")
                    continue

                keywords = []
                for attempt in range(MAX_RETRIES):
                    try:
                        keywords = await openai_client.generate_keywords(text_for_analysis)
                        if keywords:
                            break  # успешно получили
                    except Exception as e:
                        logger.warning(f"⚠️ Попытка {attempt+1}/{MAX_RETRIES} генерации тегов для {post.id} не удалась: {e}")
                        await asyncio.sleep(OPENAI_KEYWORD_DELAY)  # ждём перед повтором

                if not keywords:
                    logger.error(f"❌ Не удалось сгенерировать теги для поста {post.id} после {MAX_RETRIES} попыток")
                    continue

                for word in keywords:
                    try:
                        keyword_obj = (await session.execute(
                            select(Keyword).where(Keyword.word == word)
                        )).scalar_one_or_none()

                        if not keyword_obj:
                            keyword_obj = Keyword(word=word)
                            session.add(keyword_obj)
                            await session.flush()  # присвоение ID

                        if keyword_obj not in post.keywords:
                            post.keywords.append(keyword_obj)
                    except IntegrityError:
                        await session.rollback()
                        continue

                updated_count += 1
                logger.info(f"✅ Сгенерированы теги для поста {post.id}: {keywords}")
                await asyncio.sleep(OPENAI_KEYWORD_DELAY)  # соблюдаем rate limit

            await session.commit()
            return updated_count

    try:
        count = asyncio.run(_main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        count = loop.run_until_complete(_main())

    logger.info(f"🏷 Сгенерировано тегов для постов: {count}")
    return count
