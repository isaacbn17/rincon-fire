import { api } from "./client";

export async function fetchStations() {
  const { data } = await api.get("/stations");
  return data;
}