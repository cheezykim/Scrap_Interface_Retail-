"""One-time interactive authorization for the shared Telegram session."""

import asyncio
from pathlib import Path
import sys

# Allow direct execution with: python scripts/authorize_telegram.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telethon import TelegramClient

from app.config import Settings


async def main() -> None:
    settings = Settings.from_env()
    client = TelegramClient(
        str(settings.telegram_session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )

    print("Starting one-time Telegram administrator authorization...")
    await client.start(phone=settings.telegram_phone_number)
    try:
        user = await client.get_me()
        display_name = " ".join(
            part for part in (user.first_name, user.last_name) if part
        ) or user.username or str(user.id)
        print(f"Telegram session authorized successfully for: {display_name}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
