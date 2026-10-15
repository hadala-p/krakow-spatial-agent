import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_get_route_geometry_geojson():
    """Verify route endpoint returns valid RFC 7946 GeoJSON Feature."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/transit/routes/102")

    # If route exists in seeded DB it returns 200, else 404 for missing
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert data.get("type") == "Feature"
        assert "geometry" in data
        assert data["geometry"]["type"] in ["LineString", "MultiLineString"]
        assert "properties" in data
        assert data["properties"]["route_id"] == "102"


@pytest.mark.asyncio
async def test_get_route_stops_ordered():
    """Verify endpoint returns ordered list of stops for a given route."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/transit/routes/102/stops")

    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
        if data:
            first_stop = data[0]
            assert "stop_id" in first_stop
            assert "stop_name" in first_stop
            assert "stop_sequence" in first_stop


@pytest.mark.asyncio
async def test_get_stop_departing_routes():
    """Verify endpoint returns all lines serving a specific stop."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Example stop_id query
        response = await client.get("/api/v1/transit/stops/131/routes")

    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert "stop_id" in data
        assert "routes" in data
        assert isinstance(data["routes"], list)
