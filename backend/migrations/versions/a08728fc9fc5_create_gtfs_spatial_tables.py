"""Create GTFS tables and spatial indexes.

Revision ID: a08728fc9fc5
Revises:
Create Date: 2026-10-08 14:01:53.258908
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a08728fc9fc5"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "stops",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("stop_name", sa.String(length=255), nullable=False),
        sa.Column("stop_code", sa.String(length=32), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, spatial_index=False
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stops_stop_name", "stops", ["stop_name"], unique=False)
    op.create_index("ix_stops_stop_code", "stops", ["stop_code"], unique=False)
    op.create_index(
        "idx_stops_geom", "stops", ["geom"], unique=False, postgresql_using="gist"
    )
    op.create_table(
        "routes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("route_short_name", sa.String(length=32), nullable=False),
        sa.Column("route_long_name", sa.String(length=255), nullable=False),
        sa.Column("route_type", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_routes_route_short_name", "routes", ["route_short_name"], unique=False
    )
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
    op.create_index("ix_trips_shape_id", "trips", ["shape_id"], unique=False)
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
            geoalchemy2.types.Geometry(
                geometry_type="LINESTRING", srid=4326, spatial_index=False
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_route_shapes_shape_id", "route_shapes", ["shape_id"], unique=False
    )
    op.create_index(
        "idx_route_shapes_geom",
        "route_shapes",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_route_shapes_geom", table_name="route_shapes")
    op.drop_index("ix_route_shapes_shape_id", table_name="route_shapes")
    op.drop_table("route_shapes")
    op.drop_table("stop_times")
    op.drop_index("ix_trips_shape_id", table_name="trips")
    op.drop_table("trips")
    op.drop_index("ix_routes_route_short_name", table_name="routes")
    op.drop_table("routes")
    op.drop_index("idx_stops_geom", table_name="stops")
    op.drop_index("ix_stops_stop_code", table_name="stops")
    op.drop_index("ix_stops_stop_name", table_name="stops")
    op.drop_table("stops")
