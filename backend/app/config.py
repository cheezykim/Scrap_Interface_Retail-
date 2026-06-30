"""Environment-backed application configuration."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping


class ConfigurationError(ValueError):
    """Raised when required backend configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone_number: str
    telegram_session_path: Path
    google_credentials_path: Path
    google_sheet_id: str
    google_worksheet_name: str = "Retail_Banking"
    timezone: str = "Asia/Phnom_Penh"
    history_limit: int = 100
    max_links: int = 100

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        """Load settings without silently falling back to embedded secrets."""
        env = os.environ if environ is None else environ
        required = (
            "TELEGRAM_API_ID",
            "TELEGRAM_API_HASH",
            "TELEGRAM_PHONE_NUMBER",
            "TELEGRAM_SESSION_PATH",
            "GOOGLE_CREDENTIALS_PATH",
            "GOOGLE_SHEET_ID",
        )
        missing = [name for name in required if not str(env.get(name, "")).strip()]
        if missing:
            raise ConfigurationError(
                "Missing required environment variables: " + ", ".join(missing)
            )

        try:
            api_id = int(env["TELEGRAM_API_ID"])
            history_limit = int(env.get("SCRAPER_HISTORY_LIMIT", "100"))
            max_links = int(env.get("SCRAPER_MAX_LINKS", "100"))
        except ValueError as exc:
            raise ConfigurationError(
                "TELEGRAM_API_ID, SCRAPER_HISTORY_LIMIT, and SCRAPER_MAX_LINKS "
                "must be integers."
            ) from exc

        if api_id <= 0 or history_limit <= 0 or max_links <= 0:
            raise ConfigurationError("Numeric configuration values must be positive.")

        return cls(
            telegram_api_id=api_id,
            telegram_api_hash=env["TELEGRAM_API_HASH"].strip(),
            telegram_phone_number=env["TELEGRAM_PHONE_NUMBER"].strip(),
            telegram_session_path=Path(env["TELEGRAM_SESSION_PATH"]).expanduser(),
            google_credentials_path=Path(env["GOOGLE_CREDENTIALS_PATH"]).expanduser(),
            google_sheet_id=env["GOOGLE_SHEET_ID"].strip(),
            google_worksheet_name=env.get(
                "GOOGLE_WORKSHEET_NAME", "Retail_Banking"
            ).strip() or "Retail_Banking",
            timezone=env.get("SCRAPER_TIMEZONE", "Asia/Phnom_Penh").strip()
            or "Asia/Phnom_Penh",
            history_limit=history_limit,
            max_links=max_links,
        )
