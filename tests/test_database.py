import pytest
from app.core.database import DATABASE_URL
from asyncpg.exceptions import PostgresSyntaxError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_postgis_extension_available():
    """Verify asynchronous connection and PostGIS extension readiness."""
    test_engine = create_async_engine(DATABASE_URL)
    query = text("SELECT PostGIS_Full_Version();")

    try:
        async with test_engine.connect() as connection:
            result = await connection.execute(query)
            postgis_version = result.scalar()

        assert postgis_version is not None
        assert "POSTGIS=" in postgis_version
    finally:
        await test_engine.dispose()


@pytest.mark.asyncio
async def test_invalid_sql_syntax():
    """Verify that PostGIS syntax errors are caught and raise PostgresSyntaxError."""
    test_engine = create_async_engine(DATABASE_URL)
    # Celowy blad: FORM zamiast FROM
    query = text("SELECT 1 FORM pg_database;")

    try:
        with pytest.raises(DBAPIError) as exc_info:
            async with test_engine.connect() as connection:
                await connection.execute(query)

        # Weryfikacja, ze wyjatek to bezposredni blad skladni z PostgreSQL
        assert isinstance(exc_info.value.orig, PostgresSyntaxError)
    finally:
        await test_engine.dispose()