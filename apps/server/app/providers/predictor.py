from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from app.providers.weather import WeatherObservationInput


@dataclass(frozen=True)
class PredictionOutput:
    probability: float
    label: int


class PredictionProvider:
    def predict(self, *, model_id: str, area_id: str, weather: WeatherObservationInput) -> PredictionOutput:
        raise NotImplementedError


class MockPredictionProvider(PredictionProvider):
    _MODEL_BIAS = {
        "rf_baseline": 0.00,
        "xgb_imbalance": 0.05,
        "bayes_detector": -0.03,
    }

    def __init__(self, *, seed_prefix: str = "rincon-fire"):
        self.seed_prefix = seed_prefix

    def predict(self, *, model_id: str, area_id: str, weather: WeatherObservationInput) -> PredictionOutput:
        digest = hashlib.sha256(
            f"{self.seed_prefix}:{model_id}:{area_id}:{weather.observed_at.isoformat()}".encode("utf-8")
        ).hexdigest()
        rng = random.Random(int(digest[:16], 16))

        temp_component = min(max((weather.temperature_c - 20.0) / 20.0, 0.0), 1.0)
        humidity_component = min(max((55.0 - weather.humidity_pct) / 55.0, 0.0), 1.0)
        wind_component = min(max(weather.wind_speed_kph / 60.0, 0.0), 1.0)
        rain_component = min(max((2.0 - weather.precipitation_mm) / 2.0, 0.0), 1.0)

        base = 0.35 * temp_component + 0.35 * humidity_component + 0.2 * wind_component + 0.1 * rain_component
        probability = base + self._MODEL_BIAS.get(model_id, 0.0) + (rng.random() - 0.5) * 0.12
        probability = round(min(max(probability, 0.01), 0.99), 4)
        return PredictionOutput(probability=probability, label=int(probability >= 0.5))
