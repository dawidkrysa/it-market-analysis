"""Application settings and configuration.

This module centralizes all application configuration, making it easy to manage
environment-specific settings and maintain consistency across the application.
"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

if env_path.exists():
    load_dotenv(env_path)


class Settings:
    """Application settings loaded from environment variables."""

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "app.log"))

    # Some providers hand out "postgres://" URLs; normalise to the scheme SQLAlchemy expects.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://CHANGE_ME:CHANGE_ME@db:5432/CHANGE_ME"
    ).replace("postgres://", "postgresql://", 1)

    ADMIN_KEY: str = os.getenv("ADMIN_KEY", "CHANGE_ME")

    # Automatic scraping (scrapers/scheduler.py). An interval <= 0 disables it.
    SCRAPE_INTERVAL_HOURS: float = float(os.getenv("SCRAPE_INTERVAL_HOURS", "24"))
    SCRAPE_LEVELS: str = os.getenv("SCRAPE_LEVELS", "junior,mid,senior")
    # Postings not seen by a successful scrape for this many days are deleted (0 keeps all).
    SCRAPE_RETENTION_DAYS: int = int(os.getenv("SCRAPE_RETENTION_DAYS", "30"))
    # Open a fresh DB connection per query instead of pooling, so an idle web service
    # holds no connections (lets Railway's serverless sleep kick in). Set to "1" to enable.
    DB_NULL_POOL: bool = os.getenv("DB_NULL_POOL", "0") == "1"

    @classmethod
    def validate(cls) -> None:
        """Validate configuration values."""
        if not cls.DATABASE_URL.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string.")

    @classmethod
    def get_all(cls) -> dict[str, Any]:
        """Get all configuration as a dictionary."""
        return {
            key: getattr(cls, key) for key in dir(cls) if not key.startswith("_") and key.isupper()
        }


# Validate on import
Settings.validate()
