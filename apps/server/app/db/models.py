from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    elevation_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    weather_observations: Mapped[list[WeatherObservation]] = relationship(back_populates="station")
    model_predictions: Mapped[list[ModelPrediction]] = relationship(back_populates="station")
    satellite_images: Mapped[list[SatelliteImage]] = relationship(back_populates="station")


class ModelRegistry(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    predictions: Mapped[list[ModelPrediction]] = relationship(back_populates="model")


class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    __table_args__ = (
        UniqueConstraint("observation_id", name="uq_weather_observations_observation_id"),
        Index("ix_weather_station_observed_at", "station_id", "observed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    observation_id: Mapped[str] = mapped_column(String(300))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    dewpoint_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_direction_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_kph: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_gust_kph: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_3h_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    barometric_pressure_pa: Mapped[float | None] = mapped_column(Float, nullable=True)
    visibility_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    heat_index_c: Mapped[float | None] = mapped_column(Float, nullable=True)

    station: Mapped[Station] = relationship(back_populates="weather_observations")


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.model_id", ondelete="CASCADE"), index=True)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    probability: Mapped[float] = mapped_column(Float)
    label: Mapped[int] = mapped_column(Integer)

    station: Mapped[Station] = relationship(back_populates="model_predictions")
    model: Mapped[ModelRegistry] = relationship(back_populates="predictions")


class SatelliteImage(Base):
    __tablename__ = "satellite_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    filename: Mapped[str] = mapped_column(String(255), index=True)
    file_path: Mapped[str] = mapped_column(String(1000))
    content_type: Mapped[str] = mapped_column(String(100), default="image/png")

    station: Mapped[Station] = relationship(back_populates="satellite_images")
