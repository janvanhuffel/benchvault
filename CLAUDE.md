# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Full stack (Docker Compose)
```bash
docker compose up --build                              # start all services
docker compose exec backend uv run alembic upgrade head # run migrations + seed data
```

### Backend (uses uv)
```bash
cd backend
uv sync                                                # install deps
uv sync --group dev                                    # install deps + test deps
uv run pytest                                          # run all tests
uv run pytest tests/test_submit_run.py -v              # run one test file
uv run pytest tests/test_submit_run.py::test_submit_valid_run # run single test
uv run alembic upgrade head                            # apply migrations
uv run alembic revision --autogenerate -m "description" # generate migration
```

### Frontend
```bash
cd frontend
npm ci                                                 # install deps
npm run dev                                            # dev server (port 3000)
npm run build                                          # production build
npx eslint .                                           # lint
```

## Architecture

Three Docker Compose services: FastAPI backend (port 8000), React SPA frontend (port 3000), PostgreSQL 16.

**Backend** (`backend/app/`): FastAPI with SQLAlchemy ORM and Alembic migrations. All API routes live in `routes/` with prefix `/api`. Pydantic schemas in `schemas.py` handle request validation and response serialization. Database models in `models.py` define 7 tables.

**Frontend** (`frontend/src/`): React + Vite with React Router v7. Pages in `pages/`. All API calls go through `api.js`. Styling is global via `App.css` — no per-component CSS files.

**Data flow**: Benchmark scripts POST runs to the API. The frontend is read-only — it fetches and displays data via GET endpoints.

## Key Domain Rules

- Projects, datasets, dataset versions, and metrics must be **pre-registered** (via migrations/seed data) before runs can reference them.
- Model versions are **auto-upserted** on first submission.
- Metrics have a `higher_is_better` boolean that drives comparison highlighting and leaderboard ranking.
- Run submission validates all referenced entities exist; returns 422 with descriptive error if not.

## Conventions

- **Backend routes**: Each resource gets its own router file. The shared helper `_run_to_response()` in `routes/projects.py` is reused by the compare route.
- **Testing**: `conftest.py` provides `client` (empty DB), `seeded_client` (pre-populated with test-project, test-dataset, metrics). Tests use SQLite in-memory via `StaticPool`.
- **Commits**: Conventional commits (`feat:`, `fix:`, `docs:`).
- **Env config**: Single env var `DATABASE_URL` for backend; `VITE_API_URL` for frontend API base URL.
