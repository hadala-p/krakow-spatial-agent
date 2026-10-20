import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_settings_load_env_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "DATABASE_URL",
        "GTFS_URLS",
        "APP_ENV",
    ):
        monkeypatch.delenv(var, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_USER=feed_user\n"
        'POSTGRES_PASSWORD="secret@word"\n'
        'GTFS_URLS=["https://example.com/a.zip"]\n'
        "APP_ENV=test\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.POSTGRES_USER == "feed_user"
    assert settings.GTFS_URLS == ("https://example.com/a.zip",)
    assert settings.APP_ENV == "test"
    assert "secret%40word@" in settings.DATABASE_URL


def test_settings_normalize_explicit_database_url() -> None:
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://user:pass@aws-0-eu-central-1.pooler.supabase.com:6543/postgres",
    )

    assert settings.DATABASE_URL == (
        "postgresql+asyncpg://user:pass@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )


def test_settings_reject_invalid_database_port() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, POSTGRES_PORT=70000)
