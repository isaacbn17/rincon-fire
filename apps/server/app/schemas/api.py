from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    time_utc: datetime


class ModelInfo(BaseModel):
    model_id: str
    name: str
    description: str


class ModelsResponse(BaseModel):
    models: list[ModelInfo]


class FireAreaTopItem(BaseModel):
    area_id: str
    name: str
    lat: float
    lon: float
    predicted_at: datetime
    probability: float
    model_id: str


class FireAreasTopResponse(BaseModel):
    items: list[FireAreaTopItem]


class CompareAreaPrediction(BaseModel):
    model_id: str
    probability: float | None = Field(default=None, ge=0.0, le=1.0)
    predicted_at: datetime | None


class CompareAreaItem(BaseModel):
    area_id: str
    name: str
    lat: float
    lon: float
    predictions: list[CompareAreaPrediction]


class CompareFireAreasResponse(BaseModel):
    models: list[ModelInfo]
    items: list[CompareAreaItem]


class WeatherLatestResponse(BaseModel):
    area_id: str
    observed_at: datetime
    temperature_c: float | None
    dewpoint_c: float | None
    relative_humidity_pct: float | None
    wind_direction_deg: float | None
    wind_speed_kph: float | None
    wind_gust_kph: float | None
    precipitation_3h_mm: float | None
    barometric_pressure_pa: float | None
    visibility_m: float | None
    heat_index_c: float | None


class PredictionLatestResponse(BaseModel):
    area_id: str
    model_id: str
    predicted_at: datetime
    probability: float = Field(ge=0.0, le=1.0)
    label: int


class SatelliteLatestResponse(BaseModel):
    area_id: str
    captured_at: datetime
    filename: str
    file_path: str
    satellite_url: str
    content_type: str


class StationListItem(BaseModel):
    area_id: str
    name: str
    lat: float
    lon: float
    latest_observed_at: datetime | None
    latest_predicted_at: datetime | None


class StationsResponse(BaseModel):
    items: list[StationListItem]
