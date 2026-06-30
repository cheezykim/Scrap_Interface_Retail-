"""Reusable, single-session Telegram scraping engine."""

import asyncio
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime
import random
from typing import Any

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel, PeerChat, PeerUser

from app.config import Settings
from .parser import extract_info_from_text, has_structured_fields
from .validation import localize_date_window, normalize_telegram_links


ProgressCallback = Callable[[dict[str, Any]], None]
LOCATION_MATCH_WINDOW_MINUTES = 15


class TelegramAuthorizationError(RuntimeError):
    """Raised when the administrator-owned Telegram session is not authorized."""


def _sender_id(from_id: object) -> str:
    if isinstance(from_id, PeerUser):
        return str(from_id.user_id)
    if isinstance(from_id, PeerChannel):
        return str(from_id.channel_id)
    if isinstance(from_id, PeerChat):
        return str(from_id.chat_id)
    return str(from_id)


def _geo_from_message(message: object) -> tuple[object | None, object | None]:
    media = getattr(message, "media", None)
    geo = getattr(media, "geo", None) if media else None
    if geo and hasattr(geo, "lat") and hasattr(geo, "long"):
        return geo.lat, geo.long
    return None, None


def _pop_nearest(
    candidates: list[dict[str, Any]],
    target_date: datetime,
    max_gap_minutes: int = LOCATION_MATCH_WINDOW_MINUTES,
) -> dict[str, Any] | None:
    best_index: int | None = None
    best_gap: float | None = None

    for index, candidate in enumerate(candidates):
        gap = abs((candidate["date"] - target_date).total_seconds())
        if gap <= max_gap_minutes * 60 and (best_gap is None or gap < best_gap):
            best_index = index
            best_gap = gap

    return None if best_index is None else candidates.pop(best_index)


