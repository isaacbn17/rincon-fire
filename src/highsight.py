import math
import requests
from io import BytesIO
from PIL import Image
from pathlib import Path


# CONFIGURATION

API_KEY = "oGVK5TFmsM9QdYArq8UiXZGgGsHXqTcw"

lat = 30.59480278
lon = -96.96620053
zoom = 4


def latlon_to_tile(lat_deg: float, lon_deg: float, z: int):
    """
    Convert latitude/longitude to XYZ tile coordinates at zoom z
    using Web Mercator (slippy map) formulas.
    """
    lat_rad = math.radians(lat_deg)
    n = 2 ** z
    x_tile = int((lon_deg + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x_tile, y_tile



def main():
    x, y = latlon_to_tile(lat, lon, zoom)
    print(f"Using z={zoom}, x={x}, y={y}")

    url = f"https://api.highsight.dev/v1/satellite/{zoom}/{x}/{y}?key={API_KEY}"
    print("Requesting URL:", url)

    response = requests.get(url)
    if response.status_code != 200:
        print("Error! Status code:", response.status_code)
        print("Response text:", response.text[:500])
        return

    try:
        img = Image.open(BytesIO(response.content))
    except Exception as e:
        print("Could not open image:", e)
        return

    img.show()

    project_root = Path(__file__).resolve().parent.parent
    output_dir = project_root / "outputs" / "highsight"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"highsight_tile_z{zoom}_x{x}_y{y}.png"
    img.save(output_path)

    print("Image saved as:", output_path)


if __name__ == "__main__":
    main()
