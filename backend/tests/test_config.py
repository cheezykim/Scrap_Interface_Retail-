import unittest

from app.config import ConfigurationError, Settings


VALID_ENV = {
    "TELEGRAM_API_ID": "12345",
    "TELEGRAM_API_HASH": "sample-hash",
    "TELEGRAM_PHONE_NUMBER": "+855000000000",
    "TELEGRAM_SESSION_PATH": "../tg_sessions/geo_scraper",
    "GOOGLE_CREDENTIALS_PATH": "../khemra_account.json",
    "GOOGLE_SHEET_ID": "sample-sheet-id",
}


class SettingsTests(unittest.TestCase):
    def test_loads_required_settings_and_defaults(self):
        settings = Settings.from_env(VALID_ENV)

        self.assertEqual(settings.telegram_api_id, 12345)
        self.assertEqual(settings.google_worksheet_name, "Retail_Banking")
        self.assertEqual(settings.timezone, "Asia/Phnom_Penh")
        self.assertEqual(settings.max_links, 100)

    def test_reports_all_missing_required_values(self):
        with self.assertRaises(ConfigurationError) as context:
            Settings.from_env({})

        self.assertIn("TELEGRAM_API_ID", str(context.exception))
        self.assertIn("GOOGLE_SHEET_ID", str(context.exception))

    def test_rejects_invalid_numeric_settings(self):
        invalid = dict(VALID_ENV, SCRAPER_MAX_LINKS="many")

        with self.assertRaises(ConfigurationError):
            Settings.from_env(invalid)
