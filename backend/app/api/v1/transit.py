from typing import Annotated

from app.core.database import get_db_session
from app.models.spatial import Route, Shape, Stop, StopTime, Trip
from app.schemas.transit import (
    DepartingRouteItem,
    RouteGeoJSONFeature,
    RouteStopItem,
    StopRoutesResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/transit", tags=["Transit"])


@router.get("/routes/{route_id}", response_model=RouteGeoJSONFeature)
async def get_route_geometry(
    route_id: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> RouteGeoJSONFeature:
    """Get route LineString geometry as GeoJSON."""
    stmt = (
        select(Route, Trip.shape_id)
        .outerjoin(Trip, Trip.route_id == Route.route_id)
        .where(Route.route_id == route_id)
        .order_by(Trip.trip_id)
        .limit(1)
    )
    res = await db.execute(stmt)
    row = res.first()

    if not row or not row[0]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route '{route_id}' not found",
        )

    route_obj, shape_id = row

    if shape_id:
        shape_stmt = (
            select(Shape.shape_pt_lon, Shape.shape_pt_lat)
            .where(Shape.shape_id == shape_id)
            .order_by(Shape.shape_pt_sequence)
        )
        shape_res = await db.execute(shape_stmt)
        coordinates = [[longitude, latitude] for longitude, latitude in shape_res.all()]
    else:
        coordinates = []

    if len(coordinates) < 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No geometry found for route '{route_id}'",
        )

    return RouteGeoJSONFeature(
        geometry={"type": "LineString", "coordinates": coordinates},
        properties={
            "route_id": route_obj.route_id,
            "route_short_name": route_obj.route_short_name,
            "route_long_name": route_obj.route_long_name,
        },
    )


@router.get("/routes/{route_id}/stops", response_model=list[RouteStopItem])
async def get_route_stops(
    route_id: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[RouteStopItem]:
    """Get ordered stops for a route."""
    stmt = (
        select(Trip)
        .where(Trip.route_id == route_id)
        .order_by(Trip.trip_id)
        .options(selectinload(Trip.stop_times).selectinload(StopTime.stop))
        .limit(1)
    )
    res = await db.execute(stmt)
    trip = res.scalar_one_or_none()

    if not trip or not trip.stop_times:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stops found for route '{route_id}'",
        )

    # Posortuj po kolejności na trasie
    sorted_stop_times = sorted(trip.stop_times, key=lambda st: st.stop_sequence)

    return [
        RouteStopItem(
            stop_id=st.stop.stop_id,
            stop_name=st.stop.stop_name,
            stop_sequence=st.stop_sequence,
            lat=st.stop.stop_lat,
            lon=st.stop.stop_lon,
        )
        for st in sorted_stop_times
    ]


@router.get("/stops/{stop_id}/routes", response_model=StopRoutesResponse)
async def get_stop_routes(
    stop_id: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StopRoutesResponse:
    """Get all lines stopping at a given stop."""
    stop = await db.get(Stop, stop_id)
    if not stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stop '{stop_id}' not found",
        )

    stmt = (
        select(Route.route_id, Route.route_short_name, Trip.trip_headsign)
        .join(Trip, Trip.route_id == Route.route_id)
        .join(StopTime, StopTime.trip_id == Trip.trip_id)
        .where(StopTime.stop_id == stop_id)
        .distinct()
        .order_by(Route.route_short_name, Trip.trip_headsign)
    )
    res = await db.execute(stmt)
    rows = res.all()

    return StopRoutesResponse(
        stop_id=stop.stop_id,
        stop_name=stop.stop_name,
        routes=[
            DepartingRouteItem(
                route_id=row[0],
                route_short_name=row[1],
                trip_headsign=row[2],
            )
            for row in rows
        ],
    )
