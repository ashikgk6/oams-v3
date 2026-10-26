"""Deployment environment profile (Strategy discriminator for validators)."""

from __future__ import annotations

from enum import Enum


class AppEnvironment(str, Enum):
    development = "development"
    staging = "staging"
    production = "production"

    @classmethod
    def parse(cls, value: str) -> "AppEnvironment":
        normalized = (value or "development").strip().lower()
        aliases = {
            "dev": cls.development,
            "development": cls.development,
            "local": cls.development,
            "stage": cls.staging,
            "staging": cls.staging,
            "prod": cls.production,
            "production": cls.production,
        }
        if normalized not in aliases:
            raise ValueError(
                f"Unknown APP_ENV '{value}'. Use development|staging|production."
            )
        return aliases[normalized]

    @property
    def is_production_like(self) -> bool:
        return self in {AppEnvironment.staging, AppEnvironment.production}
