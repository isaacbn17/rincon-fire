import re
import json
from datetime import datetime, timezone
import time
import csv
from pathlib import Path
from pprint import pprint

# --- robust imports: work with `python -m src.main` OR `python src/main.py` ---
try:
    # when run as a module from project root
    from src.config import load_api_key, DEFAULT_GRID, DEFAULT_LOOKBACK, DEFAULT_TOPN, DEFAULT_OUT
    from src.preprocess import load_and_clean, aggregate_regions
    from src.risk_summarize import to_context_json
    from src.prompt_gemini import ask_gemini, ask_gemini_without_wildfire_data
    from src.api_helpers import get_station_list, request_observations
    try:
        from data.database_manager import DatabaseManager
    except Exception as e:
        print(f"Warning: database disabled because DatabaseManager could not be imported: {e}")
        DatabaseManager = None
except ModuleNotFoundError:
    # fallback if run directly (or PYTHONPATH not set)
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    from config import load_api_key, DEFAULT_GRID, DEFAULT_LOOKBACK, DEFAULT_TOPN, DEFAULT_OUT
    from preprocess import load_and_clean, aggregate_regions
    from risk_summarize import to_context_json
    from prompt_gemini import ask_gemini
    from api_helpers import get_station_list, request_observations
    from data.database_manager import DatabaseManager
# ---------------------------------------------------------------------------

def old_parse_confidence(response_text: str) -> float | None:
    """Extract confidence score (0–100) from Gemini's response text."""
    match = re.search(r"Confidence\s*score\s*:\s*([0-9]+)", response_text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None

def parse_confidence(response_text: str) -> list[float]:
    """
    Parse Gemini's response (expected to be JSON) and return a list of confidence scores.
    Expected default format from the prompt:
        {"scores": [s1, s2, ...]}
    Each s_i is in [1, 1000].
    """
    if not response_text:
        raise ValueError("Empty response from Gemini; cannot parse confidence scores.")

    text = response_text.strip()

    start_brace = text.find("{")
    start_bracket = text.find("[")

    candidates = [pos for pos in (start_brace, start_bracket) if pos != -1]
    if candidates:
        start = min(candidates)
        end = max(text.rfind("}"), text.rfind("]"))
        if end != -1 and end >= start:
            text = text[start:end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not decode Gemini JSON: {e}\nRaw text:\n{text}") from e

    # Expected shape: {"scores": [...]}
    if isinstance(data, dict) and "scores" in data:
        scores = data["scores"]
    elif isinstance(data, list):
        scores = data
    else:
        raise ValueError(f"Unexpected JSON structure from Gemini: {data!r}")

    if not isinstance(scores, list):
        raise ValueError(f"`scores` is not a list: {scores!r}")

    cleaned_scores = []
    for s in scores:
        try:
            val = float(s)
        except (TypeError, ValueError):
            raise ValueError(f"Non-numeric confidence value: {s!r}")
        cleaned_scores.append(val)

    return cleaned_scores


def simplify_weather_json(weather_json: dict, latitude: float, longitude: float) -> dict:
    props = weather_json.get("properties", {})
    station_name = props.get("stationName", "Unknown Station")

    simplified = {'stationName': station_name, 'latitude': latitude, 'longitude': longitude}
    for key, value in props.items():
        # Skip metadata and URLs
        if key in {"@id", "@type", "icon", "rawMessage", "station", "stationId", "stationName", "textDescription"}:
            continue

        # If the value is a dict with a 'value' field, use that
        if isinstance(value, dict) and "value" in value:
            simplified[key] = value["value"]

        # If it's a list (e.g., cloudLayers), extract first base value or None
        elif isinstance(value, list):
            if len(value) > 0:
                first = value[0]
                if isinstance(first, dict) and "base" in first:
                    simplified[key] = first["base"].get("value")
                else:
                    simplified[key] = None
            else:
                simplified[key] = None
        else:
            simplified[key] = value

    return simplified

def insert_prediction(station_id, station_name, latitude, longitude, timestamp, confidence, weather):
    """Insert a wildfire prediction record into the database."""
    if DatabaseManager is None:
        # DB is disabled for this run; skip inserting.
        return

    conn = DatabaseManager.get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO wildfire_location_prediction
            (station_id, station_name, latitude, longitude, timestamp, confidence, weather_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            station_id,
            station_name,
            latitude,
            longitude,
            timestamp,
            confidence,
            json.dumps(weather)  # Convert dict to JSON
        ))
        conn.commit()
    except Exception as e:
        print(f"Error inserting record: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


def write_predictions_to_csv(gemini_response, cumulative_weather_data):
    ROOT = Path(__file__).resolve().parents[1]  # goes up from src/ to rincon-fire/
    DATA_DIR = ROOT / "data" / "fire-prediction"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    csv_path = DATA_DIR / f"{date_str}-predictions.csv"

    # Get the confidence scores from the Gemini JSON
    confidence_scores = parse_confidence(gemini_response)

    if len(confidence_scores) != len(cumulative_weather_data):
        raise ValueError(
            f"Gemini returned {len(confidence_scores)} scores for "
            f"{len(cumulative_weather_data)} weather records."
        )

    for i in range(len(cumulative_weather_data)):
        weather_data = cumulative_weather_data[i]
        confidence_score = confidence_scores[i]
        weather_data["confidenceScore"] = confidence_score

        file_exists = csv_path.exists()
        with csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=weather_data.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(weather_data)

def predict_wildfire_likelihood_in_batches():
    api_key = load_api_key()
    count = 0
    weather_data_count = 0
    cumulative_weather_data = []
    with open("weather_stations.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            station_url = row["station_url"]
            print(f"\nGetting weather data for {station_url}")

            try:
                weather_json = request_observations(station_url)
                weather = simplify_weather_json(weather_json, float(row["latitude"]), float(row["longitude"]))
                cumulative_weather_data.append(weather)
                weather_data_count += 1
            except Exception as e:
                continue

            if weather_data_count >= 10:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        print(f"Querying Gemini...")
                        gemini_response = ask_gemini(api_key, cumulative_weather_data)
                        break
                    except Exception as e:
                        print(f"Error querying Gemini: {e}")
                        time.sleep(5)
                else:
                    print("Failed after maximum retries.")
                    break

                print("=== Gemini Result ===")
                print(gemini_response)

                write_predictions_to_csv(gemini_response, cumulative_weather_data)
                weather_data_count = 0
                cumulative_weather_data = []

            count += 1
            print(f"{count}/500 completed.")


def main():
    predict_wildfire_likelihood_in_batches()

if __name__ == "__main__":
    main()
