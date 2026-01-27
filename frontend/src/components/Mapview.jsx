import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import "../styles/map.css";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const UTAH_CENTER = [39.3, -111.7];

export default function MapView({ stations, onSelect }) {
  return (
    <MapContainer center={UTAH_CENTER} zoom={7} className="map">
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {stations.map((s) => (
        <Marker
          key={s.id}
          position={[s.lat, s.lng]}
          eventHandlers={{ click: () => onSelect(s.id) }}
        >
          <Popup>
            <b>{s.name}</b>
            <br />
            {s.lat}, {s.lng}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}