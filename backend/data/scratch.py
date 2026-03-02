import csv
from pathlib import Path

# Input and output file paths
input_path = Path("model_predictions/fire_predictions_2026-02-28.csv")  # <-- replace with your actual file name
output_path = Path("updated_utah_valid_weather_stations.csv")

with open(input_path, mode="r", newline="", encoding="utf-8") as infile, \
     open(output_path, mode="w", newline="", encoding="utf-8") as outfile:

    reader = csv.DictReader(infile)
    fieldnames = ["station_url", "latitude", "longitude"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)

    writer.writeheader()

    for row in reader:
        writer.writerow({
            "station_url": row["station_url"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
        })

print(f"New file written to: {output_path.resolve()}")