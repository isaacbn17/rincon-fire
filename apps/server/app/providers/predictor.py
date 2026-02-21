from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier

from app.providers.weather import WeatherObservationInput


@dataclass(frozen=True)
class PredictionOutput:
    probability: float
    label: int


class PredictionProvider:
    def predict(self, *, model_id: str, area_id: str, weather: WeatherObservationInput) -> PredictionOutput:
        raise NotImplementedError


class RandomForestFallbackPredictionProvider(PredictionProvider):
    def __init__(
        self,
        *,
        model_path: Path,
        default_probability: float = 0.2,
        threshold: float = 0.5,
    ):
        self.model_path = model_path
        self.default_probability = min(max(default_probability, 0.0), 1.0)
        self.threshold = threshold
        self._model_checked = False

    def _ensure_model_artifact(self) -> None:
        if self._model_checked:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(f"Missing RF model artifact at {self.model_path}")
        model = joblib.load(self.model_path)
        if not isinstance(model, RandomForestClassifier):
            raise TypeError(f"Unexpected RF model artifact type: {type(model)}")
        self._model_checked = True

    def predict(self, *, model_id: str, area_id: str, weather: WeatherObservationInput) -> PredictionOutput:
        # The model is intentionally untrained for now; this validates artifact wiring
        # and emits a deterministic fallback probability.
        self._ensure_model_artifact()
        probability = self.default_probability
        return PredictionOutput(probability=probability, label=int(probability >= self.threshold))
