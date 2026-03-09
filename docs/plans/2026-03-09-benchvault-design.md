# BenchVault — Design Document

## Goal

BenchVault is a lightweight internal tool for storing ML benchmark results and comparing them over time, across datasets, and across models.

The first integration point is an existing Python benchmarking script that POSTs results to the BenchVault API when a flag is passed. The first user interface is a React frontend where humans can browse, compare, and rank benchmark results.

BenchVault is not an MLOps platform. No training orchestration, no artifact storage, no auth, no multi-tenancy. Just structured storage and comparison of benchmark outputs.

### Success criteria for v1

- A benchmark script can submit a run with one POST request.
- Unknown or unregistered metrics, projects, datasets, or dataset versions cause the run to be rejected.
- A browser-based frontend lets you browse, filter, compare, and rank results.
- The whole stack runs locally via `docker compose up`.

---

## High-Level Architecture

Three containers, one network:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  React Frontend │────▶│  FastAPI Backend │────▶│   PostgreSQL    │
│   (Nginx)       │     │   (Uvicorn)      │     │                 │
│   Port 3000     │     │   Port 8000      │     │   Port 5432     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**FastAPI backend** — REST API for both the benchmark script (submitting runs) and the frontend (querying/comparing runs). Handles validation. Talks to PostgreSQL via SQLAlchemy.

**PostgreSQL** — Stores all data: projects, datasets, models, metrics registry, benchmark runs, and metric values per run.

**React frontend** — SPA served by Nginx. Calls the backend API. React + plain CSS, no framework beyond that.

**Docker Compose** ties them together for local development. In production, each becomes a Kubernetes deployment behind Tailscale.

The **benchmark script** remains in the user's existing project. It is a client, not part of this repo. The expected JSON payload is documented.

---

## Data Model

```
┌──────────┐     ┌──────────┐     ┌──────────────┐
│ Project  │     │ Dataset  │────▶│DatasetVersion│
└──────────┘     └──────────┘     └──────────────┘
                                          │
┌──────────┐     ┌──────────────┐         │
│  Metric  │     │ ModelVersion │         │
│(registry)│     └──────────────┘         │
└──────────┘            │                 │
      │                 │                 │
      ▼                 ▼                 ▼
┌──────────┐     ┌─────────────────────────────┐
│RunMetric │────▶│        BenchmarkRun          │
│(values)  │     │  project, model_version,     │
└──────────┘     │  dataset_version, epoch,     │
                 │  note, timestamp             │
                 └─────────────────────────────┘
```

### Lookup / registry tables

- **Project** — `id`, `name` (unique). Controlled: must exist before a run references it.
- **Dataset** — `id`, `name` (unique). Controlled: must exist before a run references it.
- **DatasetVersion** — `id`, `dataset_id` (FK), `version` (unique per dataset). Controlled: must exist before a run references it.
- **Metric** — `id`, `name` (unique), `higher_is_better` (bool), `description` (optional). Controlled: must exist before a run references it.
- **ModelVersion** — `id`, `model_name`, `model_version` (unique together). Flexible: upserted on submission.

### Core tables

- **BenchmarkRun** — `id`, `project_id` (FK), `model_version_id` (FK), `dataset_version_id` (FK), `epoch` (nullable int), `note` (nullable text), `created_at` (timestamp).
- **RunMetric** — `id`, `run_id` (FK), `metric_id` (FK), `value` (float). Unique on `(run_id, metric_id)`.

### Validation rules on submission

1. Project must exist → reject if not found.
2. Dataset must exist → reject if not found.
3. Dataset version must exist for that dataset → reject if not found.
4. All metric keys must be registered → reject if any are unknown.
5. Model name + model version → upsert (create if new).

### Seeding controlled entities

All controlled entities (projects, datasets, dataset versions, metrics) are seeded via Alembic migrations. Adding a new dataset or metric means writing a migration. v1 ships with dummy seed data.

---

## User Flows

### Flow 1: Benchmark script submits a run

```
Python script (--submit flag)
    │
    ▼
Builds JSON payload:
{
  "project": "my-ocr-pipeline",
  "model_name": "my-model",
  "model_version": "v3.2",
  "dataset": "COCO-2017",
  "dataset_version": "v2.1",
  "epoch": 45,
  "note": "after fixing tokenizer bug",
  "metrics": {
    "accuracy": 0.943,
    "f1_score": 0.921
  }
}
    │
    ▼
POST /api/runs
    │
    ▼
Backend validates (see rules above)
    │
    ▼
On success: stores BenchmarkRun + RunMetric rows, returns run ID
On failure: returns 422 with clear error listing what was unrecognized
```

### Flow 2: Human browses and compares results

```
Open frontend → Project list page
    │
    ▼
Select a project → Project detail page
  Shows all runs, filterable by dataset, dataset version,
  model name, model version, date range
    │
    ▼
Select 2+ runs → Comparison page
  Side-by-side metric values, best-in-column highlighting
  (uses higher_is_better to determine direction)
    │
    ▼
Leaderboard page (per dataset)
  Rank all model versions by a chosen metric
```

The frontend is **read-only** in v1. All data enters through the API.

---

## Key Decisions

1. **Strict validation at ingestion** — project, dataset, dataset version, and metrics must be pre-registered. Model name/version upserts. Prevents garbage data.
2. **Alembic for migrations and seeding** — controlled entities are managed via migrations. Auditable, version-controlled.
3. **Frontend is read-only** — no edit/delete from the UI in v1.
4. **One repo, three containers** — backend, frontend, and database in one repo with `docker-compose.yml`. Same images deploy to Kubernetes.
5. **No auth in v1** — internal tool, behind Tailscale.
6. **Metrics are numeric only** — float values, no strings or blobs.
7. **Benchmark script is a client** — not part of this repo. JSON payload is documented.
8. **Backend comparison endpoint** — `GET /api/compare?run_ids=1,2,3` returns structured comparison data. Frontend renders it.
9. **Distinct frontend pages** — project list, project detail, comparison, leaderboard.
10. **Dummy seed data in v1** — fake projects, datasets, metrics, and a few runs to demo the UI. Deletable later.

---

## Resolved Design Questions

| Question | Decision |
|----------|----------|
| Migrations tool | Alembic (standard with SQLAlchemy) |
| Comparison logic | Backend endpoint, not client-side |
| Benchmark script client | Document the JSON payload, no client library |
| Frontend routing | Distinct pages |
| Seed data strategy | Single Alembic migration with dummy data |
| v1 seed content | Dummy/placeholder data |
