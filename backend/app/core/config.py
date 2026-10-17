from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=True,
    )

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgrespassword"
    POSTGRES_DB: str = "spatial_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = Field(default=5432, gt=0, le=65535)

    GTFS_URLS: tuple[str, ...] = (
        "https://gtfs.ztp.krakow.pl/GTFS_KRK_A.zip",
        "https://gtfs.ztp.krakow.pl/GTFS_KRK_M.zip",
        "https://gtfs.ztp.krakow.pl/GTFS_KRK_T.zip",
    )
    APP_ENV: Literal["development", "test", "production"] = "development"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)


settings = Settings()
