from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=True,
        extra="ignore",
    )

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgrespassword"
    POSTGRES_DB: str = "spatial_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = Field(default=5432, gt=0, le=65535)
    DATABASE_URL: str = ""

    GTFS_URLS: tuple[str, ...] = (
        "https://gtfs.ztp.krakow.pl/GTFS_KRK_A.zip",
        "https://gtfs.ztp.krakow.pl/GTFS_KRK_M.zip",
        "https://gtfs.ztp.krakow.pl/GTFS_KRK_T.zip",
    )
    APP_ENV: Literal["development", "test", "production"] = "development"

    @model_validator(mode="after")
    def assemble_database_url(self) -> Self:
        """Build asyncpg URL from components or normalize an explicit DATABASE_URL."""
        if not self.DATABASE_URL:
            self.DATABASE_URL = URL.create(
                drivername="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database=self.POSTGRES_DB,
            ).render_as_string(hide_password=False)
        elif self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgres://", "postgresql+asyncpg://", 1
            )
        elif self.DATABASE_URL.startswith("postgresql://"):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return self


settings = Settings()
