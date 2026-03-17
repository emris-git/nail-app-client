from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    client_api_base_url: AnyHttpUrl = Field(..., alias="CLIENT_API_BASE_URL")
    client_api_hmac_secret: str = Field(..., alias="CLIENT_API_HMAC_SECRET")
    redis_url: Optional[str] = Field(None, alias="REDIS_URL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

