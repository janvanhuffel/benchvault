import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getExperimentTrash, restoreExperiments } from "../api";

export default function ExperimentTrash() {
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());

  const refresh = useCallback(() => getExperimentTrash().then(setExperiments), []);

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
    restoreExperiments([...selected])
      .then(() => {
        setSelected(new Set());
        return refresh();
      })
      .catch((err) => alert(`Restore failed: ${err.message}`));
  };

  if (loading) return <p className="empty-state">Loading trash...</p>;

  return (
    <div className="page">
      <div className="page-header">
        <h2>
          <Link to="/experiments" className="back-link">Experiments</Link>
          {" "}&rsaquo; Trash
        </h2>
      </div>

      <p className="text-muted trash-info">
        Deleted experiments are kept for 7 days before being permanently removed.
      </p>

      {experiments.length > 0 && (
        <div className="filters">
          <button onClick={handleRestore} disabled={selected.size < 1}>
            Restore Selected ({selected.size})
          </button>
        </div>
      )}

      {experiments.length === 0 ? (
        <p className="empty-state">Trash is empty.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Name</th>
              <th>Project</th>
              <th>Description</th>
              <th>Status</th>
              <th>Runs</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {experiments.map((exp) => (
              <tr key={exp.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.has(exp.id)}
                    onChange={() => toggle(exp.id)}
                  />
                </td>
                <td>{exp.name}</td>
                <td>{exp.project_name}</td>
                <td>{exp.description || "\u2014"}</td>
                <td>
                  <span className={`status-badge status-${exp.status}`}>
                    {exp.status === "active" ? "Active" : "Concluded"}
                  </span>
                </td>
                <td>{exp.run_count}</td>
                <td>{new Date(exp.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
