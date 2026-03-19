from __future__ import annotations

import os
from typing import ClassVar

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # Non-field constants (avoid Pydantic treating them as model fields)
    app_name_default: ClassVar[str] = "HealthFlow"

    APP_NAME: str = Field(
        default_factory=lambda: os.getenv("APP_NAME", Settings.app_name_default)
    )
    APP_ENV: str = Field(default_factory=lambda: os.getenv("APP_ENV", "local"))

    # API Key auth
    APP_API_KEY: str = Field(default_factory=lambda: os.getenv("APP_API_KEY", ""))

    # Database
    DB_URL: str = Field(
        default_factory=lambda: os.getenv("DB_URL", os.getenv("DATABASE_URL", ""))
    )
    DB_SCHEMA: str = Field(default_factory=lambda: os.getenv("DB_SCHEMA", "public"))

    # GenAI (optional; used by insights endpoints)
    GENAI_PROVIDER: str = Field(
        default_factory=lambda: os.getenv("GENAI_PROVIDER", "gemini")
    )
    GENAI_MODEL: str = Field(
        default_factory=lambda: os.getenv("GENAI_MODEL", "gemini-3-flash-preview")
    )
    GENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("GENAI_API_KEY", ""))
    GEMINI_API_KEY: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))


settings = Settings()
