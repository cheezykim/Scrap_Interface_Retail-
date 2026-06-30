"""Safe Google Sheets output for Retail Banking scrape records."""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
import math
from typing import Any

from app.config import Settings
from .schema import SHEET_COLUMNS


class SheetSchemaError(RuntimeError):
    """Raised when an existing worksheet does not use the expected columns."""


@dataclass(frozen=True)
class SheetWriteResult:
    submitted: int
    appended: int
    duplicates: int
    worksheet_name: str


def _column_key(name: object) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower()).strip("_")


_COLUMN_ALIASES = {_column_key(column): column for column in SHEET_COLUMNS}
_COLUMN_ALIASES.update(
    {
        "call_plan": "Call_Plan",
        "client": "Client_Name",
        "client_name": "Client_Name",
    }
)


def _safe_cell(value: object) -> str | int | float | bool:
    """Convert Python/pandas-like missing values into Sheets-safe values."""
    if value is None:
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    return value if isinstance(value, (str, int, float, bool)) else str(value)


def normalize_record(record: Mapping[str, object]) -> dict[str, object]:
    """Align aliases and unknown/missing values to the canonical sheet schema."""
    normalized: dict[str, object] = {column: "" for column in SHEET_COLUMNS}
    for original_name, value in record.items():
        canonical = _COLUMN_ALIASES.get(_column_key(original_name))
        if canonical and normalized[canonical] in ("", None):
            normalized[canonical] = _safe_cell(value)
    return normalized


def record_identity(record: Mapping[str, object]) -> tuple[str, str, str, str]:
    """Identify the same Telegram report without collapsing distinct messages."""
    normalized = normalize_record(record)
    sender = normalized["Sender_ID"] or normalized["Sender_Name"]
    return tuple(
        str(value).strip()
        for value in (
            normalized["Source_Channel"],
            sender,
            normalized["Message_Date"],
            normalized["Raw_Text"],
        )
    )


def rows_to_records(values: Sequence[Sequence[object]]) -> list[dict[str, object]]:
    """Convert worksheet values into canonical records."""
    if not values:
        return []
    header = list(values[0])
    records: list[dict[str, object]] = []
    for row in values[1:]:
        padded = list(row) + [""] * max(0, len(header) - len(row))
        if any(str(cell).strip() for cell in padded):
            records.append(normalize_record(dict(zip(header, padded))))
    return records


class GoogleSheetsWriter:
    """Append new records while preserving all existing worksheet data."""

    def __init__(
        self,
        settings: Settings,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.settings = settings
        self._client_factory = client_factory or self._authorize

    def _authorize(self) -> Any:
        # Imports are delayed so parser and API tests do not require Google SDKs.
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = (
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        )
        credentials = Credentials.from_service_account_file(
            str(self.settings.google_credentials_path), scopes=scopes
        )
        return gspread.authorize(credentials)

    def write(self, records: Iterable[Mapping[str, object]]) -> SheetWriteResult:
        normalized = [normalize_record(record) for record in records]
        client = self._client_factory()
        worksheet = client.open_by_key(self.settings.google_sheet_id).worksheet(
            self.settings.google_worksheet_name
        )
        existing_values = worksheet.get_all_values()

        if not existing_values:
            worksheet.update("A1", [list(SHEET_COLUMNS)], value_input_option="RAW")
            existing_records: list[dict[str, object]] = []
        else:
            existing_header = tuple(existing_values[0])
            if existing_header != SHEET_COLUMNS:
                raise SheetSchemaError(
                    "Worksheet header does not match the required Retail Banking schema."
                )
            existing_records = rows_to_records(existing_values)

        seen = {record_identity(record) for record in existing_records}
        rows_to_append: list[list[object]] = []
        duplicate_count = 0

        for record in normalized:
            identity = record_identity(record)
            if identity in seen:
                duplicate_count += 1
                continue
            seen.add(identity)
            rows_to_append.append([record[column] for column in SHEET_COLUMNS])

        if rows_to_append:
            worksheet.append_rows(rows_to_append, value_input_option="RAW")

        return SheetWriteResult(
            submitted=len(normalized),
            appended=len(rows_to_append),
            duplicates=duplicate_count,
            worksheet_name=self.settings.google_worksheet_name,
        )
