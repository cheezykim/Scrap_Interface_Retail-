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
        self.assertEqual(str(settings.telegram_session_path), "..\\tg_sessions\\geo_scraper")
        self.assertIsNone(settings.telegram_session_string)
        self.assertEqual(settings.google_worksheet_name, "Retail_Banking")
        self.assertEqual(settings.timezone, "Asia/Phnom_Penh")
        self.assertEqual(settings.max_links, 100)

    def test_accepts_serverless_secret_values(self):
        env = dict(VALID_ENV)
        env.pop("TELEGRAM_SESSION_PATH")
        env.pop("GOOGLE_CREDENTIALS_PATH")
        env["TELEGRAM_SESSION_STRING"] = "sample-session"
        env["GOOGLE_CREDENTIALS_JSON"] = '{"type":"service_account"}'

        settings = Settings.from_env(env)

        self.assertIsNone(settings.telegram_session_path)
        self.assertEqual(settings.telegram_session_string, "sample-session")
        self.assertTrue(settings.google_credentials_path.name.endswith(".json"))

    def test_reports_all_missing_required_values(self):
        with self.assertRaises(ConfigurationError) as context:
            Settings.from_env({})

        self.assertIn("TELEGRAM_API_ID", str(context.exception))
        self.assertIn("GOOGLE_SHEET_ID", str(context.exception))

    def test_rejects_invalid_numeric_settings(self):
        invalid = dict(VALID_ENV, SCRAPER_MAX_LINKS="many")

        with self.assertRaises(ConfigurationError):
            Settings.from_env(invalid)
