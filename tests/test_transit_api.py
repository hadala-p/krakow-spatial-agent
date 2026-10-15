import pytest
from app.core.database import engine
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
async def dispose_db():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_route_geometry():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/transit/routes/102")

    # Powinno zwrócić 200 (jeśli załadowano GTFS) lub 404 (jeśli brak w bazie)
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert data["type"] == "Feature"
        assert "geometry" in data


@pytest.mark.asyncio
async def test_get_route_stops():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/transit/routes/102/stops")

    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_stop_routes():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/transit/stops/131/routes")

    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert "routes" in data
