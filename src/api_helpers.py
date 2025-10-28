import requests
import time

# Structure for API requests
# Get stations method that returns list of station ids

def get_station_list():
    points_url = f"https://api.weather.gov/stations"
    headers = {'User-Agent': 'RinconFire/1.0'}  # Required User-Agent
    response = requests.get(points_url, headers=headers)

    station_list = []
    if response.status_code == 200:
        data = response.json()
        for station in data['features']:
            station_list.append(station['id'])
        return station_list
    else:
        print(f"Error fetching points data: {response.status_code}")

    return None

def request_observations(station_id):
    points_url = station_id + "/observations"
    headers = {'User-Agent': 'RinconFire/1.0'}  # Required User-Agent
    response = requests.get(points_url, headers=headers)

    if response.status_code == 200:
        station_observations = response.json()
        return station_observations

    return None

def get_all_station_observations(station_id_list):
    all_station_observations = dict()
    for station_id in station_id_list:
        observations = request_observations(station_id)
        if observations is not None:
            all_station_observations[station_id] = observations
        else:
            print('Limit exceeded, waiting 1 minute')
            time.sleep(60)
    return all_station_observations

print(get_all_station_observations(get_station_list()))