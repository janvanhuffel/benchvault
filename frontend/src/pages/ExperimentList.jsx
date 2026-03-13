import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getExperiments, getProjects, createExperiment } from "../api";

export default function ExperimentList() {
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [projects, setProjects] = useState([]);
  const [form, setForm] = useState({ project_name: "", name: "", description: "" });
  const [formError, setFormError] = useState("");

  const load = () => {
    setLoading(true);
    getExperiments().then(setExperiments).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openForm = () => {
    setShowForm(true);
    setFormError("");
    getProjects().then((ps) => {
      setProjects(ps);
      if (ps.length > 0 && !form.project_name) {
        setForm((f) => ({ ...f, project_name: ps[0].name }));
      }
    });
  };

  const handleCreate = async () => {
    if (!form.name.trim()) {
      setFormError("Name is required");
      return;
    }
    try {
      await createExperiment({
        project_name: form.project_name,
        name: form.name.trim(),
        description: form.description.trim() || null,
      });
      setForm({ project_name: "", name: "", description: "" });
      setShowForm(false);
      load();
    } catch (e) {
      setFormError(e.message || "Failed to create experiment");
    }
  };

  const active = experiments.filter((e) => e.status === "active");
  const concluded = experiments.filter((e) => e.status === "concluded");

  if (loading) return <p className="empty-state">Loading experiments…</p>;

  return (
    <div className="page">
      <div className="page-header">
        <h2>Experiments</h2>
        <button className="btn btn-primary" onClick={openForm}>+ New Experiment</button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: "1.5rem", padding: "1rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>New Experiment</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <label>
              Project
              <select
                value={form.project_name}
                onChange={(e) => setForm({ ...form, project_name: e.target.value })}
              >
                {projects.map((p) => (
                  <option key={p.name} value={p.name}>{p.name}</option>
                ))}
              </select>
            </label>
            <label>
              Name
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g., Pretraining Checkpoint Impact"
              />
            </label>
            <label>
              Description (optional)
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={2}
                placeholder="What is this experiment investigating?"
              />
            </label>
            {formError && <p className="error-text">{formError}</p>}
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-primary" onClick={handleCreate}>Create</button>
              <button className="btn" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {active.length === 0 && concluded.length === 0 && (
        <p className="empty-state">No experiments yet. Create one to get started.</p>
      )}

      {active.length > 0 && (
        <section>
          <h3 className="section-heading">Active Experiments</h3>
          <div className="experiment-list">
            {active.map((exp) => (
              <ExperimentCard key={exp.id} experiment={exp} />
            ))}
          </div>
        </section>
      )}

      {concluded.length > 0 && (
        <section style={{ marginTop: "2rem" }}>
          <h3 className="section-heading" style={{ color: "var(--color-text-secondary)" }}>Concluded</h3>
          <div className="experiment-list concluded">
            {concluded.map((exp) => (
              <ExperimentCard key={exp.id} experiment={exp} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ExperimentCard({ experiment }) {
  return (
    <Link to={`/experiments/${experiment.id}`} className="experiment-card">
      <div className="experiment-card-main">
        <div className="experiment-card-title">{experiment.name}</div>
        <div className="experiment-card-project">{experiment.project_name}</div>
        {experiment.description && (
          <div className="experiment-card-desc">{experiment.description}</div>
        )}
      </div>
      <div className="experiment-card-meta">
        <span className={`status-badge status-${experiment.status}`}>
          {experiment.status === "active" ? "Active" : "Concluded"}
        </span>
        <span>{experiment.run_count} runs</span>
        <span>{new Date(experiment.created_at).toLocaleDateString()}</span>
      </div>
    </Link>
  );
}
