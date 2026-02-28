from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.services.model_runtime import BackendModelsRuntime


@dataclass(frozen=True)
class PredictionOutput:
    probability: float
    label: int


class PredictionProvider:
    def predict(self, *, model_id: str, area_id: str, feature_row: dict[str, float]) -> PredictionOutput:
        raise NotImplementedError

    def available_model_ids(self) -> list[str]:
        raise NotImplementedError


class MultiModelPredictionProvider(PredictionProvider):
    def __init__(
        self,
        *,
        model_artifact_dir: Path,
        enabled_model_ids: list[str],
        threshold: float = 0.5,
        runtime: BackendModelsRuntime | None = None,
    ):
        self.model_artifact_dir = model_artifact_dir
        self.threshold = threshold
        self.runtime = runtime or BackendModelsRuntime(
            model_artifact_dir=model_artifact_dir,
            enabled_model_ids=enabled_model_ids,
        )

    def available_model_ids(self) -> list[str]:
        return self.runtime.available_model_ids()

    def predict(self, *, model_id: str, area_id: str, feature_row: dict[str, float]) -> PredictionOutput:
        _ = area_id  # area_id is currently only used for logging/correlation at call sites.
        _predicted_label, raw_probability = self.runtime.predict(model_id=model_id, feature_row=feature_row)
        probability = 0.0 if raw_probability is None else min(max(raw_probability, 0.0), 1.0)
        return PredictionOutput(probability=probability, label=int(probability >= self.threshold))
