import asyncio
from unittest.mock import MagicMock, patch

import httpx
import pytest
from app.main import app
from app.services.live_feed_service import LiveFeedService
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
@patch("app.services.live_feed_service.httpx.AsyncClient.get")
async def test_get_vehicles_geojson_parsing_and_filtering(mock_get):
    """Verify protobuf parsing and filtering by route_short_name (AC 4, AC 5, AC 6)."""
    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake_binary_data"
    mock_get.return_value = mock_response

    # Intercept Protobuf parsing
    with patch(
        "app.services.live_feed_service.gtfs_realtime_pb2.FeedMessage"
    ) as mock_feed_class:
        service = LiveFeedService()
        mock_feed = MagicMock()

        # Fake Bus 139
        entity1 = MagicMock()
        entity1.HasField.return_value = True
        entity1.vehicle.trip.route_id = "139"
        entity1.vehicle.vehicle.id = "BU123"
        entity1.vehicle.position.latitude = 50.061
        entity1.vehicle.position.longitude = 19.937
        entity1.vehicle.position.bearing = 90.0
        entity1.vehicle.position.speed = 10.5

        # Fake Tram 50
        entity2 = MagicMock()
        entity2.HasField.return_value = True
        entity2.vehicle.trip.route_id = "50"
        entity2.vehicle.vehicle.id = "TR456"
        entity2.vehicle.position.latitude = 50.062
        entity2.vehicle.position.longitude = 19.938

        mock_feed.entity = [entity1, entity2]
        mock_feed_class.return_value = mock_feed

        await service.fetch_feed("bus_mpk")

        # Test filtering for '139'
        result = await service.get_vehicles_geojson(
            route_short_name="139", vehicle_type="bus_mpk"
        )

        # Assertions
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 1

        feature = result["features"][0]
        assert feature["geometry"]["type"] == "Point"
        assert feature["geometry"]["coordinates"] == [19.937, 50.061]
        assert feature["properties"]["route_short_name"] == "139"
        assert feature["properties"]["vehicle_id"] == "BU123"


@pytest.mark.asyncio
async def test_live_api_endpoint():
    """Verify GET /api/v1/live/vehicles endpoint exposure."""
    with patch(
        "app.services.live_feed_service.LiveFeedService.get_vehicles_geojson"
    ) as mock_service:
        mock_service.return_value = {"type": "FeatureCollection", "features": []}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/live/vehicles?route_short_name=139")

        assert response.status_code == 200
        assert response.json() == {"type": "FeatureCollection", "features": []}
        mock_service.assert_called_once_with(route_short_name="139", vehicle_type=None)


@pytest.mark.asyncio
async def test_all_vehicle_feeds_are_fetched_concurrently():
    service = LiveFeedService()
    all_feeds_started = asyncio.Event()
    started_count = 0
    feed = MagicMock(entity=[])

    async def fake_fetch_feed(*args: object, **kwargs: object):
        nonlocal started_count
        started_count += 1
        if started_count == 3:
            all_feeds_started.set()
        await asyncio.wait_for(all_feeds_started.wait(), timeout=1)
        return feed

    with patch.object(service, "fetch_feed", side_effect=fake_fetch_feed) as fetch:
        await asyncio.wait_for(service.refresh_feeds(), timeout=2)

    assert fetch.await_count == 3
    assert all(call.kwargs["force_refresh"] for call in fetch.await_args_list)


@pytest.mark.asyncio
async def test_geojson_uses_cached_snapshot_without_fetching_feeds():
    service = LiveFeedService()
    service._cache["tram"] = MagicMock(entity=[])

    with patch.object(service, "fetch_feed") as fetch:
        result = await service.get_vehicles_geojson(vehicle_type="tram")

    assert result == {"type": "FeatureCollection", "features": []}
    fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_failure_preserves_last_successful_feed():
    service = LiveFeedService()
    stale_feed = MagicMock(entity=[])

    async def fake_fetch_feed(vehicle_type: str, **kwargs: object):
        if vehicle_type == "bus_mpk":
            raise httpx.TimeoutException("feed timed out")
        return MagicMock(entity=[])

    service._cache["bus_mpk"] = stale_feed
    with patch.object(service, "fetch_feed", side_effect=fake_fetch_feed):
        await service.refresh_feeds()

    assert service._cache["bus_mpk"] is stale_feed
