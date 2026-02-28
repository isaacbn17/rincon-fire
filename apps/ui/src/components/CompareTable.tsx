import { Link } from "react-router-dom"

import { ProbabilityBadge } from "@/components/ProbabilityBadge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { CompareAreaItem, ModelInfo } from "@/types/api"

type CompareTableProps = {
  models: ModelInfo[]
  items: CompareAreaItem[]
}

export function CompareTable({ models, items }: CompareTableProps) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Area</TableHead>
            <TableHead>Location</TableHead>
            {models.map((model) => (
              <TableHead key={model.model_id}>{model.name}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => {
            const predictionsByModel = new Map(item.predictions.map((prediction) => [prediction.model_id, prediction]))
            return (
              <TableRow key={item.area_id}>
                <TableCell>
                  <Link className="font-medium underline-offset-4 hover:underline" to={`/areas/${item.area_id}`}>
                    {item.name}
                  </Link>
                </TableCell>
                <TableCell>{item.lat.toFixed(4)}, {item.lon.toFixed(4)}</TableCell>
                {models.map((model) => {
                  const prediction = predictionsByModel.get(model.model_id)
                  return (
                    <TableCell key={`${item.area_id}-${model.model_id}`}>
                      {prediction?.probability == null ? (
                        <span className="text-sm text-muted-foreground">--</span>
                      ) : (
                        <ProbabilityBadge probability={prediction.probability} />
                      )}
                    </TableCell>
                  )
                })}
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
