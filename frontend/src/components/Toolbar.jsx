export default function Toolbar({ onGetPredictions, onGetSatellite }) {
  return (
    <div className="toolbar">
      <button className="btn" onClick={onGetPredictions}>
        Get Predictions
      </button>
      <button className="btn" onClick={onGetSatellite}>
        Get Satellite Images
      </button>
    </div>
  );
}