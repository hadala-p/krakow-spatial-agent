from app.models.spatial import Route, RouteShape, Stop, StopTime, Trip
from geoalchemy2.types import Geometry


def test_stop_model_attributes_and_geometry():
    """Verify Stop model attributes and spatial point column definition."""
    columns = Stop.__table__.columns
    assert "id" in columns
    assert "stop_name" in columns
    assert "stop_code" in columns
    assert "geom" in columns

    geom_col = columns["geom"]
    assert isinstance(geom_col.type, Geometry)
    assert geom_col.type.geometry_type == "POINT"
    assert geom_col.type.srid == 4326
    assert geom_col.type.spatial_index is True


def test_route_model_attributes():
    """Verify Route model columns."""
    columns = Route.__table__.columns
    assert "id" in columns
    assert "route_short_name" in columns
    assert "route_long_name" in columns
    assert "route_type" in columns


def test_trip_model_attributes_and_relationships():
    """Verify Trip model columns and foreign key to routes table."""
    columns = Trip.__table__.columns
    assert "id" in columns
    assert "route_id" in columns
    assert "trip_headsign" in columns
    assert "direction_id" in columns
    assert "shape_id" in columns

    # Verify foreign key constraint targets routes.id
    route_fk = list(columns["route_id"].foreign_keys)
    assert len(route_fk) == 1
    assert route_fk[0].target_fullname == "routes.id"


def test_stop_time_model_attributes_and_foreign_keys():
    """Verify StopTime columns and foreign keys to trips and stops."""
    columns = StopTime.__table__.columns
    assert "id" in columns
    assert "trip_id" in columns
    assert "stop_id" in columns
    assert "stop_sequence" in columns
    assert "arrival_time" in columns
    assert "departure_time" in columns

    # Verify foreign keys
    trip_fk = list(columns["trip_id"].foreign_keys)
    assert len(trip_fk) == 1
    assert trip_fk[0].target_fullname == "trips.id"

    stop_fk = list(columns["stop_id"].foreign_keys)
    assert len(stop_fk) == 1
    assert stop_fk[0].target_fullname == "stops.id"


def test_route_shape_model_attributes_and_geometry():
    """Verify RouteShape model attributes and LineString geometry column."""
    columns = RouteShape.__table__.columns
    assert "id" in columns
    assert "shape_id" in columns
    assert "geom" in columns

    geom_col = columns["geom"]
    assert isinstance(geom_col.type, Geometry)
    assert geom_col.type.geometry_type == "LINESTRING"
    assert geom_col.type.srid == 4326
    assert geom_col.type.spatial_index is True
