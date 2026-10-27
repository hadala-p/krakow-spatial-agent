from unittest.mock import MagicMock, patch

import pytest
from app.services.live_feed_service import LiveFeedService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
@patch("app.services.live_feed_service.httpx.AsyncClient.get")
async def test_live_feed_robust_route_matching(mock_get):
    """Verify that live feed correctly matches routes even with whitespace padding."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake"
    mock_get.return_value = mock_response

    with patch(
        "app.services.live_feed_service.gtfs_realtime_pb2.FeedMessage"
    ) as mock_feed_class:
        service = LiveFeedService()
        mock_feed = MagicMock()

        # Symulacja czystego rekordu z API GTFS-RT (ZTP)
        entity = MagicMock()
        entity.HasField.return_value = True
        entity.vehicle.trip.route_id = "139"
        entity.vehicle.vehicle.id = "BU123"
        entity.vehicle.position.latitude = 50.061
        entity.vehicle.position.longitude = 19.937

        mock_feed.entity = [entity]
        mock_feed_class.return_value = mock_feed

        await service.fetch_feed("bus_mpk")

        # Symulujemy żądanie ze spacja na końcu (częsty przypadek z bazy)
        result = await service.get_vehicles_geojson(
            route_short_name="139 ", vehicle_type="bus_mpk"
        )

        assert len(result["features"]) == 1, (
            "Pojazd nie został dopasowany z powodu formatowania znaków!"
        )
        assert result["features"][0]["properties"]["vehicle_id"] == "BU123"
