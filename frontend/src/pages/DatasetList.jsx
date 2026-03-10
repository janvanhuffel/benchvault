import { useEffect, useState } from "react";
import { getDatasets, createDataset, createDatasetVersion } from "../api";

const EMPTY_DATASET = { name: "", modality: "", task: "", license: "", source_url: "" };
const EMPTY_VERSION = {
  version: "", description: "", num_classes: "", class_names: "",
  train_count: "", val_count: "", test_count: "", total_samples: "",
  total_size_gb: "", collection_method: "", sensor: "", file_type: "", storage_url: "",
};

function FormField({ label, value, onChange, type = "text", placeholder }) {
  return (
    <label className="form-field">
      <span className="form-label">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}

function DatasetForm({ onSubmit, onCancel }) {
  const [form, setForm] = useState(EMPTY_DATASET);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const set = (key) => (val) => setForm({ ...form, [key]: val });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.name.trim()) return setError("Name is required");
    setSubmitting(true);
    setError(null);
    const body = { name: form.name.trim() };
    if (form.modality.trim()) body.modality = form.modality.trim();
    if (form.task.trim()) body.task = form.task.trim();
    if (form.license.trim()) body.license = form.license.trim();
    if (form.source_url.trim()) body.source_url = form.source_url.trim();
    onSubmit(body).catch((err) => { setError(err.message); setSubmitting(false); });
  };

  return (
    <form className="dataset-form" onSubmit={handleSubmit}>
      <h3>Add Dataset</h3>
      <div className="form-grid">
        <FormField label="Name *" value={form.name} onChange={set("name")} placeholder="e.g. WHU-Railway3D" />
        <FormField label="Modality" value={form.modality} onChange={set("modality")} placeholder="e.g. point cloud" />
        <FormField label="Task" value={form.task} onChange={set("task")} placeholder="e.g. semantic segmentation" />
        <FormField label="License" value={form.license} onChange={set("license")} placeholder="e.g. CC BY 4.0" />
        <FormField label="Source URL" value={form.source_url} onChange={set("source_url")} placeholder="https://..." />
      </div>
      {error && <p className="form-error">{error}</p>}
      <div className="form-actions">
        <button type="submit" disabled={submitting}>{submitting ? "Creating..." : "Create Dataset"}</button>
        <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function VersionForm({ datasetName, onSubmit, onCancel }) {
  const [form, setForm] = useState(EMPTY_VERSION);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const set = (key) => (val) => setForm({ ...form, [key]: val });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.version.trim()) return setError("Version is required");
    setSubmitting(true);
    setError(null);
    const body = { version: form.version.trim() };
    if (form.description.trim()) body.description = form.description.trim();
    if (form.num_classes) body.num_classes = parseInt(form.num_classes, 10);
    if (form.class_names.trim()) body.class_names = form.class_names.split(",").map((s) => s.trim()).filter(Boolean);
    if (form.train_count) body.train_count = parseInt(form.train_count, 10);
    if (form.val_count) body.val_count = parseInt(form.val_count, 10);
    if (form.test_count) body.test_count = parseInt(form.test_count, 10);
    if (form.total_samples) body.total_samples = parseInt(form.total_samples, 10);
    if (form.total_size_gb) body.total_size_gb = parseFloat(form.total_size_gb);
    if (form.collection_method.trim()) body.collection_method = form.collection_method.trim();
    if (form.sensor.trim()) body.sensor = form.sensor.trim();
    if (form.file_type.trim()) body.file_type = form.file_type.trim();
    if (form.storage_url.trim()) body.storage_url = form.storage_url.trim();
    onSubmit(body).catch((err) => { setError(err.message); setSubmitting(false); });
  };

  return (
    <form className="dataset-form" onSubmit={handleSubmit}>
      <h3>Add Version to {datasetName}</h3>
      <div className="form-grid">
        <FormField label="Version *" value={form.version} onChange={set("version")} placeholder="e.g. v1.0" />
        <FormField label="Description" value={form.description} onChange={set("description")} placeholder="Short description" />
        <FormField label="File type" value={form.file_type} onChange={set("file_type")} placeholder="e.g. laz, jpg, json" />
        <FormField label="Storage URL" value={form.storage_url} onChange={set("storage_url")} placeholder="s3://bucket/path/" />
        <FormField label="Train count" value={form.train_count} onChange={set("train_count")} type="number" />
        <FormField label="Val count" value={form.val_count} onChange={set("val_count")} type="number" />
        <FormField label="Test count" value={form.test_count} onChange={set("test_count")} type="number" />
        <FormField label="Total samples" value={form.total_samples} onChange={set("total_samples")} type="number" />
        <FormField label="Total size (GB)" value={form.total_size_gb} onChange={set("total_size_gb")} type="number" />
        <FormField label="Num classes" value={form.num_classes} onChange={set("num_classes")} type="number" />
        <FormField label="Class names" value={form.class_names} onChange={set("class_names")} placeholder="comma separated" />
        <FormField label="Collection method" value={form.collection_method} onChange={set("collection_method")} placeholder="e.g. LiDAR survey" />
        <FormField label="Sensor" value={form.sensor} onChange={set("sensor")} placeholder="e.g. Riegl VZ-400" />
      </div>
      {error && <p className="form-error">{error}</p>}
      <div className="form-actions">
        <button type="submit" disabled={submitting}>{submitting ? "Creating..." : "Create Version"}</button>
        <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

export default function DatasetList() {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedDataset, setExpandedDataset] = useState(null);
  const [expandedVersion, setExpandedVersion] = useState(null);
  const [showDatasetForm, setShowDatasetForm] = useState(false);
  const [showVersionForm, setShowVersionForm] = useState(null);

  const refresh = () => getDatasets().then(setDatasets);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, []);

  const toggleDataset = (id) => {
    setExpandedDataset(expandedDataset === id ? null : id);
    setExpandedVersion(null);
    setShowVersionForm(null);
  };

  const toggleVersion = (id) => {
    setExpandedVersion(expandedVersion === id ? null : id);
  };

  const handleCreateDataset = async (body) => {
    await createDataset(body);
    await refresh();
    setShowDatasetForm(false);
  };

  const handleCreateVersion = async (datasetName, body) => {
    await createDatasetVersion(datasetName, body);
    await refresh();
    setShowVersionForm(null);
  };

  if (loading) return <p className="empty-state">Loading datasets...</p>;

  return (
    <div>
      <div className="page-header">
        <h1>Datasets</h1>
        <button onClick={() => setShowDatasetForm(!showDatasetForm)}>
          {showDatasetForm ? "Cancel" : "+ Add Dataset"}
        </button>
      </div>

      {showDatasetForm && (
        <DatasetForm
          onSubmit={handleCreateDataset}
          onCancel={() => setShowDatasetForm(false)}
        />
      )}

      <div className="project-grid">
        {datasets.map((ds) => (
          <div key={ds.id} className="dataset-card-wrapper">
            <button
              className="project-card dataset-card"
              onClick={() => toggleDataset(ds.id)}
            >
              <div className="dataset-card-header">
                <span className="dataset-name">{ds.name}</span>
                <span className="dataset-meta">
                  {ds.modality && <span className="tag">{ds.modality}</span>}
                  {ds.task && <span className="tag">{ds.task}</span>}
                  {ds.license && <span className="text-muted">{ds.license}</span>}
                  <span className="text-muted">
                    {ds.versions.length} version{ds.versions.length !== 1 ? "s" : ""}
                  </span>
                </span>
              </div>
              {ds.source_url && (
                <div className="dataset-card-url">
                  <a
                    href={ds.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {ds.source_url}
                  </a>
                </div>
              )}
            </button>

            {expandedDataset === ds.id && (
              <div className="dataset-versions">
                {ds.versions.map((v) => {
                  const isExpanded = expandedVersion === v.id;
                  const splits = [
                    v.train_count != null && `Train: ${v.train_count.toLocaleString()}`,
                    v.val_count != null && `Val: ${v.val_count.toLocaleString()}`,
                    v.test_count != null && `Test: ${v.test_count.toLocaleString()}`,
                  ].filter(Boolean);

                  return (
                    <div key={v.id} className="dataset-version-row">
                      <button
                        className="dataset-version-toggle"
                        onClick={() => toggleVersion(v.id)}
                      >
                        <span className="dataset-version-summary">
                          <strong>{v.version}</strong>
                          {v.file_type && <span className="tag">{v.file_type}</span>}
                          {v.description && (
                            <span className="text-secondary">{v.description}</span>
                          )}
                        </span>
                        <span className="expand-icon">{isExpanded ? "\u25B2" : "\u25BC"}</span>
                      </button>

                      {isExpanded && (
                        <div className="dataset-version-details">
                          {splits.length > 0 && (
                            <div className="detail-group">
                              <span className="detail-label">Splits</span>
                              <span>{splits.join(" / ")}</span>
                            </div>
                          )}
                          {v.total_samples != null && (
                            <div className="detail-group">
                              <span className="detail-label">Total samples</span>
                              <span>{v.total_samples.toLocaleString()}</span>
                            </div>
                          )}
                          {v.total_size_gb != null && (
                            <div className="detail-group">
                              <span className="detail-label">Size</span>
                              <span>{v.total_size_gb} GB</span>
                            </div>
                          )}
                          {v.num_classes != null && (
                            <div className="detail-group">
                              <span className="detail-label">Classes</span>
                              <span>{v.num_classes}</span>
                            </div>
                          )}
                          {v.class_names && v.class_names.length > 0 && (
                            <div className="detail-group">
                              <span className="detail-label">Class names</span>
                              <div className="tag-list">
                                {v.class_names.map((c) => (
                                  <span key={c} className="tag">{c}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {v.collection_method && (
                            <div className="detail-group">
                              <span className="detail-label">Collection</span>
                              <span>{v.collection_method}</span>
                            </div>
                          )}
                          {v.sensor && (
                            <div className="detail-group">
                              <span className="detail-label">Sensor</span>
                              <span>{v.sensor}</span>
                            </div>
                          )}
                          {v.storage_url && (
                            <div className="detail-group">
                              <span className="detail-label">Storage</span>
                              <a
                                href={v.storage_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="detail-link"
                              >
                                {v.storage_url}
                              </a>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}

                <div className="dataset-version-row">
                  {showVersionForm === ds.id ? (
                    <VersionForm
                      datasetName={ds.name}
                      onSubmit={(body) => handleCreateVersion(ds.name, body)}
                      onCancel={() => setShowVersionForm(null)}
                    />
                  ) : (
                    <button
                      className="btn-secondary btn-small"
                      onClick={() => setShowVersionForm(ds.id)}
                    >
                      + Add Version
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      {datasets.length === 0 && !showDatasetForm && <p className="empty-state">No datasets found.</p>}
    </div>
  );
}
