import csv
import io
import tempfile
import zipfile

import httpx
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app.core.database import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from app.models import Base

GTFS_URL = "https://gtfs.ztp.krakow.pl/GTFS_KRK_A.zip"
DB_CONN = make_conninfo(
    host=POSTGRES_HOST,
    port=int(POSTGRES_PORT),
    dbname=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
)

IMPORT_ORDER = (
    "agency",
    "calendar",
    "calendar_dates",
    "feed_info",
    "routes",
    "shapes",
    "stops",
    "trips",
    "stop_times",
)
REQUIRED_TABLES = {"agency", "routes", "stops", "trips", "stop_times"}


def inspect_gtfs_archive(
    archive: zipfile.ZipFile,
) -> dict[str, tuple[str, list[str]]]:
    """Validate supported CSV headers against the SQLAlchemy table metadata."""
    table_files: dict[str, tuple[str, list[str]]] = {}

    for filename in archive.namelist():
        if not filename.lower().endswith(".txt") or filename.startswith("__MACOSX/"):
            continue

        table_name = filename.rsplit("/", maxsplit=1)[-1][:-4].lower()
        table = Base.metadata.tables.get(table_name)
        if table is None:
            continue
        if table_name in table_files:
            raise ValueError(f"GTFS archive contains multiple {table_name}.txt files")

        with archive.open(filename) as file:
            header_line = file.readline().decode("utf-8-sig")
        columns = next(csv.reader([header_line]), [])
        if not columns or any(not column for column in columns):
            raise ValueError(f"{filename} has an empty or invalid header")
        if len(columns) != len(set(columns)):
            raise ValueError(f"{filename} contains duplicate column names")

        unknown_columns = set(columns) - set(table.columns.keys())
        if unknown_columns:
            names = ", ".join(sorted(unknown_columns))
            raise ValueError(
                f"{filename} contains columns without ORM mappings: {names}"
            )

        missing_required = {
            column.name
            for column in table.columns
            if not column.nullable and column.name not in columns
        }
        if missing_required:
            names = ", ".join(sorted(missing_required))
            raise ValueError(f"{filename} is missing required columns: {names}")

        table_files[table_name] = (filename, columns)

    missing_tables = REQUIRED_TABLES - table_files.keys()
    if missing_tables:
        names = ", ".join(sorted(f"{name}.txt" for name in missing_tables))
        raise ValueError(f"GTFS archive is missing required files: {names}")

    return table_files


def ingest_gtfs_feed(gtfs_zip_bytes: bytes, dsn: str = DB_CONN) -> None:
    """Bulk-load a GTFS archive into tables defined by the SQLAlchemy models."""
    with zipfile.ZipFile(io.BytesIO(gtfs_zip_bytes)) as archive:
        _load_gtfs_archive(archive, dsn)


def _load_gtfs_archive(archive: zipfile.ZipFile, dsn: str) -> None:
    table_files = inspect_gtfs_archive(archive)

    # Replace the complete GTFS snapshot so omitted optional files cannot go stale.
    tables_to_truncate = set(Base.metadata.tables)
    truncate_statement = sql.SQL("TRUNCATE TABLE {}").format(
        sql.SQL(", ").join(
            sql.Identifier(table_name) for table_name in sorted(tables_to_truncate)
        )
    )

    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name = ANY(%s)
                """,
                (sorted(tables_to_truncate),),
            )
            existing_tables = {row[0] for row in cursor.fetchall()}
            missing_tables = tables_to_truncate - existing_tables
            if missing_tables:
                names = ", ".join(sorted(missing_tables))
                raise RuntimeError(
                    f"GTFS database tables are missing: {names}. "
                    "Run `uv run alembic -c backend/alembic.ini upgrade head` "
                    "and verify that the importer and Alembic use the same "
                    "database settings."
                )

            cursor.execute(truncate_statement)

            for table_name in IMPORT_ORDER:
                if table_name not in table_files:
                    continue

                filename, columns = table_files[table_name]
                table = Base.metadata.tables[table_name]
                column_identifiers = sql.SQL(", ").join(
                    sql.Identifier(column) for column in columns
                )
                copy_statement = sql.SQL(
                    "COPY {} ({}) FROM STDIN WITH (FORMAT CSV, ENCODING 'UTF8')"
                ).format(sql.Identifier(table.name), column_identifiers)

                print(f"--> Importing {filename} into {table.name}...")
                with archive.open(filename) as file:
                    file.readline()
                    with cursor.copy(copy_statement) as copy:
                        while chunk := file.read(262144):
                            copy.write(chunk)

    print("GTFS files loaded successfully.")


def download_and_ingest_gtfs(url: str = GTFS_URL, dsn: str = DB_CONN) -> None:
    """Download the GTFS archive and load it into the configured database."""
    with httpx.Client(timeout=60.0) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with tempfile.TemporaryFile() as archive_file:
                for chunk in response.iter_bytes(chunk_size=262144):
                    archive_file.write(chunk)
                archive_file.seek(0)
                with zipfile.ZipFile(archive_file) as archive:
                    _load_gtfs_archive(archive, dsn)


if __name__ == "__main__":
    print(f"Downloading GTFS feed from {GTFS_URL}...")
    download_and_ingest_gtfs()
