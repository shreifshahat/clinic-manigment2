"""Application settings.

Every secret is read from the environment (or a local ``.env``). Nothing here
is hardcoded: the defaults are safe for local development only and the
production guardrails below refuse to start with a wildcard CORS origin.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- runtime -------------------------------------------------------------
    app_name: str = "Clinic Management API"
    env: Environment = "local"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    docs_enabled: bool = True

    # --- clinic --------------------------------------------------------------
    clinic_name: str = "عيادة"
    clinic_phone: str = ""
    clinic_address: str = ""
    clinic_tax_number: str = ""
    clinic_timezone: str = "Africa/Cairo"
    clinic_currency: str = "EGP"
    currency_decimals: int = 2
    # ISO-8601 weekday numbering: Monday=1 ... Sunday=7. Default Saturday (6).
    week_start_weekday: int = Field(default=6, ge=1, le=7)

    # --- database ------------------------------------------------------------
    database_url: str = ""
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # --- supabase auth -------------------------------------------------------
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwks_url: str = ""

    # --- development-only authentication (never available in production) -----
    dev_auth_enabled: bool = False
    dev_auth_secret: str = ""

    # --- http ----------------------------------------------------------------
    cors_origins: str = "http://localhost:3000"
    access_token_ttl_minutes: int = 30
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15
    rate_limit_per_minute: int = 120
    # "database" = العدّاد مشترك بين كل العمليات والنسخ (الافتراضي في الإنتاج)
    # "memory"   = داخل العملية الواحدة (تطوير واختبارات)
    rate_limit_mode: Literal["database", "memory"] = "database"
    #: يسمح بتشغيل مهام الصيانة في الإنتاج (السكربت تطلبه صراحةً).
    allow_cleanup_in_production: bool = False

    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, value: str) -> str:
        return ",".join(origin.strip() for origin in value.split(",") if origin.strip())

    @field_validator("clinic_timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:  # pragma: no cover - config error
            raise ValueError(f"Unknown timezone: {value}") from exc
        return value

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if self.env == "production":
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS must not contain '*' in production")
            if self.docs_enabled:
                # OpenAPI stays reachable but only as JSON (no interactive UI)
                # in production so the endpoint map is not publicly browsable.
                pass
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
        return self

    # --- derived -------------------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin for origin in self.cors_origins.split(",") if origin]

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.clinic_timezone)

    @property
    def jwks_url(self) -> str:
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        if not self.supabase_url:
            return ""
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def supabase_auth_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1" if self.supabase_url else ""

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_test(self) -> bool:
        return self.env == "test"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
