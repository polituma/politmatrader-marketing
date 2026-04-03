"""
Application settings with validation.

All values are read from environment variables (or .env file).
Pydantic validates types and constraints at startup so misconfigurations
fail loudly rather than silently corrupting data at runtime.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Application ----
    app_env: str = "development"
    log_level: str = "INFO"
    base_url: str = "http://127.0.0.1:8000"
    default_timezone: str = "America/New_York"

    # ---- Database ----
    database_url: str = "sqlite:///./politma_marketing.db"

    # ---- Brand ----
    brand_name: str = "POLITMATRADER"
    brand_domain: str = "https://politmatrader.com"
    primary_offer: str = "Trading Challenges"
    coupon_code: str = "EASTER20"
    coupon_description: str = "20% OFF all challenges for the month of April"
    cta_primary: str = "Start Challenge Now"
    cta_secondary: str = "Visit PolitmaTrader.com"
    brand_primary_color: str = "#000000"
    brand_accent_color: str = "#C8A95A"

    # ---- Scheduling ----
    enable_autopublish: bool = False
    scheduler_daily_hour: int = 7
    scheduler_daily_minute: int = 0

    # ---- Security ----
    api_keys: str = ""  # comma-separated
    webhook_secret: str = ""
    cors_origins: str = "https://politmatrader.com"

    # ---- Webhooks (outbound) ----
    publish_webhook_url: Optional[str] = None
    publish_webhook_token: Optional[str] = None
    ai_webhook_url: Optional[str] = None
    ai_webhook_token: Optional[str] = None

    # ---- Rate Limiting ----
    rate_limit_per_minute: int = 60

    # ---- Derived helpers ----
    @property
    def api_key_list(self) -> List[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v

    @field_validator("brand_domain")
    @classmethod
    def validate_brand_domain(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("brand_domain must start with http:// or https://")
        return v.rstrip("/")


settings = Settings()
