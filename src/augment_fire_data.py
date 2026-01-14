from meteostat import Point, Hourly
import pandas as pd
from datetime import datetime, timedelta
import os

# for each fire date, lat and long
#   add fire_index to be able to associate each entry to the same fire
#   add day [1-7]
#   request data for date and time then loop through subtracting 1 from day (plan for potential month change or disregard)
#   request the same series of time 1 year earlier labeled as no fire


data_range = range(0, 1000)
base_dir = os.getcwd()

fire_data = pd.read_csv(base_dir + '\\..\\data\\fires.csv')

count = data_range[0]

augmented_data = []

for i, row in fire_data.iterrows():
    if int(i) > data_range[-1]:
        break
    if int(i) not in data_range:
        continue
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

    # Retrieve week-long fire data
    fire_date = datetime(year, month, day, hour)
    fire_week_before_date = fire_date - timedelta(days=6)
    fire_loc = Point(lat, long)

    weather = Hourly(fire_loc, fire_week_before_date, fire_date)
    weather_data = weather.fetch()
    weather_data = pd.DataFrame(weather_data)

    # If data is retrieved, filter for same hour every day of the past week
    if not weather_data.empty:
        daily_data = weather_data.loc[weather_data.index.hour == hour]
        previous_year_end_date = fire_date - timedelta(days=365)
        previous_year_start_date = fire_week_before_date - timedelta(days=365)
        previous_year_weather = Hourly(fire_loc, previous_year_start_date, previous_year_end_date)
        previous_year_weather_data = previous_year_weather.fetch()

        # If data for a year earlier is retrieved, filter for one entry per day at the same hour
        if not previous_year_weather_data.empty:
            previous_year_daily_data = previous_year_weather_data.loc[previous_year_weather_data.index.hour == hour]

            # make time a normal column rather than the index
            daily_data = daily_data.reset_index()
            for index, daily_row in daily_data.iterrows():
                augmented_row = pd.concat([pd.Series([object_id]), pd.Series([index + 1]), daily_data.iloc[index], pd.Series([1])])
                augmented_data.append(augmented_row.to_numpy())

            previous_year_daily_data = previous_year_daily_data.reset_index()
            for index, daily_row in previous_year_daily_data.iterrows():
                augmented_row = pd.concat([pd.Series([object_id]), pd.Series([index + 1]), previous_year_daily_data.iloc[index], pd.Series([0])])
                augmented_data.append(augmented_row.to_numpy())

            count += 1
            print(count)

# temp,dwpt,rhum,prcp,snow,wdir,wspd,wpgt,pres,tsun,coco,hasFire
cols = ['object_id', 'day', 'date_time', 'temperature', 'dewpoint', 'relative_humidity', 'precipitation', 'snow', 'wind_direction', 'wind_speed', 'wind_gust', 'air_pressure', 'sunshine', 'weather_code', 'fire']

augmented_data_df = pd.DataFrame(augmented_data, columns=cols)

augmented_data_df.to_csv(base_dir + '\\..\\data\\fires_week_long_1000.csv',index_label='id')
