from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import get_db
from app.schemas.api import PredictionLatestResponse, SatelliteLatestResponse, WeatherLatestResponse
from app.services.prediction import get_latest_prediction
from app.services.satellite import get_latest_satellite
from app.services.weather import get_latest_weather


router = APIRouter(prefix="/areas", tags=["areas"])


@router.get("/{area_id}/weather/latest", response_model=WeatherLatestResponse)
def get_area_weather_latest(area_id: str, db: Session = Depends(get_db)) -> WeatherLatestResponse:
    weather = get_latest_weather(db, area_id=area_id)
    if weather is None:
        raise HTTPException(status_code=404, detail="Area weather not found")
    return WeatherLatestResponse(
        area_id=area_id,
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


@router.get("/{area_id}/predictions/latest", response_model=PredictionLatestResponse)
def get_area_prediction_latest(
    area_id: str,
    model_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PredictionLatestResponse:
    settings = get_settings()
    chosen_model = model_id or settings.default_model_id
    prediction = get_latest_prediction(db, area_id=area_id, model_id=chosen_model)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Area prediction not found")
    return PredictionLatestResponse(
        area_id=area_id,
        model_id=prediction.model_id,
        predicted_at=prediction.predicted_at,
        probability=prediction.probability,
        label=prediction.label,
    )


@router.get("/{area_id}/satellite/latest", response_model=SatelliteLatestResponse)
def get_area_satellite_latest(
    area_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> SatelliteLatestResponse:
    satellite = get_latest_satellite(db, area_id=area_id)
    if satellite is None:
        raise HTTPException(status_code=404, detail="Area satellite image not found")

    url = request.url_for("get_satellite_file", filename=satellite.filename)
    return SatelliteLatestResponse(
        area_id=area_id,
        captured_at=satellite.captured_at,
        filename=satellite.filename,
        file_path=satellite.file_path,
        satellite_url=str(url),
        content_type=satellite.content_type,
    )
