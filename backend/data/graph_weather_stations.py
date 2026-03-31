import pandas as pd
import matplotlib.pyplot as plt

def plot_weather_stations(csv_path):
    # Load CSV
    df = pd.read_csv(csv_path)

    # Ensure required columns exist
    required_cols = {"latitude", "longitude"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required_cols}")

    # Extract coordinates
    latitudes = df["latitude"]
    longitudes = df["longitude"]

    # Plot
    plt.figure()
    plt.scatter(longitudes, latitudes, s=5)

    # Label axes
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Filtered Weather Station Locations")

    # Improve readability
    plt.grid(True)

    plt.show()


# plot_weather_stations("updated_utah_valid_weather_stations.csv")
plot_weather_stations("utah_weather_stations_filtered_12km.csv")