# BenchVault

Track and compare ML benchmark results across models, datasets, and metrics.

BenchVault is a full-stack tool for storing benchmark runs submitted via a REST API and browsing/comparing them through a web UI. It enforces strict validation — projects, datasets, and metrics must be pre-registered, so results stay consistent and comparable.

## How It Works

```
benchmark script                 FastAPI backend              PostgreSQL
    |                                |                            |
    |-- POST /api/runs ------------->|-- validate & store ------->|
    |   (model, dataset, metrics)    |                            |
    |<---- 201 { id, created_at } --|                            |
                                     |                            |
React frontend                       |                            |
    |-- GET /api/projects ---------->|-- query ------------------>|
    |-- GET /api/compare?run_ids= -->|                            |
    |<---- runs, metrics, rankings --|                            |
```

**Submit** benchmark runs from scripts or CI with a JSON payload. The API validates that the project, dataset, dataset version, and all metrics exist before accepting. Model versions are auto-created on first use.

**Browse** results in the React frontend — filter runs by model/dataset, select runs for side-by-side comparison with best-value highlighting, or view ranked leaderboards by metric.

## Architecture

Three services orchestrated with Docker Compose:

- **Backend** — Python (FastAPI, SQLAlchemy, Alembic) serving the REST API on port 8000
- **Frontend** — React (Vite, React Router) SPA served on port 3000
- **Database** — PostgreSQL 16 with Alembic-managed migrations and seed data

## Quick Start

```bash
docker compose up --build
docker compose exec backend alembic upgrade head   # run migrations + seed data
```

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs (auto-generated): http://localhost:8000/docs

Submit a test run:

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project": "demo-ocr-pipeline",
    "model_name": "my-model",
    "model_version": "v1",
    "dataset": "COCO-2017",
    "dataset_version": "v1.0",
    "epoch": 5,
    "metrics": {"accuracy": 0.92, "f1_score": 0.88}
  }'
```

See [docs/api-payload.md](docs/api-payload.md) for the full API reference.

To tear down and reset the database:

```bash
docker compose down -v
```

## Running Tests

```bash
cd backend
uv sync --group dev
uv run pytest
```
