import time

import httpx
from google.transit import gtfs_realtime_pb2

FEED_URLS = {
    "bus": "https://gtfs.ztp.krakow.pl/VehiclePositions_A.pb",
    "tram": "https://gtfs.ztp.krakow.pl/VehiclePositions_T.pb",
}


class LiveFeedService:
    def __init__(self, ttl_seconds: int = 15):
        self.ttl = ttl_seconds
        self._cache = {}
        self._last_fetch = {}

    async def fetch_feed(self, vehicle_type: str) -> gtfs_realtime_pb2.FeedMessage:
        now = time.time()
        # Zwróć z in-memory cache jeśli TTL nie wygasł
        if (
            vehicle_type in self._cache
            and (now - self._last_fetch.get(vehicle_type, 0)) < self.ttl
        ):
            return self._cache[vehicle_type]

        url = FEED_URLS.get(vehicle_type)
        if not url:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)

        self._cache[vehicle_type] = feed
        self._last_fetch[vehicle_type] = now
        return feed

    async def get_vehicles_geojson(
        self, route_short_name: str | None = None, vehicle_type: str | None = None
    ) -> dict:
        features = []
        types_to_fetch = ["bus", "tram"] if not vehicle_type else [vehicle_type]

        for v_type in types_to_fetch:
            try:
                feed = await self.fetch_feed(v_type)
                for entity in feed.entity:
                    if not entity.HasField("vehicle"):
                        continue

                    veh = entity.vehicle
                    v_route = veh.trip.route_id if veh.HasField("trip") else ""

                    if route_short_name and route_short_name != v_route:
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
            except Exception as e:
                print(f"Error fetching {v_type} feed: {e}")

        return {"type": "FeatureCollection", "features": features}


live_feed_service = LiveFeedService()
