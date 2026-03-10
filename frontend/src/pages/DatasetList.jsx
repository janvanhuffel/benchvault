import { useEffect, useState } from "react";
import { getDatasets } from "../api";

export default function DatasetList() {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    getDatasets()
      .then(setDatasets)
      .finally(() => setLoading(false));
  }, []);

  const toggleExpand = (id) => {
    setExpanded(expanded === id ? null : id);
  };

  if (loading) return <p className="empty-state">Loading datasets...</p>;

  return (
    <div>
      <h1>Datasets</h1>
      <div className="project-grid">
        {datasets.map((ds) => (
          <div key={ds.id} className="dataset-card-wrapper">
            <button
              className="project-card dataset-card"
              onClick={() => toggleExpand(ds.id)}
            >
              <div className="dataset-card-header">
                <span className="dataset-name">{ds.name}</span>
                <span className="dataset-meta">
                  {ds.modality && <span className="tag">{ds.modality}</span>}
                  {ds.task && <span className="tag">{ds.task}</span>}
                  <span className="text-muted">
                    {ds.versions.length} version{ds.versions.length !== 1 ? "s" : ""}
                  </span>
                </span>
              </div>
            </button>

            {expanded === ds.id && (
              <div className="dataset-versions">
                {ds.versions.length === 0 ? (
                  <p className="text-muted" style={{ padding: "1rem" }}>No versions registered.</p>
                ) : (
                  ds.versions.map((v) => {
                    const splits = [
                      v.train_count != null && `Train: ${v.train_count.toLocaleString()}`,
                      v.val_count != null && `Val: ${v.val_count.toLocaleString()}`,
                      v.test_count != null && `Test: ${v.test_count.toLocaleString()}`,
                    ].filter(Boolean);

                    return (
                      <div key={v.id} className="dataset-version-row">
                        <div className="dataset-version-header">
                          <strong>{v.version}</strong>
                          {v.file_type && <span className="tag">{v.file_type}</span>}
                          {v.description && (
                            <span className="text-secondary">{v.description}</span>
                          )}
                        </div>

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
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      {datasets.length === 0 && <p className="empty-state">No datasets found.</p>}
    </div>
  );
}
