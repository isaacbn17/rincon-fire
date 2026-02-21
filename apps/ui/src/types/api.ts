export type ModelInfo = {
  model_id: string
  name: string
  description: string
}

export type ModelsResponse = {
  models: ModelInfo[]
}

export type StationListItem = {
  area_id: string
  name: string
  lat: number
  lon: number
  latest_observed_at: string | null
  latest_predicted_at: string | null
}

export type StationsResponse = {
  items: StationListItem[]
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
  temperature_c: number | null
  dewpoint_c: number | null
  relative_humidity_pct: number | null
  wind_direction_deg: number | null
  wind_speed_kph: number | null
  wind_gust_kph: number | null
  precipitation_3h_mm: number | null
  barometric_pressure_pa: number | null
  visibility_m: number | null
  heat_index_c: number | null
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
