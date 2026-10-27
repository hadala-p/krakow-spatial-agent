import asyncio
import logging
import time
from time import perf_counter

import httpx
from google.protobuf.message import DecodeError
from google.transit import gtfs_realtime_pb2

logger = logging.getLogger("uvicorn.error")

FEED_URLS = {
    "bus_mpk": "https://gtfs.ztp.krakow.pl/VehiclePositions_A.pb",
    "bus_mobilis": "https://gtfs.ztp.krakow.pl/VehiclePositions_M.pb",
    "tram": "https://gtfs.ztp.krakow.pl/VehiclePositions_T.pb",
}


class LiveFeedService:
    def __init__(self, ttl_seconds: int = 15):
        self.ttl = ttl_seconds
        self._cache: dict[str, gtfs_realtime_pb2.FeedMessage] = {}
        self._last_fetch: dict[str, float] = {}
        self._feed_locks = {vehicle_type: asyncio.Lock() for vehicle_type in FEED_URLS}

    async def fetch_feed(
        self, vehicle_type: str, force_refresh: bool = False
    ) -> gtfs_realtime_pb2.FeedMessage:
        started_at = perf_counter()
        url = FEED_URLS.get(vehicle_type)
        if not url:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")

        async with self._feed_locks[vehicle_type]:
            now = time.time()
            if (
                not force_refresh
                and vehicle_type in self._cache
                and (now - self._last_fetch.get(vehicle_type, 0)) < self.ttl
            ):
                logger.info(
                    "Live feed %s served from cache in %.2f ms",
                    vehicle_type,
                    (perf_counter() - started_at) * 1000,
                )
                return self._cache[vehicle_type]

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            self._cache[vehicle_type] = feed
            self._last_fetch[vehicle_type] = time.time()
            logger.info(
                "Live feed %s fetched %d vehicles in %.2f ms",
                vehicle_type,
                len(feed.entity),
                (perf_counter() - started_at) * 1000,
            )
            return feed

    async def refresh_feeds(self) -> None:
        """Refresh all configured feeds concurrently, retaining stale data on errors."""

        async def refresh_feed(vehicle_type: str) -> None:
            try:
                await self.fetch_feed(vehicle_type, force_refresh=True)
            except (httpx.HTTPError, DecodeError, ValueError):
                logger.exception("Failed to refresh live feed %s", vehicle_type)

        await asyncio.gather(*(refresh_feed(name) for name in FEED_URLS))

    async def run_refresh_loop(self) -> None:
        """Continuously refresh the live vehicle snapshot in the background."""
        while True:
            await self.refresh_feeds()
            await asyncio.sleep(self.ttl)

    async def get_vehicles_geojson(
        self, route_short_name: str | None = None, vehicle_type: str | None = None
    ) -> dict:
        features = []
        if vehicle_type == "bus":
            types_to_fetch = ["bus_mpk", "bus_mobilis"]
        elif vehicle_type:
            types_to_fetch = [vehicle_type]
        else:
            types_to_fetch = list(FEED_URLS.keys())

        geojson_started_at = perf_counter()
        for v_type in types_to_fetch:
            feed = self._cache.get(v_type)
            if feed is None:
                continue
            for entity in feed.entity:
                if not entity.HasField("vehicle"):
                    continue

                veh = entity.vehicle
                v_route = veh.trip.route_id if veh.HasField("trip") else ""

                if route_short_name:
                    clean_filter = str(route_short_name).strip().upper()
                    clean_route = str(v_route).strip().upper()
                    if clean_filter != clean_route:
                        continue

                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            veh.position.longitude,
                            veh.position.latitude,
                        ],
                    },
                    "properties": {
                        "vehicle_id": veh.vehicle.id
                        if veh.HasField("vehicle")
                        else entity.id,
                        "route_short_name": v_route,
                        "bearing": veh.position.bearing
                        if veh.position.HasField("bearing")
                        else None,
                        "speed": veh.position.speed
                        if veh.position.HasField("speed")
                        else None,
                        "vehicle_type": v_type,
                    },
                }
                features.append(feature)

        logger.info(
            "Converted live feeds to %d GeoJSON features in %.2f ms",
            len(features),
            (perf_counter() - geojson_started_at) * 1000,
        )
        return {"type": "FeatureCollection", "features": features}


live_feed_service = LiveFeedService()
