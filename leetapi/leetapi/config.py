from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{ROOT / 'data' / 'app.db'}"
    )

    llm_provider: str = "openrouter"

    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4.5"
    openrouter_referer: str = "http://localhost:3000"

    lmstudio_url: str = "http://localhost:1234/v1"
    lmstudio_model: str = "local-model"

    mlx_url: str = "http://localhost:8080/v1"
    mlx_model: str = "mlx-community/Llama-3.2-3B-Instruct-4bit"

    cors_origins: list[str] = ["http://localhost:3000"]

    repo_root: Path = ROOT
    problems_dir: Path = ROOT / "problems"

    @property
    def sync_database_url(self) -> str:
        return (
            self.database_url
            .replace("+aiosqlite", "")
            .replace("+asyncpg", "")
            .replace("+psycopg", "")
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
