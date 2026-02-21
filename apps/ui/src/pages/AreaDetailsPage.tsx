import { useEffect } from "react"
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { Link, useParams, useSearchParams } from "react-router-dom"

import { ProbabilityBadge } from "@/components/ProbabilityBadge"
import { ModelSelector } from "@/components/ModelSelector"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { getLatestPrediction, getLatestSatellite, getLatestWeather, getModels } from "@/lib/api"

export function AreaDetailsPage() {
  const { areaId = "" } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedModelId = searchParams.get("model") ?? ""

  const modelsQuery = useQuery({
    queryKey: ["models"],
    queryFn: getModels,
    staleTime: 60_000,
  })

  useEffect(() => {
    const firstModel = modelsQuery.data?.models[0]
    if (!selectedModelId && firstModel) {
      setSearchParams({ model: firstModel.model_id }, { replace: true })
    }
  }, [modelsQuery.data, selectedModelId, setSearchParams])

  const weatherQuery = useQuery({
    queryKey: ["area-weather", areaId],
    queryFn: () => getLatestWeather(areaId),
    enabled: Boolean(areaId),
    refetchInterval: 10_000,
    placeholderData: keepPreviousData,
  })

  const predictionQuery = useQuery({
    queryKey: ["area-prediction", areaId, selectedModelId],
    queryFn: () => getLatestPrediction(areaId, selectedModelId),
    enabled: Boolean(areaId && selectedModelId),
    refetchInterval: 10_000,
    placeholderData: keepPreviousData,
  })

  const satelliteQuery = useQuery({
    queryKey: ["area-satellite", areaId],
    queryFn: () => getLatestSatellite(areaId),
    enabled: Boolean(areaId),
    refetchInterval: 10_000,
    placeholderData: keepPreviousData,
  })

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 p-4 md:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Area Details</h1>
          <p className="text-sm text-muted-foreground">Area ID: {areaId}</p>
        </div>
        <Link to="/" className="text-sm underline">
          Back to dashboard
        </Link>
      </div>

      <div className="max-w-sm">
        {modelsQuery.isLoading ? (
          <Skeleton className="h-10 w-full" />
        ) : (
          <ModelSelector
            models={modelsQuery.data?.models ?? []}
            selectedModelId={selectedModelId}
            onChange={(modelId) => setSearchParams({ model: modelId }, { replace: true })}
          />
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Latest Weather</CardTitle>
            <CardDescription>Refreshed every 10s</CardDescription>
          </CardHeader>
          <CardContent>
            {weatherQuery.isLoading && !weatherQuery.data ? (
              <Skeleton className="h-24 w-full" />
            ) : weatherQuery.data ? (
              <div className="space-y-1 text-sm">
                <div>Temperature: {weatherQuery.data.temperature_c.toFixed(2)} C</div>
                <div>Humidity: {weatherQuery.data.humidity_pct.toFixed(2)}%</div>
                <div>Wind Speed: {weatherQuery.data.wind_speed_kph.toFixed(2)} kph</div>
                <div>Precipitation: {weatherQuery.data.precipitation_mm.toFixed(2)} mm</div>
                <div>Observed At: {new Date(weatherQuery.data.observed_at).toISOString()}</div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">No weather data available.</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Latest Prediction</CardTitle>
            <CardDescription>Model-specific output</CardDescription>
          </CardHeader>
          <CardContent>
            {predictionQuery.isLoading && !predictionQuery.data ? (
              <Skeleton className="h-24 w-full" />
            ) : predictionQuery.data ? (
              <div className="space-y-2 text-sm">
                <div>
                  Probability: <ProbabilityBadge probability={predictionQuery.data.probability} />
                </div>
                <div>Label: {predictionQuery.data.label === 1 ? "Fire Risk" : "No Fire Risk"}</div>
                <div>Predicted At: {new Date(predictionQuery.data.predicted_at).toISOString()}</div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">No prediction data available.</div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Latest Satellite Image</CardTitle>
          <CardDescription>Stored file served by API</CardDescription>
        </CardHeader>
        <CardContent>
          {satelliteQuery.isLoading && !satelliteQuery.data ? (
            <Skeleton className="h-80 w-full" />
          ) : satelliteQuery.data ? (
            <div className="space-y-3">
              <img
                src={satelliteQuery.data.satellite_url}
                alt={`Satellite for ${areaId}`}
                className="h-auto w-full rounded-lg border"
              />
              <div className="text-xs text-muted-foreground">
                {satelliteQuery.data.filename} · {new Date(satelliteQuery.data.captured_at).toISOString()}
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">No satellite image available.</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
