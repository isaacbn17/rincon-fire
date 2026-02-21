import { Badge } from "@/components/ui/badge"
import { probabilityColor, probabilityLabel } from "@/lib/risk"

export function ProbabilityBadge({ probability }: { probability: number }) {
  const color = probabilityColor(probability)
  const label = probabilityLabel(probability)

  return (
    <Badge
      className="border-transparent text-white transition-colors"
      style={{ backgroundColor: color }}
      title={label}
    >
      {(probability * 100).toFixed(1)}%
    </Badge>
  )
}
