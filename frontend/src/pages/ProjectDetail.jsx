import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getProjectRuns, deleteRuns, getExperiments, addRunsToExperiment } from "../api";

export default function ProjectDetail() {
  const { name } = useParams();
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());
  const [filters, setFilters] = useState({
    dataset: "",
    datasetVersion: "",
    modelName: "",
    modelVersion: "",
  });
  const [sortBy, setSortBy] = useState(null);
  const [sortDir, setSortDir] = useState("desc");
  const [experiments, setExperiments] = useState([]);
  const [showExpDropdown, setShowExpDropdown] = useState(false);

  const refresh = useCallback(() => getProjectRuns(name).then(setRuns), [name]);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  // Client-side filtering
  const filtered = runs.filter((r) => {
    if (filters.dataset && r.dataset !== filters.dataset) return false;
    if (filters.datasetVersion && r.dataset_version !== filters.datasetVersion) return false;
    if (filters.modelName && r.model_name !== filters.modelName) return false;
    if (filters.modelVersion && r.model_version !== filters.modelVersion) return false;
    return true;
  });

  // Extract unique values for filter dropdowns
  const unique = (key) => [...new Set(runs.map((r) => r[key]))].sort();

  // Extract all metric names across all runs
  const metricNames = [...new Set(runs.flatMap((r) => r.metrics.map((m) => m.metric_name)))].sort();

  // Toggle selection
  const toggle = (id) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  // Get metric value for a run
  const getMetric = (run, metricName) => {
    const m = run.metrics.find((metric) => metric.metric_name === metricName);
    return m ? m.value.toFixed(4) : "\u2014";
  };

  const getMetricRaw = (run, metricName) => {
    const m = run.metrics.find((metric) => metric.metric_name === metricName);
    return m ? m.value : null;
  };

  const handleSort = (col) => {
    if (sortBy === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(col);
      setSortDir("desc");
    }
  };

  const sortIndicator = (col) => {
    if (sortBy !== col) return "";
    return sortDir === "asc" ? " \u2191" : " \u2193";
  };

  // Sort filtered runs
  const sorted = [...filtered].sort((a, b) => {
    if (!sortBy) return 0;
    let aVal, bVal;
    if (sortBy === "date") {
      aVal = new Date(a.created_at).getTime();
      bVal = new Date(b.created_at).getTime();
    } else {
      aVal = getMetricRaw(a, sortBy);
      bVal = getMetricRaw(b, sortBy);
    }
    if (aVal === null && bVal === null) return 0;
    if (aVal === null) return 1;
    if (bVal === null) return -1;
    return sortDir === "asc" ? aVal - bVal : bVal - aVal;
  });

  const handleCompare = () => {
    navigate(`/compare?run_ids=${[...selected].join(",")}`);
  };

  const handleDelete = () => {
    const count = selected.size;
    if (!window.confirm(`Are you sure you want to delete ${count} run${count !== 1 ? "s" : ""}? They can be restored from trash within 7 days.`)) {
      return;
    }
    deleteRuns([...selected])
      .then(() => {
        setSelected(new Set());
        return refresh();
      })
      .catch((err) => alert(`Delete failed: ${err.message}`));
  };

  const handleOpenExpDropdown = async () => {
    try {
      const exps = await getExperiments(name);
      setExperiments(exps.filter((e) => e.status === "active"));
      setShowExpDropdown(true);
    } catch (err) {
      alert(`Failed to load experiments: ${err.message}`);
    }
  };

  const handleAddToExperiment = async (experimentId) => {
    try {
      await addRunsToExperiment(experimentId, [...selected]);
      setShowExpDropdown(false);
      setSelected(new Set());
      refresh();
    } catch (err) {
      alert(`Failed to add runs: ${err.message}`);
    }
  };

  useEffect(() => {
    if (!showExpDropdown) return;
    const handleClick = () => setShowExpDropdown(false);
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [showExpDropdown]);

  if (loading) return <p className="empty-state">Loading runs...</p>;

  return (
    <div>
      <h1>{decodeURIComponent(name)}</h1>

      <div className="filters">
        {/* Filter dropdowns */}
        <select value={filters.dataset} onChange={(e) => setFilters({...filters, dataset: e.target.value})}>
          <option value="">All datasets</option>
          {unique("dataset").map((v) => <option key={v}>{v}</option>)}
        </select>
        <select value={filters.datasetVersion} onChange={(e) => setFilters({...filters, datasetVersion: e.target.value})}>
          <option value="">All dataset versions</option>
          {unique("dataset_version").map((v) => <option key={v}>{v}</option>)}
        </select>
        <select value={filters.modelName} onChange={(e) => setFilters({...filters, modelName: e.target.value})}>
          <option value="">All models</option>
          {unique("model_name").map((v) => <option key={v}>{v}</option>)}
        </select>
        <select value={filters.modelVersion} onChange={(e) => setFilters({...filters, modelVersion: e.target.value})}>
          <option value="">All model versions</option>
          {unique("model_version").map((v) => <option key={v}>{v}</option>)}
        </select>

        <button onClick={handleCompare} disabled={selected.size < 2}>
          Compare Selected ({selected.size})
        </button>
        <button className="btn-danger" onClick={handleDelete} disabled={selected.size < 1}>
          Delete Selected ({selected.size})
        </button>
        {selected.size > 0 && (
          <div style={{ position: "relative", display: "inline-block" }}>
            <button className="btn" onClick={(e) => { e.stopPropagation(); handleOpenExpDropdown(); }}>
              Add to Experiment &#9662;
            </button>
            {showExpDropdown && (
              <div className="dropdown-menu">
                {experiments.length === 0 ? (
                  <div className="dropdown-item disabled">No active experiments</div>
                ) : (
                  experiments.map((exp) => (
                    <div
                      key={exp.id}
                      className="dropdown-item"
                      onClick={() => handleAddToExperiment(exp.id)}
                    >
                      {exp.name}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}
        <Link to={`/projects/${encodeURIComponent(name)}/trash`} className="trash-link">
          Trash
        </Link>
      </div>

      <table>
        <thead>
          <tr>
            <th></th>
            <th>Model</th>
            <th>Model Version</th>
            <th>Dataset</th>
            <th>Dataset Version</th>
            <th>Epoch</th>
            {metricNames.map((m) => <th key={m} className="sortable metric-value" onClick={() => handleSort(m)}>{m}{sortIndicator(m)}</th>)}
            <th className="sortable" onClick={() => handleSort("date")}>Date{sortIndicator("date")}</th>
            <th>Note</th>
            <th>Experiments</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((run) => (
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
              {metricNames.map((m) => <td key={m} className="metric-value">{getMetric(run, m)}</td>)}
              <td>{new Date(run.created_at).toLocaleDateString()}</td>
              <td>{run.note || "\u2014"}</td>
              <td className="tag-list-cell">
                {run.experiments && run.experiments.length > 0 ? (
                  <div className="tag-list">
                    {run.experiments.map((exp) => (
                      <Link key={exp.id} to={`/experiments/${exp.id}`} className="experiment-tag">
                        {exp.name}
                      </Link>
                    ))}
                  </div>
                ) : (
                  <span className="text-muted">{"\u2014"}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {filtered.length === 0 && <p className="empty-state">No runs match the current filters.</p>}
    </div>
  );
}
