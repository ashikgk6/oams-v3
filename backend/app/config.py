from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.bootstrap.environment import AppEnvironment


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./oams.db"
    secret_key: str = "dev-secret-key-change-me"
    qr_hmac_secret: str = "dev-qr-hmac-secret"
    internal_cron_secret: str = "dev-cron-secret"
    app_name: str = "OAMS Office"
    access_token_expire_minutes: int = 480
    seed_admin_email: str = "admin@office.local"
    seed_admin_password: str = "admin123"
    algorithm: str = "HS256"
    qr_ttl_seconds: int = 25
    duplicate_punch_minutes: int = 2
    # Dummy office coordinates for development only; replace before deployment.
    office_latitude: float = 12.924913
    office_longitude: float = 77.551212
    office_geofence_radius_meters: float = 100.0
    max_location_accuracy_meters: float = 50.0
    auto_create_schema: bool = True
    run_seed_on_startup: bool = True
    cors_origins: str = "*"
    # None = auto (off in production-like envs)
    enable_docs: bool | None = None
    strict_production: bool = True
    security_headers: bool = True

    @property
    def app_environment(self) -> AppEnvironment:
        return AppEnvironment.parse(self.app_env)

    @property
    def docs_enabled(self) -> bool:
        if self.enable_docs is not None:
            return self.enable_docs
        return not self.app_environment.is_production_like

    @model_validator(mode="after")
    def _normalize_env(self) -> "Settings":
        # Fail fast on unknown APP_ENV values.
        AppEnvironment.parse(self.app_env)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
