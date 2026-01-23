from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import joblib
import numpy as np

@dataclass(frozen=True)
class PredictionResult:
    wildfire_probability: float
    label: int
    threshold: float
    model_version: str

class RandomForestPredictor:
    def __init__(self, model_path: Path, model_version: str):
        self.model_path = model_path
        self.model_version = model_version
        self._model = None

    def load(self) -> None:
        if self._model is None:
            self._model = joblib.load(self.model_path)

    def predict_proba_one(self, features: np.ndarray, threshold: float = 0.5) -> PredictionResult:
        """
        features: shape (n_features,) OR (1, n_features)
        """
        self.load()
        x = np.asarray(features)
        if x.ndim == 1:
            x = x.reshape(1, -1)

        # Most sklearn RF classifiers support predict_proba
        proba = float(self._model.predict_proba(x)[0, 1])
        label = int(proba >= threshold)
        return PredictionResult(
            wildfire_probability=proba,
            label=label,
            threshold=threshold,
            model_version=self.model_version,
        )
