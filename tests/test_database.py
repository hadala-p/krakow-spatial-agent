import pytest
from app.core.database import engine
from sqlalchemy import text


@pytest.mark.asyncio
async def test_postgis_extension_available():
    """Verify asynchronous connection and PostGIS extension readiness."""
    query = text("SELECT PostGIS_Full_Version();")

    async with engine.connect() as connection:
        result = await connection.execute(query)
        postgis_version = result.scalar()

    assert postgis_version is not None
    assert "POSTGIS=" in postgis_version
