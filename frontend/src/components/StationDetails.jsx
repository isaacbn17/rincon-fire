export default function StationDetails({ station, predictions, satellite }) {
  if (!station) return <div>Select a station</div>;

  return (
    <div>
      <h2>{station.name}</h2>
      <p>
        {station.lat}, {station.lng}
      </p>

      <h3>Predictions</h3>
      {predictions ? (
        <pre>{JSON.stringify(predictions, null, 2)}</pre>
      ) : (
        <p>No predictions yet</p>
      )}

      <h3>Satellite Images</h3>
      {satellite ? (
        satellite.map((img, i) => (
          <img key={i} src={img.url} width="100%" />
        ))
      ) : (
        <p>No satellite images</p>
      )}
    </div>
  );
}