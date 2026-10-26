"""Create a materialized view for route geometries.

Revision ID: b7269c5ef103
Revises: c4e13b21d67a
Create Date: 2026-10-26 13:32:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7269c5ef103"
down_revision: str | Sequence[str] | None = "c4e13b21d67a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Precompute simplified route geometries by route and direction."""
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_route_geometries AS
        WITH route_shapes AS (
            SELECT DISTINCT
                routes.route_id,
                routes.route_short_name,
                trips.direction_id,
                trips.shape_id
            FROM routes
            JOIN trips ON trips.route_id = routes.route_id
            WHERE trips.shape_id IS NOT NULL
        ),
        shape_geometries AS (
            SELECT
                shapes.shape_id,
                ST_MakeLine(
                    ST_SetSRID(
                        ST_MakePoint(shapes.shape_pt_lon, shapes.shape_pt_lat), 4326
                    )
                    ORDER BY shapes.shape_pt_sequence
                ) AS geom
            FROM shapes
            JOIN (SELECT DISTINCT shape_id FROM route_shapes) AS used_shapes
                ON used_shapes.shape_id = shapes.shape_id
            GROUP BY shapes.shape_id
            HAVING COUNT(*) >= 2
        )
        SELECT
            route_shapes.route_id,
            route_shapes.route_short_name,
            route_shapes.direction_id,
            ST_Simplify(ST_Union(shape_geometries.geom), 0.0001) AS geom
        FROM route_shapes
        JOIN shape_geometries ON shape_geometries.shape_id = route_shapes.shape_id
        GROUP BY
            route_shapes.route_id,
            route_shapes.route_short_name,
            route_shapes.direction_id
        """
    )
    op.create_index(
        "idx_mv_route_geometries_geom",
        "mv_route_geometries",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    """Drop the route geometry materialized view."""
    op.drop_index("idx_mv_route_geometries_geom", table_name="mv_route_geometries")
    op.execute("DROP MATERIALIZED VIEW mv_route_geometries")
