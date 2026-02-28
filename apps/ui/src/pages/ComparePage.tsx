import { keepPreviousData, useQuery } from "@tanstack/react-query"

import { CompareTable } from "@/components/CompareTable"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { getCompareFireAreas, getModels } from "@/lib/api"

export function ComparePage() {
  const modelsQuery = useQuery({
    queryKey: ["models"],
    queryFn: getModels,
    staleTime: 60_000,
  })

  const compareQuery = useQuery({
    queryKey: ["compare-fire-areas", 5],
    queryFn: () => getCompareFireAreas({ n: 5 }),
    refetchInterval: 10_000,
    placeholderData: keepPreviousData,
  })

  const models = compareQuery.data?.models ?? modelsQuery.data?.models ?? []
  const items = compareQuery.data?.items ?? []
  const showEmptyState = !compareQuery.isLoading && !compareQuery.error && items.length === 0

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 p-4 md:p-6">
      <header>
        <h2 className="text-2xl font-bold tracking-tight">Compare Models</h2>
        <p className="text-sm text-muted-foreground">
          Top 5 at-risk areas per model, compared across all model probabilities.
        </p>
      </header>

      {compareQuery.error ? (
        <Card className="border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <CardHeader>
            <CardTitle>Unable to Load Comparison Data</CardTitle>
            <CardDescription>{String(compareQuery.error)}</CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Cross-Model Risk Table</CardTitle>
          <CardDescription>{compareQuery.isFetching ? "Refreshing..." : "Latest sample"}</CardDescription>
        </CardHeader>
        <CardContent>
          {compareQuery.isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : showEmptyState ? (
            <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
              No ranked areas are available yet. The worker may still be ingesting weather data and predictions.
            </div>
          ) : (
            <CompareTable items={items} models={models} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
