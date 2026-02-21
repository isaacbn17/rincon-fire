from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier

from app.providers.predictor import RandomForestFallbackPredictionProvider
from app.providers.weather import NoaaWeatherProvider, NwsLatestObservation, to_weather_input


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]):
        self.responses = responses
        self.calls = 0

    def get(self, *args, **kwargs):  # noqa: ANN002, ANN003
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


def _sample_payload() -> dict:
    return {
        "id": "https://api.weather.gov/stations/0007W/observations/2026-02-21T18:30:00+00:00",
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-84.18, 30.53]},
        "properties": {
            "@id": "https://api.weather.gov/stations/0007W/observations/2026-02-21T18:30:00+00:00",
            "stationId": "0007W",
            "stationName": "Montford Middle",
            "timestamp": "2026-02-21T18:30:00+00:00",
            "elevation": {"unitCode": "wmoUnit:m", "value": 49.1},
            "temperature": {"unitCode": "wmoUnit:degC", "value": 26.44, "qualityControl": "V"},
            "dewpoint": {"unitCode": "wmoUnit:degC", "value": 21.58, "qualityControl": "V"},
            "windDirection": {"unitCode": "wmoUnit:degree_(angle)", "value": 0, "qualityControl": "V"},
            "windSpeed": {"unitCode": "wmoUnit:km_h-1", "value": 0, "qualityControl": "V"},
            "windGust": {"unitCode": "wmoUnit:km_h-1", "value": 22.536, "qualityControl": "S"},
            "barometricPressure": {"unitCode": "wmoUnit:Pa", "value": None, "qualityControl": "Z"},
            "visibility": {"unitCode": "wmoUnit:m", "value": None, "qualityControl": "Z"},
            "precipitationLast3Hours": {"unitCode": "wmoUnit:mm", "value": None, "qualityControl": "Z"},
            "relativeHumidity": {"unitCode": "wmoUnit:percent", "value": 74.681317074733, "qualityControl": "V"},
            "heatIndex": {"unitCode": "wmoUnit:degC", "value": 28.22166585447, "qualityControl": "V"},
        },
    }


def test_noaa_payload_transform_keeps_nullable_quantitative_values() -> None:
    parsed = NwsLatestObservation.model_validate(_sample_payload())
    obs = to_weather_input(parsed)

    assert obs.station_id == "0007W"
    assert obs.observed_at == datetime(2026, 2, 21, 18, 30, tzinfo=timezone.utc)
    assert obs.temperature_c == 26.44
    assert obs.precipitation_3h_mm is None
    assert obs.barometric_pressure_pa is None


def test_noaa_provider_retries_and_returns_data() -> None:
    session = _FakeSession(
        [
            _FakeResponse(500, {}),
            _FakeResponse(200, _sample_payload()),
        ]
    )
    provider = NoaaWeatherProvider(
        base_url="https://api.weather.gov",
        user_agent="test",
        max_retries=2,
        backoff_seconds=0.001,
        session=session,
    )
    obs = provider.get_latest(station_id="0007W")

    assert obs is not None
    assert obs.station_id == "0007W"
    assert session.calls == 2


def test_noaa_provider_returns_status_for_404() -> None:
    session = _FakeSession([_FakeResponse(404, {"status": 404})])
    provider = NoaaWeatherProvider(base_url="https://api.weather.gov", user_agent="test", session=session)

    obs = provider.get_latest(station_id="bad")
    assert obs == 404


def test_noaa_provider_returns_status_after_retry_exhaustion() -> None:
    session = _FakeSession([_FakeResponse(500, {}), _FakeResponse(500, {})])
    provider = NoaaWeatherProvider(
        base_url="https://api.weather.gov",
        user_agent="test",
        session=session,
        max_retries=2,
        backoff_seconds=0.001,
    )

    obs = provider.get_latest(station_id="bad")
    assert obs == 500
    assert session.calls == 2


def test_rf_fallback_predictor_uses_fixed_probability(tmp_path: Path) -> None:
    model_path = tmp_path / "rf.joblib"
    joblib.dump(RandomForestClassifier(n_estimators=10, random_state=42), model_path)

    predictor = RandomForestFallbackPredictionProvider(
        model_path=model_path,
        default_probability=0.2,
        threshold=0.5,
    )
    weather = to_weather_input(NwsLatestObservation.model_validate(_sample_payload()))

    first = predictor.predict(model_id="rf_baseline", area_id="0007W", weather=weather)
    second = predictor.predict(model_id="rf_baseline", area_id="0007W", weather=weather)

    assert first == second
    assert first.probability == 0.2
    assert first.label == 0
