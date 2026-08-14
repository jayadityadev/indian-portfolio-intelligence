"""Application configuration.

All environment-driven settings live here. Read via `from app.config import settings`.
Values come from environment variables or a local `.env` file (copy `.env.example`).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"
    env: str = "dev"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql://ipu:ipu@localhost:5432/ipu"
    redis_url: str = "redis://localhost:6379/0"
    parquet_dir: str = "./data/parquet"

    twelvedata_api_key: str = ""
    nsepython_mode: str = "remote"
    nsepython_server: str = ""


settings = Settings()
