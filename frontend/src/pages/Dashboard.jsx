import { useEffect, useMemo, useState } from "react";
import { fetchWeatherPredictions } from "../api/predictions";
import { requestSatelliteImage, satelliteImageUrl } from "../api/satellite";

import MapView from "../components/MapView";
import StationTable from "../components/StationTable";
import StationDetails from "../components/StationDetails";
import Toolbar from "../components/Toolbar";

import "../styles/app.css";

export default function Dashboard() {
  const [stations, setStations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);

  const [predictionsById, setPredictionsById] = useState({});
  const [satelliteById, setSatelliteById] = useState({});
  const [errorMsg, setErrorMsg] = useState("");

  const selectedStation = useMemo(
    () => stations.find((s) => s.id === selectedId) || null,
    [stations, selectedId]
  );

  // Auto-load predictions on first load (optional, but convenient)
  useEffect(() => {
    getPredictions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function getPredictions() {
    try {
      setErrorMsg("");

      const data = await fetchWeatherPredictions(25);

      // IMPORTANT:
      // Backend must include lat/lon (or latitude/longitude). If missing, stations will be filtered out.
      const stationsFromApi = (data.results || [])
        .map((r, idx) => ({
          id: r.station || `station-${idx}`,
          name: r.station || `Station ${idx + 1}`,
          lat: r.lat ?? r.latitude,
          lng: r.lon ?? r.longitude,
          weather: r.weather,
          prediction: r.prediction,
        }))
        .filter((s) => Number.isFinite(s.lat) && Number.isFinite(s.lng));

      setStations(stationsFromApi);
      if (stationsFromApi.length) setSelectedId(stationsFromApi[0].id);

      // Cache predictions for table/details
      const preds = {};
      for (const s of stationsFromApi) preds[s.id] = s.prediction;
      setPredictionsById(preds);

      // If backend didn't provide coords, help you notice immediately
      if ((data.results || []).length > 0 && stationsFromApi.length === 0) {
        setErrorMsg(
          "Predictions loaded, but no stations had coordinates. Ensure /api/v1/predict/weather returns lat/lon (or latitude/longitude) for each result."
        );
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(
        err?.response?.data?.error ||
          err?.message ||
          "Failed to load predictions."
      );
    }
  }

  async function getSatellite() {
    try {
      setErrorMsg("");

      const station = selectedStation;
      if (!station) return;

      const resp = await requestSatelliteImage({
        lat: station.lat,
        lon: station.lng,
        zoom: 10,
        format: "png",
      });

      const url = satelliteImageUrl(resp.filename);

      setSatelliteById((prev) => ({
        ...prev,
        [station.id]: [{ url, timestamp: new Date().toISOString() }],
      }));
    } catch (err) {
      console.error(err);
      setErrorMsg(
        err?.response?.data?.error ||
          err?.message ||
          "Failed to get satellite image."
      );
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="title">Utah Fire Risk Dashboard</div>
        <Toolbar onGetPredictions={getPredictions} onGetSatellite={getSatellite} />
      </header>

      {errorMsg ? (
        <div style={{ padding: "8px 12px", color: "#b00020" }}>{errorMsg}</div>
      ) : null}

      <main className="grid">
        <div className="mapPanel">
          <MapView
            stations={stations}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>

        <div className="detailsPanel">
          <StationDetails
            station={selectedStation}
            predictions={selectedId ? predictionsById[selectedId] : null}
            satellite={selectedId ? satelliteById[selectedId] : null}
          />
        </div>

        <div className="tablePanel">
          <StationTable
            stations={stations}
            selectedId={selectedId}
            onSelect={setSelectedId}
            predictionsById={predictionsById}
            satelliteById={satelliteById}
          />
        </div>
      </main>
    </div>
  );
}