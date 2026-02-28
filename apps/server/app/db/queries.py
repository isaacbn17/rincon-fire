from __future__ import annotations

from datetime import datetime
import logging

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import ModelPrediction, ModelRegistry, SatelliteImage, Station, WeatherObservation

LOGGER = logging.getLogger(__name__)


def upsert_station(
    db: Session,
    *,
    station_id: str,
    active: bool = True,
    name: str,
    lat: float,
    lon: float,
    timezone: str | None = None,
    elevation_m: float | None = None,
    source_url: str | None = None,
) -> Station:
    station = db.execute(select(Station).where(Station.station_id == station_id)).scalar_one_or_none()
    if station is None:
        station = Station(
            station_id=station_id,
            active=active,
            name=name,
            lat=lat,
            lon=lon,
            timezone=timezone,
            elevation_m=elevation_m,
            source_url=source_url,
        )
        db.add(station)
        db.commit()
        db.refresh(station)
        return station

    station.active = active
    station.name = name
    station.lat = lat
    station.lon = lon
    station.timezone = timezone
    station.elevation_m = elevation_m
    station.source_url = source_url
    db.commit()
    db.refresh(station)
    return station


def insert_weather(
    db: Session,
    *,
    station_id: int,
    observation_id: str,
    observed_at: datetime,
    temperature_c: float | None,
    dewpoint_c: float | None,
    relative_humidity_pct: float | None,
    wind_direction_deg: float | None,
    wind_speed_kph: float | None,
    wind_gust_kph: float | None,
    precipitation_3h_mm: float | None,
    barometric_pressure_pa: float | None,
    visibility_m: float | None,
    heat_index_c: float | None,
) -> tuple[WeatherObservation, bool]:
    existing = db.execute(
        select(WeatherObservation).where(WeatherObservation.observation_id == observation_id)
    ).scalar_one_or_none()
    if existing is not None:
        LOGGER.info(
            "Skipping duplicate observation for station_id=%s observation_id=%s",
            station_id,
            observation_id,
        )
        return existing, False

    row = WeatherObservation(
        station_id=station_id,
        observation_id=observation_id,
        observed_at=observed_at,
        temperature_c=temperature_c,
        dewpoint_c=dewpoint_c,
        relative_humidity_pct=relative_humidity_pct,
        wind_direction_deg=wind_direction_deg,
        wind_speed_kph=wind_speed_kph,
        wind_gust_kph=wind_gust_kph,
        precipitation_3h_mm=precipitation_3h_mm,
        barometric_pressure_pa=barometric_pressure_pa,
        visibility_m=visibility_m,
        heat_index_c=heat_index_c,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, True


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
    LOGGER.debug(
        "event=prediction.inserted prediction_id=%s station_id=%s model_id=%s probability=%.6f label=%s predicted_at=%s",
        row.id,
        row.station_id,
        row.model_id,
        row.probability,
        row.label,
        row.predicted_at.isoformat(),
    )
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
    models = list(db.execute(select(ModelRegistry).order_by(ModelRegistry.model_id)).scalars())
    LOGGER.debug("event=models.list count=%s", len(models))
    return models


def list_stations(db: Session) -> list[Station]:
    return list(db.execute(select(Station).order_by(Station.station_id)).scalars())


def list_active_stations(db: Session) -> list[Station]:
    return list(
        db.execute(select(Station).where(Station.active.is_(True)).order_by(Station.station_id)).scalars()
    )


def set_station_active(db: Session, *, station_id: int, active: bool) -> Station | None:
    station = db.execute(select(Station).where(Station.id == station_id)).scalar_one_or_none()
    if station is None:
        return None
    station.active = active
    db.commit()
    db.refresh(station)
    return station


def get_station_by_area_id(db: Session, area_id: str) -> Station | None:
    return db.execute(select(Station).where(Station.station_id == area_id)).scalar_one_or_none()


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
    prediction = db.execute(stmt).scalar_one_or_none()
    LOGGER.debug(
        "event=prediction.latest.query station_id=%s model_id=%s found=%s",
        station_id,
        model_id,
        prediction is not None,
    )
    return prediction


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
    LOGGER.debug(
        "event=fire_areas.top.query model_id=%s requested_n=%s raw_rows=%s",
        model_id,
        n,
        len(rows),
    )

    latest_by_station: dict[int, tuple[Station, ModelPrediction]] = {}
    for station, prediction in rows:
        if station.id not in latest_by_station:
            latest_by_station[station.id] = (station, prediction)

    ordered = sorted(
        latest_by_station.values(),
        key=lambda item: (item[1].probability, item[1].predicted_at),
        reverse=True,
    )
    result = ordered[:n]
    LOGGER.debug(
        "event=fire_areas.top.result model_id=%s requested_n=%s latest_station_rows=%s returned_rows=%s",
        model_id,
        n,
        len(latest_by_station),
        len(result),
    )
    return result


def get_compare_fire_areas(
    db: Session,
    *,
    n_per_model: int,
) -> tuple[list[ModelRegistry], list[tuple[Station, dict[str, ModelPrediction | None]]]]:
    models = list_models(db)
    if not models:
        return [], []

    stations_by_id: dict[int, Station] = {}
    for model in models:
        top_rows = get_top_fire_areas(db, n=n_per_model, model_id=model.model_id)
        for station, _ in top_rows:
            stations_by_id[station.id] = station

    if not stations_by_id:
        return models, []

    model_ids = [model.model_id for model in models]
    compare_rows: list[tuple[Station, dict[str, ModelPrediction | None]]] = []
    for station in stations_by_id.values():
        predictions_by_model: dict[str, ModelPrediction | None] = {}
        for model_id in model_ids:
            predictions_by_model[model_id] = get_latest_prediction_for_station(
                db,
                station_id=station.id,
                model_id=model_id,
            )
        compare_rows.append((station, predictions_by_model))

    return models, compare_rows
