import io
import zipfile

import pytest
from app.etl.gtfs_ingest import (
    ingest_gtfs_feed,
    ingest_gtfs_feeds,
    inspect_gtfs_archive,
)

GTFS_FILES = {
    "agency.txt": (
        "agency_id,agency_name,agency_url,agency_timezone\n"
        "MPK,MPK,https://example.com,Europe/Warsaw\n"
    ),
    "routes.txt": "route_id,route_type\n1,3\n",
    "stops.txt": "stop_id\nstop-1\n",
    "trips.txt": "route_id,service_id,trip_id\n1,service-1,trip-1\n",
    "stop_times.txt": (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "trip-1,08:00:00,08:00:00,stop-1,1\n"
    ),
    "calendar.txt": (
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,"
        "sunday,start_date,end_date\n"
        "service-1,1,1,1,1,1,0,0,20261010,20270131\n"
    ),
    "calendar_dates.txt": "service_id,date,exception_type\nservice-1,20261010,1\n",
    "feed_info.txt": (
        "feed_publisher_name,feed_publisher_url,feed_lang\nMPK,https://example.com,pl\n"
    ),
    "shapes.txt": (
        "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\nshape-1,50.0,19.0,1\n"
    ),
}


def make_gtfs_archive(files: dict[str, str] | None = None) -> bytes:
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        for filename, content in (files or GTFS_FILES).items():
            archive.writestr(filename, content)
    return archive_bytes.getvalue()


def test_inspect_gtfs_archive_maps_provided_files_to_orm_tables():
    with zipfile.ZipFile(io.BytesIO(make_gtfs_archive())) as archive:
        table_files = inspect_gtfs_archive(archive)

    assert set(table_files) == {
        "agency",
        "calendar",
        "calendar_dates",
        "feed_info",
        "routes",
        "shapes",
        "stop_times",
        "stops",
        "trips",
    }
    assert table_files["agency"][1] == [
        "agency_id",
        "agency_name",
        "agency_url",
        "agency_timezone",
    ]


def test_inspect_gtfs_archive_rejects_unmapped_columns():
    files = dict(GTFS_FILES)
    files["stops.txt"] = "stop_id,unmapped_field\nstop-1,value\n"

    with zipfile.ZipFile(io.BytesIO(make_gtfs_archive(files))) as archive:
        with pytest.raises(ValueError, match="without ORM mappings"):
            inspect_gtfs_archive(archive)


def test_inspect_gtfs_archive_requires_core_gtfs_files():
    files = dict(GTFS_FILES)
    del files["routes.txt"]

    with zipfile.ZipFile(io.BytesIO(make_gtfs_archive(files))) as archive:
        with pytest.raises(ValueError, match="routes.txt"):
            inspect_gtfs_archive(archive)


def test_inspect_gtfs_archive_maps_krakow_blocks_file():
    files = dict(GTFS_FILES)
    files["blocks.txt"] = "block_id,shift\nblock_1,71-01\n"

    with zipfile.ZipFile(io.BytesIO(make_gtfs_archive(files))) as archive:
        table_files = inspect_gtfs_archive(archive)

    assert table_files["blocks"] == ("blocks.txt", ["block_id", "shift"])


class FakeCopy:
    def __init__(self) -> None:
        self.chunks: list[bytes] = []

    def __enter__(self) -> "FakeCopy":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def write(self, chunk: bytes) -> None:
        self.chunks.append(chunk)


class FakeCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.copies: list[tuple[str, FakeCopy]] = []
        self.tables = {
            "agency",
            "calendar",
            "calendar_dates",
            "feed_info",
            "blocks",
            "routes",
            "shapes",
            "stop_times",
            "stops",
            "trips",
        }
        self._result: list[tuple[str]] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, statement: object, parameters: object = None) -> None:
        rendered = (
            statement.as_string(None)
            if hasattr(statement, "as_string")
            else str(statement)
        )
        self.statements.append(rendered)
        if "information_schema.tables" in self.statements[-1]:
            requested_tables = set(parameters[0])
            self._result = [
                (table_name,) for table_name in self.tables & requested_tables
            ]

    def fetchall(self) -> list[tuple[str]]:
        return self._result

    def copy(self, statement: object) -> FakeCopy:
        copy = FakeCopy()
        self.copies.append((statement.as_string(None), copy))
        return copy


