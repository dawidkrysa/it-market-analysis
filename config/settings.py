"""Application settings and configuration.

This module centralizes all application configuration, making it easy to manage
environment-specific settings and maintain consistency across the application.
"""

import os
from typing import Any
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'

if env_path.exists():
    load_dotenv(env_path)

class Settings:
    """Application settings loaded from environment variables."""

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', '/app/logs/app.log')

    DATABASE_URL: str = os.getenv(
        'DATABASE_URL', 
        'postgresql://navigator:DeepDive_2026_Secure@db:5432/blue_ocean_db'
    )

    ADMIN_KEY: str = os.getenv('ADMIN_KEY','defau!tYolo511')

    
    @classmethod
    def validate(cls) -> None:
        """Validate configuration values."""
        if not cls.DATABASE_URL.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string.")
    
    @classmethod
    def get_all(cls)-> dict[str, Any]:
        """Get all configuration as a dictionary."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and key.isupper()
        }


# Validate on import
Settings.validate()