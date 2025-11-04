from meteostat import Point, Hourly
import pandas as pd
from datetime import datetime
import os

base_dir = os.getcwd()

fire_data = pd.read_csv(base_dir + '\\..\\data\\fires.csv')

count = 0

augmented_data = []

for i, row in fire_data.iterrows():
    object_id = row['OBJECTID']

    date, time = row['attr_FireDiscoveryDateTime'].split(" ")
    date = date.split("/")

    time = time.split(":")
    hour = int(time[0])


    # label to make more readable
    month = int(date[0])
    day = int(date[1])
    year = int(date[2])

    lat = float(row['attr_InitialLatitude'])
    long = float(row['attr_InitialLongitude'])

    fire_date = datetime(year, month, day, hour)
    fire_loc = Point(lat, long)

    weather = Hourly(fire_loc, fire_date, fire_date)
    weather_data = weather.fetch()

    previous_year_date = datetime(year - 1, month, day, hour)
    weather2 = Hourly(fire_loc, previous_year_date, previous_year_date)
    weather_data_2 = weather2.fetch()

    if not weather_data.empty and not weather_data_2.empty:
        augmented_row = pd.concat([fire_data.iloc[i], weather_data.iloc[0]], ignore_index=True)
        augmented_row = pd.concat([augmented_row, pd.Series([1])])
        augmented_data.append(augmented_row.to_numpy())

        previous_year_row = fire_data.iloc[i].copy()
        previous_year_row['attr_FireDiscoveryDateTime'] = date[0] + "/" + date[1] + "/" + str(year - 1) + " " + str(time[0]) + ":" + str(time[1])
        augmented_row_2 = pd.concat([previous_year_row, weather_data_2.iloc[0]], ignore_index=True)
        augmented_row_2 = pd.concat([augmented_row_2, pd.Series([0])])
        augmented_data.append(augmented_row_2.to_numpy())
        count += 1
        print(count)
    if count >= 500:
        break

# temp,dwpt,rhum,prcp,snow,wdir,wspd,wpgt,pres,tsun,coco,hasFire
cols = ['object_id', 'date_time', 'latitude', 'longitude', 'temperature', 'dewpoint', 'relative_humidity', 'precipitation', 'snow', 'wind_direction', 'wind_speed', 'wind_gust', 'air_pressure', 'sunshine', 'weather_code', 'fire']

augmented_data_df = pd.DataFrame(augmented_data, columns=cols)
augmented_data_df = augmented_data_df.drop('object_id', axis=1)

augmented_data_df.to_csv(base_dir + '\\..\\data\\fires_augmented.csv',index_label='id')
