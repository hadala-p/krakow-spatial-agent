import io
import zipfile

import geopandas as gpd
import httpx
import pandas as pd
from shapely.geometry import LineString
from sqlalchemy import create_engine, text

from app.core.database import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

GTFS_KRK_A_URL = "https://gtfs.ztp.krakow.pl/GTFS_KRK_A.zip"

SYNC_DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


def standardize_time_series(series: pd.Series) -> pd.Series:
    """Normalize GTFS time strings, wrapping hours >= 24 into 00-23."""

    def _normalize(val: str) -> str:
        if pd.isna(val):
            return val
        parts = str(val).strip().split(":")
        if len(parts) != 3:
            return val
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        h = h % 24
        return f"{h:02d}:{m:02d}:{s:02d}"

    return series.astype(str).apply(_normalize)


def build_route_shapes_geodataframe(df_shapes: pd.DataFrame) -> gpd.GeoDataFrame:
    """Sort shape points by sequence and build valid LineString geometries."""
    sorted_points = df_shapes.sort_values(["shape_id", "shape_pt_sequence"])

    geoms = (
        sorted_points.groupby("shape_id")
        .apply(
            lambda group: LineString(
                zip(group["shape_pt_lon"], group["shape_pt_lat"], strict=False)
            )
        )
        .reset_index(name="geom")
    )

    return gpd.GeoDataFrame(geoms, geometry="geom", crs="EPSG:4326")


def download_gtfs_archive(url: str = GTFS_KRK_A_URL) -> zipfile.ZipFile:
    """Fetch GTFS zip archive into an in-memory buffer."""
    with httpx.Client(timeout=60.0) as client:
        response = client.get(url)
        response.raise_for_status()
        return zipfile.ZipFile(io.BytesIO(response.content))


def ingest_gtfs_feed(
    zip_ref: zipfile.ZipFile, engine_url: str = SYNC_DATABASE_URL
) -> None:
    """Transform and idempotently bulk-insert GTFS tables into PostGIS."""
    engine = create_engine(engine_url)

    # 1. Ingest routes
    if "routes.txt" in zip_ref.namelist():
        with zip_ref.open("routes.txt") as f:
            df_routes = pd.read_csv(f, dtype=str)
        routes_payload = (
            df_routes[["route_id", "route_short_name", "route_long_name", "route_type"]]
            .rename(columns={"route_id": "id"})
            .to_dict(orient="records")
        )

        with engine.begin() as conn:
            stmt = text(
                """
                INSERT INTO routes (id, route_short_name, route_long_name, route_type)
                VALUES (:id, :route_short_name, :route_long_name, :route_type::integer)
                ON CONFLICT (id) DO UPDATE SET
                    route_short_name = EXCLUDED.route_short_name,
                    route_long_name = EXCLUDED.route_long_name,
                    route_type = EXCLUDED.route_type;
                """
            )
            conn.execute(stmt, routes_payload)

    # 2. Ingest stops
    if "stops.txt" in zip_ref.namelist():
        with zip_ref.open("stops.txt") as f:
            df_stops = pd.read_csv(f, dtype=str)
        df_stops["stop_lat"] = pd.to_numeric(df_stops["stop_lat"])
        df_stops["stop_lon"] = pd.to_numeric(df_stops["stop_lon"])

        stops_payload = []
        for _, row in df_stops.iterrows():
            stops_payload.append(
                {
                    "id": str(row["stop_id"]),
                    "stop_name": str(row["stop_name"]),
                    "stop_code": str(row.get("stop_code", "")) or None,
                    "lon": row["stop_lon"],
                    "lat": row["stop_lat"],
                }
            )

        with engine.begin() as conn:
            stmt = text(
                """
                INSERT INTO stops (id, stop_name, stop_code, geom)
                VALUES (:id,
                            :stop_name,
                            :stop_code,
                            ST_SetSRID(
                                ST_Point(:lon, :lat),
                                4326
                            )
                        )
                ON CONFLICT (id) DO UPDATE SET
                    stop_name = EXCLUDED.stop_name,
                    stop_code = EXCLUDED.stop_code,
                    geom = EXCLUDED.geom;
                """
            )
            conn.execute(stmt, stops_payload)

    # 3. Ingest route_shapes
    if "shapes.txt" in zip_ref.namelist():
        with zip_ref.open("shapes.txt") as f:
            df_shapes = pd.read_csv(f)
        gdf_shapes = build_route_shapes_geodataframe(df_shapes)

        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE route_shapes RESTART IDENTITY;"))
            for _, row in gdf_shapes.iterrows():
                conn.execute(
                    text(
                        """
                        INSERT INTO route_shapes (shape_id, geom)
                        VALUES (:shape_id, ST_SetSRID(ST_GeomFromText(:wkt), 4326));
                        """
                    ),
                    {"shape_id": row["shape_id"], "wkt": row["geom"].wkt},
                )

    # 4. Ingest trips
    if "trips.txt" in zip_ref.namelist():
        with zip_ref.open("trips.txt") as f:
            df_trips = pd.read_csv(f, dtype=str)
        trips_payload = (
            df_trips[
                ["trip_id", "route_id", "trip_headsign", "direction_id", "shape_id"]
            ]
            .rename(columns={"trip_id": "id"})
            .to_dict(orient="records")
        )

        with engine.begin() as conn:
            stmt = text(
                """
                INSERT INTO trips (id, route_id, trip_headsign, direction_id, shape_id)
                VALUES (:id,
                            :route_id,
                            :trip_headsign,
                            :direction_id::integer,
                            :shape_id
                        )
                ON CONFLICT (id) DO UPDATE SET
                    route_id = EXCLUDED.route_id,
                    trip_headsign = EXCLUDED.trip_headsign,
                    direction_id = EXCLUDED.direction_id,
                    shape_id = EXCLUDED.shape_id;
                """
            )
            conn.execute(stmt, trips_payload)

    # 5. Ingest stop_times
    if "stop_times.txt" in zip_ref.namelist():
        with zip_ref.open("stop_times.txt") as f:
            df_st = pd.read_csv(f, dtype=str)
        df_st["arrival_time"] = standardize_time_series(df_st["arrival_time"])
        df_st["departure_time"] = standardize_time_series(df_st["departure_time"])

        st_payload = df_st[
            ["trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"]
        ].to_dict(orient="records")

        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE stop_times RESTART IDENTITY;"))
            stmt = text(
                """
                INSERT INTO stop_times (trip_id,
                                            stop_id,
                                            stop_sequence,
                                            arrival_time,
                                            departure_time
                                        )
                VALUES (:trip_id,
                            :stop_id,
                            :stop_sequence::integer,
                            :arrival_time,
                            :departure_time
                        );
                """
            )
            conn.execute(stmt, st_payload)


if __name__ == "__main__":
    print("Downloading ZTP Krakow GTFS bus feed...")
    archive = download_gtfs_archive()
    print("Ingesting GTFS layers into PostGIS...")
    ingest_gtfs_feed(archive)
    print("GTFS ingestion finished successfully.")
