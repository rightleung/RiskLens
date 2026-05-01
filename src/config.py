"""Centralized runtime settings for RiskLens."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "RiskLens"
    app_port: int = 8000
    version: str = "1.1.0"

    sentry_dsn: str = ""
    environment: str = "development"
    debug: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    assess_max_concurrency: int = 8
    assess_ticker_timeout_seconds: float = 20.0
    symbol_search_timeout_seconds: float = 8.0
    cache_ttl_seconds: int = 600

    upstream_max_workers: int = 12
    data_cache_maxsize: int = 1000
    localized_name_cache_maxsize: int = 500

    assess_timeout_seconds: float = 25.0
    api_report_dir: str = "/tmp/credit_api_reports"
    rich_report_dir: str = "/tmp/risklens_rich_reports"
    mvp_report_dir: str = "/tmp/risklens_mvp_reports"
    ratio_report_dir: str = "../reports"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings loaded from environment and optional .env."""
    return Settings()


settings = get_settings()
