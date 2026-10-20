from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models.spatial import Route, Shape, Stop, StopTime, Trip
from app.schemas.transit import (
    DepartingRouteItem,
    GeoJSONGeometry,
    RouteGeoJSONFeature,
    RouteListItem,
    RouteStopItem,
    StopRoutesResponse,
)


class TransitServiceError(Exception):
    """Base exception for transit service operations."""

    code: str = "TRANSIT_ERROR"

    def __init__(self, message: str, identifier: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.identifier = identifier

    def to_dict(self) -> dict[str, str]:
        data = {"code": self.code, "message": self.message}
        if self.identifier is not None:
            data["identifier"] = self.identifier
        return data


class RouteNotFoundError(TransitServiceError):
    """Raised when a route identifier cannot be resolved."""

    code: str = "ROUTE_NOT_FOUND"


class GeometryNotFoundError(TransitServiceError):
    """Raised when route has no associated geometry shape."""

    code: str = "GEOMETRY_NOT_FOUND"


class StopsNotFoundError(TransitServiceError):
    """Raised when no stops are found for a route."""

    code: str = "STOPS_NOT_FOUND"


class StopNotFoundError(TransitServiceError):
    """Raised when a stop is not found."""

    code: str = "STOP_NOT_FOUND"


class TransitService:
    """Service encapsulating transit database queries and business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_routes(self) -> list[RouteListItem]:
        """Fetch all routes sorted by public route short name."""
        stmt = select(Route).order_by(
            Route.route_short_name.asc(), Route.route_id.asc()
        )
        res = await self.db.execute(stmt)
        routes = res.scalars().all()
        return [
            RouteListItem(
                id=r.route_id,
                route_short_name=r.route_short_name,
                route_long_name=r.route_long_name,
                route_type=r.route_type,
            )
            for r in routes
        ]

    async def get_route_by_identifier(self, route_identifier: str) -> Route | None:
        """Resolve route by route_short_name first, falling back to route_id."""
        stmt_short_name = (
            select(Route)
            .where(Route.route_short_name == route_identifier)
            .order_by(Route.route_id)
            .limit(1)
        )
        res = await self.db.execute(stmt_short_name)
        route = res.scalar_one_or_none()
        if route is not None:
            return route

        stmt_id = select(Route).where(Route.route_id == route_identifier).limit(1)
        res = await self.db.execute(stmt_id)
        return res.scalar_one_or_none()

    async def get_route_geometry(self, route_identifier: str) -> RouteGeoJSONFeature:
        """Get route geometry as GeoJSON by public number or internal ID."""
        route = await self.get_route_by_identifier(route_identifier)
        if not route:
            raise RouteNotFoundError(
                f"Route '{route_identifier}' not found",
                identifier=route_identifier,
            )

        trip_stmt = (
            select(Trip.shape_id)
            .where(Trip.route_id == route.route_id)
            .where(Trip.shape_id.is_not(None))
            .order_by(Trip.trip_id)
            .limit(1)
        )
        trip_res = await self.db.execute(trip_stmt)
        shape_id = trip_res.scalar_one_or_none()

        if not shape_id:
            raise GeometryNotFoundError(
                f"No geometry found for route '{route_identifier}'",
                identifier=route_identifier,
            )

        shape_stmt = (
            select(Shape.shape_pt_lon, Shape.shape_pt_lat)
            .where(Shape.shape_id == shape_id)
            .order_by(Shape.shape_pt_sequence)
        )
        shape_res = await self.db.execute(shape_stmt)
        coordinates = [[longitude, latitude] for longitude, latitude in shape_res.all()]

        if len(coordinates) < 2:
            raise GeometryNotFoundError(
                f"No geometry found for route '{route_identifier}'",
                identifier=route_identifier,
            )

        return RouteGeoJSONFeature(
            geometry=GeoJSONGeometry(type="LineString", coordinates=coordinates),
            properties={
                "route_id": route.route_id,
                "route_short_name": route.route_short_name,
                "route_long_name": route.route_long_name,
            },
        )

    async def get_route_stops(self, route_identifier: str) -> list[RouteStopItem]:
        """Get ordered stops for a route by public number or internal ID."""
        route = await self.get_route_by_identifier(route_identifier)
        if not route:
            raise RouteNotFoundError(
                f"Route '{route_identifier}' not found",
                identifier=route_identifier,
            )

        stmt = (
            select(Trip)
            .where(Trip.route_id == route.route_id)
            .order_by(Trip.trip_id)
            .options(selectinload(Trip.stop_times).selectinload(StopTime.stop))
            .limit(1)
        )
        res = await self.db.execute(stmt)
        trip = res.scalar_one_or_none()

        if not trip or not trip.stop_times:
            raise StopsNotFoundError(
                f"No stops found for route '{route_identifier}'",
                identifier=route_identifier,
            )

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

    async def get_stop_routes(self, stop_id: str) -> StopRoutesResponse:
        """Get all lines stopping at a given stop."""
        stop = await self.db.get(Stop, stop_id)
        if not stop:
            raise StopNotFoundError(
                f"Stop '{stop_id}' not found",
                identifier=stop_id,
            )

        stmt = (
            select(Route.route_id, Route.route_short_name, Trip.trip_headsign)
            .join(Trip, Trip.route_id == Route.route_id)
            .join(StopTime, StopTime.trip_id == Trip.trip_id)
            .where(StopTime.stop_id == stop_id)
            .distinct()
            .order_by(Route.route_short_name, Trip.trip_headsign)
        )
        res = await self.db.execute(stmt)
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


def get_transit_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TransitService:
    """FastAPI dependency provider for TransitService."""
    return TransitService(db)
