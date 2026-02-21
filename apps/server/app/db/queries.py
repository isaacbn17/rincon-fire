from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import ModelPrediction, ModelRegistry, SatelliteImage, Station, WeatherObservation


def upsert_station(db: Session, *, area_id: str, name: str, lat: float, lon: float) -> Station:
    station = db.execute(select(Station).where(Station.area_id == area_id)).scalar_one_or_none()
    if station is None:
        station = Station(area_id=area_id, name=name, lat=lat, lon=lon)
        db.add(station)
        db.commit()
        db.refresh(station)
        return station

    station.name = name
    station.lat = lat
    station.lon = lon
    db.commit()
    db.refresh(station)
    return station


def insert_weather(
    db: Session,
    *,
    station_id: int,
    observed_at: datetime,
    temperature_c: float,
    humidity_pct: float,
    wind_speed_kph: float,
    precipitation_mm: float,
) -> WeatherObservation:
    row = WeatherObservation(
        station_id=station_id,
        observed_at=observed_at,
        temperature_c=temperature_c,
        humidity_pct=humidity_pct,
        wind_speed_kph=wind_speed_kph,
        precipitation_mm=precipitation_mm,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def insert_prediction(
    db: Session,
    *,
    station_id: int,
    model_id: str,
    predicted_at: datetime,
    probability: float,
    label: int,
) -> ModelPrediction:
    row = ModelPrediction(
        station_id=station_id,
        model_id=model_id,
        predicted_at=predicted_at,
        probability=probability,
        label=label,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def insert_satellite(
    db: Session,
    *,
    station_id: int,
    captured_at: datetime,
    filename: str,
    file_path: str,
    content_type: str,
) -> SatelliteImage:
    row = SatelliteImage(
        station_id=station_id,
        captured_at=captured_at,
        filename=filename,
        file_path=file_path,
        content_type=content_type,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_models(db: Session) -> list[ModelRegistry]:
    return list(db.execute(select(ModelRegistry).order_by(ModelRegistry.model_id)).scalars())


def get_station_by_area_id(db: Session, area_id: str) -> Station | None:
    return db.execute(select(Station).where(Station.area_id == area_id)).scalar_one_or_none()


def get_nearest_station(db: Session, *, lat: float, lon: float) -> Station | None:
    stations = list(db.execute(select(Station)).scalars())
    if not stations:
        return None
    return min(
        stations,
        key=lambda station: ((station.lat - lat) ** 2 + (station.lon - lon) ** 2),
    )


def get_latest_weather_for_station(db: Session, station_id: int) -> WeatherObservation | None:
    stmt = (
        select(WeatherObservation)
        .where(WeatherObservation.station_id == station_id)
        .order_by(desc(WeatherObservation.observed_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_latest_prediction_for_station(
    db: Session,
    *,
    station_id: int,
    model_id: str,
) -> ModelPrediction | None:
    stmt = (
        select(ModelPrediction)
        .where(
            ModelPrediction.station_id == station_id,
            ModelPrediction.model_id == model_id,
        )
        .order_by(desc(ModelPrediction.predicted_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_latest_satellite_for_station(db: Session, station_id: int) -> SatelliteImage | None:
    stmt = (
        select(SatelliteImage)
        .where(SatelliteImage.station_id == station_id)
        .order_by(desc(SatelliteImage.captured_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_top_fire_areas(
    db: Session,
    *,
    n: int,
    model_id: str,
) -> list[tuple[Station, ModelPrediction]]:
    rows = db.execute(
        select(Station, ModelPrediction)
        .join(ModelPrediction, ModelPrediction.station_id == Station.id)
        .where(ModelPrediction.model_id == model_id)
        .order_by(desc(ModelPrediction.predicted_at))
    ).all()

    latest_by_station: dict[int, tuple[Station, ModelPrediction]] = {}
    for station, prediction in rows:
        if station.id not in latest_by_station:
            latest_by_station[station.id] = (station, prediction)

    ordered = sorted(
        latest_by_station.values(),
        key=lambda item: (item[1].probability, item[1].predicted_at),
        reverse=True,
    )
    return ordered[:n]
