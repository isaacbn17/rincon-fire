from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherObservationInput:
    observation_id: str
    station_id: str
    station_name: str | None
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
    latitude: float | None
    longitude: float | None
    elevation_m: float | None


class NwsQuantitativeValue(BaseModel):
    unitCode: str | None = None
    value: float | None = None
    qualityControl: str | None = None


class NwsGeometry(BaseModel):
    type: str
    coordinates: list[float]


class NwsObservationProperties(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    at_id: str = Field(alias="@id")
    station: str | None = None
    stationId: str
    stationName: str | None = None
    timestamp: datetime
    elevation: NwsQuantitativeValue | None = None
    temperature: NwsQuantitativeValue | None = None
    dewpoint: NwsQuantitativeValue | None = None
    relativeHumidity: NwsQuantitativeValue | None = None
    windDirection: NwsQuantitativeValue | None = None
    windSpeed: NwsQuantitativeValue | None = None
    windGust: NwsQuantitativeValue | None = None
    precipitationLast3Hours: NwsQuantitativeValue | None = None
    barometricPressure: NwsQuantitativeValue | None = None
    visibility: NwsQuantitativeValue | None = None
    heatIndex: NwsQuantitativeValue | None = None


class NwsLatestObservation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    geometry: NwsGeometry
    properties: NwsObservationProperties


def to_weather_input(observation: NwsLatestObservation) -> WeatherObservationInput:
    coords = observation.geometry.coordinates if observation.geometry else []
    lon = coords[0] if len(coords) > 0 else None
    lat = coords[1] if len(coords) > 1 else None
    props = observation.properties

    return WeatherObservationInput(
        observation_id=props.at_id,
        station_id=props.stationId,
        station_name=props.stationName,
        observed_at=props.timestamp.astimezone(timezone.utc),
        temperature_c=(props.temperature.value if props.temperature else None),
        dewpoint_c=(props.dewpoint.value if props.dewpoint else None),
        relative_humidity_pct=(props.relativeHumidity.value if props.relativeHumidity else None),
        wind_direction_deg=(props.windDirection.value if props.windDirection else None),
        wind_speed_kph=(props.windSpeed.value if props.windSpeed else None),
        wind_gust_kph=(props.windGust.value if props.windGust else None),
        precipitation_3h_mm=(props.precipitationLast3Hours.value if props.precipitationLast3Hours else None),
        barometric_pressure_pa=(props.barometricPressure.value if props.barometricPressure else None),
        visibility_m=(props.visibility.value if props.visibility else None),
        heat_index_c=(props.heatIndex.value if props.heatIndex else None),
        latitude=lat,
        longitude=lon,
        elevation_m=(props.elevation.value if props.elevation else None),
    )


class WeatherProvider:
    def get_latest(self, *, station_id: str) -> WeatherObservationInput | int | None:
        raise NotImplementedError

    def get_recent_observations(self, *, station_id: str, days: int = 7) -> list[WeatherObservationInput] | int | None:
        raise NotImplementedError


class NoaaWeatherProvider(WeatherProvider):
    def __init__(
        self,
        *,
        base_url: str,
        user_agent: str,
        require_qc: bool = True,
        timeout_seconds: float = 15,
        max_retries: int = 3,
        backoff_seconds: float = 1.5,
        session: requests.Session | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.require_qc = require_qc
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.session = session or requests.Session()

    def _request(
        self,
        *,
        url: str,
        station_id: str,
        params: dict[str, str] | None = None,
    ) -> requests.Response | int | None:
        headers = {
            "accept": "application/geo+json",
            "User-Agent": self.user_agent,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException:
                if attempt < self.max_retries:
                    time.sleep(self.backoff_seconds ** attempt)
                    continue
                LOGGER.warning("NOAA request failed after retries for station_id=%s", station_id)
                return None

            if response.status_code == 404:
                return response.status_code

            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt < self.max_retries:
                    time.sleep(self.backoff_seconds ** attempt)
                    continue
                return response.status_code

            if response.status_code != 200:
                body_preview = (getattr(response, "text", "") or "").strip().replace("\n", " ")
                if len(body_preview) > 240:
                    body_preview = f"{body_preview[:240]}..."
                LOGGER.warning(
                    "NOAA request non-200 for station_id=%s status=%s url=%s params=%s body=%s",
                    station_id,
                    response.status_code,
                    url,
                    params,
                    body_preview,
                )
                return response.status_code

            return response

        return None

    def get_latest(self, *, station_id: str) -> WeatherObservationInput | int | None:
        url = f"{self.base_url}/stations/{station_id}/observations/latest"
        params = {"require_qc": str(self.require_qc).lower()}
        response = self._request(url=url, station_id=station_id, params=params)
        if response is None or isinstance(response, int):
            if response == 404:
                LOGGER.info("No latest observation for station_id=%s (404)", station_id)
            return response

        try:
            payload = response.json()
            parsed = NwsLatestObservation.model_validate(payload)
        except (ValueError, ValidationError):
            LOGGER.warning("NOAA latest payload parse failed for station_id=%s", station_id)
            return None

        return to_weather_input(parsed)

    def get_recent_observations(self, *, station_id: str, days: int = 7) -> list[WeatherObservationInput] | int | None:
        if days <= 0:
            return []

        params = {"limit": "500"}
        next_url = f"{self.base_url}/stations/{station_id}/observations"
        next_params = params

        target_hour: int | None = None
        seen_dates: set[str] = set()
        picked: list[WeatherObservationInput] = []

        while next_url and len(picked) < days:
            response = self._request(url=next_url, station_id=station_id, params=next_params)
            next_params = None
            if response is None or isinstance(response, int):
                return response

            try:
                payload = response.json()
            except ValueError:
                LOGGER.warning("NOAA observations payload parse failed for station_id=%s", station_id)
                return None

            features = payload.get("features", [])
            for feature in features:
                try:
                    parsed = NwsLatestObservation.model_validate(feature)
                except ValidationError:
                    continue
                obs = to_weather_input(parsed)

                if target_hour is None:
                    target_hour = obs.observed_at.hour
                if obs.observed_at.hour != target_hour:
                    continue

                date_key = obs.observed_at.date().isoformat()
                if date_key in seen_dates:
                    continue
                seen_dates.add(date_key)
                picked.append(obs)
                if len(picked) >= days:
                    break

            pagination = payload.get("pagination") or {}
            next_url = pagination.get("next")

        if not picked:
            return None

        picked.sort(key=lambda item: item.observed_at)
        return picked[-days:]
