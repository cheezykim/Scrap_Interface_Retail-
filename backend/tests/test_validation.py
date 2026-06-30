from datetime import datetime, timezone
import unittest

from app.scraper.validation import (
    ScrapeInputError,
    localize_date_window,
    normalize_telegram_links,
)


class ScrapeInputValidationTests(unittest.TestCase):
    def test_accepts_public_and_private_telegram_links(self):
        links = normalize_telegram_links(
            ["https://t.me/public_channel", "https://t.me/+privateInvite123"]
        )

        self.assertEqual(len(links), 2)

    def test_removes_duplicate_links(self):
        links = normalize_telegram_links(
            ["https://t.me/example/", "https://t.me/example"]
        )

        self.assertEqual(links, ["https://t.me/example"])

    def test_rejects_non_telegram_links(self):
        with self.assertRaises(ScrapeInputError):
            normalize_telegram_links(["https://example.com/channel"])

    def test_localizes_naive_dates_to_cambodia(self):
        start, end = localize_date_window(
            datetime(2026, 6, 1), datetime(2026, 6, 2)
        )

        self.assertEqual(start.utcoffset().total_seconds(), 7 * 60 * 60)
        self.assertLess(start, end)

    def test_converts_aware_dates_and_rejects_reverse_window(self):
        with self.assertRaises(ScrapeInputError):
            localize_date_window(
                datetime(2026, 6, 2, tzinfo=timezone.utc),
                datetime(2026, 6, 1, tzinfo=timezone.utc),
            )
