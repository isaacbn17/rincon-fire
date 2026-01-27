import { api } from "./client";

export async function requestSatelliteImage({ lat, lon, zoom = 8, format = "png" }) {
  const { data } = await api.post("/api/v1/satellite/image", {
    lat,
    lon,
    zoom,
    format,
    return_image: false,
  });
  return data;
}

export function satelliteImageUrl(filename) {
  const base = api.defaults.baseURL.replace(/\/$/, "");
  return `${base}/api/v1/satellite/image/${encodeURIComponent(filename)}`;
}
