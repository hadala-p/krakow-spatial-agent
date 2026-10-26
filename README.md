# Krakow Spatial Agent (KSA)

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![PostGIS 16-3.4](https://img.shields.io/badge/PostGIS-16--3.4-brightgreen.svg)](https://hub.docker.com/r/postgis/postgis)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

Autonomous Geo-AI agent translating natural language inquiries into spatial PostGIS queries executed on Krakow Public Transport Authority (ZTP) datasets.

---

## 🛠️ Prerequisites
- [Docker Engine & Docker Compose](https://docs.docker.com/get-docker/)
- [uv package manager](https://docs.astral.sh/uv/) (Python 3.12+)
- Git

---

## 🚀 Quickstart & Setup

### 1. Environment configuration
Copy the environment variables template:
```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

### 2. Install dependencies & register git hooks
Synchronize the virtual environment and register local pre-commit hooks:
```bash
uv sync --all-extras
uv run pre-commit install
```

### 3. Start the PostGIS database
Launch the PostgreSQL 16 + PostGIS 3.4 container:
```bash
docker compose up -d db
```
Verify container health:
```bash
docker compose ps
```

### 4. Verify database connectivity
Execute the async verification script to check PostGIS extensions:
```bash
uv run python backend/test_connection.py
```

### 5. Import the GTFS feeds
Apply the latest database migration, then download and import the A, M, and T feeds:
```bash
uv run alembic -c backend/alembic.ini upgrade head
uv run --directory backend python -m app.etl.gtfs_ingest
```
The feeds are loaded together as one snapshot. The Krakow-specific `blocks.txt`
from the T feed is stored in the `blocks` table.

---

## 🧪 Code Quality & Formatting
This repository enforces code standards using **Ruff** and **pre-commit**:
```bash
# Run all pre-commit hooks across staged files
uv run pre-commit run --all-files

# Manual linting and formatting verification
uv run ruff check .
uv run ruff format --check .
```

---

## Transit API
Start the FastAPI server from the repository root:
```bash
uv run uvicorn app.main:app --app-dir backend --reload
```

Interactive API documentation is available at `http://localhost:8000/docs`.

The initial transit endpoints are:
- `GET /api/v1/transit/routes/{route_id}?direction_id=0|1` — precomputed route
  geometry as a GeoJSON `Feature`; omitting `direction_id` returns both directions.
- `GET /api/v1/transit/routes/{route_id}/stops` — ordered stops from a representative trip on the route.
- `GET /api/v1/transit/stops/{stop_id}/routes` — route lines serving a stop, including trip headsigns.

Route geometries are stored in the `mv_route_geometries` materialized view and
refreshed automatically after each GTFS ingestion.

## 🏛️ Architecture
Refer to [ARCHITECTURE.md](ARCHITECTURE.md) for structural diagrams and spatial database schemas.
