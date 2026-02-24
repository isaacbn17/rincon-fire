import random
from urllib.error import URLError

from meteostat import Point, Hourly
import pandas as pd
from datetime import datetime, timedelta
import os
import random

# for n times (1000 probably)
# pick random station in utah
# pick random time 2020-present
# get and store data


base_dir = os.getcwd()

stations = pd.read_csv(base_dir + '\\weather_stations_utah_valid.csv')


augmented_data = []
n_stations = len(stations)
n_rows = 100000

i = 0
while i < n_rows:
    try:
        # label to make more readable
        station_idx = random.randint(0, n_stations - 1)
        s = stations.iloc[station_idx]
        lat = float(s['latitude'])
        long = float(s['longitude'])

        # Retrieve week-long fire data
        fire_date = datetime(2020, 1, 1, 0)
        # up until roughly 2 weeks ago
        hour = random.randint(1, 23)
        fire_date += timedelta(days=random.randint(0, 2230), hours=hour)

        fire_week_before_date = fire_date - timedelta(days=6)
        fire_loc = Point(lat, long)

        weather = Hourly(fire_loc, fire_week_before_date, fire_date)
        weather_data = weather.fetch()
        weather_data = pd.DataFrame(weather_data)

        # If data is retrieved, filter for same hour every day of the past week
        if not weather_data.empty:
            daily_data = weather_data.loc[weather_data.index.hour == hour]

            daily_data = daily_data.reset_index()
            augmented_row = pd.Series([fire_date])
            daily_data = daily_data.drop('coco', axis = 1)
            daily_data = daily_data.drop('time', axis = 1)
            daily_data = daily_data.drop('tsun', axis = 1)
            for index, daily_row in daily_data.iterrows():
                augmented_row = pd.concat([augmented_row, daily_data.iloc[index]])
            augmented_row = pd.concat([augmented_row, pd.Series([0])])
            augmented_data.append(augmented_row.to_numpy())

            i += 1
            print(i)
    except URLError as e:
        print(e)
        break


# temp,dwpt,rhum,prcp,snow,wdir,wspd,wpgt,pres,tsun,coco,hasFire
cols = ['temperature', 'dewpoint', 'relative_humidity', 'precipitation', 'snow', 'wind_direction', 'wind_speed', 'wind_gust', 'air_pressure']

final_cols = ['date_time']
for i in range(1, 8):
    for col in cols:
        final_cols.append(col + '_' + str(i))
final_cols.append('has_fire')

augmented_data_df = pd.DataFrame(augmented_data, columns=final_cols)

augmented_data_df.to_csv(base_dir + '\\..\\data\\non_fire_weather_utah_unbalanced.csv', index_label='id')
