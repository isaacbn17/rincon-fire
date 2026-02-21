from __future__ import annotations

from datetime import datetime, timezone

from app.providers.predictor import MockPredictionProvider
from app.providers.weather import MockWeatherProvider


def test_mock_weather_provider_is_deterministic() -> None:
    provider = MockWeatherProvider(seed_prefix="test")
    observed_at = datetime(2026, 2, 21, 0, 0, tzinfo=timezone.utc)

    first = provider.get_latest(area_id="area-1", lat=12.34, lon=56.78, observed_at=observed_at)
    second = provider.get_latest(area_id="area-1", lat=12.34, lon=56.78, observed_at=observed_at)

    assert first == second


def test_mock_prediction_provider_is_deterministic() -> None:
    weather_provider = MockWeatherProvider(seed_prefix="test")
    predictor = MockPredictionProvider(seed_prefix="test")
    observed_at = datetime(2026, 2, 21, 0, 0, tzinfo=timezone.utc)

    weather = weather_provider.get_latest(area_id="area-1", lat=12.34, lon=56.78, observed_at=observed_at)
    first = predictor.predict(model_id="rf_baseline", area_id="area-1", weather=weather)
    second = predictor.predict(model_id="rf_baseline", area_id="area-1", weather=weather)

    assert first == second
    assert 0 <= first.probability <= 1
