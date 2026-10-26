"""Application bootstrap orchestration (Facade over startup concerns)."""

from __future__ import annotations

import logging

from app.bootstrap.validators import (
    CompositeStartupValidator,
    ConfigurationError,
    default_production_validators,
)
from app.config import Settings
from app.database import Base, SessionLocal, engine
from app.seed import seed_database

logger = logging.getLogger("oams.bootstrap")


class ApplicationBootstrap:
    """
    Single entry for process startup side-effects.
    Depends on Settings + optional StartupValidator (DIP).
    """

    def __init__(
        self,
        settings: Settings,
        validator: CompositeStartupValidator | None = None,
    ) -> None:
        self._settings = settings
        self._validator = validator or default_production_validators()

    def run(self) -> None:
        self._validator.validate(self._settings)
        logger.info(
            "Bootstrapping env=%s docs=%s",
            self._settings.app_env,
            self._settings.docs_enabled,
        )
        if self._settings.auto_create_schema:
            Base.metadata.create_all(bind=engine)
            logger.warning("AUTO_CREATE_SCHEMA enabled — use Alembic in production")
        if self._settings.run_seed_on_startup:
            db = SessionLocal()
            try:
                seed_database(db)
                logger.info("Seed completed")
            finally:
                db.close()


def validate_or_raise(settings: Settings) -> None:
    try:
        default_production_validators().validate(settings)
    except ConfigurationError:
        raise
