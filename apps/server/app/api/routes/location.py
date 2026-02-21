from __future__ import annotations

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


@router.get("/weather/latest", response_model=WeatherLatestResponse)
def get_weather_by_location(
    lat: float = Query(...),
    lon: float = Query(...),
    db: Session = Depends(get_db),
) -> WeatherLatestResponse:
    station = get_nearest_station(db, lat=lat, lon=lon)
    if station is None:
        raise HTTPException(status_code=404, detail="No stations available")

    weather = get_latest_weather_for_station(db, station.id)
    if weather is None:
        raise HTTPException(status_code=404, detail="Weather not found for nearest station")

    return WeatherLatestResponse(
        area_id=station.area_id,
        observed_at=weather.observed_at,
        temperature_c=weather.temperature_c,
        humidity_pct=weather.humidity_pct,
        wind_speed_kph=weather.wind_speed_kph,
        precipitation_mm=weather.precipitation_mm,
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

    station = get_nearest_station(db, lat=lat, lon=lon)
    if station is None:
        raise HTTPException(status_code=404, detail="No stations available")

    prediction = get_latest_prediction_for_station(db, station_id=station.id, model_id=chosen_model)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found for nearest station")

    return PredictionLatestResponse(
        area_id=station.area_id,
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
    station = get_nearest_station(db, lat=lat, lon=lon)
    if station is None:
        raise HTTPException(status_code=404, detail="No stations available")

    satellite = get_latest_satellite_for_station(db, station.id)
    if satellite is None:
        raise HTTPException(status_code=404, detail="Satellite not found for nearest station")

    url = request.url_for("get_satellite_file", filename=satellite.filename)
    return SatelliteLatestResponse(
        area_id=station.area_id,
        captured_at=satellite.captured_at,
        filename=satellite.filename,
        file_path=satellite.file_path,
        satellite_url=str(url),
        content_type=satellite.content_type,
    )
