import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import ProjectList from "./pages/ProjectList";
import ProjectDetail from "./pages/ProjectDetail";
import Compare from "./pages/Compare";
import Leaderboard from "./pages/Leaderboard";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <nav>
        <Link to="/">Projects</Link>
        <Link to="/leaderboard">Leaderboard</Link>
      </nav>
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
