from typing import Literal

from pydantic import BaseModel, Field


class LiveVehiclePointGeometry(BaseModel):
    """RFC 7946 Point Geometry."""

    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(
        ...,
        description="[longitude, latitude] coordinates in WGS84 (EPSG:4326)",
        examples=[[19.9383, 50.0614]],
    )


class LiveVehicleProperties(BaseModel):
    """Telemetry attributes for an active transit vehicle."""

    vehicle_id: str
    route_short_name: str | None = None
    vehicle_type: Literal["bus", "tram"]
    bearing: float | None = None
    speed: float | None = None
    delay: int | None = None
    timestamp: int | None = None
    trip_id: str | None = None


class LiveVehicleFeature(BaseModel):
    """RFC 7946 Feature representation for a live vehicle."""

    type: Literal["Feature"] = "Feature"
    geometry: LiveVehiclePointGeometry
    properties: LiveVehicleProperties


class LiveVehicleFeatureCollection(BaseModel):
    """RFC 7946 FeatureCollection payload for live transit fleet."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[LiveVehicleFeature]
