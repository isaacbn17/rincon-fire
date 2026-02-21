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


class WeatherLatestResponse(BaseModel):
    area_id: str
    observed_at: datetime
    temperature_c: float
    humidity_pct: float
    wind_speed_kph: float
    precipitation_mm: float


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
