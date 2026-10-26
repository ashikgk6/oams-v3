"""
Startup configuration validators.

Patterns:
- Strategy: each validator encapsulates one rule
- Composite / Chain of Responsibility: CompositeStartupValidator runs all rules
- Open/Closed: add validators without changing bootstrap orchestration
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from app.bootstrap.environment import AppEnvironment
from app.config import Settings


class ConfigurationError(Exception):
    """Raised when production (or strict) settings are unsafe."""


class StartupValidator(Protocol):
    def validate(self, settings: Settings) -> None: ...


@dataclass(frozen=True)
class WeakSecretPatterns:
    """Shared denylist for obviously unsafe secrets."""

    fragments: tuple[str, ...] = (
        "change-me",
        "dev-secret",
        "dev-qr",
        "dev-cron",
        "secret-key-change",
        "admin123",
        "oams_secret",
        "password",
        "123456",
    )


class SecretStrengthValidator:
    """Fails when JWT/QR/cron secrets look like placeholders (prod/staging)."""

    def __init__(self, patterns: WeakSecretPatterns | None = None) -> None:
        self._patterns = patterns or WeakSecretPatterns()

    def validate(self, settings: Settings) -> None:
        if not settings.app_environment.is_production_like:
            return
        checks = {
            "SECRET_KEY": settings.secret_key,
            "QR_HMAC_SECRET": settings.qr_hmac_secret,
            "INTERNAL_CRON_SECRET": settings.internal_cron_secret,
        }
        errors: list[str] = []
        for name, value in checks.items():
            if len(value) < 24:
                errors.append(f"{name} must be at least 24 characters")
            lowered = value.lower()
            if any(frag in lowered for frag in self._patterns.fragments):
                errors.append(f"{name} looks like a default/placeholder secret")
        if errors:
            raise ConfigurationError("; ".join(errors))


class DatabaseUrlValidator:
    """Production must not use SQLite."""

    def validate(self, settings: Settings) -> None:
        if not settings.app_environment.is_production_like:
            return
        if settings.database_url.startswith("sqlite"):
            raise ConfigurationError(
                "Production/staging cannot use SQLite. Set DATABASE_URL to Postgres."
            )


class SchemaModeValidator:
    """Discourage create_all in production-like environments."""

    def validate(self, settings: Settings) -> None:
        if not settings.app_environment.is_production_like:
            return
        if settings.auto_create_schema:
            raise ConfigurationError(
                "AUTO_CREATE_SCHEMA must be false in production/staging; use Alembic."
            )


class CorsValidator:
    """Block wildcard CORS in production."""

    def validate(self, settings: Settings) -> None:
        if settings.app_environment != AppEnvironment.production:
            return
        origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
        if not origins or "*" in origins:
            raise ConfigurationError(
                "CORS_ORIGINS must be an explicit allow-list in production (no *)."
            )


class SeedPolicyValidator:
    """Warn-level policy: seeding demo users in production is blocked when strict."""

    def validate(self, settings: Settings) -> None:
        if settings.app_environment != AppEnvironment.production:
            return
        if settings.run_seed_on_startup and settings.strict_production:
            raise ConfigurationError(
                "RUN_SEED_ON_STARTUP must be false in strict production. "
                "Create the first admin out-of-band, then disable seeding."
            )


class CompositeStartupValidator:
    """Composite: runs child validators in order; first failure aborts boot."""

    def __init__(self, validators: Sequence[StartupValidator]) -> None:
        self._validators = list(validators)

    def validate(self, settings: Settings) -> None:
        for validator in self._validators:
            validator.validate(settings)


def default_production_validators() -> CompositeStartupValidator:
    return CompositeStartupValidator(
        [
            SecretStrengthValidator(),
            DatabaseUrlValidator(),
            SchemaModeValidator(),
            CorsValidator(),
            SeedPolicyValidator(),
        ]
    )
