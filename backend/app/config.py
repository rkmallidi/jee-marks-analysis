from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL used for both dev and prod — no SQLite fallback
    database_url: str = "postgresql+asyncpg://jee:jeepass@localhost:5432/jeedb"

    secret_key: str = "change-me-to-64-random-bytes-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    cors_origins: list[str] = ["http://localhost:5173"]
    environment: str = "development"

    # PostgreSQL connection pool tuning
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30


settings = Settings()
