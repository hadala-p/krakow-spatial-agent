from collections.abc import AsyncGenerator

import pytest
from app.core.database import engine
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.fixture(autouse=True)
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    yield engine
    await engine.dispose()
