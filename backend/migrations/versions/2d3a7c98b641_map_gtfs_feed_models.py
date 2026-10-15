"""Replace legacy spatial tables with tables matching the GTFS files.

Revision ID: 2d3a7c98b641
Revises: a08728fc9fc5
Create Date: 2026-10-15 21:14:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = "2d3a7c98b641"
down_revision: str | Sequence[str] | None = "a08728fc9fc5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace the legacy schema with the nine provided GTFS tables."""
    op.drop_table("stop_times", if_exists=True)
    op.drop_table("trips", if_exists=True)
    op.drop_table("routes", if_exists=True)
    op.drop_table("stops", if_exists=True)
    op.drop_table("route_shapes", if_exists=True)

    op.create_table(
        "agency",
        sa.Column("agency_id", sa.Text(), nullable=False),
        sa.Column("agency_name", sa.Text(), nullable=False),
        sa.Column("agency_url", sa.Text(), nullable=False),
        sa.Column("agency_timezone", sa.Text(), nullable=False),
        sa.Column("agency_lang", sa.Text(), nullable=True),
        sa.Column("agency_phone", sa.Text(), nullable=True),
        sa.Column("agency_fare_url", sa.Text(), nullable=True),
        sa.Column("agency_email", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("agency_id"),
    )
    op.create_table(
        "calendar",
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("monday", sa.Boolean(), nullable=False),
        sa.Column("tuesday", sa.Boolean(), nullable=False),
        sa.Column("wednesday", sa.Boolean(), nullable=False),
        sa.Column("thursday", sa.Boolean(), nullable=False),
        sa.Column("friday", sa.Boolean(), nullable=False),
        sa.Column("saturday", sa.Boolean(), nullable=False),
        sa.Column("sunday", sa.Boolean(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("service_id"),
    )
    op.create_table(
        "calendar_dates",
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("exception_type", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("service_id", "date"),
    )
    op.create_table(
        "feed_info",
        sa.Column("feed_publisher_name", sa.Text(), nullable=False),
        sa.Column("feed_publisher_url", sa.Text(), nullable=False),
        sa.Column("feed_lang", sa.String(length=16), nullable=False),
        sa.Column("feed_start_date", sa.Date(), nullable=True),
        sa.Column("feed_end_date", sa.Date(), nullable=True),
        sa.Column("feed_version", sa.Text(), nullable=True),
        sa.Column("feed_contact_email", sa.Text(), nullable=True),
        sa.Column("feed_contact_url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint(
            "feed_publisher_name",
            "feed_publisher_url",
            "feed_lang",
            name="pk_feed_info",
        ),
    )
    op.create_table(
        "routes",
        sa.Column("route_id", sa.Text(), nullable=False),
        sa.Column("agency_id", sa.Text(), nullable=True),
        sa.Column("route_short_name", sa.Text(), nullable=True),
        sa.Column("route_long_name", sa.Text(), nullable=True),
        sa.Column("route_desc", sa.Text(), nullable=True),
        sa.Column("route_type", sa.Integer(), nullable=False),
        sa.Column("route_url", sa.Text(), nullable=True),
        sa.Column("route_color", sa.String(length=6), nullable=True),
        sa.Column("route_text_color", sa.String(length=6), nullable=True),
        sa.Column("route_sort_order", sa.Integer(), nullable=True),
        sa.Column("continuous_pickup", sa.Integer(), nullable=True),
        sa.Column("continuous_drop_off", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["agency_id"], ["agency.agency_id"]),
        sa.PrimaryKeyConstraint("route_id"),
    )
    op.create_index("ix_routes_route_short_name", "routes", ["route_short_name"])
    op.create_table(
        "shapes",
        sa.Column("shape_id", sa.Text(), nullable=False),
        sa.Column("shape_pt_lat", sa.Float(), nullable=False),
        sa.Column("shape_pt_lon", sa.Float(), nullable=False),
        sa.Column("shape_pt_sequence", sa.Integer(), nullable=False),
        sa.Column("shape_dist_traveled", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("shape_id", "shape_pt_sequence"),
    )
    op.create_table(
        "stops",
        sa.Column("stop_id", sa.Text(), nullable=False),
        sa.Column("stop_code", sa.Text(), nullable=True),
        sa.Column("stop_name", sa.Text(), nullable=True),
        sa.Column("stop_desc", sa.Text(), nullable=True),
        sa.Column("stop_lat", sa.Float(), nullable=True),
        sa.Column("stop_lon", sa.Float(), nullable=True),
        sa.Column("zone_id", sa.Text(), nullable=True),
        sa.Column("stop_url", sa.Text(), nullable=True),
        sa.Column("location_type", sa.Integer(), nullable=True),
        sa.Column("parent_station", sa.Text(), nullable=True),
        sa.Column("stop_timezone", sa.Text(), nullable=True),
        sa.Column("wheelchair_boarding", sa.Integer(), nullable=True),
        sa.Column("platform_code", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("stop_id"),
    )
    op.create_index("ix_stops_stop_code", "stops", ["stop_code"])
    op.create_index("ix_stops_stop_name", "stops", ["stop_name"])
    op.create_table(
        "trips",
        sa.Column("route_id", sa.Text(), nullable=False),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("trip_id", sa.Text(), nullable=False),
        sa.Column("trip_headsign", sa.Text(), nullable=True),
        sa.Column("trip_short_name", sa.Text(), nullable=True),
        sa.Column("direction_id", sa.Integer(), nullable=True),
        sa.Column("block_id", sa.Text(), nullable=True),
        sa.Column("shape_id", sa.Text(), nullable=True),
        sa.Column("wheelchair_accessible", sa.Integer(), nullable=True),
        sa.Column("bikes_allowed", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["route_id"], ["routes.route_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("trip_id"),
    )
    op.create_index("ix_trips_shape_id", "trips", ["shape_id"])
    op.create_table(
        "stop_times",
        sa.Column("trip_id", sa.Text(), nullable=False),
        sa.Column("arrival_time", sa.String(length=16), nullable=True),
        sa.Column("departure_time", sa.String(length=16), nullable=True),
        sa.Column("stop_id", sa.Text(), nullable=False),
        sa.Column("stop_sequence", sa.Integer(), nullable=False),
        sa.Column("stop_headsign", sa.Text(), nullable=True),
        sa.Column("pickup_type", sa.Integer(), nullable=True),
        sa.Column("drop_off_type", sa.Integer(), nullable=True),
        sa.Column("shape_dist_traveled", sa.Float(), nullable=True),
        sa.Column("timepoint", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["stop_id"], ["stops.stop_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.trip_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("trip_id", "stop_sequence"),
    )


def downgrade() -> None:
    """Restore the original spatial schema."""
    op.drop_table("stop_times")
    op.drop_index("ix_trips_shape_id", table_name="trips")
    op.drop_table("trips")
    op.drop_index("ix_stops_stop_name", table_name="stops")
    op.drop_index("ix_stops_stop_code", table_name="stops")
    op.drop_table("stops")
    op.drop_table("shapes")
    op.drop_index("ix_routes_route_short_name", table_name="routes")
    op.drop_table("routes")
    op.drop_table("feed_info")
    op.drop_table("calendar_dates")
    op.drop_table("calendar")
    op.drop_table("agency")

    op.create_table(
        "stops",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("stop_name", sa.String(length=255), nullable=False),
        sa.Column("stop_code", sa.String(length=32), nullable=True),
        sa.Column(
            "geom",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stops_stop_name", "stops", ["stop_name"])
    op.create_index("ix_stops_stop_code", "stops", ["stop_code"])
    op.create_index("idx_stops_geom", "stops", ["geom"], postgresql_using="gist")

    op.create_table(
        "routes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("route_short_name", sa.String(length=32), nullable=False),
        sa.Column("route_long_name", sa.String(length=255), nullable=False),
        sa.Column("route_type", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_routes_route_short_name", "routes", ["route_short_name"])

    op.create_table(
        "trips",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("route_id", sa.String(length=64), nullable=False),
        sa.Column("trip_headsign", sa.String(length=255), nullable=True),
        sa.Column("direction_id", sa.Integer(), nullable=True),
        sa.Column("shape_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trips_shape_id", "trips", ["shape_id"])

    op.create_table(
        "stop_times",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trip_id", sa.String(length=128), nullable=False),
        sa.Column("stop_id", sa.String(length=64), nullable=False),
        sa.Column("stop_sequence", sa.Integer(), nullable=False),
        sa.Column("arrival_time", sa.String(length=16), nullable=False),
        sa.Column("departure_time", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["stop_id"], ["stops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "route_shapes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shape_id", sa.String(length=64), nullable=False),
        sa.Column(
            "geom",
            Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_route_shapes_shape_id", "route_shapes", ["shape_id"])
    op.create_index(
        "idx_route_shapes_geom", "route_shapes", ["geom"], postgresql_using="gist"
    )
