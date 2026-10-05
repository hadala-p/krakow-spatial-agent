import pytest
from app.core.database import engine
from asyncpg.exceptions import PostgresSyntaxError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


@pytest.mark.asyncio
async def test_postgis_extension_available():
    """Verify asynchronous connection and PostGIS extension readiness."""
    query = text("SELECT PostGIS_Full_Version();")

    async with engine.connect() as connection:
        result = await connection.execute(query)
        postgis_version = result.scalar()

    assert postgis_version is not None
    assert "POSTGIS=" in postgis_version


@pytest.mark.asyncio
async def test_invalid_sql_syntax():
    """Verify that PostGIS syntax errors are caught and raise DBAPIError."""
    query = text("SELECT 1 FORM pg_database;")
    with pytest.raises(DBAPIError) as exc_info:
        async with engine.connect() as connection:
            await connection.execute(query)

    assert isinstance(exc_info.value.orig, PostgresSyntaxError)
