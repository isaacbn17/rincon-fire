from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.api import PredictionLatestResponse


def test_prediction_schema_validates_probability_range() -> None:
    PredictionLatestResponse(
        area_id="abc",
        model_id="rf_baseline",
        predicted_at=datetime.now(timezone.utc),
        probability=0.8,
        label=1,
    )

    with pytest.raises(ValidationError):
        PredictionLatestResponse(
            area_id="abc",
            model_id="rf_baseline",
            predicted_at=datetime.now(timezone.utc),
            probability=1.5,
            label=1,
        )
