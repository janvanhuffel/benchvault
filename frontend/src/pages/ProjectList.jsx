import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getProjects } from "../api";

export default function ProjectList() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProjects()
      .then(setProjects)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="empty-state">Loading projects...</p>;

  return (
    <div>
      <h1>Projects</h1>
      <div className="project-grid">
        {projects.map((p) => (
          <Link
            key={p.id}
            to={`/projects/${encodeURIComponent(p.name)}`}
            className="project-card"
          >
            {p.name}
          </Link>
        ))}
      </div>
      {projects.length === 0 && <p className="empty-state">No projects found.</p>}
    </div>
  );
}
