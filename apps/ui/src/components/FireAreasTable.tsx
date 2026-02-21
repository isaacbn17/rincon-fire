import { Link } from "react-router-dom"

import { ProbabilityBadge } from "@/components/ProbabilityBadge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { FireAreaTopItem } from "@/types/api"

type FireAreasTableProps = {
  items: FireAreaTopItem[]
}

export function FireAreasTable({ items }: FireAreasTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Area</TableHead>
          <TableHead>Location</TableHead>
          <TableHead>Predicted At (UTC)</TableHead>
          <TableHead>Probability</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => (
          <TableRow key={item.area_id} className="transition-colors duration-500">
            <TableCell>
              <Link className="font-medium underline-offset-4 hover:underline" to={`/areas/${item.area_id}`}>
                {item.name}
              </Link>
            </TableCell>
            <TableCell>{item.lat.toFixed(4)}, {item.lon.toFixed(4)}</TableCell>
            <TableCell>{new Date(item.predicted_at).toISOString()}</TableCell>
            <TableCell>
              <ProbabilityBadge probability={item.probability} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
