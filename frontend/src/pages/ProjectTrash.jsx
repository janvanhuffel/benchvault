import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getProjectTrash, restoreRuns } from "../api";

export default function ProjectTrash() {
  const { name } = useParams();
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());

  const refresh = useCallback(() => getProjectTrash(name).then(setRuns), [name]);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const toggle = (id) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  const handleRestore = () => {
    restoreRuns([...selected])
      .then(() => {
        setSelected(new Set());
        return refresh();
      })
      .catch((err) => alert(`Restore failed: ${err.message}`));
  };

  if (loading) return <p className="empty-state">Loading trash...</p>;

  return (
    <div>
      <div className="page-header">
        <h1>
          <Link to={`/projects/${encodeURIComponent(name)}`} className="back-link">
            {decodeURIComponent(name)}
          </Link>
          {" "}&rsaquo; Trash
        </h1>
      </div>

      <p className="text-muted trash-info">
        Deleted runs are kept for 7 days before being permanently removed.
      </p>

      {runs.length > 0 && (
        <div className="filters">
          <button onClick={handleRestore} disabled={selected.size < 1}>
            Restore Selected ({selected.size})
          </button>
        </div>
      )}

      {runs.length === 0 ? (
        <p className="empty-state">Trash is empty.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Model</th>
              <th>Model Version</th>
              <th>Dataset</th>
              <th>Dataset Version</th>
              <th>Epoch</th>
              <th>Date</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.has(run.id)}
                    onChange={() => toggle(run.id)}
                  />
                </td>
                <td>{run.model_name}</td>
                <td>{run.model_version}</td>
                <td>{run.dataset}</td>
                <td>{run.dataset_version}</td>
                <td>{run.epoch ?? "\u2014"}</td>
                <td>{new Date(run.created_at).toLocaleDateString()}</td>
                <td>{run.note || "\u2014"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
