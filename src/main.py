import re
import json
from datetime import datetime
import time
import csv

# --- robust imports: work with `python -m src.main` OR `python src/main.py` ---
try:
    # when run as a module from project root
    from src.config import load_api_key, DEFAULT_GRID, DEFAULT_LOOKBACK, DEFAULT_TOPN, DEFAULT_OUT
    from src.preprocess import load_and_clean, aggregate_regions
    from src.risk_summarize import to_context_json
    from src.prompt_gemini import ask_gemini, ask_gemini_without_wildfire_data
    from src.api_helpers import get_station_list, request_observations
    from data.database_manager import DatabaseManager
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

def insert_prediction(station_id, station_name, latitude, longitude, timestamp, confidence, weather):
    """Insert a wildfire prediction record into the database."""
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

def predict_wildfire_likelihood_in_batches():
    api_key = load_api_key()
    count = 0
    weather_data_count = 0
    with open("weather_stations.csv", newline="", encoding="utf-8") as f:
        weather_data = []

        reader = csv.DictReader(f)
        for row in reader:
            station_url = row["station_url"]
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])

            print(f"\nGetting weather data for {station_url}")
            try:
                data = request_observations(station_url)
                weather = data["properties"]

                station_id = weather["stationId"]
                station_name = weather["stationName"]
                timestamp = datetime.fromisoformat(weather["timestamp"])

                weather_data.append(weather)
                weather_data_count += 1
            except Exception as e:
                print(f"Error retrieving weather data: {e}")
                continue

            if weather_data_count >= 10:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        print(f"Querying Gemini...")
                        gemini_response = ask_gemini_without_wildfire_data(api_key, weather)
                        break
                    except Exception as e:
                        print(f"Error querying Gemini: {e}")
                        time.sleep(5)
                else:
                    print("Failed after maximum retries.")
                    break

                print("=== Gemini Result ===")
                print(gemini_response)

                # TODO: Implement a parse_confidence function that returns a list of the ten confidence scores returned by Gemini for the ten weather stations
                # confidence_scores = parse_confidence(gemini_response)
                for i in range(len(weather_data)):
                    # confidence_score = confidence_scores[i]
                    pass

            count += weather_data_count
            print(f"{count}/500 completed.")
            weather_data_count = 0

def main():
    predict_wildfire_likelihood_in_batches()

if __name__ == "__main__":
    main()
