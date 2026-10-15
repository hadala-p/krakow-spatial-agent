import pandas as pd
from shapely.geometry import LineString


def test_standardize_gtfs_time_normal_and_over_24h():
    """Verify time formatting normalizes times beyond 24:00:00 correctly."""
    from app.etl.gtfs_ingest import standardize_time_series

    raw_times = pd.Series(["08:15:30", "24:05:00", "25:30:15", "06:00:00"])
    result = standardize_time_series(raw_times)

    expected = pd.Series(["08:15:30", "00:05:00", "01:30:15", "06:00:00"])
    pd.testing.assert_series_equal(result, expected)


def test_reconstruct_shape_linestrings():
    """Verify points sequence from shapes.txt is converted to valid LineStrings."""
    from app.etl.gtfs_ingest import build_route_shapes_geodataframe

    data = {
        "shape_id": ["shape_1", "shape_1", "shape_1", "shape_2", "shape_2"],
        "shape_pt_lat": [50.061, 50.062, 50.063, 50.070, 50.071],
        "shape_pt_lon": [19.937, 19.938, 19.939, 19.940, 19.941],
        "shape_pt_sequence": [1, 2, 3, 1, 2],
    }
    df_shapes = pd.DataFrame(data)

    gdf = build_route_shapes_geodataframe(df_shapes)

    assert len(gdf) == 2
    assert "shape_id" in gdf.columns
    assert "geom" in gdf.columns
    assert gdf.crs == "EPSG:4326"

    # Shape 1 validation: 3 vertices
    shape1_geom = gdf[gdf["shape_id"] == "shape_1"]["geom"].iloc[0]
    assert isinstance(shape1_geom, LineString)
    assert len(shape1_geom.coords) == 3
    # Check (lon, lat) WGS84 coordinate ordering
    assert shape1_geom.coords[0] == (19.937, 50.061)
