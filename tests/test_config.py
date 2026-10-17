import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_settings_load_env_file(tmp_path) -> None:
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


def test_settings_reject_invalid_database_port() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, POSTGRES_PORT=70000)
