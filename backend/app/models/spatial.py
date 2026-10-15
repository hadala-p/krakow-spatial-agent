from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for GTFS models."""


class Agency(Base):
    """GTFS agency.txt row."""

    __tablename__ = "agency"

    agency_id: Mapped[str] = mapped_column(Text, primary_key=True)
    agency_name: Mapped[str] = mapped_column(Text, nullable=False)
    agency_url: Mapped[str] = mapped_column(Text, nullable=False)
    agency_timezone: Mapped[str] = mapped_column(Text, nullable=False)
    agency_lang: Mapped[str | None] = mapped_column(Text, nullable=True)
    agency_phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    agency_fare_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    agency_email: Mapped[str | None] = mapped_column(Text, nullable=True)

    routes: Mapped[list["Route"]] = relationship(back_populates="agency")


class Calendar(Base):
    """GTFS calendar.txt row."""

    __tablename__ = "calendar"

    service_id: Mapped[str] = mapped_column(Text, primary_key=True)
    monday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tuesday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    wednesday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    thursday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    friday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    saturday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sunday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)


class CalendarDate(Base):
    """GTFS calendar_dates.txt row."""

    __tablename__ = "calendar_dates"

    service_id: Mapped[str] = mapped_column(Text, primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    exception_type: Mapped[int] = mapped_column(Integer, nullable=False)


class FeedInfo(Base):
    """GTFS feed_info.txt row."""

    __tablename__ = "feed_info"
    __table_args__ = (
        PrimaryKeyConstraint(
            "feed_publisher_name",
            "feed_publisher_url",
            "feed_lang",
            name="pk_feed_info",
        ),
    )

    feed_publisher_name: Mapped[str] = mapped_column(Text, nullable=False)
    feed_publisher_url: Mapped[str] = mapped_column(Text, nullable=False)
    feed_lang: Mapped[str] = mapped_column(String(16), nullable=False)
    feed_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    feed_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    feed_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    feed_contact_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    feed_contact_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class Route(Base):
    """GTFS routes.txt row."""

    __tablename__ = "routes"

    route_id: Mapped[str] = mapped_column(Text, primary_key=True)
    agency_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("agency.agency_id"), nullable=True
    )
    route_short_name: Mapped[str | None] = mapped_column(
        Text, nullable=True, index=True
    )
    route_long_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    route_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    route_type: Mapped[int] = mapped_column(Integer, nullable=False)
    route_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    route_color: Mapped[str | None] = mapped_column(String(6), nullable=True)
    route_text_color: Mapped[str | None] = mapped_column(String(6), nullable=True)
    route_sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    continuous_pickup: Mapped[int | None] = mapped_column(Integer, nullable=True)
    continuous_drop_off: Mapped[int | None] = mapped_column(Integer, nullable=True)

    agency: Mapped[Agency | None] = relationship(back_populates="routes")
    trips: Mapped[list["Trip"]] = relationship(back_populates="route")


class Shape(Base):
    """GTFS shapes.txt coordinate row."""

    __tablename__ = "shapes"

    shape_id: Mapped[str] = mapped_column(Text, primary_key=True)
    shape_pt_lat: Mapped[float] = mapped_column(Float, nullable=False)
    shape_pt_lon: Mapped[float] = mapped_column(Float, nullable=False)
    shape_pt_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    shape_dist_traveled: Mapped[float | None] = mapped_column(Float, nullable=True)


class StopTime(Base):
    """GTFS stop_times.txt row."""

    __tablename__ = "stop_times"

    trip_id: Mapped[str] = mapped_column(
        Text, ForeignKey("trips.trip_id", ondelete="CASCADE"), primary_key=True
    )
    arrival_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    departure_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    stop_id: Mapped[str] = mapped_column(
        Text, ForeignKey("stops.stop_id", ondelete="CASCADE"), nullable=False
    )
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_headsign: Mapped[str | None] = mapped_column(Text, nullable=True)
    pickup_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drop_off_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shape_dist_traveled: Mapped[float | None] = mapped_column(Float, nullable=True)
    timepoint: Mapped[int | None] = mapped_column(Integer, nullable=True)

    trip: Mapped["Trip"] = relationship(back_populates="stop_times")
    stop: Mapped["Stop"] = relationship(back_populates="stop_times")


class Stop(Base):
    """GTFS stops.txt row."""

    __tablename__ = "stops"

    stop_id: Mapped[str] = mapped_column(Text, primary_key=True)
    stop_code: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    stop_name: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    stop_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    zone_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_station: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_timezone: Mapped[str | None] = mapped_column(Text, nullable=True)
    wheelchair_boarding: Mapped[int | None] = mapped_column(Integer, nullable=True)
    platform_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    stop_times: Mapped[list[StopTime]] = relationship(back_populates="stop")


class Trip(Base):
    """GTFS trips.txt row."""

    __tablename__ = "trips"

    route_id: Mapped[str] = mapped_column(
        Text, ForeignKey("routes.route_id", ondelete="CASCADE"), nullable=False
    )
    service_id: Mapped[str] = mapped_column(Text, nullable=False)
    trip_id: Mapped[str] = mapped_column(Text, primary_key=True)
    trip_headsign: Mapped[str | None] = mapped_column(Text, nullable=True)
    trip_short_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    direction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    shape_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    wheelchair_accessible: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bikes_allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    route: Mapped[Route] = relationship(back_populates="trips")
    stop_times: Mapped[list[StopTime]] = relationship(back_populates="trip")
