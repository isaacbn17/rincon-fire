from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import queries
from app.db.models import WeatherObservation


def get_latest_weather(db: Session, *, area_id: str) -> WeatherObservation | None:
    station = queries.get_station_by_area_id(db, area_id)
    if station is None:
        return None
    return queries.get_latest_weather_for_station(db, station.id)
