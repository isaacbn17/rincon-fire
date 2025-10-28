from pprint import pprint
from api_helpers import request_weather

if __name__ == "__main__":
    # Example: near (39.7456, -97.0892)
    lat, lon = 39.7456, -97.0892
    weather_data = request_weather(lat, lon)
    if weather_data is None:
        print("No weather data returned.")
    else:
        pprint(weather_data)
