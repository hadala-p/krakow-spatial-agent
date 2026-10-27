"""Add a database function for route stop lookup.

Revision ID: 91d4e8a2c6f0
Revises: b7269c5ef103
Create Date: 2026-10-27 13:06:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91d4e8a2c6f0"
down_revision: str | Sequence[str] | None = "b7269c5ef103"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create one-query route and representative-trip stop lookup."""
    op.execute(
        """
        CREATE FUNCTION get_route_stops_by_identifier(p_identifier text)
        RETURNS TABLE (
            route_exists boolean,
            has_stops boolean,
            stop_id text,
            stop_name text,
            stop_sequence integer,
            stop_lat double precision,
            stop_lon double precision
        )
        LANGUAGE sql
        STABLE
        AS $function$
            WITH selected_route AS (
                SELECT routes.route_id
                FROM routes
                WHERE routes.route_short_name = p_identifier
                   OR routes.route_id = p_identifier
                ORDER BY
                    (routes.route_short_name = p_identifier) DESC,
                    routes.route_id
                LIMIT 1
            ),
            selected_trip AS (
                SELECT trips.trip_id
                FROM trips
                JOIN selected_route ON selected_route.route_id = trips.route_id
                ORDER BY trips.trip_id
                LIMIT 1
            )
            SELECT
                selected_route.route_id IS NOT NULL AS route_exists,
                stop_times.trip_id IS NOT NULL AS has_stops,
                stops.stop_id,
                stops.stop_name,
                stop_times.stop_sequence,
                stops.stop_lat,
                stops.stop_lon
            FROM (SELECT 1) AS singleton
            LEFT JOIN selected_route ON TRUE
            LEFT JOIN selected_trip ON TRUE
            LEFT JOIN stop_times ON stop_times.trip_id = selected_trip.trip_id
            LEFT JOIN stops ON stops.stop_id = stop_times.stop_id
            ORDER BY stop_times.stop_sequence NULLS LAST
        $function$
        """
    )


def downgrade() -> None:
    """Drop the route stop lookup function."""
    op.execute("DROP FUNCTION get_route_stops_by_identifier(text)")
