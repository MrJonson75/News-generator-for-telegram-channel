# app/news_parser/parser_telegram.py
from typing import List, Dict
from datetime import datetime

from telethon import TelegramClient
from telethon.errors import FloodWaitError

from app.config import settings
from app.logger import logger
from app.utils.rate_limit import random_delay


async def parse_telegram_channel(limit: int = 50) -> List[Dict]:
    """
    Парсинг новостей из Telegram-канала.
    Возвращает данные в унифицированном формате для ParsedNewsSchema:

    {
        "title": str,
        "url": str,
        "summary": str,
        "published_at": datetime | None,
        "raw_text": str,
        "source": str,
        "source_type": "tg",
        "source_url": str
    }
    """
    api_id = settings.telegram_api_id
    api_hash = settings.telegram_api_hash
    channel = settings.telegram_news_channel

    if not api_id or not api_hash:
        logger.error("❌ Не заданы TELEGRAM_API_ID или TELEGRAM_API_HASH")
        return []

    if not channel:
        logger.error("❌ Не задан TELEGRAM_NEWS_CHANNEL")
        return []

    news_items: List[Dict] = []

    async with TelegramClient("telegram_parser_session", api_id, api_hash) as client:
        logger.info(f"📡 Подключение к Telegram каналу: {channel}")

        try:
            async for message in client.iter_messages(channel, limit=min(limit, 60)):
                await random_delay(1.0, 2.5)  # защита от flood wait

                if not message.text:
                    continue

                text = message.text.strip()
                if len(text) < 30:
                    continue

                title = text.split("\n")[0][:200]
                summary = text[:500]

                published_at = None
                if message.date:
                    try:
                        published_at = message.date
                    except Exception:
                        logger.warning(f"⚠️ Ошибка преобразования даты сообщения {message.id}")

                news_items.append(
                    {
                        "title": title,
                        "url": f"https://t.me/{channel}/{message.id}",
                        "summary": summary,
                        "published_at": published_at,
                        "raw_text": text,
                        "source": channel,
                        "source_type": "tg",
                        "source_url": f"https://t.me/{channel}",
                    }
                )
        except FloodWaitError as e:
            logger.warning(f"⏱ Телеграм просит ждать {e.seconds} секунд")
        except Exception as e:
            logger.exception(f"❌ Ошибка при чтении канала {channel}: {e}")

    logger.info(f"✅ Успешно спарсено сообщений Telegram: {len(news_items)}")
    return news_items


# =========================
# Тестовый запуск
# =========================
async def main():
    news = await parse_telegram_channel(limit=10)
    for item in news:
        print(item)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
