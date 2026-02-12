from shapely.geometry import Point
import geopandas as gpd
import pandas as pd
import os

# Load once at module import
_state_polygons = {}

def _load_state_polygon(state_abbr: str):
    if state_abbr not in _state_polygons:
        url = "https://www2.census.gov/geo/tiger/TIGER2023/STATE/tl_2023_us_state.zip"
        states = gpd.read_file(url)
        state = states.loc[states["STUSPS"] == state_abbr]
        if state.empty:
            raise ValueError(f"Unknown state abbreviation: {state_abbr}")
        _state_polygons[state_abbr] = state.geometry.union_all()
    return _state_polygons[state_abbr]


def is_in_state(lat: float, lon: float, state_abbr: str) -> bool:
    """
    Returns True if the given latitude and longitude
    fall within the given state.
    """
    utah_polygon = _load_state_polygon(state_abbr)
    point = Point(lon, lat)  # shapely uses (lon, lat)
    return utah_polygon.covers(point)


if __name__ == "__main__":
    # Filter fires.csv in data directory to only include fires in Utah
    base_dir = os.getcwd()
    fire_data = pd.read_csv(base_dir + '\\..\\data\\fires.csv')
    state_abbr = "UT" # Change this to the desired state abbreviation
    fire_data['in_state'] = fire_data.apply(lambda row: is_in_state(row['attr_InitialLatitude'], row['attr_InitialLongitude'], state_abbr), axis=1)
    filtered_data = fire_data[fire_data['in_state']]
    filtered_data.to_csv(base_dir + '\\..\\data\\fires_utah.csv', index=False)
