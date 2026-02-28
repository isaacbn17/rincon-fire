from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import get_db
from app.db.queries import (
    get_latest_prediction_for_station,
    get_latest_weather_for_station,
    list_stations,
)
from app.schemas.api import StationListItem, StationsResponse


router = APIRouter(tags=["stations"])
LOGGER = logging.getLogger(__name__)


@router.get("/stations", response_model=StationsResponse)
def get_stations(
    model_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> StationsResponse:
    settings = get_settings()
    chosen_model = model_id or settings.default_model_id
    LOGGER.debug("event=api.stations.request model_id=%s", chosen_model)

    stations = list_stations(db)
    items: list[StationListItem] = []
    for station in stations:
        latest_weather = get_latest_weather_for_station(db, station.id)
        latest_prediction = get_latest_prediction_for_station(db, station_id=station.id, model_id=chosen_model)
        items.append(
            StationListItem(
                area_id=station.station_id,
                name=station.name,
                lat=station.lat,
                lon=station.lon,
                latest_observed_at=(latest_weather.observed_at if latest_weather else None),
                latest_predicted_at=(latest_prediction.predicted_at if latest_prediction else None),
            )
        )

    LOGGER.debug(
        "event=api.stations.response model_id=%s stations_scanned=%s rows_returned=%s",
        chosen_model,
        len(stations),
        len(items),
    )
    return StationsResponse(items=items)
