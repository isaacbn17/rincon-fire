from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app
from services.weather_service import request_seven_day_observations, extract_weather, prepare_weather_week

FEATURE_NAMES = [
    'temperature_day0', 'temperature_day1', 'temperature_day2',
    'temperature_day3', 'temperature_day4', 'temperature_day5',
    'temperature_day6', 'dewpoint_day0', 'dewpoint_day1', 'dewpoint_day2',
    'dewpoint_day3', 'dewpoint_day4', 'dewpoint_day5', 'dewpoint_day6',
    'relativeHumidity_day0', 'relativeHumidity_day1',
    'relativeHumidity_day2', 'relativeHumidity_day3',
    'relativeHumidity_day4', 'relativeHumidity_day5',
    'relativeHumidity_day6', 'precipitationLast3Hours_day0',
    'precipitationLast3Hours_day1', 'precipitationLast3Hours_day2',
    'precipitationLast3Hours_day3', 'precipitationLast3Hours_day4',
    'precipitationLast3Hours_day5', 'precipitationLast3Hours_day6',
    'windDirection_day0', 'windDirection_day1', 'windDirection_day2',
    'windDirection_day3', 'windDirection_day4', 'windDirection_day5',
    'windDirection_day6', 'windSpeed_day0', 'windSpeed_day1',
    'windSpeed_day2', 'windSpeed_day3', 'windSpeed_day4', 'windSpeed_day5',
    'windSpeed_day6', 'windGust_day0', 'windGust_day1', 'windGust_day2',
    'windGust_day3', 'windGust_day4', 'windGust_day5', 'windGust_day6',
    'barometricPressure_day0', 'barometricPressure_day1',
    'barometricPressure_day2', 'barometricPressure_day3',
    'barometricPressure_day4', 'barometricPressure_day5',
    'barometricPressure_day6'
]

bp_predict = Blueprint("predict", __name__)

@bp_predict.post("/api/v1/predict/fire_single_station")
def predict_fire():
    payload = request.get_json(silent=True) or {}

    try:
        station_url = payload.get("station_url")
    except (ValueError):
        return jsonify({"error": "station_url must be specified"}), 400

    weather_api_response = request_seven_day_observations(station_url)
    print("Hello")
    print(weather_api_response)

    try:
        weather_data  = extract_weather(weather_api_response)
        weather_prepared = prepare_weather_week(weather_data)

        predictor = current_app.extensions["rf_predictor"]

        prediction = predictor.predict_proba_one(weather_prepared[FEATURE_NAMES].to_numpy())
    except Exception as e:
        return jsonify({"error": f"Error processing weather data: {str(e)}"}), 500

    fire_message = "High risk of wildfire at station {station_url}" if prediction.label == 1 else "Low risk of wildfire at station {station_url}"
    
    return jsonify({"station_url": station_url,
                    "prediction": {
                        "wildfire_probability": prediction.wildfire_probability,
                        "model_version": prediction.model_version,
                        "threshold": prediction.threshold,
                        "label": prediction.label
                        },
                    "fire_message": fire_message.format(station_url=station_url)
                    }), 200