class FakeConnection:
    def __init__(self) -> None:
        self.fake_cursor = FakeCursor()

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self.fake_cursor


def test_ingest_uses_mapped_tables_copy_and_dependency_order(monkeypatch):
    from app.etl import gtfs_ingest

    connection = FakeConnection()
    monkeypatch.setattr(gtfs_ingest.psycopg, "connect", lambda _: connection)

    ingest_gtfs_feed(make_gtfs_archive(), dsn="postgresql://test")

    assert len(connection.fake_cursor.statements) == 3
    truncate_statement = connection.fake_cursor.statements[1]
    assert truncate_statement.startswith("TRUNCATE TABLE")
    assert "CASCADE" not in truncate_statement
    assert (
        connection.fake_cursor.statements[2]
        == "REFRESH MATERIALIZED VIEW mv_route_geometries"
    )
    assert {
        name
        for name in ("agency", "blocks", "routes", "stops", "trips", "stop_times")
        if f'"{name}"' in truncate_statement
    } == {
        "agency",
        "blocks",
        "routes",
        "stops",
        "trips",
        "stop_times",
    }

    imported_tables = [
        statement.split('"')[1] for statement, _ in connection.fake_cursor.copies
    ]
    assert imported_tables == [
        "agency",
        "calendar",
        "calendar_dates",
        "feed_info",
        "routes",
        "shapes",
        "stops",
        "trips",
        "stop_times",
    ]
    assert all(
        statement.startswith("COPY ") for statement, _ in connection.fake_cursor.copies
    )
    assert all(copy.chunks for _, copy in connection.fake_cursor.copies)


def test_ingest_multiple_feeds_truncates_once_and_loads_blocks(monkeypatch):
    from app.etl import gtfs_ingest

    connection = FakeConnection()
    monkeypatch.setattr(gtfs_ingest.psycopg, "connect", lambda _: connection)
    t_feed_files = dict(GTFS_FILES)
    t_feed_files["blocks.txt"] = "block_id,shift\nblock_1,71-01\n"

    ingest_gtfs_feeds(
        (
            make_gtfs_archive(),
            make_gtfs_archive(t_feed_files),
        ),
        dsn="postgresql://test",
    )

    statements = connection.fake_cursor.statements
    assert sum(statement.startswith("TRUNCATE TABLE") for statement in statements) == 1
    assert statements[-1] == "REFRESH MATERIALIZED VIEW mv_route_geometries"
    assert (
        sum(
            statement.startswith("REFRESH MATERIALIZED VIEW")
            for statement in statements
        )
        == 1
    )
    imported_tables = [
        statement.split('"')[1] for statement, _ in connection.fake_cursor.copies
    ]
    assert imported_tables.count("routes") == 2
    assert imported_tables.count("blocks") == 1


def test_ingest_multiple_feeds_rejects_empty_input():
    with pytest.raises(ValueError, match="At least one GTFS archive"):
        ingest_gtfs_feeds(())


def test_ingest_reports_missing_migrated_tables_before_truncating(monkeypatch):
    from app.etl import gtfs_ingest

    connection = FakeConnection()
    connection.fake_cursor.tables.remove("agency")
    monkeypatch.setattr(gtfs_ingest.psycopg, "connect", lambda _: connection)

    with pytest.raises(RuntimeError, match="agency.*alembic"):
        ingest_gtfs_feed(make_gtfs_archive(), dsn="postgresql://test")

    assert len(connection.fake_cursor.statements) == 1
    assert "information_schema.tables" in connection.fake_cursor.statements[0]
