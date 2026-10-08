from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for ORM models."""

    pass


class Stop(Base):
    """Transit stop positions and stations."""

    __tablename__ = "stops"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    stop_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    stop_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
    )

    stop_times: Mapped[list["StopTime"]] = relationship(
        "StopTime", back_populates="stop", cascade="all, delete-orphan"
    )


class Route(Base):
    """Transit routes (bus lines)."""

    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    route_short_name: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False
    )
    route_long_name: Mapped[str] = mapped_column(String(255), nullable=False)
    route_type: Mapped[int] = mapped_column(Integer, nullable=False)

    trips: Mapped[list["Trip"]] = relationship(
        "Trip", back_populates="route", cascade="all, delete-orphan"
    )


class Trip(Base):
    """Individual trips for specific routes."""

    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    route_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    trip_headsign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shape_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    route: Mapped["Route"] = relationship("Route", back_populates="trips")
    stop_times: Mapped[list["StopTime"]] = relationship(
        "StopTime", back_populates="trip", cascade="all, delete-orphan"
    )


class StopTime(Base):
    """Scheduled arrival and departure times per trip and stop sequence."""

    __tablename__ = "stop_times"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    stop_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("stops.id", ondelete="CASCADE"), nullable=False
    )
    stop_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_time: Mapped[str] = mapped_column(String(16), nullable=False)
    departure_time: Mapped[str] = mapped_column(String(16), nullable=False)

    trip: Mapped["Trip"] = relationship("Trip", back_populates="stop_times")
    stop: Mapped["Stop"] = relationship("Stop", back_populates="stop_times")


class RouteShape(Base):
    """Spatial LineString traces of routes."""

    __tablename__ = "route_shapes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shape_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=True),
        nullable=False,
    )
