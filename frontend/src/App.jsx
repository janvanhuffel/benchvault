import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import ProjectList from "./pages/ProjectList";
import ProjectDetail from "./pages/ProjectDetail";
import Compare from "./pages/Compare";
import Leaderboard from "./pages/Leaderboard";
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
          to="/leaderboard"
          className={`nav-link${isActive(["/leaderboard"]) ? " active" : ""}`}
        >
          Leaderboard
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
          <Route path="/compare" element={<Compare />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
