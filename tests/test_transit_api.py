from collections.abc import AsyncGenerator

import pytest
from app.core.database import async_session_maker
from app.main import app
from app.models.spatial import Route, Shape, Stop, StopTime, Trip
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text


@pytest.fixture(scope="module", autouse=True)
async def seed_test_transit_data() -> AsyncGenerator[None, None]:
    """Seed isolated test transit entities without colliding with real GTFS feeds."""
    async with async_session_maker() as session:
        r_test = Route(
            route_id="route_test_999t",
            route_short_name="999T",
            route_long_name="Dworzec Testowy - Pętla Testowa",
            route_type=3,
        )
        trip = Trip(
            trip_id="trip_test_999t",
            route_id="route_test_999t",
            service_id="service_test_1",
            trip_headsign="Pętla Testowa",
            shape_id="shape_test_999t",
            direction_id=0,
        )
        reverse_trip = Trip(
            trip_id="trip_test_999t_reverse",
            route_id="route_test_999t",
            service_id="service_test_1",
            trip_headsign="Dworzec Testowy",
            shape_id="shape_test_999t_reverse",
            direction_id=1,
        )
        shape_1 = Shape(
            shape_id="shape_test_999t",
            shape_pt_lat=50.061,
            shape_pt_lon=19.937,
            shape_pt_sequence=1,
        )
        shape_2 = Shape(
            shape_id="shape_test_999t",
            shape_pt_lat=50.062,
            shape_pt_lon=19.938,
            shape_pt_sequence=2,
        )
        reverse_shape_1 = Shape(
            shape_id="shape_test_999t_reverse",
            shape_pt_lat=50.062,
            shape_pt_lon=19.938,
            shape_pt_sequence=1,
        )
        reverse_shape_2 = Shape(
            shape_id="shape_test_999t_reverse",
            shape_pt_lat=50.061,
            shape_pt_lon=19.937,
            shape_pt_sequence=2,
        )
        stop = Stop(
            stop_id="stop_test_999t",
            stop_name="Słupek Testowy",
            stop_lat=50.066,
            stop_lon=19.945,
        )
        stop_time = StopTime(
            trip_id="trip_test_999t",
            stop_id="stop_test_999t",
            stop_sequence=1,
            arrival_time="08:00:00",
            departure_time="08:00:00",
        )

        for obj in (
            r_test,
            trip,
            reverse_trip,
            shape_1,
            shape_2,
            reverse_shape_1,
            reverse_shape_2,
            stop,
            stop_time,
        ):
            await session.merge(obj)
        await session.commit()
        await session.execute(text("REFRESH MATERIALIZED VIEW mv_route_geometries"))
        await session.commit()

    yield

    async with async_session_maker() as session:
        await session.execute(
            delete(StopTime).where(StopTime.trip_id == "trip_test_999t_reverse")
        )
        await session.execute(
            delete(StopTime).where(StopTime.trip_id == "trip_test_999t")
        )
        await session.execute(
            delete(Trip).where(Trip.trip_id == "trip_test_999t_reverse")
        )
        await session.execute(delete(Trip).where(Trip.trip_id == "trip_test_999t"))
        await session.execute(
            delete(Shape).where(Shape.shape_id == "shape_test_999t_reverse")
        )
        await session.execute(delete(Shape).where(Shape.shape_id == "shape_test_999t"))
        await session.execute(delete(Stop).where(Stop.stop_id == "stop_test_999t"))
        await session.execute(delete(Route).where(Route.route_id == "route_test_999t"))
        await session.commit()
        await session.execute(text("REFRESH MATERIALIZED VIEW mv_route_geometries"))
        await session.commit()


@pytest.mark.asyncio
async def test_list_routes_returns_sorted_active_lines() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/transit/routes")

    assert response.status_code == 200
    routes = response.json()
    assert isinstance(routes, list)
    assert len(routes) >= 1

    sample_route = next(r for r in routes if r["id"] == "route_test_999t")
    assert sample_route["route_short_name"] == "999T"
    assert sample_route["route_long_name"] == "Dworzec Testowy - Pętla Testowa"
    assert sample_route["route_type"] == 3