class TelegramScraper:
    """Scrape user-submitted links through one pre-authorized account.

    The lock deliberately serializes all runs that share this engine instance so
    the Telethon session database is never used by overlapping jobs.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._run_lock = asyncio.Lock()
        self._sender_cache: dict[str, str] = {}

    @staticmethod
    def _emit(callback: ProgressCallback | None, **event: Any) -> None:
        if callback:
            callback(event)

    async def _get_sender_info(self, client: TelegramClient, from_id: object) -> tuple[str, str]:
        sender_id = _sender_id(from_id)
        if sender_id in self._sender_cache:
            return sender_id, self._sender_cache[sender_id]

        try:
            sender = await client.get_entity(from_id)
            first = getattr(sender, "first_name", "") or ""
            last = getattr(sender, "last_name", "") or ""
            sender_name = (first + " " + last).strip() or getattr(
                sender, "username", f"ID:{sender_id}"
            )
            await asyncio.sleep(random.uniform(0.5, 1.0))
        except Exception:
            sender_name = f"ID:{sender_id}"

        self._sender_cache[sender_id] = sender_name
        return sender_id, sender_name

    async def scrape(
        self,
        links: Sequence[str],
        start: datetime,
        end: datetime,
        progress: ProgressCallback | None = None,
    ) -> list[dict[str, Any]]:
        """Scrape all validated links and return records in notebook schema."""
        normalized_links = normalize_telegram_links(links, self.settings.max_links)
        start_local, end_local = localize_date_window(
            start, end, self.settings.timezone
        )

        async with self._run_lock:
            self._sender_cache.clear()
            self._emit(progress, type="started", total_links=len(normalized_links))

            session = (
                StringSession(self.settings.telegram_session_string)
                if self.settings.telegram_session_string
                else str(self.settings.telegram_session_path)
            )
            client = TelegramClient(
                session,
                self.settings.telegram_api_id,
                self.settings.telegram_api_hash,
            )
            await client.connect()
            try:
                if not await client.is_user_authorized():
                    raise TelegramAuthorizationError(
                        "The shared Telegram session is not authorized. "
                        "An administrator must sign in once before web jobs can run."
                    )

                all_records: list[dict[str, Any]] = []
                for index, link in enumerate(normalized_links, start=1):
                    self._emit(
                        progress,
                        type="channel_started",
                        link=link,
                        channel_index=index,
                        total_links=len(normalized_links),
                    )
                    records = await self._scrape_link(
                        client, link, start_local, end_local, progress
                    )
                    all_records.extend(records)
                    self._emit(
                        progress,
                        type="channel_completed",
                        link=link,
                        channel_index=index,
                        total_links=len(normalized_links),
                        records=len(records),
                        total_records=len(all_records),
                    )

                self._emit(progress, type="scrape_completed", records=len(all_records))
                return all_records
            finally:
                await client.disconnect()

    async def _scrape_link(
        self,
        client: TelegramClient,
        link: str,
        start: datetime,
        end: datetime,
        progress: ProgressCallback | None,
    ) -> list[dict[str, Any]]:
        entity = await client.get_entity(link)
        channel_name = getattr(entity, "title", link)
        records: list[dict[str, Any]] = []
        pending_text: dict[str, list[dict[str, Any]]] = defaultdict(list)
        pending_locations: dict[str, list[dict[str, Any]]] = defaultdict(list)
        offset_id = 0
        batch = 0

        while True:
            try:
                history = await client(
                    GetHistoryRequest(
                        peer=entity,
                        limit=self.settings.history_limit,
                        offset_id=offset_id,
                        offset_date=None,
                        max_id=0,
                        min_id=0,
                        add_offset=0,
                        hash=0,
                    )
                )
            except FloodWaitError as exc:
                wait_seconds = exc.seconds + random.randint(5, 15)
                self._emit(progress, type="flood_wait", seconds=wait_seconds)
                await asyncio.sleep(wait_seconds)
                continue
            except RPCError as exc:
                self._emit(progress, type="telegram_retry", message=str(exc))
                await asyncio.sleep(20)
                continue

            messages = history.messages
            if not messages:
                break

            offset_id = messages[-1].id
            batch += 1

            for message in messages:
                message_date = getattr(message, "date", None)
                if message_date is None:
                    continue
                local_date = message_date.astimezone(start.tzinfo)
                if local_date < start or local_date > end:
                    continue

                from_id = getattr(message, "from_id", None)
                sender_id = ""
                sender_name = ""
                if from_id:
                    sender_id, sender_name = await self._get_sender_info(client, from_id)

                raw_text = message.message or getattr(message, "caption", "") or ""
                text = raw_text.strip()
                latitude, longitude = _geo_from_message(message)
                has_location = latitude is not None and longitude is not None
                has_media = bool(getattr(message, "media", None))

                if has_location and not text:
                    if sender_id:
                        match = _pop_nearest(pending_text[sender_id], local_date)
                        if match:
                            record = records[match["record_index"]]
                            record["Latitude"] = latitude
                            record["Longitude"] = longitude
                            record["Has_Location"] = True
                        else:
                            pending_locations[sender_id].append(
                                {"date": local_date, "lat": latitude, "lon": longitude}
                            )
                    continue

                if not text or not has_structured_fields(text):
                    continue

                extracted = extract_info_from_text(text)
                record: dict[str, Any] = {
                    "Source_Channel": channel_name,
                    "Sender_ID": sender_id,
                    "Sender_Name": sender_name,
                    "Type": extracted["Type"],
                    "Call_Plan": extracted["Call Plan"],
                    "Direction": extracted["Direction"],
                    "Client_Name": extracted["Client Name"],
                    "Contact": extracted["Contact"],
                    "Category": extracted["Category"],
                    "Message_Date": local_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "Latitude": latitude if has_location else "",
                    "Longitude": longitude if has_location else "",
                    "Raw_Text": raw_text,
                    "Has_Image": bool(has_media and not has_location),
                    "Has_Location": has_location,
                }

                if sender_id and not has_location:
                    location = _pop_nearest(pending_locations[sender_id], local_date)
                    if location:
                        record["Latitude"] = location["lat"]
                        record["Longitude"] = location["lon"]
                        record["Has_Location"] = True

                records.append(record)
                if sender_id and not record["Has_Location"]:
                    pending_text[sender_id].append(
                        {"date": local_date, "record_index": len(records) - 1}
                    )

            self._emit(
                progress,
                type="batch_completed",
                channel=channel_name,
                batch=batch,
                records=len(records),
            )

            if messages[-1].date.astimezone(start.tzinfo) < start:
                break
            await asyncio.sleep(random.uniform(2.0, 4.0))

        return records
