from typing import Any, Literal

from pydantic import BaseModel, Field


class GeoJSONGeometry(BaseModel):
    """RFC 7946 Geometry representation."""

    type: str = Field(..., examples=["LineString", "MultiLineString"])
    coordinates: list[Any]


class RouteGeoJSONFeature(BaseModel):
    """RFC 7946 Feature object for route trace."""

    type: Literal["Feature"] = "Feature"
    geometry: GeoJSONGeometry
    properties: dict[str, Any]


class RouteListItem(BaseModel):
    """Transit route list item with metadata."""

    id: str
    route_short_name: str | None = None
    route_long_name: str | None = None
    route_type: int


class RouteStopItem(BaseModel):
    """Stop details on a route itinerary."""

    stop_id: str
    stop_name: str | None
    stop_sequence: int
    lat: float | None = None
    lon: float | None = None


class DepartingRouteItem(BaseModel):
    """Transit route departing from a given stop."""

    route_id: str
    route_short_name: str | None
    trip_headsign: str | None = None


class StopRoutesResponse(BaseModel):
    """Response containing stop metadata and serving routes."""

    stop_id: str
    stop_name: str | None
    routes: list[DepartingRouteItem]
