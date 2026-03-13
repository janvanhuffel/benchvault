import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import {
  getExperiment,
  updateExperiment,
  deleteExperiment,
  removeRunsFromExperiment,
} from "../api";

export default function ExperimentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [experiment, setExperiment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());

  // Inline editing state
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState("");
  const [editingDesc, setEditingDesc] = useState(false);
  const [descDraft, setDescDraft] = useState("");

  // Notes state
  const [notesMode, setNotesMode] = useState("preview"); // "edit" | "preview"
  const [notesDraft, setNotesDraft] = useState("");
  const [notesSaving, setNotesSaving] = useState(false);

  // Delete confirmation
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const refresh = useCallback(() => getExperiment(id).then((data) => {
    setExperiment(data);
    setNotesDraft(data.notes || "");
  }), [id]);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const handleToggleStatus = async () => {
    try {
      const newStatus = experiment.status === "active" ? "concluded" : "active";
      await updateExperiment(id, { status: newStatus });
      refresh();
    } catch (e) {
      console.error("Failed to toggle status:", e);
    }
  };

  const handleSaveName = async () => {
    if (!editingName) return;
    try {
      if (nameDraft.trim() && nameDraft.trim() !== experiment.name) {
        await updateExperiment(id, { name: nameDraft.trim() });
        refresh();
      }
    } catch (e) {
      console.error("Failed to save name:", e);
    }
    setEditingName(false);
  };

  const handleSaveDesc = async () => {
    try {
      const val = descDraft.trim() || null;
      if (val !== experiment.description) {
        await updateExperiment(id, { description: val });
        refresh();
      }
    } catch (e) {
      console.error("Failed to save description:", e);
    }
    setEditingDesc(false);
  };

  const handleSaveNotes = async () => {
    setNotesSaving(true);
    try {
      await updateExperiment(id, { notes: notesDraft || null });
      setNotesMode("preview");
      refresh();
    } catch (e) {
      console.error("Failed to save notes:", e);
    } finally {
      setNotesSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await deleteExperiment(id);
      navigate("/experiments");
    } catch (e) {
      console.error("Failed to delete experiment:", e);
    }
  };

  const handleRemoveSelected = async () => {
    try {
      await removeRunsFromExperiment(id, [...selected]);
      setSelected(new Set());
      refresh();
    } catch (e) {
      console.error("Failed to remove runs:", e);
    }
  };

  const toggleSelect = (runId) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (!experiment) return;
    if (selected.size === experiment.runs.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(experiment.runs.map((r) => r.id)));
    }
  };

  if (loading) return <p className="empty-state">Loading experiment…</p>;
  if (!experiment) return <p className="error-text">Experiment not found.</p>;

  const metricNames = [
    ...new Set(experiment.runs.flatMap((r) => r.metrics.map((m) => m.metric_name))),
  ].sort();

  const compareUrl = (ids) => `/compare?run_ids=${ids.join(",")}`;

  return (
    <div className="page">
      {/* Breadcrumb */}
      <div className="breadcrumb">
        <Link to="/experiments">Experiments</Link> ›{" "}
        <span>{experiment.project_name}</span> ›{" "}
        <span>{experiment.name}</span>
      </div>

      {/* Header */}
      <div className="experiment-header">
        <div className="experiment-header-left">
          {editingName ? (
            <input
              className="inline-edit-input"
              value={nameDraft}
              onChange={(e) => setNameDraft(e.target.value)}
              onBlur={handleSaveName}
              onKeyDown={(e) => e.key === "Enter" && handleSaveName()}
              autoFocus
            />
          ) : (
            <h2
              className="experiment-title"
              onClick={() => { setNameDraft(experiment.name); setEditingName(true); }}
              title="Click to edit"
            >
              {experiment.name} <span className="edit-hint">✎</span>
            </h2>
          )}
          <span className="experiment-project">Project: {experiment.project_name}</span>
        </div>
        <div className="experiment-header-right">
          <label className="toggle-switch" title={experiment.status === "active" ? "Mark as concluded" : "Mark as active"}>
            <input
              type="checkbox"
              checked={experiment.status === "active"}
              onChange={handleToggleStatus}
            />
            <span className="toggle-slider"></span>
            <span className="toggle-label">
              {experiment.status === "active" ? "Active" : "Concluded"}
            </span>
          </label>
          {showDeleteConfirm ? (
            <span className="delete-confirm">
              Delete?{" "}
              <button className="btn-text btn-text-danger" onClick={handleDelete}>Yes</button>
              {" / "}
              <button className="btn-text" onClick={() => setShowDeleteConfirm(false)}>No</button>
            </span>
          ) : (
            <button className="btn-text btn-subtle" onClick={() => setShowDeleteConfirm(true)}>
              Delete
            </button>
          )}
        </div>
      </div>

      {/* Description */}
      <div className="experiment-description">
        <span className="label">Description</span>
        {editingDesc ? (
          <div>
            <textarea
              className="inline-edit-textarea"
              value={descDraft}
              onChange={(e) => setDescDraft(e.target.value)}
              rows={2}
            />
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.25rem" }}>
              <button className="btn btn-small" onClick={handleSaveDesc}>Save</button>
              <button className="btn btn-small" onClick={() => setEditingDesc(false)}>Cancel</button>
            </div>
          </div>
        ) : (
          <p
            onClick={() => { setDescDraft(experiment.description || ""); setEditingDesc(true); }}
            className="editable-text"
            title="Click to edit"
          >
            {experiment.description || <em>No description</em>}{" "}
            <span className="edit-hint">✎</span>
          </p>
        )}
      </div>

      {/* Runs Section */}
      <div className="experiment-runs-header">
        <h3>Runs ({experiment.runs.length})</h3>
        <div className="experiment-runs-actions">
          {experiment.runs.length > 0 && (
            <Link className="btn btn-primary" to={compareUrl(experiment.runs.map((r) => r.id))}>
              Compare All
            </Link>
          )}
          {selected.size >= 2 && (
            <Link className="btn btn-primary" to={compareUrl([...selected])}>
              Compare Selected
            </Link>
          )}
          {selected.size > 0 && (
            <button className="btn" onClick={handleRemoveSelected}>
              Remove Selected
            </button>
          )}
        </div>
      </div>

      {experiment.runs.length === 0 ? (
        <p className="empty-state">No runs in this experiment yet. Add runs from the project page.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={selected.size === experiment.runs.length}
                    onChange={toggleSelectAll}
                  />
                </th>
                <th>Model</th>
                <th>Version</th>
                <th>Dataset</th>
                <th>DS Ver.</th>
                <th className="num">Epoch</th>
                {metricNames.map((m) => (
                  <th key={m} className="num">{m}</th>
                ))}
                <th>Date</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {experiment.runs.map((run) => (
                <tr key={run.id} className={selected.has(run.id) ? "selected" : ""}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(run.id)}
                      onChange={() => toggleSelect(run.id)}
                    />
                  </td>
                  <td>{run.model_name}</td>
                  <td>{run.model_version}</td>
                  <td>{run.dataset}</td>
                  <td>{run.dataset_version}</td>
                  <td className="num">{run.epoch}</td>
                  {metricNames.map((m) => {
                    const mv = run.metrics.find((rm) => rm.metric_name === m);
                    return <td key={m} className="num">{mv ? mv.value.toFixed(4) : "—"}</td>;
                  })}
                  <td>{new Date(run.created_at).toLocaleDateString()}</td>
                  <td className="note-cell">{run.note || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Notes Section */}
      <div className="experiment-notes">
        <div className="experiment-notes-header">
          <h3>Notes</h3>
          <div className="experiment-notes-actions">
            {notesMode === "preview" ? (
              <button
                className="btn btn-small"
                onClick={() => { setNotesDraft(experiment.notes || ""); setNotesMode("edit"); }}
              >
                Edit
              </button>
            ) : (
              <>
                <button
                  className="btn btn-small btn-primary"
                  onClick={handleSaveNotes}
                  disabled={notesSaving}
                >
                  {notesSaving ? "Saving…" : "Save"}
                </button>
                <button
                  className="btn btn-small"
                  onClick={() => setNotesMode("preview")}
                >
                  Cancel
                </button>
              </>
            )}
          </div>
        </div>
        <div className="experiment-notes-body">
          {notesMode === "edit" ? (
            <textarea
              className="notes-editor"
              value={notesDraft}
              onChange={(e) => setNotesDraft(e.target.value)}
              placeholder="Write your findings in markdown…"
            />
          ) : (
            <div className="notes-preview">
              {experiment.notes ? (
                <ReactMarkdown>{experiment.notes}</ReactMarkdown>
              ) : (
                <p className="empty-state">No notes yet. Click Edit to add findings.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
