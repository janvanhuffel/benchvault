# Experiments Feature Design

## Overview

Add an "Experiments" concept to BenchVault that lets users group benchmark runs within a project, compare them as a set, and document findings. Experiments provide a persistent, named grouping layer between projects and individual runs.

**Example use case:** Finetuning from different pretraining checkpoints — group the relevant runs, compare them, record that epoch 25 is the sweet spot.

## Data Model

### `experiments` table

| Column       | Type     | Constraints                          |
|-------------|----------|--------------------------------------|
| `id`        | int PK   | auto-increment                       |
| `project_id`| int FK   | → projects, not null                 |
| `name`      | varchar  | not null                             |
| `description`| text    | optional                             |
| `notes`     | text     | markdown content, optional           |
| `status`    | varchar  | `active` or `concluded`, default `active` |
| `created_at`| datetime | auto-set                             |
| `updated_at`| datetime | auto-set on change                   |

- Unique constraint on `(project_id, name)`

### `experiment_runs` join table

| Column         | Type   | Constraints                              |
|---------------|--------|------------------------------------------|
| `id`          | int PK | auto-increment                           |
| `experiment_id`| int FK | → experiments, not null, cascade delete  |
| `run_id`      | int FK | → benchmark_runs, not null, cascade delete|
| `added_at`    | datetime| auto-set                                 |

- Unique constraint on `(experiment_id, run_id)`

### Relationships

- `experiments` → `projects`: many-to-one
- `experiments` ↔ `benchmark_runs`: many-to-many via `experiment_runs`
- A run can belong to multiple experiments
- Deleting an experiment removes join table entries but not the runs themselves
- Hard-deleting a run cascades to remove its join table entries (DB-level cascade)
- Soft-deleting a run (setting `deleted_at`) does NOT remove join entries. Instead, soft-deleted runs are filtered out when querying experiment runs (same `deleted_at IS NULL` filter used elsewhere). This means a soft-deleted run remains linked but invisible; restoring it makes it reappear in the experiment.

## API Endpoints

New route file: `backend/app/routes/experiments.py`

| Method   | Endpoint                        | Purpose                                              |
|----------|---------------------------------|------------------------------------------------------|
| `GET`    | `/api/experiments`              | List all experiments. Optional `?project_name=X` filter. Returns experiments with run count, project name. Ordered: active first (by `updated_at` desc), then concluded (by `updated_at` desc). |
| `POST`   | `/api/experiments`              | Create experiment. Body: `{project_name, name, description?}`. Project must exist. Name must be unique within project. |
| `GET`    | `/api/experiments/{id}`         | Get experiment detail — full metadata + list of runs (same shape as project detail runs, including scalar metrics). |
| `PATCH`  | `/api/experiments/{id}`         | Update any of: name, description, notes, status. Partial updates. |
| `DELETE` | `/api/experiments/{id}`         | Hard delete experiment. Requires confirmation in the UI (not API-level). Removes join table entries, not the runs. |
| `POST`   | `/api/experiments/{id}/runs`    | Add runs. Body: `{run_ids: [1,2,3]}`. Validates runs belong to same project as experiment and are not soft-deleted. |
| `DELETE`  | `/api/experiments/{id}/runs`    | Remove runs. Body: `{run_ids: [1,2,3]}`. Removes join entries only. |

### Modification to existing endpoint

- `GET /api/projects/{project_name}/runs` — each run in the response gains an `experiments` field: a list of `{id, name}` objects. Used for badge display on the project detail page.

### Pydantic schemas (new)

- `ExperimentCreateRequest`: `project_name: str`, `name: str`, `description: str | None`
- `ExperimentUpdateRequest`: `name: str | None`, `description: str | None`, `notes: str | None`, `status: Literal['active', 'concluded'] | None`
- `ExperimentSummaryResponse`: `id`, `name`, `project_name`, `description`, `status`, `run_count`, `created_at`, `updated_at`
- `ExperimentDetailResponse`: `id`, `name`, `project_name`, `description`, `notes`, `status`, `created_at`, `updated_at`, `runs: list[RunResponse]` (each run includes its `experiments` list, so you can see what other experiments a run belongs to)
- `ExperimentRunsRequest`: reuse existing `RunIdsRequest` (`run_ids: list[int]`) from `schemas.py`
- `RunExperimentInfo`: `id: int`, `name: str` (lightweight, for badge display)

