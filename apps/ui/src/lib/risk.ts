export function probabilityColor(probability: number): string {
  if (probability >= 0.8) return "#b91c1c"
  if (probability >= 0.6) return "#ea580c"
  if (probability >= 0.4) return "#f59e0b"
  if (probability >= 0.2) return "#65a30d"
  return "#15803d"
}

export function probabilityLabel(probability: number): string {
  if (probability >= 0.8) return "Critical"
  if (probability >= 0.6) return "High"
  if (probability >= 0.4) return "Moderate"
  if (probability >= 0.2) return "Low"
  return "Very Low"
}
