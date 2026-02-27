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
    plt.scatter(longitudes, latitudes)

    # Label axes
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Weather Station Locations")

    # Improve readability
    plt.grid(True)

    plt.show()


plot_weather_stations("weather_stations_utah_valid.csv")