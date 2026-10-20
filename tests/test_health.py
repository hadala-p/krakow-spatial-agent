from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.core.database import check_db_health
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError


@pytest.mark.parametrize(
    ("database_is_healthy", "expected_status", "expected_body"),
    [
        (True, 200, {"status": "healthy"}),
        (False, 503, {"status": "unhealthy"}),
    ],
)
@pytest.mark.asyncio
async def test_health_check(
    monkeypatch: pytest.MonkeyPatch,
    database_is_healthy: bool,
    expected_status: int,
    expected_body: dict[str, str],
) -> None:
    check_db_health = AsyncMock(return_value=database_is_healthy)
    monkeypatch.setattr("app.main.check_db_health", check_db_health)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == expected_status
    assert response.json() == expected_body
    check_db_health.assert_awaited_once()


@pytest.mark.parametrize(
    ("execute_error", "expected_health"),
    [(None, True), (SQLAlchemyError("database unavailable"), False)],
)
@pytest.mark.asyncio
async def test_check_db_health(
    monkeypatch: pytest.MonkeyPatch,
    execute_error: SQLAlchemyError | None,
    expected_health: bool,
) -> None:
    connection = AsyncMock()
    connection.execute.side_effect = execute_error

    @asynccontextmanager
    async def connect():
        yield connection

    monkeypatch.setattr("app.core.database.engine", SimpleNamespace(connect=connect))

    assert await check_db_health() is expected_health
    assert str(connection.execute.await_args.args[0]) == "SELECT 1;"
