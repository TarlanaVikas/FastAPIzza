"""Runtime configuration, read from environment variables (and an optional .env file)."""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("fastapizza")


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"Environment variable {name} must be an integer, got {raw!r}") from None


def _secret_key() -> str:
    key = os.getenv("JWT_SECRET_KEY", "").strip()
    if key:
        if len(key) < 32:
            raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters long.")
        return key
    # No key configured: fall back to a random per-process key so the app never
    # ships with a guessable default. Tokens stop working when the process restarts.
    logger.warning(
        "JWT_SECRET_KEY is not set; using a temporary random key. "
        "Sessions will be invalidated on restart. Set JWT_SECRET_KEY for any real deployment."
    )
    return secrets.token_urlsafe(48)


@dataclass(frozen=True)
class Settings:
    app_name: str = "FastAPIzza"
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "").strip()
        or f"sqlite:///{PROJECT_ROOT / 'fastapizza.db'}"
    )
    jwt_secret_key: str = field(default_factory=_secret_key)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = field(default_factory=lambda: _int("ACCESS_TOKEN_MINUTES", 30))
    refresh_token_days: int = field(default_factory=lambda: _int("REFRESH_TOKEN_DAYS", 7))
    upload_dir: Path = field(
        default_factory=lambda: Path(os.getenv("UPLOAD_DIR", "").strip() or PROJECT_ROOT / "upload")
    )
    max_upload_bytes: int = field(default_factory=lambda: _int("MAX_UPLOAD_MB", 5) * 1024 * 1024)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def get_settings() -> Settings:
    return _settings


_settings = Settings()
