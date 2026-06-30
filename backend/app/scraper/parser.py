"""Parser for labeled Retail Banking messages from Telegram.

This module is intentionally independent from Telethon, pandas, and Google Sheets
so the existing business rules can be tested without external services.
"""

import re

from .schema import FIELD_ORDER


FIELD_LABEL_ALIASES = {
    "type": "Type",
    "call plan": "Call Plan",
    "direction": "Direction",
    "client name": "Client Name",
    "client": "Client Name",
    "contact": "Contact",
    "category": "Category",
}

LABEL_PATTERN = r"Client\s*Name|Call\s*Plan|Direction|Category|Contact|Type"
LABEL_SEPARATOR_PATTERN = r"\s*[:：\-–—]\s*"
LABEL_LINE_RE = re.compile(
    rf"^\s*(?:[-*•]\s*)?(?P<label>{LABEL_PATTERN})"
    rf"\s*{LABEL_SEPARATOR_PATTERN}\s*(?P<value>.*)$",
    re.IGNORECASE,
)
INLINE_LABEL_RE = re.compile(
    rf"(?<!^)(?<!\n)(?<![-*•])[^\S\r\n]+"
    rf"(?=(?:{LABEL_PATTERN})\s*{LABEL_SEPARATOR_PATTERN})",
    re.IGNORECASE,
)
ONLY_LABEL_RE = re.compile(
    rf"^(?:{LABEL_PATTERN})\s*{LABEL_SEPARATOR_PATTERN}?\s*$",
    re.IGNORECASE,
)


def normalize_field_label(label: object) -> str | None:
    """Map a message label to its canonical field name."""
    cleaned = re.sub(r"\s+", " ", str(label or "").strip().lower())
    return FIELD_LABEL_ALIASES.get(cleaned)


def prepare_structured_text(text: object) -> str:
    """Normalize line endings and split labels written on a single line."""
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", normalized)
    return INLINE_LABEL_RE.sub("\n", normalized)


def clean_extracted_value(value: object) -> str:
    """Collapse whitespace and reject values that are actually labels."""
    cleaned = re.sub(r"\s+", " ", str(value or "").strip())
    if not cleaned or ONLY_LABEL_RE.match(cleaned):
        return ""

    if cleaned.lower() in FIELD_LABEL_ALIASES:
        return ""

    return cleaned


def extract_info_from_text(text: object) -> dict[str, str]:
    """Extract supported labeled values while preserving the notebook rules."""
    data = {field: "" for field in FIELD_ORDER}
    current_key: str | None = None
    current_value_lines: list[str] = []

    for raw_line in prepare_structured_text(text).splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            if current_key is not None:
                current_value_lines.append("")
            continue

        match = LABEL_LINE_RE.match(line)
        if match:
            if current_key is not None:
                data[current_key] = clean_extracted_value(
                    "\n".join(current_value_lines)
                )

            current_key = normalize_field_label(match.group("label"))
            current_value_lines = (
                [match.group("value") or ""] if current_key else []
            )
            continue

        if current_key is not None and not ONLY_LABEL_RE.match(line.strip()):
            current_value_lines.append(line.strip())

    if current_key is not None:
        data[current_key] = clean_extracted_value("\n".join(current_value_lines))

    return data


def has_structured_fields(text: object) -> bool:
    """Return whether a message contains at least one supported label."""
    return any(
        LABEL_LINE_RE.match(raw_line.strip())
        for raw_line in prepare_structured_text(text).splitlines()
    )
