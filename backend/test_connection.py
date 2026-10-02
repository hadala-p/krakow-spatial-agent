import asyncio
import sys

from app.core.database import engine
from sqlalchemy import text


async def verify_postgis_connection() -> None:
    """Execute PostGIS version verification query via async engine."""
    query = text("SELECT PostGIS_Full_Version();")

    try:
        async with engine.connect() as connection:
            result = await connection.execute(query)
            postgis_version = result.scalar()
            print("Successfully connected to PostGIS database via asyncpg!")
            print(f"Version details:\n{postgis_version}")
    except Exception as exc:
        print(f"Database connection failed: {exc}", file=sys.stderr)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(verify_postgis_connection())
