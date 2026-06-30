"""Environment-backed application configuration."""

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import Mapping


class ConfigurationError(ValueError):
    """Raised when required backend configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone_number: str
    telegram_session_path: Path | None
    telegram_session_string: str | None
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
            "GOOGLE_SHEET_ID",
        )
        missing = [name for name in required if not str(env.get(name, "")).strip()]
        if not str(env.get("TELEGRAM_SESSION_PATH", "")).strip() and not str(
            env.get("TELEGRAM_SESSION_STRING", "")
        ).strip():
            missing.append("TELEGRAM_SESSION_PATH or TELEGRAM_SESSION_STRING")
        if not str(env.get("GOOGLE_CREDENTIALS_PATH", "")).strip() and not str(
            env.get("GOOGLE_CREDENTIALS_JSON", "")
        ).strip():
            missing.append("GOOGLE_CREDENTIALS_PATH or GOOGLE_CREDENTIALS_JSON")
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

        google_credentials_path = _credentials_path_from_env(env)
        telegram_session_path = (
            Path(env["TELEGRAM_SESSION_PATH"]).expanduser()
            if str(env.get("TELEGRAM_SESSION_PATH", "")).strip()
            else None
        )

        return cls(
            telegram_api_id=api_id,
            telegram_api_hash=env["TELEGRAM_API_HASH"].strip(),
            telegram_phone_number=env["TELEGRAM_PHONE_NUMBER"].strip(),
            telegram_session_path=telegram_session_path,
            telegram_session_string=env.get("TELEGRAM_SESSION_STRING", "").strip()
            or None,
            google_credentials_path=google_credentials_path,
            google_sheet_id=env["GOOGLE_SHEET_ID"].strip(),
            google_worksheet_name=env.get(
                "GOOGLE_WORKSHEET_NAME", "Retail_Banking"
            ).strip() or "Retail_Banking",
            timezone=env.get("SCRAPER_TIMEZONE", "Asia/Phnom_Penh").strip()
            or "Asia/Phnom_Penh",
            history_limit=history_limit,
            max_links=max_links,
        )


def _credentials_path_from_env(env: Mapping[str, str]) -> Path:
    credentials_json = str(env.get("GOOGLE_CREDENTIALS_JSON", "")).strip()
    if credentials_json:
        path = Path(tempfile.gettempdir()) / "google-service-account.json"
        path.write_text(credentials_json, encoding="utf-8")
        return path
    return Path(env["GOOGLE_CREDENTIALS_PATH"]).expanduser()
