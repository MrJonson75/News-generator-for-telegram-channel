# app/news_parser/parser_telegram.py
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from app.config import settings
from app.logger import logger
from app.utils.rate_limit import random_delay


async def parse_telegram_channel(limit: int = 50):
    api_id = settings.telegram_api_id
    api_hash = settings.telegram_api_hash
    channel = settings.telegram_news_channel

    if not api_id or not api_hash:
        logger.error("❌ Не заданы TELEGRAM_API_ID или TELEGRAM_API_HASH")
        return []

    news_items = []

    async with TelegramClient("telegram_parser_session", api_id, api_hash) as client:
        logger.info(f"📡 Подключение к Telegram каналу: {channel}")

        async for message in client.iter_messages(channel, limit=min(limit, 60)):
            await random_delay(1.0, 2.5)  # защита от flood wait

            if not message.text:
                continue
            text = message.text.strip()
            if len(text) < 30:
                continue

            news_items.append(
                {
                    "title": message.text.split("\n")[0][:200],
                    "url": f"https://t.me/{channel}/{message.id}",
                    "summary": message.text[:500],
                    "source": "telegram",
                    "published_at": message.date.isoformat() if message.date else None,
                }
            )

    logger.info(f"Успешно спарсено сообщений Telegram: {len(news_items)}")
    return news_items



# Тестовый запуск
async def main():
    news = await parse_telegram_channel(limit=10)
    for item in news:
        print(item)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
