import { useEffect } from "react"
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { Link, useSearchParams } from "react-router-dom"

import { FireAreasTable } from "@/components/FireAreasTable"
import { FireRiskMap } from "@/components/FireRiskMap"
import { ModelSelector } from "@/components/ModelSelector"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { getModels, getTopFireAreas } from "@/lib/api"

export function DashboardPage() {
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

  const areasQuery = useQuery({
    queryKey: ["top-fire-areas", selectedModelId],
    queryFn: () => getTopFireAreas({ n: 5, modelId: selectedModelId }),
    enabled: Boolean(selectedModelId),
    refetchInterval: 10_000,
    placeholderData: keepPreviousData,
  })

  const items = areasQuery.data?.items ?? []
  const showEmptyState = Boolean(selectedModelId) && !areasQuery.isLoading && !areasQuery.error && items.length === 0

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 p-4 md:p-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Wildfire Risk Dashboard</h1>
          <p className="text-sm text-muted-foreground">Top 5 areas by predicted fire probability, refreshed every 10 seconds.</p>
        </div>
        {modelsQuery.isLoading ? (
          <Skeleton className="h-10 w-64" />
        ) : (
          <ModelSelector
            models={modelsQuery.data?.models ?? []}
            selectedModelId={selectedModelId}
            onChange={(modelId) => setSearchParams({ model: modelId }, { replace: true })}
          />
        )}
      </header>

      {areasQuery.error ? (
        <Card className="border-red-300 bg-white-100 dark:border-red-800 dark:bg-red-50">
          <CardHeader>
            <CardTitle>Unable to Load data for Fire Areas</CardTitle>
            <CardDescription>{String(areasQuery.error)}</CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Risk Map</CardTitle>
            <CardDescription>Marker color tracks model probability.</CardDescription>
          </CardHeader>
          <CardContent>
            {areasQuery.isLoading && items.length === 0 ? (
              <Skeleton className="h-[460px] w-full" />
            ) : showEmptyState ? (
              <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
                No predictions are available yet for the selected model. The worker may still be ingesting weather data.
              </div>
            ) : (
              <FireRiskMap items={items} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top 5 Areas</CardTitle>
            <CardDescription>
              {areasQuery.isFetching ? "Refreshing..." : "Latest sample"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {areasQuery.isLoading && items.length === 0 ? (
              <div className="space-y-3">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : showEmptyState ? (
              <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
                No ranked fire areas yet. Check worker logs for prediction generation and storage events.
              </div>
            ) : (
              <FireAreasTable items={items} />
            )}
            {items[0] ? (
              <div className="mt-4 text-sm text-muted-foreground">
                Quick view: <Link className="underline" to={`/areas/${items[0].area_id}?model=${selectedModelId}`}>open highest-risk area details</Link>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
