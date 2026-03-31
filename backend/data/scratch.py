import csv
from pathlib import Path
from  satellite_images import SatelliteManager

manager = SatelliteManager(
    input_filepath="../model_predictions/test.csv",
    # input_filepath="../model_predictions/fire_predictions_2026-02-28.csv",
    output_dir=Path("test"),
)
manager.run(number_of_images=1)