from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app
from services.weather_service import get_weather_for_stations, weather_to_features
import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "temperature",
    "dewpoint",
    "humidity",
    "precipitationLast3Hours",
    "windDirection",
    "windSpeed",
    "windGust",
    "barometricPressure",
]


bp_predict = Blueprint("predict", __name__)

@bp_predict.post("/api/v1/predict/weather")
def predict_weather():
    payload = request.get_json(silent=True) or {}

    try:
        n_stations = int(payload.get("n_stations"))
    except (TypeError, ValueError):
        return jsonify({"error": "n_stations must be an integer"}), 400

    if n_stations <= 0:
        return jsonify({"error": "n_stations must be > 0"}), 400

    weather_records = get_weather_for_stations(n_stations)

    predictor = current_app.extensions["rf_predictor"]

    results = []
    for rec in weather_records:
        station_url = rec.get("station_url")
        weather = rec.get("weather")

        features = np.array(weather_to_features(weather), dtype=float)
        feature_dict = dict(zip(FEATURE_NAMES, features.tolist()))
        X_df = pd.DataFrame([features], columns=FEATURE_NAMES)
        pred = predictor.predict_proba_one(X_df)

        results.append({
            "station": station_url,
            "weather": feature_dict,
            "prediction": {
                "wildfire_probability": pred.wildfire_probability,
                "model_version": pred.model_version,
                "threshold": pred.threshold,
                "label": pred.label
            }
        })

    return jsonify({"count": len(results), "results": results}), 200
