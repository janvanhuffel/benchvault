import { useEffect, useState } from "react";
import { getProjects, getProjectRuns, getMetrics } from "../api";

export default function Leaderboard() {
  const [projects, setProjects] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);

  const [selectedProject, setSelectedProject] = useState("");
  const [selectedDataset, setSelectedDataset] = useState("");
  const [selectedDatasetVersion, setSelectedDatasetVersion] = useState("");
  const [selectedMetric, setSelectedMetric] = useState("");

  // Fetch projects and metrics on mount
  useEffect(() => {
    getProjects().then(setProjects);
    getMetrics().then(setMetrics);
  }, []);

  // Fetch runs when project changes
  useEffect(() => {
    if (!selectedProject) {
      setRuns([]);
      return;
    }
    setLoading(true);
    getProjectRuns(selectedProject)
      .then(setRuns)
      .finally(() => setLoading(false));
  }, [selectedProject]);

  // Derive filter options from runs
  const datasets = [...new Set(runs.map((r) => r.dataset))].sort();
  const datasetVersions = [
    ...new Set(
      runs
        .filter((r) => !selectedDataset || r.dataset === selectedDataset)
        .map((r) => r.dataset_version)
    ),
  ].sort();

  // Filter runs
  const filtered = runs.filter((r) => {
    if (selectedDataset && r.dataset !== selectedDataset) return false;
    if (selectedDatasetVersion && r.dataset_version !== selectedDatasetVersion)
      return false;
    return true;
  });

  // Get metric info
  const metricInfo = metrics.find((m) => m.name === selectedMetric);
  const higherIsBetter = metricInfo ? metricInfo.higher_is_better : true;

  // Build leaderboard: for each model+version, take the best metric value
  const seen = new Map();

  for (const run of filtered) {
    const m = run.metrics.find((metric) => metric.metric_name === selectedMetric);
    if (!m) continue;

    const key = `${run.model_name}|${run.model_version}`;
    const existing = seen.get(key);

    if (!existing) {
      seen.set(key, {
        modelName: run.model_name,
        modelVersion: run.model_version,
        value: m.value,
      });
    } else {
      if (higherIsBetter && m.value > existing.value) {
        existing.value = m.value;
      } else if (!higherIsBetter && m.value < existing.value) {
        existing.value = m.value;
      }
    }
  }

  const ranked = [...seen.values()].sort((a, b) =>
    higherIsBetter ? b.value - a.value : a.value - b.value
  );

  return (
    <div>
      <h1>Leaderboard</h1>

      <div className="filters">
        <select
          value={selectedProject}
          onChange={(e) => {
            setSelectedProject(e.target.value);
            setSelectedDataset("");
            setSelectedDatasetVersion("");
          }}
        >
          <option value="">Select project</option>
          {projects.map((p) => (
            <option key={p.id} value={p.name}>
              {p.name}
            </option>
          ))}
        </select>

        <select
          value={selectedDataset}
          onChange={(e) => {
            setSelectedDataset(e.target.value);
            setSelectedDatasetVersion("");
          }}
          disabled={!selectedProject}
        >
          <option value="">All datasets</option>
          {datasets.map((d) => (
            <option key={d}>{d}</option>
          ))}
        </select>

        <select
          value={selectedDatasetVersion}
          onChange={(e) => setSelectedDatasetVersion(e.target.value)}
          disabled={!selectedProject}
        >
          <option value="">All versions</option>
          {datasetVersions.map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>

        <select
          value={selectedMetric}
          onChange={(e) => setSelectedMetric(e.target.value)}
        >
          <option value="">Select metric</option>
          {metrics.map((m) => (
            <option key={m.id} value={m.name}>
              {m.name} ({m.higher_is_better ? "\u2191" : "\u2193"})
            </option>
          ))}
        </select>
      </div>

      {loading && <p>Loading...</p>}

      {!loading && selectedProject && selectedMetric && (
        ranked.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Model</th>
                <th>Version</th>
                <th>
                  {selectedMetric} ({higherIsBetter ? "\u2191" : "\u2193"})
                </th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((entry, i) => (
                <tr key={`${entry.modelName}-${entry.modelVersion}`}>
                  <td>{i + 1}</td>
                  <td>{entry.modelName}</td>
                  <td>{entry.modelVersion}</td>
                  <td>{entry.value.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No runs found with the selected metric.</p>
        )
      )}

      {!selectedProject && <p>Select a project to see the leaderboard.</p>}
      {selectedProject && !selectedMetric && !loading && (
        <p>Select a metric to rank by.</p>
      )}
    </div>
  );
}
