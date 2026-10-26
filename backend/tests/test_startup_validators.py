from app.bootstrap.environment import AppEnvironment
from app.bootstrap.validators import (
    CompositeStartupValidator,
    ConfigurationError,
    CorsValidator,
    DatabaseUrlValidator,
    SchemaModeValidator,
    SecretStrengthValidator,
    SeedPolicyValidator,
)
from app.config import Settings


def _settings(**overrides) -> Settings:
    base = {
        "app_env": "production",
        "database_url": "postgresql+psycopg2://oams:x@db/oams",
        "secret_key": "a" * 32,
        "qr_hmac_secret": "b" * 32,
        "internal_cron_secret": "c" * 32,
        "cors_origins": "https://attendance.example.com",
        "auto_create_schema": False,
        "run_seed_on_startup": False,
        "strict_production": True,
    }
    base.update(overrides)
    return Settings(**base)


def test_production_validators_pass_with_strong_config():
    default = CompositeStartupValidator(
        [
            SecretStrengthValidator(),
            DatabaseUrlValidator(),
            SchemaModeValidator(),
            CorsValidator(),
            SeedPolicyValidator(),
        ]
    )
    default.validate(_settings())


def test_rejects_weak_secret():
    try:
        SecretStrengthValidator().validate(_settings(secret_key="change-me-short"))
        assert False, "expected ConfigurationError"
    except ConfigurationError:
        pass


def test_rejects_sqlite_in_prod():
    try:
        DatabaseUrlValidator().validate(_settings(database_url="sqlite:///./x.db"))
        assert False
    except ConfigurationError:
        pass


def test_rejects_wildcard_cors_in_prod():
    try:
        CorsValidator().validate(_settings(cors_origins="*"))
        assert False
    except ConfigurationError:
        pass


def test_dev_allows_sqlite_and_weak_secrets():
    s = _settings(app_env="development", database_url="sqlite:///./x.db", secret_key="dev")
    # development validators no-op for these rules
    SecretStrengthValidator().validate(s)
    DatabaseUrlValidator().validate(s)
    assert AppEnvironment.parse("prod") is AppEnvironment.production
