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

  if (loading) return <p>Loading projects...</p>;

  return (
    <div>
      <h1>Projects</h1>
      <ul style={{ listStyle: "none", display: "grid", gap: "1rem" }}>
        {projects.map((p) => (
          <li key={p.id}>
            <Link
              to={`/projects/${encodeURIComponent(p.name)}`}
              style={{
                display: "block",
                padding: "1rem 1.5rem",
                background: "#fff",
                borderRadius: "8px",
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                textDecoration: "none",
                color: "#1a1a1a",
                fontWeight: 500,
                fontSize: "1.1rem",
              }}
            >
              {p.name}
            </Link>
          </li>
        ))}
      </ul>
      {projects.length === 0 && <p>No projects found.</p>}
    </div>
  );
}
