from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.providers.predictor import MultiModelPredictionProvider
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
        self.request_kwargs: list[dict] = []

    def get(self, *args, **kwargs):  # noqa: ANN002, ANN003
        self.request_kwargs.append(kwargs)
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


class _FakeRuntime:
    def __init__(self, model_ids: list[str], probability: float):
        self.model_ids = model_ids
        self.probability = probability
        self.predict_calls: list[tuple[str, dict[str, float]]] = []

    def available_model_ids(self) -> list[str]:
        return self.model_ids

    def predict(self, *, model_id: str, feature_row: dict[str, float]) -> tuple[int, float]:
        self.predict_calls.append((model_id, feature_row))
        return 1, self.probability


def _sample_payload(*, observed_at: datetime | None = None) -> dict:
    ts = observed_at or datetime(2026, 2, 21, 18, 30, tzinfo=timezone.utc)
    iso = ts.isoformat().replace("+00:00", "+00:00")
    return {
        "id": f"https://api.weather.gov/stations/0007W/observations/{iso}",
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-84.18, 30.53]},
        "properties": {
            "@id": f"https://api.weather.gov/stations/0007W/observations/{iso}",
            "stationId": "0007W",
            "stationName": "Montford Middle",
            "timestamp": iso,
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


def test_noaa_provider_recent_observations_collects_one_per_day() -> None:
    base = datetime(2026, 2, 21, 18, 30, tzinfo=timezone.utc)
    features = []
    for day in range(5):
        features.append(_sample_payload(observed_at=base - timedelta(days=day)))
    payload = {"type": "FeatureCollection", "features": features}
    session = _FakeSession([_FakeResponse(200, payload)])
    provider = NoaaWeatherProvider(
        base_url="https://api.weather.gov",
        user_agent="test",
        session=session,
        max_retries=1,
    )

    observations = provider.get_recent_observations(station_id="0007W", days=4)

    assert observations is not None
    assert not isinstance(observations, int)
    assert len(observations) == 4
    assert observations[0].observed_at < observations[-1].observed_at
    assert session.request_kwargs[0]["params"] == {"limit": "500"}


def test_noaa_provider_recent_observations_returns_status_for_400() -> None:
    session = _FakeSession([_FakeResponse(400, {"title": "Bad Request"})])
    provider = NoaaWeatherProvider(
        base_url="https://api.weather.gov",
        user_agent="test",
        session=session,
        max_retries=1,
    )

    observations = provider.get_recent_observations(station_id="0007W", days=7)

    assert observations == 400


def test_multi_model_predictor_uses_runtime_and_threshold() -> None:
    runtime = _FakeRuntime(model_ids=["rf_unbalanced", "xgb_unbalanced"], probability=0.74)
    predictor = MultiModelPredictionProvider(
        model_artifact_dir=Path("."),
        enabled_model_ids=["rf_unbalanced"],
        threshold=0.5,
        runtime=runtime,  # type: ignore[arg-type]
    )
    row = {"temperature_1": 10.0}

    first = predictor.predict(model_id="rf_unbalanced", area_id="0007W", feature_row=row)
    second = predictor.predict(model_id="xgb_unbalanced", area_id="0007W", feature_row=row)

    assert predictor.available_model_ids() == ["rf_unbalanced", "xgb_unbalanced"]
    assert first.probability == 0.74
    assert first.label == 1
    assert second.probability == 0.74
    assert len(runtime.predict_calls) == 2
