import pandas as pd

UTAH_LAT_MIN, UTAH_LAT_MAX = 37.0, 42.0
UTAH_LON_MIN, UTAH_LON_MAX = -114.1, -109.0

fires = pd.read_csv("fires.csv")

fires_utah = fires[
    fires["attr_InitialLatitude"].between(UTAH_LAT_MIN, UTAH_LAT_MAX) &
    fires["attr_InitialLongitude"].between(UTAH_LON_MIN, UTAH_LON_MAX)
].copy()

print("Total fires:", len(fires))
print("Utah fires:", len(fires_utah))

fires_utah.to_csv("fires_utah.csv", index=False)
print("Saved fires_utah.csv")