import random

import pandas as pd
import os
from sklearn.model_selection import train_test_split

base_dir = os.getcwd()

fire_data = pd.read_csv(base_dir + '\\..\\data\\fire_weather_utah.csv')
non_fire_data = pd.read_csv(base_dir + '\\..\\data\\non_fire_weather_utah_unbalanced.csv')

non_fire_train, non_fire_test = train_test_split(non_fire_data, test_size=0.2, random_state=42)
fire_train, fire_test = train_test_split(fire_data, test_size=0.2, random_state=42)

train_set = pd.concat([non_fire_train, fire_train])
test_set = pd.concat([non_fire_test, fire_test])
train_set = train_set.drop('id', axis = 1)
test_set = test_set.drop('id', axis = 1)
train_set = train_set.sample(frac=1)
test_set = test_set.sample(frac=1)

train_set.to_csv(base_dir + '\\..\\data\\train_set_unbalanced.csv', index_label='id')
test_set.to_csv(base_dir + '\\..\\data\\test_set_unbalanced.csv', index_label='id')