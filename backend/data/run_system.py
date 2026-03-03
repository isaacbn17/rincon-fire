import time
from pathlib import Path
from datetime import datetime, timezone

from models.XG_boost import WildfireXGBoostModel
from satellite_images.satellite_images import SatelliteManager

if __name__ == "__main__":
    # 1. Initialize and Load Model
    model = WildfireXGBoostModel()
    model.load("models/unbalanced_xgb_model.joblib")

    # 2. Run Predictions
    print("Starting prediction pipeline...")
    start = time.perf_counter()
    prediction_file = model.predict()
    end = time.perf_counter()
    print(f"Prediction execution time: {end - start:.6f} seconds\n")

    # 3. Download Satellite Images for Top Probabilities
    if prediction_file:
        # Create a folder name based on the current date: yyyy-mm-dd
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        image_folder = Path(f"satellite_images/{current_date}")
        
        print(f"Fetching satellite imagery from predictions in: {prediction_file}")
        
        manager = SatelliteManager(
            input_filepath=prediction_file,
            output_dir=image_folder,
            zoom=8,
            fmt='png'
        )
        
        manager.run(number_of_images=4)
    else:
        print("Prediction failed to return a valid file path.")
