import asyncio
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.celery_app import celery_app
from app.database import async_session
from app.models import Post, PostStatus
from app.config import settings
from app.logger import logger

@celery_app.task(name="publish_posts_to_telegram")
def publish_posts_to_telegram():
    """
    Публикует посты со статусом `published` в Telegram канал через Telethon.
    После успешной публикации статус меняется на `sent`.
    Под новостью публикуются ключевые слова (теги) и ссылка на источник в кликабельном формате.
    """
    async def _main():
        client = TelegramClient(StringSession(), settings.telegram_api_id, settings.telegram_api_hash)
        await client.start(bot_token=settings.telegram_bot_token)
        logger.info("✅ Telegram client started")

        async with async_session() as session:
            result = await session.execute(
                select(Post)
                .where(Post.status == PostStatus.published)
                .options(
                    selectinload(Post.keywords),  # загружаем теги
                    selectinload(Post.news)       # загружаем связанный NewsItem
                )
            )
            posts = result.scalars().all()

            count = 0
            for post in posts:
                try:
                    message_text = post.generated_text or "Без текста"

                    # Добавляем теги, если есть
                    if post.keywords:
                        tags_text = " ".join(f"#{kw.word.replace(' ', '_')}" for kw in post.keywords)
                        message_text += f"\n\n{tags_text}"

                    # Добавляем кликабельную ссылку на источник
                    if post.news and post.news.url:
                        message_text += f"\n\n🔗 [Источник]({post.news.url})"

                    # Отправка сообщения с MarkdownV2
                    await client.send_message(
                        settings.telegram_channel_id,
                        message_text,
                        parse_mode="markdown"
                    )

                    # Обновляем статус поста после успешной публикации
                    post.status = PostStatus.sent
                    post.published_at = datetime.utcnow()
                    await session.commit()

                    logger.info(
                        f"📣 Опубликован пост {post.id} с тегами: "
                        + (', '.join(kw.word for kw in post.keywords) if post.keywords else "нет")
                        + (f" и источником: {post.news.url}" if post.news and post.news.url else "")
                    )
                    count += 1
                    await asyncio.sleep(1)

                except Exception as e:
                    await session.rollback()
                    logger.exception(f"❌ Ошибка публикации поста {post.id}: {e}")

        await client.disconnect()
        logger.info("✅ Telegram client disconnected")
        return count

    # --- запуск асинхронной функции ---
    count = asyncio.run(_main())
    logger.info(f"✅ Опубликовано постов в Telegram: {count}")
    return count
