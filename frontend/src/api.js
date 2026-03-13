const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function fetchJson(path) {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

async function postJson(path, body) {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${response.status}`);
  }
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

export function createDataset(body) {
  return postJson("/api/datasets", body);
}

export function createDatasetVersion(datasetName, body) {
  return postJson(`/api/datasets/${encodeURIComponent(datasetName)}/versions`, body);
}

export function deleteRuns(runIds) {
  return fetch(`${API_URL}/api/runs`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_ids: runIds }),
  }).then((r) => {
    if (!r.ok) throw new Error(`API error: ${r.status}`);
    return r.json();
  });
}

export function restoreRuns(runIds) {
  return postJson("/api/runs/restore", { run_ids: runIds });
}

export function getProjectTrash(projectName) {
  return fetchJson(`/api/projects/${encodeURIComponent(projectName)}/trash`);
}

export function getSchema() {
  return fetchJson("/api/schema");
}

export function getSchemaSync() {
  return fetchJson("/api/schema/sync");
}
