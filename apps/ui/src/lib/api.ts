import type {
  FireAreasTopResponse,
  ModelsResponse,
  PredictionLatestResponse,
  SatelliteLatestResponse,
  WeatherLatestResponse,
} from "@/types/api"

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000"

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed with ${response.status}`)
  }
  return (await response.json()) as T
}

export function getModels() {
  return apiGet<ModelsResponse>("/api/v1/models")
}

export function getTopFireAreas(params: { n?: number; modelId?: string }) {
  const n = params.n ?? 5
  const query = new URLSearchParams({ n: String(n) })
  if (params.modelId) {
    query.set("model_id", params.modelId)
  }
  return apiGet<FireAreasTopResponse>(`/api/v1/fire-areas/top?${query.toString()}`)
}

export function getLatestWeather(areaId: string) {
  return apiGet<WeatherLatestResponse>(`/api/v1/areas/${encodeURIComponent(areaId)}/weather/latest`)
}

export function getLatestPrediction(areaId: string, modelId?: string) {
  const query = new URLSearchParams()
  if (modelId) {
    query.set("model_id", modelId)
  }
  return apiGet<PredictionLatestResponse>(
    `/api/v1/areas/${encodeURIComponent(areaId)}/predictions/latest${query.toString() ? `?${query.toString()}` : ""}`,
  )
}

export function getLatestSatellite(areaId: string) {
  return apiGet<SatelliteLatestResponse>(`/api/v1/areas/${encodeURIComponent(areaId)}/satellite/latest`)
}
