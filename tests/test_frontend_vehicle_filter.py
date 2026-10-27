from frontend.vehicle_filter import is_in_krakow


def test_is_in_krakow_accepts_vehicle_coordinates_in_city() -> None:
    assert is_in_krakow([19.9383, 50.0614])


def test_is_in_krakow_rejects_vehicle_coordinates_outside_city() -> None:
    assert not is_in_krakow([31.2357, 30.0444])


def test_is_in_krakow_rejects_invalid_coordinates() -> None:
    assert not is_in_krakow([19.9383])
    assert not is_in_krakow(["unknown", 50.0614])
    assert not is_in_krakow([float("nan"), 50.0614])
