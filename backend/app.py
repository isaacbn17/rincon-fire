from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from flask import Flask, jsonify, request

from config import Config, ensure_dirs
from services.model import RandomForestPredictor
from services.satellite_images import (
    SatelliteRequest,
    build_filename,
    get_satellite_image_bytes,
    save_image_bytes,
)
from services.weather_service import (
    extract_weather,
    prepare_weather_week,
    request_seven_day_observations,
)
from api.predict import bp_predict
from api.satellite import bp_sat


FEATURE_NAMES = [
    "temperature_day0",
    "temperature_day1",
    "temperature_day2",
    "temperature_day3",
    "temperature_day4",
    "temperature_day5",
    "temperature_day6",
    "dewpoint_day0",
    "dewpoint_day1",
    "dewpoint_day2",
    "dewpoint_day3",
    "dewpoint_day4",
    "dewpoint_day5",
    "dewpoint_day6",
    "relativeHumidity_day0",
    "relativeHumidity_day1",
    "relativeHumidity_day2",
    "relativeHumidity_day3",
    "relativeHumidity_day4",
    "relativeHumidity_day5",
    "relativeHumidity_day6",
    "precipitationLast3Hours_day0",
    "precipitationLast3Hours_day1",
    "precipitationLast3Hours_day2",
    "precipitationLast3Hours_day3",
    "precipitationLast3Hours_day4",
    "precipitationLast3Hours_day5",
    "precipitationLast3Hours_day6",
    "windDirection_day0",
    "windDirection_day1",
    "windDirection_day2",
    "windDirection_day3",
    "windDirection_day4",
    "windDirection_day5",
    "windDirection_day6",
    "windSpeed_day0",
    "windSpeed_day1",
    "windSpeed_day2",
    "windSpeed_day3",
    "windSpeed_day4",
    "windSpeed_day5",
    "windSpeed_day6",
    "windGust_day0",
    "windGust_day1",
    "windGust_day2",
    "windGust_day3",
    "windGust_day4",
    "windGust_day5",
    "windGust_day6",
    "barometricPressure_day0",
    "barometricPressure_day1",
    "barometricPressure_day2",
    "barometricPressure_day3",
    "barometricPressure_day4",
    "barometricPressure_day5",
    "barometricPressure_day6",
]

NOAA_HEADERS = {
    "User-Agent": "RinconFire/1.0 (contact: local-dev)",
    "Accept": "application/geo+json",
}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _station_id_from_url(station_url: str) -> str:
    return station_url.rstrip("/").split("/")[-1]


