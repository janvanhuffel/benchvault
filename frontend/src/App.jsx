import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import ProjectList from "./pages/ProjectList";
import ProjectDetail from "./pages/ProjectDetail";
import Compare from "./pages/Compare";
import DatasetList from "./pages/DatasetList";
import ProjectTrash from "./pages/ProjectTrash";
import ExperimentList from "./pages/ExperimentList";
import SchemaERD from "./pages/SchemaERD";
import useTheme from "./hooks/useTheme";
import "./App.css";

function Nav() {
  const location = useLocation();
  const { theme, toggle } = useTheme();

  const isActive = (paths) =>
    paths.some((p) =>
      p === "/" ? location.pathname === "/" : location.pathname.startsWith(p)
    );

  return (
    <nav>
      <div className="nav-left">
        <span className="nav-logo">BenchVault</span>
        <Link
          to="/"
          className={`nav-link${isActive(["/", "/projects", "/compare"]) ? " active" : ""}`}
        >
          Projects
        </Link>
        <Link
          to="/datasets"
          className={`nav-link${isActive(["/datasets"]) ? " active" : ""}`}
        >
          Datasets
        </Link>
        <Link
          to="/experiments"
          className={`nav-link${isActive(["/experiments"]) ? " active" : ""}`}
        >
          Experiments
        </Link>
        <Link
          to="/schema"
          className={`nav-link${isActive(["/schema"]) ? " active" : ""}`}
        >
          Schema
        </Link>
      </div>
      <button className="theme-toggle" onClick={toggle} aria-label="Toggle theme">
        {theme === "dark" ? "\u2600" : "\u263E"}
      </button>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Nav />
      <main>
        <Routes>
          <Route path="/" element={<ProjectList />} />
          <Route path="/projects/:name" element={<ProjectDetail />} />
          <Route path="/projects/:name/trash" element={<ProjectTrash />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/datasets" element={<DatasetList />} />
          <Route path="/experiments" element={<ExperimentList />} />
          <Route path="/schema" element={<SchemaERD />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
