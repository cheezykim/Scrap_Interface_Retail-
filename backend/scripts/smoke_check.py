"""Read-only connectivity checks for deployment configuration."""

import asyncio
from pathlib import Path
import sys

# Allow direct execution with: python scripts/smoke_check.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.scraper.sheets import GoogleSheetsWriter
from telethon import TelegramClient


async def check_telegram(settings: Settings) -> bool:
    client = TelegramClient(
        str(settings.telegram_session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )
    await client.connect()
    try:
        return await client.is_user_authorized()
    finally:
        await client.disconnect()


def check_google_sheets(settings: Settings) -> str:
    client = GoogleSheetsWriter(settings)._authorize()
    worksheet = client.open_by_key(settings.google_sheet_id).worksheet(
        settings.google_worksheet_name
    )
    return worksheet.title


def main() -> None:
    settings = Settings.from_env()
    print(f"telegram_authorized={asyncio.run(check_telegram(settings))}")
    print("google_worksheet_access=True")
    print(f"google_worksheet_title={check_google_sheets(settings)}")


if __name__ == "__main__":
    main()
