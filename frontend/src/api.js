const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function fetchJson(path) {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

export function getProjects() {
  return fetchJson("/api/projects");
}

export function getProjectRuns(projectName) {
  return fetchJson(`/api/projects/${encodeURIComponent(projectName)}/runs`);
}

export function getDatasets() {
  return fetchJson("/api/datasets");
}

export function getMetrics() {
  return fetchJson("/api/metrics");
}

export function compareRuns(runIds) {
  return fetchJson(`/api/compare?run_ids=${runIds.join(",")}`);
}
