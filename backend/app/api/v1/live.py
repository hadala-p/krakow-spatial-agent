from app.services.live_feed_service import live_feed_service
from fastapi import APIRouter, Query

router = APIRouter(prefix="/live", tags=["Live Telemetry"])


@router.get("/vehicles", summary="Get live vehicle positions mapped to GeoJSON")
async def get_live_vehicles(
    route_short_name: str | None = Query(
        None, description="Filter by line number (e.g. '139')"
    ),
    vehicle_type: str | None = Query(
        None, description="Filter by type ('bus' or 'tram')"
    ),
):
    return await live_feed_service.get_vehicles_geojson(
        route_short_name=route_short_name, vehicle_type=vehicle_type
    )
