import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.path import Path as MplPath
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter


# Approximate Utah border in lon/lat.
# This removes the northeast rectangle above 41°N and east of ~111.05°W.
UTAH_POLYGON = np.array([
    [-114.05, 37.00],  # SW
    [-109.04, 37.00],  # SE
    [-109.04, 41.00],  # east border up to Wyoming line
    [-111.05, 41.00],  # top-right cutout corner
    [-111.05, 42.00],  # continue north
    [-114.05, 42.00],  # NW
])

UTAH_LON_MIN = -114.05
UTAH_LON_MAX = -109.04
UTAH_LAT_MIN = 37.00
UTAH_LAT_MAX = 42.00


def build_blue_red_cmap():
    return LinearSegmentedColormap.from_list(
        "blue_red_fire",
        ["#08306b", "#2171b5", "#6baed6", "#fcbba1", "#fb6a4a", "#cb181d", "#67000d"],
        N=256,
    )


def mask_to_utah(grid_lon, grid_lat):
    path = MplPath(UTAH_POLYGON)
    pts = np.column_stack([grid_lon.ravel(), grid_lat.ravel()])
    inside = path.contains_points(pts).reshape(grid_lon.shape)
    return inside


def plot_fire_heatmap(csv_path, output_path=None, grid_size=500, sigma=4.0, method="linear"):
    df = pd.read_csv(csv_path)

    required_cols = {"latitude", "longitude", "fire_probability"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    df = df.dropna(subset=["latitude", "longitude", "fire_probability"]).copy()

    lat = df["latitude"].to_numpy()
    lon = df["longitude"].to_numpy()
    fire_prob = df["fire_probability"].to_numpy()

    grid_lon, grid_lat = np.mgrid[
        UTAH_LON_MIN:UTAH_LON_MAX:complex(grid_size),
        UTAH_LAT_MIN:UTAH_LAT_MAX:complex(grid_size),
    ]

    grid_fire = griddata(
        points=(lon, lat),
        values=fire_prob,
        xi=(grid_lon, grid_lat),
        method=method,
    )

    # Fill outside-convex-hull gaps first.
    grid_fire_nearest = griddata(
        points=(lon, lat),
        values=fire_prob,
        xi=(grid_lon, grid_lat),
        method="nearest",
    )
    grid_fire = np.where(np.isnan(grid_fire), grid_fire_nearest, grid_fire)

    # Smooth to remove triangular interpolation artifacts.
    grid_fire = gaussian_filter(grid_fire, sigma=sigma)

    # Mask everything outside Utah so the NE corner becomes white.
    inside_utah = mask_to_utah(grid_lon, grid_lat)
    masked_fire = np.ma.array(grid_fire, mask=~inside_utah)

    cmap = build_blue_red_cmap()
    cmap.set_bad(color="white")

    plt.figure(figsize=(9, 9))
    heatmap = plt.pcolormesh(
        grid_lon,
        grid_lat,
        masked_fire,
        shading="auto",
        cmap=cmap,
    )
    plt.colorbar(heatmap, label="Fire Probability")

    plt.scatter(
        lon,
        lat,
        s=12,
        edgecolors="black",
        linewidths=0.3,
    )

    # Draw border for clarity
    border = np.vstack([UTAH_POLYGON, UTAH_POLYGON[0]])
    plt.plot(border[:, 0], border[:, 1], linewidth=1.0)

    plt.xlim(UTAH_LON_MIN, UTAH_LON_MAX)
    plt.ylim(UTAH_LAT_MIN, UTAH_LAT_MAX)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Utah Wildfire Prediction Heat Map")
    plt.tight_layout()

    if output_path:
        output_path = Path(output_path)
        plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"Saved heat map to: {output_path}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Generate a smoothed Utah wildfire heat map.")
    parser.add_argument("csv_path", help="Path to prediction CSV")
    parser.add_argument("--output", "-o", help="Optional output image path")
    parser.add_argument("--grid-size", type=int, default=500, help="Interpolation grid resolution")
    parser.add_argument("--sigma", type=float, default=4.0, help="Gaussian smoothing strength")
    parser.add_argument(
        "--method",
        choices=["linear", "nearest", "cubic"],
        default="linear",
        help="Interpolation method before smoothing",
    )
    args = parser.parse_args()

    plot_fire_heatmap(
        csv_path=args.csv_path,
        output_path=args.output,
        grid_size=args.grid_size,
        sigma=args.sigma,
        method=args.method,
    )


if __name__ == "__main__":
    main()
