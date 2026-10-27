from collections.abc import Sequence
from math import isfinite

KRAKOW_BOUNDS = (49.93, 50.16, 19.74, 20.27)


def is_in_krakow(coordinates: Sequence[object]) -> bool:
    """Return whether GeoJSON [longitude, latitude] coordinates are near Krakow."""
    if len(coordinates) < 2:
        return False

    longitude, latitude = coordinates[:2]
    if not isinstance(longitude, (int, float)) or not isinstance(
        latitude, (int, float)
    ):
        return False
    if not isfinite(longitude) or not isfinite(latitude):
        return False

    min_latitude, max_latitude, min_longitude, max_longitude = KRAKOW_BOUNDS
    return (
        min_latitude <= latitude <= max_latitude
        and min_longitude <= longitude <= max_longitude
    )
