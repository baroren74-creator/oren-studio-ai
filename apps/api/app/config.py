"""Settings — loaded from environment variables (see .env.example at the
repo root). ADR-006: simple API-key auth for the MVP, not Clerk/Auth.js.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    studio_api_key: str = "change-me"
    database_url: str = "sqlite:///./oren_studio_dev.db"


settings = Settings()
