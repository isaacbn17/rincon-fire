import { api } from "./client";

export async function fetchWeatherPredictions(nStations = 25) {
  const { data } = await api.post("/api/v1/predict/weather", {
    n_stations: nStations,
  });
  return data;
}
