import requests

def request_weather(latitude, longitude, time_period='daily'):
    points_url = f"https://api.weather.gov/points/{latitude},{longitude}"
    headers = {'User-Agent': 'RinconFire/1.0'} # Required User-Agent
    response = requests.get(points_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        forecast_url = data['properties']['forecast']
        if time_period == 'hourly':
            forecast_url = data['properties']['forecastHourly']

        forecast_response = requests.get(forecast_url, headers=headers)

        if forecast_response.status_code == 200:
            forecast_data = forecast_response.json()
            return forecast_data

        else:
            print(f"Error fetching forecast: {forecast_response.status_code}")
    else:
        print(f"Error fetching points data: {response.status_code}")

    return None