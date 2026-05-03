"""Centralized runtime settings for RiskLens."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
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

    assess_max_concurrency: int = Field(8, ge=1)
    assess_ticker_timeout_seconds: float = Field(20.0, gt=0)
    symbol_search_timeout_seconds: float = Field(8.0, gt=0)
    cache_ttl_seconds: int = Field(600, gt=0)

    upstream_max_workers: int = Field(12, ge=1)
    pdf_max_workers: int = Field(2, ge=1)
    search_max_workers: int = Field(3, ge=1)
    data_cache_maxsize: int = Field(1000, ge=1)
    localized_name_cache_maxsize: int = Field(500, ge=1)
    negative_cache_ttl_seconds: int = Field(300, gt=0)

    yfinance_clear_proxy_mode: str = "retry_only"
    pdf_export_timeout_seconds: float = Field(20.0, gt=0)
    single_flight_wait_timeout_seconds: float = Field(20.0, gt=0)
    max_pdf_periods: int = Field(12, ge=1)
    max_pdf_detail_rows: int = Field(80, ge=1)

    assess_timeout_seconds: float = Field(25.0, gt=0)
    api_report_dir: str = "/tmp/credit_api_reports"
    rich_report_dir: str = "/tmp/risklens_rich_reports"
    mvp_report_dir: str = "/tmp/risklens_mvp_reports"
    ratio_report_dir: str = "../reports"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings loaded from environment and optional .env."""
    return Settings()


settings = get_settings()
