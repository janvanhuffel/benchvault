# Experiments Feature Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an "Experiments" feature that lets users group benchmark runs within a project, compare them as a set, and document findings with markdown notes.

**Architecture:** New `experiments` + `experiment_runs` (join) tables. New REST endpoints in a dedicated route file. Two new frontend pages (list + detail) plus modifications to the existing ProjectDetail page for experiment badges and "Add to Experiment" flow.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic (backend); React, React Router, react-markdown (frontend)

---

## Chunk 1: Backend — Database & API

### Task 1: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/010_add_experiments.py`

- [ ] **Step 1: Write the migration file**

```python
"""Add experiments and experiment_runs tables

Revision ID: 010_add_experiments
Revises: 009_seed_per_class_demo
"""
from alembic import op
import sqlalchemy as sa

revision = "010_add_experiments"
down_revision = "009_seed_per_class_demo"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "name", name="uq_experiment_project_name"),
    )

    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "experiment_id",
            sa.Integer(),
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("benchmark_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("added_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("experiment_id", "run_id", name="uq_experiment_run"),
    )


def downgrade():
    op.drop_table("experiment_runs")
    op.drop_table("experiments")
```

- [ ] **Step 2: Verify migration applies**

Run: `cd backend && uv run alembic upgrade head`
Expected: Migration applies without errors.

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/010_add_experiments.py
git commit -m "feat: add experiments and experiment_runs migration"
```

---

### Task 2: SQLAlchemy Models

**Files:**
- Modify: `backend/app/models.py` (add `Experiment`, `ExperimentRun` classes; add relationship to `BenchmarkRun`)

- [ ] **Step 1: Add the Experiment model**

Add after `RunClassMetric` class (after line 166) in `backend/app/models.py`:

```python
class Experiment(Base):
    __tablename__ = "experiments"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_experiment_project_name"),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, server_default="active")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project")
    experiment_runs = relationship("ExperimentRun", back_populates="experiment", cascade="all, delete-orphan")


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    __table_args__ = (
        UniqueConstraint("experiment_id", "run_id", name="uq_experiment_run"),
    )

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("benchmark_runs.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime, server_default=func.now(), nullable=False)

    experiment = relationship("Experiment", back_populates="experiment_runs")
    run = relationship("BenchmarkRun")
```

- [ ] **Step 2: Add `UniqueConstraint` import if missing**

At the top of `models.py`, ensure the import line includes `UniqueConstraint`:

```python
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, UniqueConstraint, TypeDecorator
```

Check the existing imports — `UniqueConstraint` may already be imported via `__table_args__` usage in other models. If it's already there, skip.

- [ ] **Step 3: Verify models load**

Run: `cd backend && uv run python -c "from app.models import Experiment, ExperimentRun; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add Experiment and ExperimentRun models"
```

---

### Task 3: Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Add RunExperimentInfo and update RunResponse**

Add `RunExperimentInfo` before `RunResponse` (before line 121) in `schemas.py`:

```python
class RunExperimentInfo(BaseModel):
    id: int
    name: str
```

Then add the `experiments` field to `RunResponse`:

```python
class RunResponse(BaseModel):
    id: int
    project: str
    model_name: str
    model_version: str
    dataset: str
    dataset_version: str
    epoch: int
    note: str | None
    created_at: datetime
    metrics: list[MetricValueResponse]
    experiments: list[RunExperimentInfo] = []
```

The default `= []` ensures backward compatibility — existing code that builds `RunResponse` without `experiments` still works.

- [ ] **Step 2: Add experiment request/response schemas**

Add at the end of `schemas.py`:

```python
class ExperimentCreateRequest(BaseModel):
    project_name: str
    name: str
    description: str | None = None


class ExperimentUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    notes: str | None = None
    status: Literal["active", "concluded"] | None = None


class ExperimentSummaryResponse(BaseModel):
    id: int
    name: str
    project_name: str
    description: str | None
    status: str
    run_count: int
    created_at: datetime
    updated_at: datetime


class ExperimentDetailResponse(BaseModel):
    id: int
    name: str
    project_name: str
    description: str | None
    notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    runs: list[RunResponse]
```

- [ ] **Step 3: Add the `Literal` import**

At the top of `schemas.py`, add `Literal` to imports:

```python
from typing import Literal
```

- [ ] **Step 4: Verify schemas load**

Run: `cd backend && uv run python -c "from app.schemas import ExperimentCreateRequest, ExperimentDetailResponse, RunExperimentInfo; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat: add experiment Pydantic schemas and RunExperimentInfo"
```

---

### Task 4: Experiments API Routes — CRUD

**Files:**
- Create: `backend/app/routes/experiments.py`
- Modify: `backend/app/main.py` (register router)

- [ ] **Step 1: Write the experiments route file with list and create endpoints**

Create `backend/app/routes/experiments.py`:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.database import get_db
from app.models import (
    BenchmarkRun,
    Experiment,
    ExperimentRun,
    Project,
    RunMetric,
)
from app.routes.projects import _run_to_response
from app.schemas import (
    ExperimentCreateRequest,
    ExperimentDetailResponse,
    ExperimentSummaryResponse,
    ExperimentUpdateRequest,
    RunExperimentInfo,
    RunIdsRequest,
    RunResponse,
)

router = APIRouter(prefix="/api")


def _get_experiment_or_404(db: Session, experiment_id: int) -> Experiment:
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return experiment


def _experiment_to_summary(experiment: Experiment, run_count: int) -> ExperimentSummaryResponse:
    return ExperimentSummaryResponse(
        id=experiment.id,
        name=experiment.name,
        project_name=experiment.project.name,
        description=experiment.description,
        status=experiment.status,
        run_count=run_count,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
    )


@router.get("/experiments", response_model=list[ExperimentSummaryResponse])
def list_experiments(
    project_name: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Experiment, func.count(ExperimentRun.id).label("run_count"))
        .outerjoin(ExperimentRun, Experiment.id == ExperimentRun.experiment_id)
        .join(Project, Experiment.project_id == Project.id)
        .options(contains_eager(Experiment.project))
        .group_by(Experiment.id)
    )

    if project_name:
        query = query.filter(Project.name == project_name)

    # Active first (by updated_at desc), then concluded (by updated_at desc)
    query = query.order_by(
        Experiment.status.desc(),  # "active" > "concluded" alphabetically
        Experiment.updated_at.desc(),
    )

    results = query.all()
    return [_experiment_to_summary(exp, count) for exp, count in results]


@router.post("/experiments", response_model=ExperimentSummaryResponse, status_code=201)
def create_experiment(
    req: ExperimentCreateRequest,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.name == req.project_name).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{req.project_name}' not found")

    existing = (
        db.query(Experiment)
        .filter(Experiment.project_id == project.id, Experiment.name == req.name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Experiment '{req.name}' already exists in project '{req.project_name}'",
        )

    experiment = Experiment(
        project_id=project.id,
        name=req.name,
        description=req.description,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    experiment.project = project  # avoid lazy load

    return _experiment_to_summary(experiment, 0)


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetailResponse)
def get_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
):
    experiment = (
        db.query(Experiment)
        .options(joinedload(Experiment.project))
        .filter(Experiment.id == experiment_id)
        .first()
    )
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")

    # Load runs that are not soft-deleted, ordered by created_at desc
    runs = (
        db.query(BenchmarkRun)
        .join(ExperimentRun, ExperimentRun.run_id == BenchmarkRun.id)
        .filter(
            ExperimentRun.experiment_id == experiment_id,
            BenchmarkRun.deleted_at.is_(None),
        )
        .options(
            joinedload(BenchmarkRun.project),
            joinedload(BenchmarkRun.model_version),
            joinedload(BenchmarkRun.dataset_version).joinedload(
                BenchmarkRun.dataset_version.property.mapper.class_.dataset
            ),
            joinedload(BenchmarkRun.run_metrics).joinedload(RunMetric.metric),
        )
        .order_by(BenchmarkRun.created_at.desc())
        .all()
    )

    # Build run responses with experiment info (bulk query to avoid N+1)
    run_ids = [r.id for r in runs]
    if run_ids:
        exp_memberships = (
            db.query(ExperimentRun.run_id, Experiment.id, Experiment.name)
            .join(Experiment, ExperimentRun.experiment_id == Experiment.id)
            .filter(ExperimentRun.run_id.in_(run_ids))
            .all()
        )
        exp_by_run = {}
        for rid, eid, ename in exp_memberships:
            exp_by_run.setdefault(rid, []).append(RunExperimentInfo(id=eid, name=ename))
    else:
        exp_by_run = {}

    run_responses = []
    for run in runs:
        run_resp = _run_to_response(run)
        run_resp.experiments = exp_by_run.get(run.id, [])
        run_responses.append(run_resp)

    return ExperimentDetailResponse(
        id=experiment.id,
        name=experiment.name,
        project_name=experiment.project.name,
        description=experiment.description,
        notes=experiment.notes,
        status=experiment.status,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
        runs=run_responses,
    )


@router.patch("/experiments/{experiment_id}", response_model=ExperimentSummaryResponse)
def update_experiment(
    experiment_id: int,
    req: ExperimentUpdateRequest,
    db: Session = Depends(get_db),
):
    experiment = _get_experiment_or_404(db, experiment_id)

    if req.name is not None:
        # Check uniqueness within project
        existing = (
            db.query(Experiment)
            .filter(
                Experiment.project_id == experiment.project_id,
                Experiment.name == req.name,
                Experiment.id != experiment.id,
            )
            .first()
        )
        if existing:
            project = db.query(Project).filter(Project.id == experiment.project_id).first()
            raise HTTPException(
                status_code=409,
                detail=f"Experiment '{req.name}' already exists in project '{project.name}'",
            )
        experiment.name = req.name

    if req.description is not None:
        experiment.description = req.description
    if req.notes is not None:
        experiment.notes = req.notes
    if req.status is not None:
        experiment.status = req.status

    db.commit()
    db.refresh(experiment)

    run_count = db.query(func.count(ExperimentRun.id)).filter(
        ExperimentRun.experiment_id == experiment.id
    ).scalar()

    # Eager-load project for the summary
    project = db.query(Project).filter(Project.id == experiment.project_id).first()
    experiment.project = project

    return _experiment_to_summary(experiment, run_count)


@router.delete("/experiments/{experiment_id}", status_code=204)
def delete_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
):
    experiment = _get_experiment_or_404(db, experiment_id)
    db.delete(experiment)
    db.commit()
```

- [ ] **Step 2: Add run membership endpoints to the same file**

Append to `backend/app/routes/experiments.py`:

```python
@router.post("/experiments/{experiment_id}/runs", status_code=204)
def add_runs_to_experiment(
    experiment_id: int,
    req: RunIdsRequest,
    db: Session = Depends(get_db),
):
    experiment = _get_experiment_or_404(db, experiment_id)
    project = db.query(Project).filter(Project.id == experiment.project_id).first()

    for run_id in req.run_ids:
        run = (
            db.query(BenchmarkRun)
            .filter(BenchmarkRun.id == run_id)
            .first()
        )
        if not run or run.deleted_at is not None:
            raise HTTPException(status_code=422, detail=f"Run {run_id} not found or deleted")
        if run.project_id != experiment.project_id:
            raise HTTPException(
                status_code=422,
                detail=f"Run {run_id} does not belong to project '{project.name}'",
            )

        # Skip if already added (idempotent)
        existing = (
            db.query(ExperimentRun)
            .filter(
                ExperimentRun.experiment_id == experiment_id,
                ExperimentRun.run_id == run_id,
            )
            .first()
        )
        if not existing:
            db.add(ExperimentRun(experiment_id=experiment_id, run_id=run_id))

    db.commit()


@router.delete("/experiments/{experiment_id}/runs", status_code=204)
def remove_runs_from_experiment(
    experiment_id: int,
    req: RunIdsRequest,
    db: Session = Depends(get_db),
):
    _get_experiment_or_404(db, experiment_id)

    db.query(ExperimentRun).filter(
        ExperimentRun.experiment_id == experiment_id,
        ExperimentRun.run_id.in_(req.run_ids),
    ).delete(synchronize_session=False)

    db.commit()
```

- [ ] **Step 3: Register the router in main.py**

In `backend/app/main.py`, add:

```python
from app.routes.experiments import router as experiments_router
```

And:

```python
app.include_router(experiments_router)
```

Follow the same pattern as the existing router imports/includes.

- [ ] **Step 4: Verify server starts**

Run: `cd backend && uv run python -c "from app.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/experiments.py backend/app/main.py
git commit -m "feat: add experiments CRUD and run membership API routes"
```

---

### Task 5: Update Project Runs Endpoint for Experiment Badges

**Files:**
- Modify: `backend/app/routes/projects.py`

- [ ] **Step 1: Update `_run_to_response()` to include experiments**

In `backend/app/routes/projects.py`, update the `_run_to_response` function to accept an optional `experiments` parameter and include it in the response:

```python
def _run_to_response(run: BenchmarkRun, experiments: list | None = None) -> RunResponse:
    return RunResponse(
        id=run.id,
        project=run.project.name,
        model_name=run.model_version.model_name,
        model_version=run.model_version.model_version,
        dataset=run.dataset_version.dataset.name,
        dataset_version=run.dataset_version.version,
        epoch=run.epoch,
        note=run.note,
        created_at=run.created_at,
        metrics=[
            MetricValueResponse(
                metric_name=rm.metric.name,
                value=rm.value,
                higher_is_better=rm.metric.higher_is_better,
            )
            for rm in run.run_metrics
        ],
        experiments=experiments or [],
    )
```

- [ ] **Step 2: Update `get_project_runs` to load experiment memberships**

In the `get_project_runs` endpoint, after fetching runs, load experiment memberships and pass them to `_run_to_response`. Add these imports at the top of `projects.py`:

```python
from app.models import Experiment, ExperimentRun
from app.schemas import RunExperimentInfo
```

(Add `Experiment` and `ExperimentRun` to the existing models import, and `RunExperimentInfo` to the existing schemas import.)

After the runs query, add:

```python
# Load experiment memberships for all runs in one query
run_ids = [r.id for r in runs]
if run_ids:
    exp_memberships = (
        db.query(ExperimentRun.run_id, Experiment.id, Experiment.name)
        .join(Experiment, ExperimentRun.experiment_id == Experiment.id)
        .filter(ExperimentRun.run_id.in_(run_ids))
        .all()
    )
    # Group by run_id
    exp_by_run = {}
    for rid, eid, ename in exp_memberships:
        exp_by_run.setdefault(rid, []).append(RunExperimentInfo(id=eid, name=ename))
else:
    exp_by_run = {}

return [_run_to_response(r, experiments=exp_by_run.get(r.id)) for r in runs]
```

Replace the existing `return [_run_to_response(r) for r in runs]` with the above.

- [ ] **Step 3: Verify existing tests still pass**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All existing tests pass. The `experiments=[]` default on `RunResponse` keeps backward compatibility.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routes/projects.py
git commit -m "feat: include experiment badges in project runs response"
```

---

### Task 6: Backend Tests

**Files:**
- Create: `backend/tests/test_experiments.py`
- Modify: `backend/tests/conftest.py` (add experiment fixture)

- [ ] **Step 1: Add experiment test fixture to conftest.py**

In `backend/tests/conftest.py`, add a new fixture after `seeded_client`:

```python
@pytest.fixture
def experiment_client(seeded_db):
    """seeded_db + one experiment for test-project."""
    from app.models import Experiment

    from app.models import Project
    project = seeded_db.query(Project).filter(Project.name == "test-project").first()
    experiment = Experiment(
        project_id=project.id,
        name="Test Experiment",
        description="A test experiment",
    )
    seeded_db.add(experiment)
    seeded_db.commit()

    def override_get_db():
        try:
            yield seeded_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Write test file for experiment CRUD**

Create `backend/tests/test_experiments.py`:

```python
import pytest


def test_create_experiment(seeded_client):
    resp = seeded_client.post("/api/experiments", json={
        "project_name": "test-project",
        "name": "My Experiment",
        "description": "Testing something",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Experiment"
    assert data["project_name"] == "test-project"
    assert data["status"] == "active"
    assert data["run_count"] == 0


def test_create_experiment_unknown_project(seeded_client):
    resp = seeded_client.post("/api/experiments", json={
        "project_name": "nonexistent",
        "name": "Exp",
    })
    assert resp.status_code == 404


def test_create_experiment_duplicate_name(seeded_client):
    seeded_client.post("/api/experiments", json={
        "project_name": "test-project",
        "name": "Dup",
    })
    resp = seeded_client.post("/api/experiments", json={
        "project_name": "test-project",
        "name": "Dup",
    })
    assert resp.status_code == 409


def test_list_experiments(seeded_client):
    seeded_client.post("/api/experiments", json={
        "project_name": "test-project",
        "name": "Exp A",
    })
    resp = seeded_client.get("/api/experiments")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_experiments_filter_by_project(seeded_client):
    seeded_client.post("/api/experiments", json={
        "project_name": "test-project",
        "name": "Exp A",
    })
    resp = seeded_client.get("/api/experiments?project_name=test-project")
    assert len(resp.json()) == 1
    resp = seeded_client.get("/api/experiments?project_name=other")
    assert len(resp.json()) == 0


def test_get_experiment_detail(experiment_client):
    resp = experiment_client.get("/api/experiments/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Experiment"
    assert data["runs"] == []


def test_get_experiment_not_found(seeded_client):
    resp = seeded_client.get("/api/experiments/999")
    assert resp.status_code == 404


def test_update_experiment(experiment_client):
    resp = experiment_client.patch("/api/experiments/1", json={
        "notes": "## Findings\nGood results.",
        "status": "concluded",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "concluded"

    # Verify notes persisted via detail
    detail = experiment_client.get("/api/experiments/1").json()
    assert detail["notes"] == "## Findings\nGood results."


def test_update_experiment_invalid_status(experiment_client):
    resp = experiment_client.patch("/api/experiments/1", json={
        "status": "invalid",
    })
    assert resp.status_code == 422


def test_delete_experiment(experiment_client):
    resp = experiment_client.delete("/api/experiments/1")
    assert resp.status_code == 204

    resp = experiment_client.get("/api/experiments/1")
    assert resp.status_code == 404


def test_add_runs_to_experiment(experiment_client):
    # First submit a run
    run_resp = experiment_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "test-model",
        "model_version": "v1",
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 10,
        "metrics": {"accuracy": 0.9},
    })
    run_id = run_resp.json()["id"]

    # Add run to experiment
    resp = experiment_client.post(f"/api/experiments/1/runs", json={
        "run_ids": [run_id],
    })
    assert resp.status_code == 204

    # Verify run appears in experiment detail
    detail = experiment_client.get("/api/experiments/1").json()
    assert len(detail["runs"]) == 1
    assert detail["runs"][0]["id"] == run_id


def test_add_run_wrong_project(experiment_client):
    # Submit a run to a different project (create project first via a run won't work
    # since projects are pre-registered — test the error)
    resp = experiment_client.post("/api/experiments/1/runs", json={
        "run_ids": [99999],
    })
    assert resp.status_code == 422


def test_add_runs_idempotent(experiment_client):
    run_resp = experiment_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "test-model",
        "model_version": "v1",
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 10,
        "metrics": {"accuracy": 0.9},
    })
    run_id = run_resp.json()["id"]

    experiment_client.post("/api/experiments/1/runs", json={"run_ids": [run_id]})
    # Adding again should not error
    resp = experiment_client.post("/api/experiments/1/runs", json={"run_ids": [run_id]})
    assert resp.status_code == 204

    detail = experiment_client.get("/api/experiments/1").json()
    assert len(detail["runs"]) == 1


def test_remove_runs_from_experiment(experiment_client):
    run_resp = experiment_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "test-model",
        "model_version": "v1",
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 10,
        "metrics": {"accuracy": 0.9},
    })
    run_id = run_resp.json()["id"]

    experiment_client.post("/api/experiments/1/runs", json={"run_ids": [run_id]})

    resp = experiment_client.request(
        "DELETE", "/api/experiments/1/runs", json={"run_ids": [run_id]}
    )
    assert resp.status_code == 204

    detail = experiment_client.get("/api/experiments/1").json()
    assert len(detail["runs"]) == 0


def test_project_runs_include_experiment_badges(experiment_client):
    run_resp = experiment_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "test-model",
        "model_version": "v1",
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 10,
        "metrics": {"accuracy": 0.9},
    })
    run_id = run_resp.json()["id"]

    experiment_client.post("/api/experiments/1/runs", json={"run_ids": [run_id]})

    # Fetch project runs — should include experiment badge
    resp = experiment_client.get("/api/projects/test-project/runs")
    runs = resp.json()
    target_run = [r for r in runs if r["id"] == run_id][0]
    assert len(target_run["experiments"]) == 1
    assert target_run["experiments"][0]["name"] == "Test Experiment"


def test_soft_deleted_run_hidden_in_experiment(experiment_client):
    run_resp = experiment_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "test-model",
        "model_version": "v1",
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 10,
        "metrics": {"accuracy": 0.9},
    })
    run_id = run_resp.json()["id"]

    experiment_client.post("/api/experiments/1/runs", json={"run_ids": [run_id]})

    # Soft-delete the run
    experiment_client.request("DELETE", "/api/runs", json={"run_ids": [run_id]})

    # Run should not appear in experiment detail
    detail = experiment_client.get("/api/experiments/1").json()
    assert len(detail["runs"]) == 0
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run pytest tests/test_experiments.py -v`
Expected: All tests pass.

- [ ] **Step 4: Run full test suite to verify no regressions**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_experiments.py backend/tests/conftest.py
git commit -m "test: add comprehensive experiments API tests"
```

---

## Chunk 2: Frontend — Pages & Integration

### Task 7: API Client Functions

**Files:**
- Modify: `frontend/src/api.js`

- [ ] **Step 1: Add experiment API functions**

Add to the end of `frontend/src/api.js`:

```javascript
// Experiments
export function getExperiments(projectName) {
  const params = projectName ? `?project_name=${encodeURIComponent(projectName)}` : "";
  return fetchJson(`/api/experiments${params}`);
}

export function createExperiment(body) {
  return postJson("/api/experiments", body);
}

export function getExperiment(id) {
  return fetchJson(`/api/experiments/${id}`);
}

export function updateExperiment(id, body) {
  return fetch(`${API_URL}/api/experiments/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => {
    if (!r.ok) throw new Error(`PATCH /api/experiments/${id} failed: ${r.status}`);
    return r.json();
  });
}

export function deleteExperiment(id) {
  return fetch(`${API_URL}/api/experiments/${id}`, {
    method: "DELETE",
  }).then((r) => {
    if (!r.ok) throw new Error(`DELETE /api/experiments/${id} failed: ${r.status}`);
  });
}

export function addRunsToExperiment(experimentId, runIds) {
  return postJson(`/api/experiments/${experimentId}/runs`, { run_ids: runIds });
}

export function removeRunsFromExperiment(experimentId, runIds) {
  return fetch(`${API_URL}/api/experiments/${experimentId}/runs`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_ids: runIds }),
  }).then((r) => {
    if (!r.ok) throw new Error(`DELETE /api/experiments/${experimentId}/runs failed: ${r.status}`);
  });
}
```

Note: `API_URL` is the existing module-level constant (line 1 of `api.js`).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api.js
git commit -m "feat: add experiment API client functions"
```

---

### Task 8: ExperimentList Page

**Files:**
- Create: `frontend/src/pages/ExperimentList.jsx`
- Modify: `frontend/src/App.jsx` (add route + nav tab)

- [ ] **Step 1: Create ExperimentList.jsx**

Create `frontend/src/pages/ExperimentList.jsx`:

```jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getExperiments, getProjects, createExperiment } from "../api";

export default function ExperimentList() {
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [projects, setProjects] = useState([]);
  const [form, setForm] = useState({ project_name: "", name: "", description: "" });
  const [formError, setFormError] = useState("");

  const load = () => {
    setLoading(true);
    getExperiments().then(setExperiments).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openForm = () => {
    setShowForm(true);
    setFormError("");
    getProjects().then((ps) => {
      setProjects(ps);
      if (ps.length > 0 && !form.project_name) {
        setForm((f) => ({ ...f, project_name: ps[0].name }));
      }
    });
  };

  const handleCreate = async () => {
    if (!form.name.trim()) {
      setFormError("Name is required");
      return;
    }
    try {
      await createExperiment({
        project_name: form.project_name,
        name: form.name.trim(),
        description: form.description.trim() || null,
      });
      setForm({ project_name: "", name: "", description: "" });
      setShowForm(false);
      load();
    } catch (e) {
      setFormError(e.message || "Failed to create experiment");
    }
  };

  const active = experiments.filter((e) => e.status === "active");
  const concluded = experiments.filter((e) => e.status === "concluded");

  if (loading) return <p className="empty-state">Loading experiments…</p>;

  return (
    <div className="page">
      <div className="page-header">
        <h2>Experiments</h2>
        <button className="btn btn-primary" onClick={openForm}>+ New Experiment</button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: "1.5rem", padding: "1rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>New Experiment</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <label>
              Project
              <select
                value={form.project_name}
                onChange={(e) => setForm({ ...form, project_name: e.target.value })}
              >
                {projects.map((p) => (
                  <option key={p.name} value={p.name}>{p.name}</option>
                ))}
              </select>
            </label>
            <label>
              Name
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g., Pretraining Checkpoint Impact"
              />
            </label>
            <label>
              Description (optional)
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={2}
                placeholder="What is this experiment investigating?"
              />
            </label>
            {formError && <p className="error-text">{formError}</p>}
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-primary" onClick={handleCreate}>Create</button>
              <button className="btn" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {active.length === 0 && concluded.length === 0 && (
        <p className="empty-state">No experiments yet. Create one to get started.</p>
      )}

      {active.length > 0 && (
        <section>
          <h3 className="section-heading">Active Experiments</h3>
          <div className="experiment-list">
            {active.map((exp) => (
              <ExperimentCard key={exp.id} experiment={exp} />
            ))}
          </div>
        </section>
      )}

      {concluded.length > 0 && (
        <section style={{ marginTop: "2rem" }}>
          <h3 className="section-heading" style={{ color: "var(--color-text-secondary)" }}>Concluded</h3>
          <div className="experiment-list concluded">
            {concluded.map((exp) => (
              <ExperimentCard key={exp.id} experiment={exp} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ExperimentCard({ experiment }) {
  return (
    <Link to={`/experiments/${experiment.id}`} className="experiment-card">
      <div className="experiment-card-main">
        <div className="experiment-card-title">{experiment.name}</div>
        <div className="experiment-card-project">{experiment.project_name}</div>
        {experiment.description && (
          <div className="experiment-card-desc">{experiment.description}</div>
        )}
      </div>
      <div className="experiment-card-meta">
        <span className={`status-badge status-${experiment.status}`}>
          {experiment.status === "active" ? "Active" : "Concluded"}
        </span>
        <span>{experiment.run_count} runs</span>
        <span>{new Date(experiment.created_at).toLocaleDateString()}</span>
      </div>
    </Link>
  );
}
```

- [ ] **Step 2: Add route and nav tab in App.jsx**

In `frontend/src/App.jsx`:

Add the import at the top:
```javascript
import ExperimentList from "./pages/ExperimentList";
```

Add the nav link after Datasets and before Schema (follow the existing `nav-link` + `isActive([...])` pattern):
```jsx
<Link
  to="/experiments"
  className={`nav-link${isActive(["/experiments"]) ? " active" : ""}`}
>
  Experiments
</Link>
```

Add the route inside `<Routes>`:
```jsx
<Route path="/experiments" element={<ExperimentList />} />
```

- [ ] **Step 3: Add CSS for experiment cards and status badges**

Add to `frontend/src/App.css`:

```css
/* Experiment list */
.experiment-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.experiment-list.concluded {
  opacity: 0.55;
}

.experiment-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s;
}

.experiment-card:hover {
  border-color: var(--color-accent);
}

.experiment-card-title {
  font-weight: 600;
  font-size: 0.95rem;
}

.experiment-card-project {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin-top: 0.125rem;
}

.experiment-card-desc {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  margin-top: 0.5rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.experiment-card-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  white-space: nowrap;
  margin-left: 1.5rem;
}

/* Status badges */
.status-badge {
  display: inline-block;
  padding: 0.125rem 0.625rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
}

.status-active {
  background: rgba(34, 197, 94, 0.13);
  color: #22c55e;
}

.status-concluded {
  background: var(--color-border);
  color: var(--color-text-secondary);
}

/* Experiment form elements */
.experiment-list label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.experiment-list label input,
.experiment-list label select,
.experiment-list label textarea {
  font-size: 0.9rem;
  padding: 0.4rem 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
}
```

- [ ] **Step 4: Verify the page renders**

Run: `cd frontend && npm run build`
Expected: Build succeeds without errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ExperimentList.jsx frontend/src/App.jsx frontend/src/App.css
git commit -m "feat: add ExperimentList page with nav tab and create form"
```

---

### Task 9: ExperimentDetail Page

**Files:**
- Create: `frontend/src/pages/ExperimentDetail.jsx`
- Modify: `frontend/src/App.jsx` (add route)

- [ ] **Step 1: Install react-markdown**

Run: `cd frontend && npm install react-markdown`

- [ ] **Step 2: Create ExperimentDetail.jsx**

Create `frontend/src/pages/ExperimentDetail.jsx`:

```jsx
import { useEffect, useState } from "react";
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

  const load = () => {
    setLoading(true);
    getExperiment(id).then((data) => {
      setExperiment(data);
      setNotesDraft(data.notes || "");
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const handleToggleStatus = async () => {
    const newStatus = experiment.status === "active" ? "concluded" : "active";
    await updateExperiment(id, { status: newStatus });
    load();
  };

  const handleSaveName = async () => {
    if (nameDraft.trim() && nameDraft.trim() !== experiment.name) {
      await updateExperiment(id, { name: nameDraft.trim() });
      load();
    }
    setEditingName(false);
  };

  const handleSaveDesc = async () => {
    const val = descDraft.trim() || null;
    if (val !== experiment.description) {
      await updateExperiment(id, { description: val });
      load();
    }
    setEditingDesc(false);
  };

  const handleSaveNotes = async () => {
    setNotesSaving(true);
    await updateExperiment(id, { notes: notesDraft || null });
    setNotesSaving(false);
    setNotesMode("preview");
    load();
  };

  const handleDelete = async () => {
    await deleteExperiment(id);
    navigate("/experiments");
  };

  const handleRemoveSelected = async () => {
    await removeRunsFromExperiment(id, [...selected]);
    setSelected(new Set());
    load();
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
```

- [ ] **Step 3: Add route in App.jsx**

Add the import:
```javascript
import ExperimentDetail from "./pages/ExperimentDetail";
```

Add the route (before the `/experiments` route to avoid matching issues, or after — React Router v7 matches specificity):
```jsx
<Route path="/experiments/:id" element={<ExperimentDetail />} />
```

- [ ] **Step 4: Add CSS for ExperimentDetail**

Add to `frontend/src/App.css`:

```css
/* Breadcrumb */
.breadcrumb {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  margin-bottom: 1rem;
}

.breadcrumb a {
  color: var(--color-accent);
  text-decoration: none;
}

.breadcrumb a:hover {
  text-decoration: underline;
}

/* Experiment header */
.experiment-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.experiment-header-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.experiment-title {
  margin: 0;
  cursor: pointer;
}

.experiment-project {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.experiment-header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.edit-hint {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  opacity: 0;
  transition: opacity 0.15s;
}

*:hover > .edit-hint {
  opacity: 1;
}

.inline-edit-input {
  font-size: 1.4rem;
  font-weight: 700;
  border: 1px solid var(--color-accent);
  border-radius: 4px;
  padding: 0.2rem 0.4rem;
  background: var(--color-surface);
  color: var(--color-text);
}

.inline-edit-textarea {
  width: 100%;
  border: 1px solid var(--color-accent);
  border-radius: 4px;
  padding: 0.4rem 0.5rem;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 0.85rem;
  resize: vertical;
}

/* Toggle switch */
.toggle-switch {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.toggle-switch input {
  display: none;
}

.toggle-slider {
  width: 36px;
  height: 20px;
  background: var(--color-border);
  border-radius: 10px;
  position: relative;
  transition: background 0.2s;
}

.toggle-slider::after {
  content: "";
  position: absolute;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  top: 2px;
  left: 2px;
  transition: transform 0.2s;
}

.toggle-switch input:checked + .toggle-slider {
  background: #22c55e;
}

.toggle-switch input:checked + .toggle-slider::after {
  transform: translateX(16px);
}

/* Subtle delete button */
.btn-text {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem;
  color: var(--color-text-secondary);
}

.btn-text:hover {
  color: var(--color-text);
}

.btn-subtle {
  color: var(--color-text-muted);
}

.btn-text-danger {
  color: #ef4444;
}

.delete-confirm {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

/* Experiment description */
.experiment-description {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
}

.editable-text {
  cursor: pointer;
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
  line-height: 1.5;
}

/* Experiment runs */
.experiment-runs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.experiment-runs-header h3 {
  margin: 0;
}

.experiment-runs-actions {
  display: flex;
  gap: 0.5rem;
}

/* Notes */
.experiment-notes {
  margin-top: 2rem;
}

.experiment-notes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.experiment-notes-header h3 {
  margin: 0;
}

.experiment-notes-actions {
  display: flex;
  gap: 0.25rem;
}

.experiment-notes-body {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
}

.notes-editor {
  width: 100%;
  min-height: 200px;
  border: none;
  background: transparent;
  color: var(--color-text);
  font-family: monospace;
  font-size: 0.85rem;
  line-height: 1.6;
  resize: vertical;
  outline: none;
}

.notes-preview {
  font-size: 0.85rem;
  line-height: 1.7;
  color: var(--color-text);
}

.notes-preview h1,
.notes-preview h2,
.notes-preview h3 {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.notes-preview ul,
.notes-preview ol {
  padding-left: 1.25rem;
}

.notes-preview li {
  margin-bottom: 0.25rem;
}

```

Note: `.btn-small` already exists in `App.css` — do not re-add it.

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds without errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ExperimentDetail.jsx frontend/src/App.jsx frontend/src/App.css
git commit -m "feat: add ExperimentDetail page with notes, runs table, and inline editing"
```

---

### Task 10: ProjectDetail — Experiment Badges & "Add to Experiment"

**Files:**
- Modify: `frontend/src/pages/ProjectDetail.jsx`

- [ ] **Step 1: Add experiment badge column to the runs table**

In `ProjectDetail.jsx`, add experiment badges to each run row. The API response already includes `experiments` on each run (from Task 5).

In the table header row, add a `<th>Experiments</th>` column after the Note column.

In each table body row, add:
```jsx
<td className="tag-list-cell">
  {run.experiments && run.experiments.length > 0 ? (
    <div className="tag-list">
      {run.experiments.map((exp) => (
        <Link key={exp.id} to={`/experiments/${exp.id}`} className="experiment-tag">
          {exp.name}
        </Link>
      ))}
    </div>
  ) : (
    <span className="text-muted">—</span>
  )}
</td>
```

- [ ] **Step 2: Add "Add to Experiment" button and dropdown**

Add state for the experiment dropdown:
```javascript
const [experiments, setExperiments] = useState([]);
const [showExpDropdown, setShowExpDropdown] = useState(false);
```

Import `getExperiments` and `addRunsToExperiment` from `../api`.

When the "Add to Experiment" button is clicked, fetch experiments for the current project:
```javascript
const handleOpenExpDropdown = async () => {
  const exps = await getExperiments(name);
  setExperiments(exps.filter((e) => e.status === "active"));
  setShowExpDropdown(true);
};

const handleAddToExperiment = async (experimentId) => {
  await addRunsToExperiment(experimentId, [...selected]);
  setShowExpDropdown(false);
  setSelected(new Set());
  refresh(); // re-fetch runs to update badges (existing useCallback in ProjectDetail)
};
```

In the action bar (where Compare Selected and Delete Selected are), add:
```jsx
{selected.size > 0 && (
  <div style={{ position: "relative", display: "inline-block" }}>
    <button className="btn" onClick={handleOpenExpDropdown}>
      Add to Experiment ▾
    </button>
    {showExpDropdown && (
      <div className="dropdown-menu">
        {experiments.length === 0 ? (
          <div className="dropdown-item disabled">No active experiments</div>
        ) : (
          experiments.map((exp) => (
            <div
              key={exp.id}
              className="dropdown-item"
              onClick={() => handleAddToExperiment(exp.id)}
            >
              {exp.name}
            </div>
          ))
        )}
      </div>
    )}
  </div>
)}
```

- [ ] **Step 3: Add CSS for experiment tags and dropdown**

Add to `frontend/src/App.css`:

```css
/* Experiment tags in project detail */
.experiment-tag {
  display: inline-block;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  background: var(--color-accent);
  color: white;
  text-decoration: none;
  white-space: nowrap;
}

.experiment-tag:hover {
  opacity: 0.85;
}

.tag-list-cell {
  max-width: 200px;
}

/* Dropdown menu */
.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.25rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 200px;
  z-index: 10;
  overflow: hidden;
}

.dropdown-item {
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  cursor: pointer;
  color: var(--color-text);
}

.dropdown-item:hover {
  background: var(--color-accent-subtle);
}

.dropdown-item.disabled {
  color: var(--color-text-muted);
  cursor: default;
  font-style: italic;
}

.dropdown-item.disabled:hover {
  background: transparent;
}
```

- [ ] **Step 4: Close dropdown when clicking outside**

Add an effect to close the dropdown when clicking outside:
```javascript
useEffect(() => {
  if (!showExpDropdown) return;
  const handleClick = () => setShowExpDropdown(false);
  document.addEventListener("click", handleClick);
  return () => document.removeEventListener("click", handleClick);
}, [showExpDropdown]);
```

And on the dropdown button, stop propagation: `onClick={(e) => { e.stopPropagation(); handleOpenExpDropdown(); }}`

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds without errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ProjectDetail.jsx frontend/src/App.css
git commit -m "feat: add experiment badges and 'Add to Experiment' to project detail"
```

---

### Task 11: Manual End-to-End Verification

- [ ] **Step 1: Start the full stack**

Run: `docker compose up --build`

- [ ] **Step 2: Apply migrations**

Run: `docker compose exec backend uv run alembic upgrade head`

- [ ] **Step 3: Verify experiment workflow**

1. Open http://localhost:3000
2. Click "Experiments" tab — should show empty state
3. Click "+ New Experiment" — create one for an existing project
4. Navigate to that project's page
5. Select some runs → click "Add to Experiment" → pick the experiment
6. Verify experiment badges appear on those runs
7. Navigate to experiment detail page
8. Verify runs appear, "Compare All" works
9. Write some markdown notes, save, verify preview renders
10. Toggle status to "Concluded"
11. Back on experiment list — concluded experiment should be greyed out

- [ ] **Step 4: Final commit if any fixes needed**

Only if manual testing reveals issues. Fix and commit with descriptive message.
