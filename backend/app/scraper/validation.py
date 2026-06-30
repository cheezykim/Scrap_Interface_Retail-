"""Validation and normalization for user-supplied scrape parameters."""

from datetime import datetime
import re
from typing import Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


TELEGRAM_LINK_RE = re.compile(
    r"^https://(?:www\.)?(?:t\.me|telegram\.me)/[^\s/]+/?$",
    re.IGNORECASE,
)


class ScrapeInputError(ValueError):
    """Raised when a scraping request cannot be safely executed."""


def normalize_telegram_links(links: Iterable[str], max_links: int = 100) -> list[str]:
    """Validate, trim, and de-duplicate Telegram links in submission order."""
    normalized: list[str] = []
    seen: set[str] = set()

    for raw_link in links:
        link = str(raw_link or "").strip().rstrip("/")
        if not link:
            continue
        if not TELEGRAM_LINK_RE.fullmatch(link):
            raise ScrapeInputError(f"Invalid Telegram link: {link}")

        key = link.casefold()
        if key not in seen:
            seen.add(key)
            normalized.append(link)

    if not normalized:
        raise ScrapeInputError("At least one Telegram link is required.")
    if len(normalized) > max_links:
        raise ScrapeInputError(f"A maximum of {max_links} Telegram links is allowed.")

    return normalized


def localize_date_window(
    start: datetime,
    end: datetime,
    timezone_name: str = "Asia/Phnom_Penh",
) -> tuple[datetime, datetime]:
    """Return an ordered, timezone-aware scrape window."""
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ScrapeInputError(f"Unknown timezone: {timezone_name}") from exc

    start_local = start.replace(tzinfo=timezone) if start.tzinfo is None else start.astimezone(timezone)
    end_local = end.replace(tzinfo=timezone) if end.tzinfo is None else end.astimezone(timezone)

    if start_local >= end_local:
        raise ScrapeInputError("Start date must be earlier than end date.")

    return start_local, end_local
