from app.models import (
    Agency,
    Base,
    Block,
    Calendar,
    CalendarDate,
    FeedInfo,
    Route,
    Shape,
    Stop,
    StopTime,
    Trip,
)


def test_orm_contains_only_tables_for_provided_gtfs_files():
    assert set(Base.metadata.tables) == {
        "agency",
        "blocks",
        "calendar",
        "calendar_dates",
        "feed_info",
        "routes",
        "shapes",
        "stop_times",
        "stops",
        "trips",
    }


def test_models_match_provided_gtfs_file_columns_exactly():
    expected_columns = {
        Agency: {
            "agency_id",
            "agency_name",
            "agency_url",
            "agency_timezone",
            "agency_lang",
            "agency_phone",
            "agency_fare_url",
            "agency_email",
        },
        Calendar: {
            "service_id",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "start_date",
            "end_date",
        },
        CalendarDate: {"service_id", "date", "exception_type"},
        FeedInfo: {
            "feed_publisher_name",
            "feed_publisher_url",
            "feed_lang",
            "feed_start_date",
            "feed_end_date",
            "feed_version",
            "feed_contact_email",
            "feed_contact_url",
        },
        Route: {
            "route_id",
            "agency_id",
            "route_short_name",
            "route_long_name",
            "route_desc",
            "route_type",
            "route_url",
            "route_color",
            "route_text_color",
            "route_sort_order",
            "continuous_pickup",
            "continuous_drop_off",
        },
        Shape: {
            "shape_id",
            "shape_pt_lat",
            "shape_pt_lon",
            "shape_pt_sequence",
            "shape_dist_traveled",
        },
        Block: {"block_id", "shift"},
        StopTime: {
            "trip_id",
            "arrival_time",
            "departure_time",
            "stop_id",
            "stop_sequence",
            "stop_headsign",
            "pickup_type",
            "drop_off_type",
            "shape_dist_traveled",
            "timepoint",
        },
        Stop: {
            "stop_id",
            "stop_code",
            "stop_name",
            "stop_desc",
            "stop_lat",
            "stop_lon",
            "zone_id",
            "stop_url",
            "location_type",
            "parent_station",
            "stop_timezone",
            "wheelchair_boarding",
            "platform_code",
        },
        Trip: {
            "route_id",
            "service_id",
            "trip_id",
            "trip_headsign",
            "trip_short_name",
            "direction_id",
            "block_id",
            "shape_id",
            "wheelchair_accessible",
            "bikes_allowed",
        },
    }

    for model, columns in expected_columns.items():
        assert set(model.__table__.columns.keys()) == columns


def test_gtfs_primary_keys_match_record_identifiers():
    assert [column.name for column in Agency.__table__.primary_key] == ["agency_id"]
    assert [column.name for column in Calendar.__table__.primary_key] == ["service_id"]
    assert [column.name for column in CalendarDate.__table__.primary_key] == [
        "service_id",
        "date",
    ]
    assert [column.name for column in Route.__table__.primary_key] == ["route_id"]
    assert [column.name for column in Shape.__table__.primary_key] == [
        "shape_id",
        "shape_pt_sequence",
    ]
    assert [column.name for column in Stop.__table__.primary_key] == ["stop_id"]
    assert [column.name for column in StopTime.__table__.primary_key] == [
        "trip_id",
        "stop_sequence",
    ]
    assert [column.name for column in Trip.__table__.primary_key] == ["trip_id"]
    assert [column.name for column in FeedInfo.__table__.primary_key] == [
        "feed_publisher_name",
        "feed_publisher_url",
        "feed_lang",
    ]
    assert [column.name for column in Block.__table__.primary_key] == ["block_id"]


def test_gtfs_relationship_foreign_keys():
    assert {fk.target_fullname for fk in Route.__table__.c.agency_id.foreign_keys} == {
        "agency.agency_id"
    }
    assert {fk.target_fullname for fk in Trip.__table__.c.route_id.foreign_keys} == {
        "routes.route_id"
    }
    assert {fk.target_fullname for fk in StopTime.__table__.c.trip_id.foreign_keys} == {
        "trips.trip_id"
    }
    assert {fk.target_fullname for fk in StopTime.__table__.c.stop_id.foreign_keys} == {
        "stops.stop_id"
    }
