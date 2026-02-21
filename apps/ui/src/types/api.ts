export type ModelInfo = {
  model_id: string
  name: string
  description: string
}

export type ModelsResponse = {
  models: ModelInfo[]
}

export type FireAreaTopItem = {
  area_id: string
  name: string
  lat: number
  lon: number
  predicted_at: string
  probability: number
  model_id: string
}

export type FireAreasTopResponse = {
  items: FireAreaTopItem[]
}

export type WeatherLatestResponse = {
  area_id: string
  observed_at: string
  temperature_c: number
  humidity_pct: number
  wind_speed_kph: number
  precipitation_mm: number
}

export type PredictionLatestResponse = {
  area_id: string
  model_id: string
  predicted_at: string
  probability: number
  label: number
}

export type SatelliteLatestResponse = {
  area_id: string
  captured_at: string
  filename: string
  file_path: string
  satellite_url: string
  content_type: string
}
