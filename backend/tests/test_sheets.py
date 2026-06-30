import unittest

from app.config import Settings
from app.scraper.schema import SHEET_COLUMNS
from app.scraper.sheets import GoogleSheetsWriter, SheetSchemaError, normalize_record


def make_record(name="Dara", raw_text="Type: Visit"):
    return {
        "Source_Channel": "Retail Team",
        "Sender_ID": "101",
        "Sender_Name": name,
        "Type": "Visit",
        "Message_Date": "2026-06-25 10:00:00",
        "Raw_Text": raw_text,
    }


class FakeWorksheet:
    def __init__(self, values=None):
        self.values = values or []
        self.updated = []
        self.appended = []

    def get_all_values(self):
        return self.values

    def update(self, range_name, values, value_input_option=None):
        self.updated.append((range_name, values, value_input_option))
        self.values = values

    def append_rows(self, rows, value_input_option=None):
        self.appended.extend(rows)


class FakeSpreadsheet:
    def __init__(self, worksheet):
        self._worksheet = worksheet

    def worksheet(self, name):
        return self._worksheet


class FakeClient:
    def __init__(self, worksheet):
        self._worksheet = worksheet

    def open_by_key(self, sheet_id):
        return FakeSpreadsheet(self._worksheet)


def settings():
    return Settings.from_env(
        {
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "sample-hash",
            "TELEGRAM_PHONE_NUMBER": "+855000000000",
            "TELEGRAM_SESSION_PATH": "session",
            "GOOGLE_CREDENTIALS_PATH": "credentials.json",
            "GOOGLE_SHEET_ID": "sheet-id",
        }
    )


class GoogleSheetsWriterTests(unittest.TestCase):
    def writer_for(self, worksheet):
        return GoogleSheetsWriter(settings(), lambda: FakeClient(worksheet))

    def test_normalizes_aliases_and_missing_values(self):
        record = normalize_record({"Client Name": "Sokha", "Latitude": None})

        self.assertEqual(record["Client_Name"], "Sokha")
        self.assertEqual(record["Latitude"], "")
        self.assertEqual(tuple(record), SHEET_COLUMNS)

    def test_creates_header_and_appends_to_empty_sheet(self):
        worksheet = FakeWorksheet()

        result = self.writer_for(worksheet).write([make_record()])

        self.assertEqual(worksheet.updated[0][1], [list(SHEET_COLUMNS)])
        self.assertEqual(len(worksheet.appended), 1)
        self.assertEqual(result.appended, 1)

    def test_skips_existing_and_submitted_duplicates(self):
        existing = normalize_record(make_record())
        worksheet = FakeWorksheet(
            [list(SHEET_COLUMNS), [existing[column] for column in SHEET_COLUMNS]]
        )

        result = self.writer_for(worksheet).write([make_record(), make_record()])

        self.assertEqual(worksheet.appended, [])
        self.assertEqual(result.duplicates, 2)

    def test_keeps_distinct_messages_from_same_sender_and_time(self):
        worksheet = FakeWorksheet([list(SHEET_COLUMNS)])

        result = self.writer_for(worksheet).write(
            [make_record(raw_text="Type: Visit"), make_record(raw_text="Type: Call")]
        )

        self.assertEqual(result.appended, 2)

    def test_refuses_to_write_under_an_unknown_header(self):
        worksheet = FakeWorksheet([["Wrong", "Header"], ["a", "b"]])

        with self.assertRaises(SheetSchemaError):
            self.writer_for(worksheet).write([make_record()])

        self.assertEqual(worksheet.appended, [])


if __name__ == "__main__":
    unittest.main()
