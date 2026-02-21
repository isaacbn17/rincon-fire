import "leaflet/dist/leaflet.css"

import { useEffect } from "react"
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet"

import { probabilityColor } from "@/lib/risk"
import type { FireAreaTopItem } from "@/types/api"

function FitBounds({ items }: { items: FireAreaTopItem[] }) {
  const map = useMap()

  useEffect(() => {
    if (items.length === 0) {
      return
    }

    const bounds = items.map((item) => [item.lat, item.lon] as [number, number])
    map.fitBounds(bounds, { padding: [25, 25], animate: true, duration: 0.75 })
  }, [items, map])

  return null
}

export function FireRiskMap({ items }: { items: FireAreaTopItem[] }) {
  return (
    <MapContainer center={[39.5, -98.35]} zoom={4} className="h-[460px] w-full rounded-lg">
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FitBounds items={items} />
      {items.map((item) => {
        const color = probabilityColor(item.probability)
        return (
          <CircleMarker
            key={item.area_id}
            center={[item.lat, item.lon]}
            pathOptions={{ color, fillColor: color, fillOpacity: 0.75 }}
            radius={7 + item.probability * 8}
          >
            <Popup>
              <div className="text-sm">
                <div className="font-semibold">{item.name}</div>
                <div>{(item.probability * 100).toFixed(1)}% fire probability</div>
              </div>
            </Popup>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