### Modification to existing schema

- `RunResponse` gains `experiments: list[RunExperimentInfo]`

## Frontend

### Navigation

Add 4th tab to the nav bar: **Projects | Datasets | Experiments | Schema**

Active on `/experiments` and `/experiments/*`.

### New routes

```
/experiments        → ExperimentList
/experiments/:id    → ExperimentDetail
```

### ExperimentList page (`/experiments`)

- Fetches `GET /api/experiments`
- Two sections: **Active** on top, **Concluded** below
- Concluded section is greyed out (reduced opacity)
- Each experiment card shows: name, project name, description (truncated), run count, created date, status badge
- Cards link to `/experiments/{id}`
- **"+ New Experiment"** button opens an inline form:
  - Project dropdown (fetches from `GET /api/projects`)
  - Name text input
  - Description textarea (optional)
  - Create button

### ExperimentDetail page (`/experiments/{id}`)

- **Breadcrumb**: Experiments › {project_name} › {experiment_name}
- **Header**: Experiment name + active/concluded toggle switch (slide toggle, not a button). Edit icon on name for inline rename.
- **Delete**: Subtle text-style button (not prominent). Clicking shows a confirmation dialog before executing.
- **Description**: Displayed with an edit icon. Inline editing on click.
- **Runs section**:
  - Run count in section header
  - Same table columns as project detail page (model, version, dataset, dataset version, epoch, metrics, date, note)
  - Runs ordered by `created_at` desc (same as project detail page)
  - Checkbox multi-select on runs
  - Action buttons:
    - **Compare All** — navigates to `/compare?run_ids=...` with all experiment runs
    - **Compare Selected** — navigates to `/compare?run_ids=...` with checked runs only
    - **Remove Selected** — removes checked runs from experiment (not delete, just unlinks)
- **Notes section**:
  - Markdown editor with Edit/Preview toggle
  - Edit mode: textarea with raw markdown
  - Preview mode: rendered markdown
  - Explicit Save button that PATCHes the notes field

### ProjectDetail page changes

- **Experiment badges**: Each run row shows colored pill badges for the experiments it belongs to. Runs in no experiment show a dash. Multiple experiments show multiple pills.
- **"Add to Experiment" button**: Appears in the action bar when runs are selected, alongside existing "Compare Selected" and "Delete Selected". Clicking opens a dropdown populated via `GET /api/experiments?project_name=X` (showing only active experiments). Selecting one POSTs the checked run IDs to that experiment's `/runs` endpoint. If no active experiments exist for the project, the dropdown shows "No active experiments" as a disabled placeholder.
- Removing runs from experiments is NOT available from the project page — only from the experiment detail page.

## Migration

Single Alembic migration that:
1. Creates `experiments` table
2. Creates `experiment_runs` join table
3. No seed data needed — experiments are created through the UI

## Key Constraints & Validations

- Experiment names are unique within a project
- Only active (non-soft-deleted) runs can be added to experiments
- Runs must belong to the same project as the experiment
- Status only accepts `active` or `concluded`
- Deleting an experiment is a hard delete (no soft delete for experiments)
- The compare flow reuses the existing `/compare` page and API — no changes needed there

## Error Handling

All error responses follow the existing pattern: `HTTPException` with a `detail` string.

| Scenario | Status Code | Detail |
|----------|-------------|--------|
| Project not found on create | 404 | `Project '{name}' not found` |
| Duplicate experiment name in project | 409 | `Experiment '{name}' already exists in project '{project}'` |
| Experiment not found | 404 | `Experiment {id} not found` |
| Invalid status value | 422 | `Status must be 'active' or 'concluded'` |
| Run not found or soft-deleted | 422 | `Run {id} not found or deleted` |
| Run belongs to different project | 422 | `Run {id} does not belong to project '{project}'` |

## Implementation Notes

- Register the new router in `backend/app/main.py` alongside existing routers.
- The `DELETE` endpoints with request bodies follow the existing pattern used by `DELETE /api/runs` in `runs.py`.
- Compare stays off the nav bar (accessed via links from project and experiment pages).
