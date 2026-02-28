from __future__ import annotations

import csv
import logging
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.bootstrap import init_db
from app.db.engine import SessionLocal
from app.db.queries import (
    insert_prediction,
    insert_weather,
    list_active_stations,
    set_station_active,
    upsert_station,
)
from app.providers.predictor import MultiModelPredictionProvider
from app.providers.weather import NoaaWeatherProvider, WeatherObservationInput
from app.services.weather_features import build_weekly_feature_row


LOGGER = logging.getLogger("worker")


@dataclass(frozen=True)
class StationInput:
    station_id: str
    name: str
    lat: float
    lon: float
    timezone: str | None
    elevation_m: float | None
    source_url: str | None


def _configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level, logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger().setLevel(level)
    LOGGER.setLevel(level)


def _pick(row: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _parse_float(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    return float(value)


def _load_from_csv(csv_path: Path, limit: int | None) -> list[StationInput]:
    stations: list[StationInput] = []
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            station_id = _pick(row, "station_id", "station_identifier", "area_id")
            lat_raw = _pick(row, "lat", "latitude")
            lon_raw = _pick(row, "lon", "longitude")
            if not station_id or lat_raw is None or lon_raw is None:
                continue

            try:
                station = StationInput(
                    station_id=station_id,
                    name=_pick(row, "name") or station_id,
                    lat=float(lat_raw),
                    lon=float(lon_raw),
                    timezone=_pick(row, "timezone"),
                    elevation_m=_parse_float(_pick(row, "elevation_m", "elevation")),
                    source_url=_pick(row, "source_url", "url"),
                )
                stations.append(station)
            except ValueError:
                LOGGER.warning("Skipping invalid station row for station_id=%s", station_id)

            if limit is not None and len(stations) >= limit:
                break
    return stations


def _load_station_id_allowlist(station_ids_file_path: Path) -> list[str]:
    if not station_ids_file_path.exists():
        raise FileNotFoundError(f"Station IDs file not found: {station_ids_file_path}")

    station_ids: list[str] = []
    seen: set[str] = set()
    with station_ids_file_path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line in seen:
                continue
            seen.add(line)
            station_ids.append(line)

    if not station_ids:
        raise ValueError(f"Station IDs file is empty: {station_ids_file_path}")

    return station_ids


def _filter_stations_by_ids(
    *,
    stations: list[StationInput],
    station_ids: list[str],
) -> tuple[list[StationInput], list[str]]:
    allowed = set(station_ids)
    filtered = [station for station in stations if station.station_id in allowed]
    found_ids = {station.station_id for station in filtered}
    missing = sorted(station_id for station_id in station_ids if station_id not in found_ids)
    return filtered, missing


def load_stations(
    *,
    runtime_csv_path: Path,
    source_csv_path: Path,
    stations_count: int,
    station_ids_file_path: Path | None = None,
) -> list[StationInput]:
    if station_ids_file_path is not None:
        station_ids = _load_station_id_allowlist(station_ids_file_path)
        candidate_paths: list[Path] = []
        for csv_path in (runtime_csv_path, source_csv_path):
            if csv_path.exists() and csv_path not in candidate_paths:
                candidate_paths.append(csv_path)

        if not candidate_paths:
            raise FileNotFoundError(
                f"No valid stations found. Checked runtime={runtime_csv_path} source={source_csv_path}"
            )

        missing_ids: list[str] | None = None
        for csv_path in candidate_paths:
            stations = _load_from_csv(csv_path, limit=None)
            filtered, missing = _filter_stations_by_ids(stations=stations, station_ids=station_ids)
            if not missing:
                return filtered[:stations_count]
            missing_ids = missing

        raise ValueError(
            f"Station IDs in {station_ids_file_path} were not found in {candidate_paths[-1]}: {missing_ids}"
        )

    if runtime_csv_path.exists():
        stations = _load_from_csv(runtime_csv_path, stations_count)
        if stations:
            return stations

    if source_csv_path.exists():
        stations = _load_from_csv(source_csv_path, stations_count)
        if stations:
            return stations

    raise FileNotFoundError(
        f"No valid stations found. Checked runtime={runtime_csv_path} source={source_csv_path}"
    )


def _build_degraded_weekly_observations(
    *,
    latest: WeatherObservationInput,
    days: int,
) -> list[WeatherObservationInput]:
    if days <= 0:
        return []

    latest_utc = latest.observed_at.astimezone(timezone.utc)
    return [
        replace(latest, observed_at=latest_utc - timedelta(days=offset))
        for offset in range(days - 1, -1, -1)
    ]


def run_cycle(
    *,
    db: Session,
    weather_provider: NoaaWeatherProvider,
    predictor: MultiModelPredictionProvider,
) -> None:
    feature_days = 7
    model_ids = predictor.available_model_ids()
    active_stations = list_active_stations(db)
    cycle_latest_observations = 0
    cycle_predictions_written = 0
    cycle_degraded_stations = 0
    LOGGER.debug(
        "event=cycle.start active_station_count=%s model_count=%s model_ids=%s",
        len(active_stations),
        len(model_ids),
        ",".join(model_ids),
    )
    for station in active_stations:
        try:
            LOGGER.debug(
                "event=cycle.station.start station_id=%s db_station_id=%s model_count=%s",
                station.station_id,
                station.id,
                len(model_ids),
            )
            weather = weather_provider.get_latest(station_id=station.station_id)
            if isinstance(weather, int):
                LOGGER.info("Skipping station_id=%s: status=%s", station.station_id, weather)
                if weather == 404 or 500 <= weather < 600:
                    set_station_active(db, station_id=station.id, active=False)
                    LOGGER.info("Set station inactive station_id=%s due_to_status=%s", station.station_id, weather)
                continue

            if weather is None:
                LOGGER.info("Skipping station_id=%s: transient_or_parse_failure", station.station_id)
                continue

            _, weather_created = insert_weather(
                db,
                station_id=station.id,
                observation_id=weather.observation_id,
                observed_at=weather.observed_at,
                temperature_c=weather.temperature_c,
                dewpoint_c=weather.dewpoint_c,
                relative_humidity_pct=weather.relative_humidity_pct,
                wind_direction_deg=weather.wind_direction_deg,
                wind_speed_kph=weather.wind_speed_kph,
                wind_gust_kph=weather.wind_gust_kph,
                precipitation_3h_mm=weather.precipitation_3h_mm,
                barometric_pressure_pa=weather.barometric_pressure_pa,
                visibility_m=weather.visibility_m,
                heat_index_c=weather.heat_index_c,
            )
            if not weather_created:
                LOGGER.info(
                    "Skipping duplicate observation for station_id=%s observation_id=%s",
                    station.station_id,
                    weather.observation_id,
                )

            cycle_latest_observations += 1
            weekly_result = weather_provider.get_recent_observations(station_id=station.station_id, days=feature_days)
            feature_source = "weekly"
            weekly_status = "ok"
            weekly_observations: list[WeatherObservationInput]
            if isinstance(weekly_result, int):
                feature_source = "degraded_latest_only"
                weekly_status = f"http_{weekly_result}"
                weekly_observations = _build_degraded_weekly_observations(latest=weather, days=feature_days)
                LOGGER.info(
                    "Using degraded features for station_id=%s due_to_weekly_status=%s",
                    station.station_id,
                    weekly_result,
                )
            elif weekly_result is None:
                feature_source = "degraded_latest_only"
                weekly_status = "unavailable"
                weekly_observations = _build_degraded_weekly_observations(latest=weather, days=feature_days)
                LOGGER.info("Using degraded features for station_id=%s due_to_weekly_history_unavailable", station.station_id)
            else:
                weekly_observations = weekly_result

            if feature_source != "weekly":
                cycle_degraded_stations += 1

            feature_row = build_weekly_feature_row(weekly_observations, days=feature_days, fill_value=0.0)
            predicted_at = datetime.now(timezone.utc)
            predictions_written = 0
            for model_id in model_ids:
                prediction = predictor.predict(
                    model_id=model_id,
                    area_id=station.station_id,
                    feature_row=feature_row,
                )
                LOGGER.debug(
                    "event=prediction.generated station_id=%s db_station_id=%s model_id=%s feature_source=%s weekly_status=%s probability=%.6f label=%s predicted_at=%s",
                    station.station_id,
                    station.id,
                    model_id,
                    feature_source,
                    weekly_status,
                    prediction.probability,
                    prediction.label,
                    predicted_at.isoformat(),
                )
                stored_prediction = insert_prediction(
                    db,
                    station_id=station.id,
                    model_id=model_id,
                    predicted_at=predicted_at,
                    probability=prediction.probability,
                    label=prediction.label,
                )
                predictions_written += 1
                cycle_predictions_written += 1
                LOGGER.debug(
                    "event=prediction.stored prediction_id=%s station_id=%s db_station_id=%s model_id=%s probability=%.6f label=%s predicted_at=%s",
                    stored_prediction.id,
                    station.station_id,
                    station.id,
                    stored_prediction.model_id,
                    stored_prediction.probability,
                    stored_prediction.label,
                    stored_prediction.predicted_at.isoformat(),
                )

            LOGGER.debug(
                "event=cycle.station.complete station_id=%s db_station_id=%s weather_created=%s feature_source=%s weekly_status=%s weekly_observation_count=%s predictions_written=%s",
                station.station_id,
                station.id,
                weather_created,
                feature_source,
                weekly_status,
                len(weekly_observations),
                predictions_written,
            )
        except Exception:
            LOGGER.exception("Failed cycle processing for station_id=%s", station.station_id)

    LOGGER.debug(
        "event=cycle.complete active_station_count=%s latest_observations=%s degraded_feature_stations=%s predictions_written=%s",
        len(active_stations),
        cycle_latest_observations,
        cycle_degraded_stations,
        cycle_predictions_written,
    )


def sync_stations_from_csv(*, db: Session, stations: list[StationInput]) -> None:
    for station in stations:
        upsert_station(
            db,
            station_id=station.station_id,
            active=True,
            name=station.name,
            lat=station.lat,
            lon=station.lon,
            timezone=station.timezone,
            elevation_m=station.elevation_m,
            source_url=station.source_url,
        )


def main() -> None:
    settings = get_settings()
    _configure_logging(settings.log_level)
    init_db(reset_db=settings.reset_db_on_start)

    stations = load_stations(
        runtime_csv_path=settings.stations_csv_path,
        source_csv_path=settings.stations_source_csv_path,
        stations_count=settings.stations_count,
        station_ids_file_path=settings.station_ids_file_path,
    )
    weather_provider = NoaaWeatherProvider(
        base_url=settings.noaa_base_url,
        user_agent=settings.noaa_user_agent,
        require_qc=settings.noaa_require_qc,
        timeout_seconds=settings.noaa_timeout_seconds,
        max_retries=settings.noaa_max_retries,
        backoff_seconds=settings.noaa_backoff_seconds,
    )
    predictor = MultiModelPredictionProvider(
        model_artifact_dir=settings.model_artifact_dir,
        enabled_model_ids=settings.enabled_model_ids,
        threshold=settings.prediction_threshold,
    )
    db = SessionLocal()
    try:
        sync_stations_from_csv(db=db, stations=stations)
    finally:
        db.close()

    LOGGER.info(
        "Worker started with %d csv stations, interval=%ss",
        len(stations),
        settings.worker_interval_seconds,
    )

    while True:
        start = time.monotonic()
        db = SessionLocal()
        try:
            run_cycle(
                db=db,
                weather_provider=weather_provider,
                predictor=predictor,
            )
        finally:
            db.close()

        elapsed = time.monotonic() - start
        sleep_for = settings.worker_interval_seconds - elapsed
        if sleep_for > 0:
            LOGGER.info("Cycle complete in %.2fs; sleeping %.2fs", elapsed, sleep_for)
            time.sleep(sleep_for)
        else:
            LOGGER.warning("Cycle lagging by %.2fs; starting next cycle immediately", abs(sleep_for))


if __name__ == "__main__":
    main()
