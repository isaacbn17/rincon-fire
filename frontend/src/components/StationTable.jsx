import "../styles/table.css";

export default function StationTable({
  stations,
  selectedId,
  onSelect,
  predictionsById,
  satelliteById,
}) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Location</th>
          <th>Predictions</th>
          <th>Satellite</th>
        </tr>
      </thead>
      <tbody>
        {stations.map((s) => (
          <tr
            key={s.id}
            className={s.id === selectedId ? "selected" : ""}
            onClick={() => onSelect(s.id)}
          >
            <td>{s.name}</td>
            <td>
              {s.lat}, {s.lng}
            </td>
            <td>{predictionsById[s.id] ? "Yes" : "No"}</td>
            <td>{satelliteById[s.id] ? "Yes" : "No"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}