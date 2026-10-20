from typing import Annotated

from app.schemas.transit import (
    RouteGeoJSONFeature,
    RouteListItem,
    RouteStopItem,
    StopRoutesResponse,
)
from app.services.transit_service import (
    TransitService,
    TransitServiceError,
    get_transit_service,
)
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/transit", tags=["Transit"])


@router.get("/routes", response_model=list[RouteListItem])
async def list_routes(
    service: Annotated[TransitService, Depends(get_transit_service)],
) -> list[RouteListItem]:
    """Get sorted list of all active transit lines with metadata."""
    return await service.list_routes()


@router.get("/routes/{route_identifier}", response_model=RouteGeoJSONFeature)
async def get_route_geometry(
    route_identifier: str,
    service: Annotated[TransitService, Depends(get_transit_service)],
) -> RouteGeoJSONFeature:
    """Get route LineString geometry as GeoJSON by public number or internal ID."""
    try:
        return await service.get_route_geometry(route_identifier)
    except TransitServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.to_dict(),
        ) from exc


@router.get("/routes/{route_identifier}/stops", response_model=list[RouteStopItem])
async def get_route_stops(
    route_identifier: str,
    service: Annotated[TransitService, Depends(get_transit_service)],
) -> list[RouteStopItem]:
    """Get ordered stops for a route by public number or internal ID."""
    try:
        return await service.get_route_stops(route_identifier)
    except TransitServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.to_dict(),
        ) from exc


@router.get("/stops/{stop_id}/routes", response_model=StopRoutesResponse)
async def get_stop_routes(
    stop_id: str,
    service: Annotated[TransitService, Depends(get_transit_service)],
) -> StopRoutesResponse:
    """Get all lines stopping at a given stop."""
    try:
        return await service.get_stop_routes(stop_id)
    except TransitServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.to_dict(),
        ) from exc
