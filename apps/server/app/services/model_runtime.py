from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from typing import Any


@dataclass(frozen=True)
class ModelCatalogEntry:
    model_id: str
    name: str
    description: str
    module_filename: str
    class_name: str
    artifact_filename: str


MODEL_CATALOG: tuple[ModelCatalogEntry, ...] = (
    ModelCatalogEntry(
        model_id="nb_balanced",
        name="Naive Bayes (Balanced)",
        description="GaussianNB trained on balanced split.",
        module_filename="naive_bayes.py",
        class_name="WildfireNBModel",
        artifact_filename="balanced_nb_model.joblib",
    ),
    ModelCatalogEntry(
        model_id="rf_balanced",
        name="Random Forest (Balanced)",
        description="RandomForest trained on balanced split.",
        module_filename="random_forest.py",
        class_name="WildfireRFModel",
        artifact_filename="balanced_rf_model.joblib",
    ),
    ModelCatalogEntry(
        model_id="xgb_balanced",
        name="XGBoost (Balanced)",
        description="XGBoost trained on balanced split.",
        module_filename="XG_boost.py",
        class_name="WildfireXGBoostModel",
        artifact_filename="balanced_xgb_model.joblib",
    ),
    ModelCatalogEntry(
        model_id="nb_unbalanced",
        name="Naive Bayes (Unbalanced)",
        description="GaussianNB trained on unbalanced split.",
        module_filename="naive_bayes.py",
        class_name="WildfireNBModel",
        artifact_filename="unbalanced_nb_model.joblib",
    ),
    ModelCatalogEntry(
        model_id="rf_unbalanced",
        name="Random Forest (Unbalanced)",
        description="RandomForest trained on unbalanced split.",
        module_filename="random_forest.py",
        class_name="WildfireRFModel",
        artifact_filename="unbalanced_rf_model.joblib",
    ),
    ModelCatalogEntry(
        model_id="xgb_unbalanced",
        name="XGBoost (Unbalanced)",
        description="XGBoost trained on unbalanced split.",
        module_filename="XG_boost.py",
        class_name="WildfireXGBoostModel",
        artifact_filename="unbalanced_xgb_model.joblib",
    ),
)

MODEL_CATALOG_BY_ID = {entry.model_id: entry for entry in MODEL_CATALOG}


def default_model_registry_rows() -> list[dict[str, str]]:
    return [
        {
            "model_id": entry.model_id,
            "name": entry.name,
            "description": entry.description,
        }
        for entry in MODEL_CATALOG
    ]


@dataclass
class _LoadedModel:
    model_id: str
    instance: Any
    feature_columns: list[str]


class BackendModelsRuntime:
    def __init__(
        self,
        *,
        model_artifact_dir: Path,
        enabled_model_ids: list[str],
    ):
        self.model_artifact_dir = model_artifact_dir
        self.enabled_model_ids = enabled_model_ids
        self._models: dict[str, _LoadedModel] = {}
        self._module_cache: dict[str, Any] = {}
        self._load_enabled_models()

    def available_model_ids(self) -> list[str]:
        return list(self._models.keys())

    def predict(self, *, model_id: str, feature_row: dict[str, float]) -> tuple[int, float | None]:
        loaded = self._models.get(model_id)
        if loaded is None:
            raise KeyError(f"Unknown model_id={model_id}")

        normalized = {
            column: float(feature_row.get(column, 0.0) or 0.0)
            for column in loaded.feature_columns
        }
        prediction, probability = loaded.instance.predict(normalized)
        return int(prediction), (None if probability is None else float(probability))

    def _load_enabled_models(self) -> None:
        if not self.enabled_model_ids:
            raise ValueError("enabled_model_ids cannot be empty")
        for model_id in self.enabled_model_ids:
            entry = MODEL_CATALOG_BY_ID.get(model_id)
            if entry is None:
                raise ValueError(f"Unsupported model_id={model_id}")
            self._models[model_id] = self._load_one_model(entry)

    def _load_one_model(self, entry: ModelCatalogEntry) -> _LoadedModel:
        model_class = self._load_model_class(entry)
        artifact_path = self.model_artifact_dir / entry.artifact_filename
        if not artifact_path.exists():
            raise FileNotFoundError(f"Missing model artifact for {entry.model_id}: {artifact_path}")

        instance = model_class()
        instance.load(str(artifact_path))
        feature_columns = getattr(instance, "feature_columns", None)
        if not isinstance(feature_columns, list) or not feature_columns:
            raise ValueError(
                f"Loaded model_id={entry.model_id} does not expose non-empty feature_columns"
            )

        return _LoadedModel(
            model_id=entry.model_id,
            instance=instance,
            feature_columns=feature_columns,
        )

    def _load_model_class(self, entry: ModelCatalogEntry) -> Any:
        module_path = self.model_artifact_dir / entry.module_filename
        if not module_path.exists():
            raise FileNotFoundError(f"Missing model module for {entry.model_id}: {module_path}")
        cache_key = str(module_path.resolve())
        module = self._module_cache.get(cache_key)
        if module is None:
            module_name = f"rincon_backend_model_{module_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Unable to load module spec from {module_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            self._module_cache[cache_key] = module

        model_class = getattr(module, entry.class_name, None)
        if model_class is None:
            raise ImportError(
                f"Module {module_path} does not define required class {entry.class_name}"
            )
        return model_class