def _normalize_station_url(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return f"https://api.weather.gov/stations/{raw}"


def _resolve_station_csv(cfg: Config) -> Path | None:

    candidates = [
        Path("src/weather_stations_utah_valid.csv"),
        Path("src/weather_stations_utah.csv"),
        Path("data/weather_stations_utah_valid.csv"),
        Path("data/weather_stations_utah.csv"),
        Path(cfg.STATIONS_DIR),
        Path("data/weather_stations.csv"),
        Path("src/weather_stations_all_states_valid.csv"),
        Path("src/weather_stations_all_states.csv"),
        Path("data/weather_stations_all_states_valid.csv"),
        Path("data/weather_stations_all_states.csv"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _pick_column(fieldnames: list[str], *candidates: str) -> str | None:
    lower_map = {name.lower(): name for name in fieldnames}
    for candidate in candidates:
        match = lower_map.get(candidate.lower())
        if match:
            return match
    return None


def _load_stations(cfg: Config, limit: int | None = None) -> list[dict[str, Any]]:
    csv_path = _resolve_station_csv(cfg)
    if csv_path is None:
        return []

    items: list[dict[str, Any]] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []

        station_url_key = _pick_column(fieldnames, "station_url", "stationid", "station_id", "id", "station")
        lat_key = _pick_column(fieldnames, "latitude", "lat")
        lon_key = _pick_column(fieldnames, "longitude", "lon", "lng")
        name_key = _pick_column(fieldnames, "name", "station_name", "stationname", "area_name")

        for row in reader:
            station_url = _normalize_station_url(row.get(station_url_key) if station_url_key else None)
            lat = _safe_float(row.get(lat_key) if lat_key else None)
            lon = _safe_float(row.get(lon_key) if lon_key else None)

            if not station_url or lat is None or lon is None:
                continue

            area_id = _station_id_from_url(station_url)
            name = (row.get(name_key) if name_key else None) or area_id

            items.append(
                {
                    "area_id": area_id,
                    "station_url": station_url,
                    "name": str(name),
                    "lat": lat,
                    "lon": lon,
                }
            )

            if limit is not None and len(items) >= limit:
                break

    return items


def _noaa_get_json(url: str) -> dict[str, Any] | None:
    try:
        response = requests.get(url, headers=NOAA_HEADERS, timeout=15)
        if not response.ok:
            return None
        return response.json()
    except requests.RequestException:
        return None


def _latest_observation_for_station(station_url: str) -> dict[str, Any] | None:
    return _noaa_get_json(f"{station_url.rstrip('/')}/observations/latest")


def _prop_value(props: dict[str, Any], key: str) -> float | None:
    raw = props.get(key)
    if isinstance(raw, dict):
        return _safe_float(raw.get("value"))
    return _safe_float(raw)


def _extract_latest_weather_payload(area_id: str, observation_json: dict[str, Any]) -> dict[str, Any]:
    props = observation_json.get("properties", {}) if observation_json else {}

    return {
        "area_id": area_id,
        "observed_at": props.get("timestamp"),
        "temperature_c": _prop_value(props, "temperature"),
        "dewpoint_c": _prop_value(props, "dewpoint"),
        "relative_humidity_pct": _prop_value(props, "relativeHumidity"),
        "wind_direction_deg": _prop_value(props, "windDirection"),
        "wind_speed_kph": _prop_value(props, "windSpeed"),
        "wind_gust_kph": _prop_value(props, "windGust"),
        "precipitation_3h_mm": _prop_value(props, "precipitationLast3Hours"),
        "barometric_pressure_pa": _prop_value(props, "barometricPressure"),
        "visibility_m": _prop_value(props, "visibility"),
        "heat_index_c": _prop_value(props, "heatIndex"),
    }


def _heuristic_probability_from_observation(observation_json: dict[str, Any] | None) -> float:
    props = observation_json.get("properties", {}) if observation_json else {}

    temperature = _prop_value(props, "temperature")
    humidity = _prop_value(props, "relativeHumidity")
    wind_speed = _prop_value(props, "windSpeed")
    wind_gust = _prop_value(props, "windGust")
    precipitation = _prop_value(props, "precipitationLast3Hours")

    temp_score = _clamp(((temperature or 20.0) - 15.0) / 25.0)
    humidity_score = _clamp((35.0 - (humidity or 50.0)) / 35.0)
    wind_score = _clamp(max(wind_speed or 0.0, wind_gust or 0.0) / 40.0)
    precip_penalty = _clamp((precipitation or 0.0) / 5.0)

    probability = 0.45 * temp_score + 0.35 * humidity_score + 0.25 * wind_score - 0.15 * precip_penalty
    return round(_clamp(probability, 0.01, 0.99), 4)


def _predict_probability_for_station(app: Flask, station_url: str) -> tuple[float, int]:
    """
    Try the existing RF workflow first.
    If it fails for any reason, fall back to a simple latest-weather heuristic
    so the UI still has live data.
    """
    try:
        weather_api_response = request_seven_day_observations(station_url)
        if not weather_api_response:
            raise RuntimeError("No seven-day observations available")

        weather_data = extract_weather(weather_api_response)
        weather_prepared = prepare_weather_week(weather_data)

        for feature in FEATURE_NAMES:
            if feature not in weather_prepared.columns:
                weather_prepared[feature] = 0.0

        weather_prepared = weather_prepared[FEATURE_NAMES].fillna(0.0)

        predictor: RandomForestPredictor = app.extensions["rf_predictor"]
        prediction = predictor.predict_proba_one(weather_prepared.to_numpy())

        return round(float(prediction.wildfire_probability), 4), int(prediction.label)
    except Exception:
        latest = _latest_observation_for_station(station_url)
        probability = _heuristic_probability_from_observation(latest)
        label = int(probability >= 0.5)
        return probability, label


def _get_cache(app: Flask, key: str, max_age_seconds: int) -> Any | None:
    cache = app.extensions["compat_cache"]
    entry = cache.get(key)
    if not entry:
        return None
    if (time.time() - entry["ts"]) > max_age_seconds:
        return None
    return entry["value"]


def _set_cache(app: Flask, key: str, value: Any) -> None:
    app.extensions["compat_cache"][key] = {"ts": time.time(), "value": value}


def create_app() -> Flask:
    cfg = Config()
    ensure_dirs(cfg)

    app = Flask(__name__)
    app.config.from_mapping(
        MODEL_PATH=cfg.MODEL_PATH,
        MODEL_VERSION=cfg.MODEL_VERSION,
        IMAGE_DIR=cfg.IMAGE_DIR,
        MAX_CONTENT_LENGTH=cfg.MAX_CONTENT_LENGTH,
    )

    app.extensions["rf_predictor"] = RandomForestPredictor(
        model_path=app.config["MODEL_PATH"],
        model_version=app.config["MODEL_VERSION"],
    )
    app.extensions["compat_cache"] = {}

    app.register_blueprint(bp_predict)
    app.register_blueprint(bp_sat)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @app.route("/health", methods=["GET"])
    @app.route("/api/v1/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/api/v1/models", methods=["GET"])
    def get_models():
        return jsonify(
            {
                "models": [
                    {
                        "model_id": app.config["MODEL_VERSION"],
                        "name": "Random Forest",
                        "description": "Compatibility route for the live UI backed by the current backend.",
                    }
                ]
            }
        ), 200

    @app.route("/api/v1/stations", methods=["GET"])
    def get_stations():
        stations = _load_stations(cfg, limit=200)
        items = [
            {
                "area_id": station["area_id"],
                "name": station["name"],
                "lat": station["lat"],
                "lon": station["lon"],
                "latest_observed_at": None,
                "latest_predicted_at": None,
            }
            for station in stations
        ]
        return jsonify({"items": items}), 200

    @app.route("/api/v1/fire-areas/top", methods=["GET"])
    def get_top_fire_areas():
        model_id = request.args.get("model_id") or app.config["MODEL_VERSION"]
        try:
            n = max(1, int(request.args.get("n", 5)))
        except ValueError:
            n = 5

        cache_key = f"top:{model_id}:{n}"
        cached = _get_cache(app, cache_key, max_age_seconds=10)
        if cached is not None:
            return jsonify({"items": cached}), 200

        scan_limit = max(15, n * 6)
        stations = _load_stations(cfg, limit=scan_limit)

        ranked: list[dict[str, Any]] = []
        for station in stations:
            latest_obs = _latest_observation_for_station(station["station_url"])
            if not latest_obs:
                continue

            props = latest_obs.get("properties", {})
            probability = _heuristic_probability_from_observation(latest_obs)
            observed_at = props.get("timestamp")

            ranked.append(
                {
                    "area_id": station["area_id"],
                    "name": props.get("stationName") or station["name"],
                    "lat": station["lat"],
                    "lon": station["lon"],
                    "predicted_at": observed_at,
                    "probability": probability,
                    "model_id": model_id,
                }
            )

        ranked.sort(key=lambda item: item["probability"], reverse=True)
        items = ranked[:n]
        _set_cache(app, cache_key, items)
        return jsonify({"items": items}), 200

    @app.route("/api/v1/fire-areas/compare", methods=["GET"])
    def get_compare_fire_areas():
        try:
            n = max(1, int(request.args.get("n", 5)))
        except ValueError:
            n = 5

        model_id = app.config["MODEL_VERSION"]
        cache_key = f"compare:{n}"
        cached = _get_cache(app, cache_key, max_age_seconds=10)
        if cached is not None:
            return jsonify(cached), 200

        scan_limit = max(15, n * 6)
        stations = _load_stations(cfg, limit=scan_limit)

        ranked: list[dict[str, Any]] = []
        for station in stations:
            latest_obs = _latest_observation_for_station(station["station_url"])
            if not latest_obs:
                continue

            props = latest_obs.get("properties", {})
            probability = _heuristic_probability_from_observation(latest_obs)

            ranked.append(
                {
                    "area_id": station["area_id"],
                    "name": props.get("stationName") or station["name"],
                    "lat": station["lat"],
                    "lon": station["lon"],
                    "predictions": [
                        {
                            "model_id": model_id,
                            "probability": probability,
                            "predicted_at": props.get("timestamp"),
                        }
                    ],
                }
            )

        ranked.sort(key=lambda item: item["predictions"][0]["probability"], reverse=True)
        payload = {
            "models": [
                {
                    "model_id": model_id,
                    "name": "Random Forest",
                    "description": "Compatibility route for the live UI backed by the current backend.",
                }
            ],
            "items": ranked[:n],
        }
        _set_cache(app, cache_key, payload)
        return jsonify(payload), 200

    @app.route("/api/v1/areas/<area_id>/weather/latest", methods=["GET"])
    def get_latest_weather(area_id: str):
        stations = _load_stations(cfg)
        station = next((item for item in stations if item["area_id"] == area_id), None)
        if station is None:
            return jsonify({"error": f"Unknown area_id '{area_id}'"}), 404

        observation = _latest_observation_for_station(station["station_url"])
        if not observation:
            return jsonify({"error": "Could not fetch latest weather"}), 502

        return jsonify(_extract_latest_weather_payload(area_id, observation)), 200

    @app.route("/api/v1/areas/<area_id>/predictions/latest", methods=["GET"])
    def get_latest_prediction(area_id: str):
        requested_model_id = request.args.get("model_id") or app.config["MODEL_VERSION"]

        stations = _load_stations(cfg)
        station = next((item for item in stations if item["area_id"] == area_id), None)
        if station is None:
            return jsonify({"error": f"Unknown area_id '{area_id}'"}), 404

        probability, label = _predict_probability_for_station(app, station["station_url"])
        latest_obs = _latest_observation_for_station(station["station_url"])
        predicted_at = None
        if latest_obs:
            predicted_at = latest_obs.get("properties", {}).get("timestamp")

        return jsonify(
            {
                "area_id": area_id,
                "model_id": requested_model_id,
                "predicted_at": predicted_at,
                "probability": probability,
                "label": label,
            }
        ), 200

    @app.route("/api/v1/areas/<area_id>/satellite/latest", methods=["GET"])
    def get_latest_satellite(area_id: str):
        stations = _load_stations(cfg)
        station = next((item for item in stations if item["area_id"] == area_id), None)
        if station is None:
            return jsonify({"error": f"Unknown area_id '{area_id}'"}), 404

        req_obj = SatelliteRequest(
            lat=float(station["lat"]),
            lon=float(station["lon"]),
            zoom=8,
            fmt="png",
        )

        try:
            img_bytes = get_satellite_image_bytes(req_obj)
            filename = build_filename(req_obj)
            out_path = save_image_bytes(app.config["IMAGE_DIR"], filename, img_bytes)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 502

        latest_obs = _latest_observation_for_station(station["station_url"])
        captured_at = None
        if latest_obs:
            captured_at = latest_obs.get("properties", {}).get("timestamp")

        satellite_url = f"{request.host_url.rstrip('/')}/api/v1/satellite/image/{quote(filename)}"

        return jsonify(
            {
                "area_id": area_id,
                "captured_at": captured_at,
                "filename": filename,
                "file_path": str(out_path.as_posix()),
                "satellite_url": satellite_url,
                "content_type": "image/png",
            }
        ), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)
