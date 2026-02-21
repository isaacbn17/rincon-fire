from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import queries
from app.db.models import SatelliteImage


def get_latest_satellite(db: Session, *, area_id: str) -> SatelliteImage | None:
    station = queries.get_station_by_area_id(db, area_id)
    if station is None:
        return None
    return queries.get_latest_satellite_for_station(db, station.id)