@pytest.mark.asyncio
async def test_get_route_geometry_by_public_number_and_id_fallback() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Wyszukanie po publicznym numerze linii ("999T")
        res_public = await client.get("/api/v1/transit/routes/999T?direction_id=0")
        assert res_public.status_code == 200
        data_public = res_public.json()
        assert data_public["type"] == "Feature"
        assert data_public["properties"]["route_id"] == "route_test_999t"
        assert data_public["properties"]["route_short_name"] == "999T"
        assert data_public["properties"]["direction_id"] == 0
        assert data_public["geometry"]["type"] == "LineString"
        assert data_public["geometry"]["coordinates"] == [
            [19.937, 50.061],
            [19.938, 50.062],
        ]

        # 2. Fallback po technicznym route_id ("route_test_999t")
        res_id = await client.get(
            "/api/v1/transit/routes/route_test_999t?direction_id=1"
        )
        assert res_id.status_code == 200
        data_id = res_id.json()
        assert data_id["properties"]["route_id"] == "route_test_999t"
        assert data_id["properties"]["direction_id"] == 1
        assert data_id["geometry"]["coordinates"] == [
            [19.938, 50.062],
            [19.937, 50.061],
        ]

        res_both = await client.get("/api/v1/transit/routes/999T")
        assert res_both.status_code == 200
        both_geometry = res_both.json()["geometry"]
        assert both_geometry["type"] == "MultiLineString"
        assert both_geometry["coordinates"] == [
            [[19.937, 50.061], [19.938, 50.062]],
            [[19.938, 50.062], [19.937, 50.061]],
        ]

        invalid_direction = await client.get(
            "/api/v1/transit/routes/999T?direction_id=2"
        )
        assert invalid_direction.status_code == 422


@pytest.mark.asyncio
async def test_get_route_stops_by_public_number_and_id_fallback() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Wyszukanie przystanków po numerze linii ("999T")
        res_public = await client.get("/api/v1/transit/routes/999T/stops")
        assert res_public.status_code == 200
        stops = res_public.json()
        assert len(stops) == 1
        assert stops[0]["stop_id"] == "stop_test_999t"
        assert stops[0]["stop_name"] == "Słupek Testowy"
        assert stops[0]["stop_sequence"] == 1

        # 2. Fallback po technicznym route_id
        res_id = await client.get("/api/v1/transit/routes/route_test_999t/stops")
        assert res_id.status_code == 200
        assert res_id.json()[0]["stop_id"] == "stop_test_999t"


@pytest.mark.asyncio
async def test_get_stop_routes() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/transit/stops/stop_test_999t/routes")

    assert response.status_code == 200
    data = response.json()
    assert data["stop_id"] == "stop_test_999t"
    assert data["stop_name"] == "Słupek Testowy"
    assert len(data["routes"]) == 1
    assert data["routes"][0]["route_short_name"] == "999T"
    assert data["routes"][0]["trip_headsign"] == "Pętla Testowa"


@pytest.mark.asyncio
async def test_non_existent_route_returns_structured_404() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res_route = await client.get("/api/v1/transit/routes/NONEXISTENT_9999")
        assert res_route.status_code == 404
        error_route = res_route.json()["detail"]
        assert error_route["code"] == "ROUTE_NOT_FOUND"
        assert error_route["identifier"] == "NONEXISTENT_9999"

        res_stops = await client.get("/api/v1/transit/routes/NONEXISTENT_9999/stops")
        assert res_stops.status_code == 404
        error_stops = res_stops.json()["detail"]
        assert error_stops["code"] == "ROUTE_NOT_FOUND"
        assert error_stops["identifier"] == "NONEXISTENT_9999"


@pytest.mark.asyncio
async def test_non_existent_stop_returns_structured_404() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/transit/stops/NONEXISTENT_STOP/routes")

    assert response.status_code == 404
    error = response.json()["detail"]
    assert error["code"] == "STOP_NOT_FOUND"
    assert error["identifier"] == "NONEXISTENT_STOP"
