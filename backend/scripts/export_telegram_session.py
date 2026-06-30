"""Print a Telethon string session for serverless hosting.

Run this after the local file session has already been authorized.
"""

import asyncio
from pathlib import Path
import sys

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402


async def main() -> None:
    load_dotenv(ROOT / ".env")
    settings = Settings.from_env()
    if not settings.telegram_session_path:
        raise RuntimeError("TELEGRAM_SESSION_PATH is required to export a string session.")

    client = TelegramClient(
        str(settings.telegram_session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError("The local Telegram session is not authorized yet.")
        print(StringSession.save(client.session))
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
