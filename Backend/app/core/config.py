from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://careloop:careloop@localhost:5432/careloop"
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    # Which chat model powers note processing, coverage checks and plain language.
    llm_provider: Literal["gemini", "anthropic", "openai"] = "gemini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_pool_size: int = 5
    reminder_days: int = 3
    database_max_overflow: int = 10

    @property
    def async_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def sync_database_url(self) -> str:
        return self.async_database_url.replace("+asyncpg", "", 1)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
