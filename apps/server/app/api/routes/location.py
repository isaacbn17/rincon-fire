from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import get_db
from app.db.queries import (
    get_latest_prediction_for_station,
    get_latest_satellite_for_station,
    get_latest_weather_for_station,
    get_nearest_station,
)
from app.schemas.api import PredictionLatestResponse, SatelliteLatestResponse, WeatherLatestResponse


router = APIRouter(prefix="/location", tags=["location"])
LOGGER = logging.getLogger(__name__)


@router.get("/weather/latest", response_model=WeatherLatestResponse)
def get_weather_by_location(
    lat: float = Query(...),
    lon: float = Query(...),
    db: Session = Depends(get_db),
) -> WeatherLatestResponse:
    LOGGER.debug("event=api.location_weather.request lat=%.6f lon=%.6f", lat, lon)
    station = get_nearest_station(db, lat=lat, lon=lon)
    if station is None:
        LOGGER.debug("event=api.location_weather.response found=false rows_returned=0 reason=no_stations")
        raise HTTPException(status_code=404, detail="No stations available")

    weather = get_latest_weather_for_station(db, station.id)
    if weather is None:
        LOGGER.debug(
            "event=api.location_weather.response station_id=%s found=false rows_returned=0 reason=no_weather",
            station.station_id,
        )
        raise HTTPException(status_code=404, detail="Weather not found for nearest station")

    LOGGER.debug(
        "event=api.location_weather.response station_id=%s found=true rows_returned=1",
        station.station_id,
    )
    return WeatherLatestResponse(
        area_id=station.station_id,
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


@router.get("/predictions/latest", response_model=PredictionLatestResponse)
def get_prediction_by_location(
    lat: float = Query(...),
    lon: float = Query(...),
    model_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PredictionLatestResponse:
    settings = get_settings()
    chosen_model = model_id or settings.default_model_id
    LOGGER.debug(
        "event=api.location_prediction.request lat=%.6f lon=%.6f model_id=%s",
        lat,
        lon,
        chosen_model,
    )

    station = get_nearest_station(db, lat=lat, lon=lon)
    if station is None:
        LOGGER.debug("event=api.location_prediction.response found=false rows_returned=0 reason=no_stations")
        raise HTTPException(status_code=404, detail="No stations available")

    prediction = get_latest_prediction_for_station(db, station_id=station.id, model_id=chosen_model)
    if prediction is None:
        LOGGER.debug(
            "event=api.location_prediction.response station_id=%s model_id=%s found=false rows_returned=0 reason=no_prediction",
            station.station_id,
            chosen_model,
        )
        raise HTTPException(status_code=404, detail="Prediction not found for nearest station")

    LOGGER.debug(
        "event=api.location_prediction.response station_id=%s model_id=%s found=true rows_returned=1",
        station.station_id,
        chosen_model,
    )
    return PredictionLatestResponse(
        area_id=station.station_id,
        model_id=prediction.model_id,
        predicted_at=prediction.predicted_at,
        probability=prediction.probability,
        label=prediction.label,
    )


@router.get("/satellite/latest", response_model=SatelliteLatestResponse)
def get_satellite_by_location(
    request: Request,
    lat: float = Query(...),
    lon: float = Query(...),
    db: Session = Depends(get_db),
) -> SatelliteLatestResponse:
    LOGGER.debug("event=api.location_satellite.request lat=%.6f lon=%.6f", lat, lon)
    station = get_nearest_station(db, lat=lat, lon=lon)
    if station is None:
        LOGGER.debug("event=api.location_satellite.response found=false rows_returned=0 reason=no_stations")
        raise HTTPException(status_code=404, detail="No stations available")

    satellite = get_latest_satellite_for_station(db, station.id)
    if satellite is None:
        LOGGER.debug(
            "event=api.location_satellite.response station_id=%s found=false rows_returned=0 reason=no_satellite",
            station.station_id,
        )
        raise HTTPException(status_code=404, detail="Satellite not found for nearest station")

    url = request.url_for("get_satellite_file", filename=satellite.filename)
    LOGGER.debug(
        "event=api.location_satellite.response station_id=%s found=true rows_returned=1",
        station.station_id,
    )
    return SatelliteLatestResponse(
        area_id=station.station_id,
        captured_at=satellite.captured_at,
        filename=satellite.filename,
        file_path=satellite.file_path,
        satellite_url=str(url),
        content_type=satellite.content_type,
    )
