# Per-Class Metrics Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-class metric support (IoU, precision, recall per class) to BenchVault so point cloud segmentation benchmarks can submit and compare per-class results.

**Architecture:** New `run_class_metrics` table stores per-class values. The `metrics` table gains an `is_per_class` boolean to distinguish scalar vs per-class metric types. Submission validates class names against `dataset_versions.class_names`. Compare endpoint aggregates per-class data into grouped response. Frontend renders a color-coded per-class table below the existing scalar table.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, React, Vite

**Spec:** `docs/superpowers/specs/2026-03-13-per-class-metrics-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/app/models.py` | Add `is_per_class` to Metric, add RunClassMetric model, add relationships |
| Modify | `backend/app/schemas.py` | Add `per_class_metrics` to RunSubmission, add PerClassRunValues/PerClassCompareGroup, update CompareResponse |
| Modify | `backend/app/routes/runs.py` | Per-class validation + storage in submit_run |
| Modify | `backend/app/routes/compare.py` | Load & aggregate per-class data, filter scalar-only in metric_names |
| Create | `backend/alembic/versions/008_add_per_class_metrics.py` | Migration: is_per_class column, run_class_metrics table, seed per-class metrics |
| Modify | `backend/tests/conftest.py` | Add class_names to seeded DatasetVersion, add per-class metrics to seed |
| Create | `backend/tests/test_per_class_submit.py` | Submission tests for per-class metrics |
| Create | `backend/tests/test_per_class_compare.py` | Compare tests for per-class metrics |
| Modify | `frontend/src/pages/Compare.jsx` | Per-class metrics table with color coding and best highlighting |
| Modify | `frontend/src/App.css` | Styles for per-class table (group separators, color classes) |
| Create | `docs/integration-guide-pointcloud-benchmark.md` | Integration guide for pointcloud-benchmark repo |

---

## Chunk 1: Backend Data Model + Migration

### Task 1: Add `is_per_class` column and `RunClassMetric` model

**Files:**
- Modify: `backend/app/models.py:89-98` (Metric class) and `backend/app/models.py:115-131` (BenchmarkRun class)

- [ ] **Step 1: Add `is_per_class` to Metric model**

In `backend/app/models.py`, first add `false` to the sqlalchemy imports (line 3): `from sqlalchemy import (..., false)`. Then add `is_per_class` column to the `Metric` class and a `run_class_metrics` relationship:

```python
class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    higher_is_better = Column(Boolean, nullable=False, default=True)
    is_per_class = Column(Boolean, nullable=False, default=False, server_default=false())
    description = Column(Text, nullable=True)

    run_metrics = relationship("RunMetric", back_populates="metric")
    run_class_metrics = relationship("RunClassMetric", back_populates="metric")
```

- [ ] **Step 2: Add `RunClassMetric` model**

Add at the bottom of `backend/app/models.py`, after `RunMetric`:

```python
class RunClassMetric(Base):
    __tablename__ = "run_class_metrics"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("benchmark_runs.id"), nullable=False)
    metric_id = Column(Integer, ForeignKey("metrics.id"), nullable=False)
    class_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)

    run = relationship("BenchmarkRun", back_populates="run_class_metrics")
    metric = relationship("Metric", back_populates="run_class_metrics")

    __table_args__ = (
        UniqueConstraint("run_id", "metric_id", "class_name", name="uq_run_class_metric"),
    )
```

- [ ] **Step 3: Add `run_class_metrics` relationship to BenchmarkRun**

In `backend/app/models.py`, add to the `BenchmarkRun` class after line 130 (`run_metrics` relationship):

```python
    run_class_metrics = relationship("RunClassMetric", back_populates="run", cascade="all, delete-orphan")
```

- [ ] **Step 4: Verify models load without errors**

Run: `cd /home/jan/Projects/benchvault/backend && uv run python -c "from app.models import RunClassMetric, Metric; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add RunClassMetric model and is_per_class flag to Metric"
```

### Task 2: Create Alembic migration

**Files:**
- Create: `backend/alembic/versions/008_add_per_class_metrics.py`

- [ ] **Step 1: Write the migration file**

Create `backend/alembic/versions/008_add_per_class_metrics.py`:

```python
"""add per-class metrics support

Revision ID: 008_per_class_metrics
Revises: c78cbd41f4e2
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_per_class_metrics"
down_revision: Union[str, Sequence[str], None] = "c78cbd41f4e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_per_class column to metrics (existing rows get False)
    op.add_column(
        "metrics",
        sa.Column("is_per_class", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # 2. Create run_class_metrics table
    op.create_table(
        "run_class_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("benchmark_runs.id"), nullable=False),
        sa.Column("metric_id", sa.Integer(), sa.ForeignKey("metrics.id"), nullable=False),
        sa.Column("class_name", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.UniqueConstraint("run_id", "metric_id", "class_name", name="uq_run_class_metric"),
    )

    # 3. Seed per-class metric types
    metrics_table = sa.table(
        "metrics",
        sa.column("name", sa.String),
        sa.column("higher_is_better", sa.Boolean),
        sa.column("is_per_class", sa.Boolean),
    )
    op.bulk_insert(metrics_table, [
        {"name": "iou", "higher_is_better": True, "is_per_class": True},
        {"name": "precision", "higher_is_better": True, "is_per_class": True},
        {"name": "recall", "higher_is_better": True, "is_per_class": True},
    ])


def downgrade() -> None:
    op.drop_table("run_class_metrics")
    op.drop_column("metrics", "is_per_class")
    # Note: seeded metric rows (iou, precision, recall) are not removed in downgrade
```

- [ ] **Step 2: Verify migration syntax**

Run: `cd /home/jan/Projects/benchvault/backend && uv run python -c "import importlib.util; spec = importlib.util.spec_from_file_location('m', 'alembic/versions/008_add_per_class_metrics.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/008_add_per_class_metrics.py
git commit -m "feat: add migration for per-class metrics table and is_per_class flag"
```

---

## Chunk 2: Backend Schemas + Submission

### Task 3: Update Pydantic schemas

**Files:**
- Modify: `backend/app/schemas.py:7-16` (RunSubmission) and `backend/app/schemas.py:132-135` (CompareResponse)

- [ ] **Step 1: Add `per_class_metrics` to RunSubmission**

In `backend/app/schemas.py`, add field to `RunSubmission` after line 15 (`metrics`):

```python
class RunSubmission(BaseModel):
    project: str
    model_name: str
    model_version: str
    dataset: str
    dataset_version: str
    epoch: int
    note: str | None = None
    metrics: dict[str, float]
    per_class_metrics: dict[str, dict[str, float]] | None = None
```

- [ ] **Step 2: Add per-class compare schemas and update CompareResponse**

In `backend/app/schemas.py`, add before `CompareResponse` (before line 132):

```python
class PerClassRunValues(BaseModel):
    run_id: int
    values: dict[str, float]


class PerClassCompareGroup(BaseModel):
    metric_name: str
    higher_is_better: bool
    classes: list[str]
    runs: list[PerClassRunValues]
```

Update `CompareResponse`:

```python
class CompareResponse(BaseModel):
    metric_names: list[str]
    higher_is_better: dict[str, bool]
    runs: list[RunResponse]
    per_class_metrics: list[PerClassCompareGroup]
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat: add per-class metric schemas for submission and compare"
```

### Task 4: Update conftest.py seed data

**Files:**
- Modify: `backend/tests/conftest.py:45-65` (seeded_db fixture)

- [ ] **Step 1: Add class_names and per-class metrics to seed**

Update the `seeded_db` fixture in `backend/tests/conftest.py`:

```python
@pytest.fixture
def seeded_db(db):
    """Insert the minimum controlled entities for a valid run submission."""
    from app.models import Project, Dataset, DatasetVersion, Metric

    db.add(Project(name="test-project"))
    db.add(Dataset(name="test-dataset"))
    db.flush()

    dataset = db.query(Dataset).filter_by(name="test-dataset").one()
    db.add(DatasetVersion(
        dataset_id=dataset.id, version="v1.0",
        num_classes=3,
        class_names=["cat", "dog", "bird"],
        train_count=800, val_count=100, test_count=100,
        total_samples=1000, total_size_gb=0.5, file_type="jpg",
        storage_url="s3://test-bucket/test-dataset/v1.0/",
    ))

    # Scalar metrics
    db.add(Metric(name="accuracy", higher_is_better=True, is_per_class=False))
    db.add(Metric(name="f1_score", higher_is_better=True, is_per_class=False))
    # Per-class metrics
    db.add(Metric(name="iou", higher_is_better=True, is_per_class=True))
    db.add(Metric(name="precision", higher_is_better=True, is_per_class=True))
    db.add(Metric(name="recall", higher_is_better=True, is_per_class=True))
    db.commit()
    return db
```

- [ ] **Step 2: Run existing tests to verify seed change doesn't break anything**

Run: `cd /home/jan/Projects/benchvault/backend && uv run pytest -x -q`
Expected: All existing tests pass (the `is_per_class=False` on scalar metrics is explicit but matches old default behavior).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "feat: add class_names and per-class metrics to test seed data"
```

### Task 5: Implement per-class validation and storage in submit_run

**Files:**
- Modify: `backend/app/routes/runs.py:1-136`
- Create: `backend/tests/test_per_class_submit.py`

- [ ] **Step 1: Write failing tests for per-class submission**

Create `backend/tests/test_per_class_submit.py`:

```python
VALID_PAYLOAD = {
    "project": "test-project",
    "model_name": "my-model",
    "model_version": "v1",
    "dataset": "test-dataset",
    "dataset_version": "v1.0",
    "epoch": 10,
    "metrics": {"accuracy": 0.95},
}

PER_CLASS = {
    "iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7},
    "precision": {"cat": 0.95, "dog": 0.85, "bird": 0.75},
}


def test_submit_with_per_class_metrics(seeded_client):
    """Happy path: scalar + per-class metrics → 201, data stored."""
    payload = {**VALID_PAYLOAD, "per_class_metrics": PER_CLASS}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 201


def test_submit_without_per_class_metrics_still_works(seeded_client):
    """Backward compat: no per_class_metrics field → 201."""
    response = seeded_client.post("/api/runs", json=VALID_PAYLOAD)
    assert response.status_code == 201


def test_submit_unknown_per_class_metric_rejected(seeded_client):
    """Unknown per-class metric name → 422."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"bogus": {"cat": 0.9, "dog": 0.8, "bird": 0.7}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "bogus" in response.json()["detail"].lower()


def test_submit_scalar_metric_as_per_class_rejected(seeded_client):
    """Scalar metric (accuracy) submitted as per-class → 422."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"accuracy": {"cat": 0.9, "dog": 0.8, "bird": 0.7}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "per-class" in response.json()["detail"].lower() or "per_class" in response.json()["detail"].lower()


def test_submit_per_class_metric_as_scalar_rejected(seeded_client):
    """Per-class metric (iou) submitted as scalar → 422."""
    payload = {
        **VALID_PAYLOAD,
        "metrics": {"accuracy": 0.95, "iou": 0.85},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422


def test_submit_per_class_missing_class_rejected(seeded_client):
    """Missing class name → 422."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"iou": {"cat": 0.9, "dog": 0.8}},  # missing "bird"
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "class" in response.json()["detail"].lower()


def test_submit_per_class_extra_class_rejected(seeded_client):
    """Extra class name → 422."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7, "fish": 0.6}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "class" in response.json()["detail"].lower()


def test_submit_per_class_wrong_class_name_rejected(seeded_client):
    """Wrong class name → 422."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"iou": {"cat": 0.9, "dog": 0.8, "snake": 0.7}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "class" in response.json()["detail"].lower()


def test_submit_per_class_no_class_names_on_dataset_version_rejected(seeded_client, seeded_db):
    """Dataset version has no class_names (None) but per_class_metrics provided → 422."""
    from app.models import Dataset, DatasetVersion

    dataset = seeded_db.query(Dataset).filter_by(name="test-dataset").one()
    seeded_db.add(DatasetVersion(
        dataset_id=dataset.id, version="v2.0",
        num_classes=0,
        class_names=None,
        train_count=100, val_count=10, test_count=10,
        total_samples=120, total_size_gb=0.1, file_type="las",
        storage_url="s3://test-bucket/test-dataset/v2.0/",
    ))
    seeded_db.commit()

    payload = {
        **VALID_PAYLOAD,
        "dataset_version": "v2.0",
        "per_class_metrics": {"iou": {"something": 0.5}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "class names" in response.json()["detail"].lower()


def test_submit_per_class_empty_class_names_rejected(seeded_client, seeded_db):
    """Dataset version has empty class_names ([]) but per_class_metrics provided → 422."""
    from app.models import Dataset, DatasetVersion

    dataset = seeded_db.query(Dataset).filter_by(name="test-dataset").one()
    seeded_db.add(DatasetVersion(
        dataset_id=dataset.id, version="v3.0",
        num_classes=0,
        class_names=[],
        train_count=100, val_count=10, test_count=10,
        total_samples=120, total_size_gb=0.1, file_type="las",
        storage_url="s3://test-bucket/test-dataset/v3.0/",
    ))
    seeded_db.commit()

    payload = {
        **VALID_PAYLOAD,
        "dataset_version": "v3.0",
        "per_class_metrics": {"iou": {"something": 0.5}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "class names" in response.json()["detail"].lower()


def test_submit_per_class_data_stored_correctly(seeded_client, seeded_db):
    """Verify RunClassMetric rows are actually persisted with correct metric link."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 201
    run_id = response.json()["id"]

    from app.models import RunClassMetric, Metric

    iou_metric = seeded_db.query(Metric).filter_by(name="iou").one()
    rows = seeded_db.query(RunClassMetric).filter_by(run_id=run_id).all()
    assert len(rows) == 3
    for row in rows:
        assert row.metric_id == iou_metric.id
    values_by_class = {r.class_name: r.value for r in rows}
    assert values_by_class == {"cat": 0.9, "dog": 0.8, "bird": 0.7}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jan/Projects/benchvault/backend && uv run pytest tests/test_per_class_submit.py -v`
Expected: Most tests FAIL (validation logic not yet implemented).

- [ ] **Step 3: Implement per-class validation and storage in submit_run**

Update `backend/app/routes/runs.py`. The full file after changes:

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Project, Dataset, DatasetVersion, Metric,
    ModelVersion, BenchmarkRun, RunMetric, RunClassMetric,
)
from app.schemas import RunSubmission, RunCreatedResponse, RunIdsRequest

router = APIRouter(prefix="/api")


@router.delete("/runs")
def delete_runs(body: RunIdsRequest, db: Session = Depends(get_db)):
    if not body.run_ids:
        raise HTTPException(422, detail="run_ids must not be empty")

    runs = (
        db.query(BenchmarkRun)
        .filter(
            BenchmarkRun.id.in_(body.run_ids),
            BenchmarkRun.deleted_at.is_(None),
        )
        .all()
    )

    if not runs:
        raise HTTPException(404, detail="No active runs found for the given IDs")

    now = datetime.now(timezone.utc)
    for run in runs:
        run.deleted_at = now
    db.commit()

    return {"deleted": len(runs)}


@router.post("/runs/restore")
def restore_runs(body: RunIdsRequest, db: Session = Depends(get_db)):
    if not body.run_ids:
        raise HTTPException(422, detail="run_ids must not be empty")

    runs = (
        db.query(BenchmarkRun)
        .filter(
            BenchmarkRun.id.in_(body.run_ids),
            BenchmarkRun.deleted_at.isnot(None),
        )
        .all()
    )

    if not runs:
        raise HTTPException(404, detail="No trashed runs found for the given IDs")

    for run in runs:
        run.deleted_at = None
    db.commit()

    return {"restored": len(runs)}


@router.post("/runs", response_model=RunCreatedResponse, status_code=201)
def submit_run(submission: RunSubmission, db: Session = Depends(get_db)):
    # Validate project
    project = db.query(Project).filter_by(name=submission.project).first()
    if not project:
        raise HTTPException(422, detail=f"Project not found: {submission.project}")

    # Validate dataset
    dataset = db.query(Dataset).filter_by(name=submission.dataset).first()
    if not dataset:
        raise HTTPException(422, detail=f"Dataset not found: {submission.dataset}")

    # Validate dataset version
    dataset_version = (
        db.query(DatasetVersion)
        .filter_by(dataset_id=dataset.id, version=submission.dataset_version)
        .first()
    )
    if not dataset_version:
        raise HTTPException(
            422,
            detail=f"Dataset_version not found: {submission.dataset_version} for dataset {submission.dataset}",
        )

    # Load all referenced metrics (scalar + per-class)
    all_metric_names = set(submission.metrics.keys())
    if submission.per_class_metrics:
        all_metric_names |= set(submission.per_class_metrics.keys())

    registered_metrics = (
        db.query(Metric).filter(Metric.name.in_(all_metric_names)).all()
    )
    metric_map = {m.name: m for m in registered_metrics}

    # Check for unknown metrics
    unknown = all_metric_names - set(metric_map.keys())
    if unknown:
        raise HTTPException(
            422,
            detail=f"Unknown metric(s): {', '.join(sorted(unknown))}. Register them first.",
        )

    # Validate scalar metrics are not per-class
    for name in submission.metrics:
        if metric_map[name].is_per_class:
            raise HTTPException(
                422,
                detail=f"Metric '{name}' is a per-class metric and cannot be submitted as a scalar. Use per_class_metrics instead.",
            )

    # Validate per-class metrics
    if submission.per_class_metrics:
        # Check each per-class metric is actually per-class
        for name in submission.per_class_metrics:
            if not metric_map[name].is_per_class:
                raise HTTPException(
                    422,
                    detail=f"Metric '{name}' is not a per-class metric. Submit it in metrics instead.",
                )

        # Check dataset version has class_names
        if not dataset_version.class_names:
            raise HTTPException(
                422,
                detail="Dataset version does not define class names. Cannot submit per-class metrics.",
            )

        expected_classes = set(dataset_version.class_names)
        for metric_name, class_values in submission.per_class_metrics.items():
            submitted_classes = set(class_values.keys())
            if submitted_classes != expected_classes:
                missing = expected_classes - submitted_classes
                extra = submitted_classes - expected_classes
                parts = []
                if missing:
                    parts.append(f"missing: {', '.join(sorted(missing))}")
                if extra:
                    parts.append(f"extra: {', '.join(sorted(extra))}")
                raise HTTPException(
                    422,
                    detail=f"Class name mismatch for metric '{metric_name}': {'; '.join(parts)}. "
                           f"Expected: {sorted(expected_classes)}",
                )

    # Upsert model version
    model_version = (
        db.query(ModelVersion)
        .filter_by(model_name=submission.model_name, model_version=submission.model_version)
        .first()
    )
    if not model_version:
        model_version = ModelVersion(
            model_name=submission.model_name,
            model_version=submission.model_version,
        )
        db.add(model_version)
        db.flush()

    # Create run
    run = BenchmarkRun(
        project_id=project.id,
        model_version_id=model_version.id,
        dataset_version_id=dataset_version.id,
        epoch=submission.epoch,
        note=submission.note,
    )
    db.add(run)
    db.flush()

    # Create scalar run metrics
    for metric_name, value in submission.metrics.items():
        db.add(RunMetric(run_id=run.id, metric_id=metric_map[metric_name].id, value=value))

    # Create per-class run metrics
    if submission.per_class_metrics:
        for metric_name, class_values in submission.per_class_metrics.items():
            for class_name, value in class_values.items():
                db.add(RunClassMetric(
                    run_id=run.id,
                    metric_id=metric_map[metric_name].id,
                    class_name=class_name,
                    value=value,
                ))

    db.commit()
    db.refresh(run)

    return RunCreatedResponse(id=run.id, created_at=run.created_at)
```

- [ ] **Step 4: Run per-class submission tests**

Run: `cd /home/jan/Projects/benchvault/backend && uv run pytest tests/test_per_class_submit.py -v`
Expected: All PASS

- [ ] **Step 5: Run all tests to check for regressions**

Run: `cd /home/jan/Projects/benchvault/backend && uv run pytest -x -q`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/runs.py backend/tests/test_per_class_submit.py
git commit -m "feat: add per-class metric validation and storage in run submission"
```

---

## Chunk 3: Compare Endpoint

### Task 6: Update compare endpoint for per-class metrics

**Files:**
- Modify: `backend/app/routes/compare.py:1-64`
- Create: `backend/tests/test_per_class_compare.py`

- [ ] **Step 1: Write failing tests for per-class compare**

Create `backend/tests/test_per_class_compare.py`:

```python
def _submit_run(client, model_name, model_version, metrics, per_class=None):
    """Helper to submit a run and return its ID."""
    payload = {
        "project": "test-project",
        "model_name": model_name,
        "model_version": model_version,
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 1,
        "metrics": metrics,
    }
    if per_class is not None:
        payload["per_class_metrics"] = per_class
    resp = client.post("/api/runs", json=payload)
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def test_compare_with_per_class_metrics(seeded_client):
    """Compare runs that both have per-class data → populated per_class_metrics."""
    pc1 = {"iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7}}
    pc2 = {"iou": {"cat": 0.85, "dog": 0.9, "bird": 0.75}}
    id1 = _submit_run(seeded_client, "m1", "v1", {"accuracy": 0.9}, pc1)
    id2 = _submit_run(seeded_client, "m2", "v1", {"accuracy": 0.95}, pc2)

    resp = seeded_client.get(f"/api/compare?run_ids={id1},{id2}")
    assert resp.status_code == 200
    data = resp.json()

    # Scalar metrics should NOT include per-class metric names
    assert "iou" not in data["metric_names"]
    assert "accuracy" in data["metric_names"]

    # Per-class section should be populated
    assert len(data["per_class_metrics"]) == 1
    group = data["per_class_metrics"][0]
    assert group["metric_name"] == "iou"
    assert group["higher_is_better"] is True
    assert group["classes"] == ["cat", "dog", "bird"]
    assert len(group["runs"]) == 2
    assert group["runs"][0]["run_id"] == id1
    assert group["runs"][0]["values"] == {"cat": 0.9, "dog": 0.8, "bird": 0.7}


def test_compare_without_per_class_data(seeded_client):
    """Compare runs with no per-class data → empty per_class_metrics."""
    id1 = _submit_run(seeded_client, "m1", "v1", {"accuracy": 0.9})
    id2 = _submit_run(seeded_client, "m2", "v1", {"accuracy": 0.95})

    resp = seeded_client.get(f"/api/compare?run_ids={id1},{id2}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["per_class_metrics"] == []


def test_compare_different_dataset_versions_no_per_class(seeded_client, seeded_db):
    """Runs from different dataset versions → empty per_class_metrics."""
    from app.models import Dataset, DatasetVersion

    dataset = seeded_db.query(Dataset).filter_by(name="test-dataset").one()
    seeded_db.add(DatasetVersion(
        dataset_id=dataset.id, version="v2.0",
        num_classes=2, class_names=["x", "y"],
        train_count=100, val_count=10, test_count=10,
        total_samples=120, total_size_gb=0.1, file_type="las",
        storage_url="s3://test-bucket/v2.0/",
    ))
    seeded_db.commit()

    pc1 = {"iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7}}
    id1 = _submit_run(seeded_client, "m1", "v1", {"accuracy": 0.9}, pc1)

    # Submit to v2.0
    payload2 = {
        "project": "test-project",
        "model_name": "m2", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v2.0",
        "epoch": 1,
        "metrics": {"accuracy": 0.95},
        "per_class_metrics": {"iou": {"x": 0.8, "y": 0.7}},
    }
    r2 = seeded_client.post("/api/runs", json=payload2)
    assert r2.status_code == 201
    id2 = r2.json()["id"]

    resp = seeded_client.get(f"/api/compare?run_ids={id1},{id2}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["per_class_metrics"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jan/Projects/benchvault/backend && uv run pytest tests/test_per_class_compare.py -v`
Expected: FAIL (compare endpoint doesn't return `per_class_metrics` yet).

- [ ] **Step 3: Implement per-class compare logic**

Update `backend/app/routes/compare.py`:

```python
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import BenchmarkRun, RunClassMetric, Metric
from app.routes.projects import _run_to_response
from app.schemas import CompareResponse, PerClassCompareGroup, PerClassRunValues

router = APIRouter(prefix="/api")


@router.get("/compare", response_model=CompareResponse)
def compare_runs(
    run_ids: str = Query(..., description="Comma-separated run IDs"),
    db: Session = Depends(get_db),
):
    try:
        id_list = [int(x.strip()) for x in run_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(422, detail="run_ids must be comma-separated integers")
    if not id_list:
        raise HTTPException(422, detail="run_ids must not be empty")

    runs = (
        db.query(BenchmarkRun)
        .filter(BenchmarkRun.id.in_(id_list))
        .filter(BenchmarkRun.deleted_at.is_(None))
        .options(
            joinedload(BenchmarkRun.project),
            joinedload(BenchmarkRun.model_version),
            joinedload(BenchmarkRun.dataset_version).joinedload(
                BenchmarkRun.dataset_version.property.mapper.class_.dataset
            ),
            joinedload(BenchmarkRun.run_metrics).joinedload(
                BenchmarkRun.run_metrics.property.mapper.class_.metric
            ),
            joinedload(BenchmarkRun.run_class_metrics).joinedload(
                BenchmarkRun.run_class_metrics.property.mapper.class_.metric
            ),
        )
        .all()
    )

    found_ids = {r.id for r in runs}
    missing = set(id_list) - found_ids
    if missing:
        raise HTTPException(404, detail=f"Run(s) not found: {sorted(missing)}")

    # Preserve caller's requested order
    id_order = {id_: idx for idx, id_ in enumerate(id_list)}
    runs.sort(key=lambda r: id_order[r.id])

    run_responses = [_run_to_response(r) for r in runs]

    # Collect scalar metric names — _run_to_response() only includes run_metrics
    # (scalar RunMetric rows), never run_class_metrics, so this is inherently filtered
    metric_names: set[str] = set()
    higher_is_better: dict[str, bool] = {}
    for rr in run_responses:
        for m in rr.metrics:
            metric_names.add(m.metric_name)
            higher_is_better[m.metric_name] = m.higher_is_better

    # Build per-class comparison groups
    per_class_groups = _build_per_class_groups(runs)

    return CompareResponse(
        metric_names=sorted(metric_names),
        higher_is_better=higher_is_better,
        runs=run_responses,
        per_class_metrics=per_class_groups,
    )


def _build_per_class_groups(runs: list[BenchmarkRun]) -> list[PerClassCompareGroup]:
    """Build per-class metric groups if all runs share the same dataset version."""
    if not runs:
        return []

    # Check all runs share the same dataset version
    dv_ids = {r.dataset_version_id for r in runs}
    if len(dv_ids) > 1:
        return []

    # Check any run has per-class data
    has_per_class = any(r.run_class_metrics for r in runs)
    if not has_per_class:
        return []

    # Get class ordering from dataset version
    dataset_version = runs[0].dataset_version
    class_names = dataset_version.class_names or []
    if not class_names:
        return []

    # Group by metric: {metric_name: {run_id: {class_name: value}}}
    metric_data: dict[str, dict[int, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    metric_info: dict[str, bool] = {}  # metric_name → higher_is_better

    for run in runs:
        for rcm in run.run_class_metrics:
            metric_data[rcm.metric.name][run.id][rcm.class_name] = rcm.value
            metric_info[rcm.metric.name] = rcm.metric.higher_is_better

    groups = []
    for metric_name in sorted(metric_data.keys()):
        run_values = []
        for run in runs:
            values = metric_data[metric_name].get(run.id, {})
            run_values.append(PerClassRunValues(run_id=run.id, values=values))
        groups.append(PerClassCompareGroup(
            metric_name=metric_name,
            higher_is_better=metric_info[metric_name],
            classes=class_names,
            runs=run_values,
        ))

    return groups
```

- [ ] **Step 4: Run per-class compare tests**

Run: `cd /home/jan/Projects/benchvault/backend && uv run pytest tests/test_per_class_compare.py -v`
Expected: All PASS

- [ ] **Step 5: Run all backend tests**

Run: `cd /home/jan/Projects/benchvault/backend && uv run pytest -x -q`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/compare.py backend/tests/test_per_class_compare.py
git commit -m "feat: add per-class metrics to compare endpoint"
```

---

## Chunk 4: Frontend

### Task 7: Add per-class metrics table to Compare page

**Files:**
- Modify: `frontend/src/pages/Compare.jsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Add CSS for per-class table**

Add to the bottom of `frontend/src/App.css` (before any final closing comment):

```css
/* ===== Per-Class Metrics Table ===== */

.pcm-section {
  margin-top: 2rem;
}

.pcm-section h2 {
  font-size: 1.1rem;
  margin-bottom: 1rem;
}

.pcm-table {
  font-size: 0.8125rem;
  min-width: 600px;
}

.pcm-table th,
.pcm-table td {
  padding: 6px 10px;
  text-align: right;
  white-space: nowrap;
}

.pcm-table .pcm-class-name {
  text-align: left;
  font-weight: 500;
}

.pcm-table .pcm-group-header {
  text-align: center;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.pcm-table .pcm-group-sep {
  border-left: 2px solid var(--color-border);
}

.pcm-info {
  color: var(--color-text-muted);
  font-size: 0.875rem;
  margin-top: 2rem;
}
```

- [ ] **Step 2: Update Compare.jsx with per-class table**

Replace `frontend/src/pages/Compare.jsx` with:

```jsx
import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { compareRuns } from "../api";

function getHslColor(value) {
  // Clamp to [0, 1]
  const v = Math.max(0, Math.min(1, value));
  // red(0) → yellow(60) → green(120)
  const hue = v * 120;
  return `hsla(${hue}, 70%, 45%, 0.18)`;
}

export default function Compare() {
  const [searchParams] = useSearchParams();
  const idsParam = searchParams.get("run_ids");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [fetchDone, setFetchDone] = useState(false);

  const fetchComparison = useCallback((ids) => {
    compareRuns(ids)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setFetchDone(true));
  }, []);

  useEffect(() => {
    if (!idsParam) return;
    const ids = idsParam.split(",").map(Number);
    fetchComparison(ids);
  }, [idsParam, fetchComparison]);

  if (!idsParam)
    return <p className="empty-state">No runs selected for comparison. Go back and select runs.</p>;
  if (!fetchDone) return <p className="empty-state">Loading comparison...</p>;
  if (error) return <p className="empty-state">{error}</p>;
  if (!data) return null;

  // For each metric, find the best value across runs
  const getBestValue = (metricName) => {
    const hib = data.higher_is_better[metricName];
    const values = data.runs
      .map((run) => {
        const metric = run.metrics.find((m) => m.metric_name === metricName);
        return metric ? metric.value : null;
      })
      .filter((v) => v !== null);

    if (values.length === 0) return null;
    return hib ? Math.max(...values) : Math.min(...values);
  };

  const getMetricValue = (run, metricName) => {
    const metric = run.metrics.find((m) => m.metric_name === metricName);
    return metric ? metric.value : null;
  };

  const perClass = data.per_class_metrics || [];
  // Check if runs have different dataset versions (for info message)
  const datasetVersions = new Set(data.runs.map((r) => `${r.dataset}/${r.dataset_version}`));
  const hasMixedVersions = datasetVersions.size > 1;

  return (
    <div>
      <h1>Run Comparison</h1>

      {/* Scalar metrics table */}
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            {data.runs.map((run) => (
              <th key={run.id} className="metric-value">
                {run.model_name} / {run.model_version}
                <br />
                <span className="text-secondary" style={{ fontWeight: "normal" }}>
                  {run.dataset} {run.dataset_version}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.metric_names.map((metricName) => {
            const best = getBestValue(metricName);
            return (
              <tr key={metricName}>
                <td style={{ fontWeight: 500 }}>
                  {metricName}
                  <span className="text-muted" style={{ marginLeft: "0.5rem" }}>
                    ({data.higher_is_better[metricName] ? "\u2191" : "\u2193"})
                  </span>
                </td>
                {data.runs.map((run) => {
                  const val = getMetricValue(run, metricName);
                  const isBest = val !== null && val === best;
                  return (
                    <td
                      key={run.id}
                      className={`metric-value${isBest ? " metric-best" : ""}`}
                    >
                      {val !== null ? val.toFixed(4) : "\u2014"}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Per-class metrics section */}
      {hasMixedVersions && perClass.length === 0 && (
        <p className="pcm-info">
          Per-class comparison is only available when all runs use the same dataset version.
        </p>
      )}

      {perClass.length > 0 && (
        <div className="pcm-section">
          <h2>Per-Class Metrics</h2>
          <div style={{ overflowX: "auto" }}>
            <table className="pcm-table">
              <thead>
                <tr>
                  <th rowSpan={2} style={{ textAlign: "left" }}>Class</th>
                  {perClass.map((group, gi) => (
                    <th
                      key={group.metric_name}
                      colSpan={data.runs.length}
                      className={`pcm-group-header${gi > 0 ? " pcm-group-sep" : ""}`}
                    >
                      {group.metric_name} ({group.higher_is_better ? "\u2191" : "\u2193"})
                    </th>
                  ))}
                </tr>
                <tr>
                  {perClass.map((group, gi) =>
                    data.runs.map((run, ri) => (
                      <th
                        key={`${group.metric_name}-${run.id}`}
                        className={gi > 0 && ri === 0 ? "pcm-group-sep" : ""}
                      >
                        {run.model_version}
                      </th>
                    ))
                  )}
                </tr>
              </thead>
              <tbody>
                {perClass[0].classes.map((className) => (
                  <tr key={className}>
                    <td className="pcm-class-name">{className}</td>
                    {perClass.map((group, gi) => {
                      // Find best value for this class across runs
                      const classValues = group.runs
                        .map((rv) => rv.values[className])
                        .filter((v) => v !== undefined && v !== null);
                      const best = classValues.length > 0
                        ? (group.higher_is_better ? Math.max(...classValues) : Math.min(...classValues))
                        : null;

                      return data.runs.map((run, ri) => {
                        const runData = group.runs.find((rv) => rv.run_id === run.id);
                        const val = runData?.values[className];
                        const isBest = val !== undefined && val !== null && val === best && classValues.length > 1;

                        return (
                          <td
                            key={`${group.metric_name}-${run.id}`}
                            className={gi > 0 && ri === 0 ? "pcm-group-sep" : ""}
                            style={{
                              backgroundColor: val !== undefined && val !== null ? getHslColor(val) : undefined,
                              fontWeight: isBest ? "bold" : undefined,
                              fontVariantNumeric: "tabular-nums",
                            }}
                          >
                            {val !== undefined && val !== null ? val.toFixed(4) : "\u2014"}
                          </td>
                        );
                      });
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify frontend builds**

Run: `cd /home/jan/Projects/benchvault/frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 4: Verify lint passes**

Run: `cd /home/jan/Projects/benchvault/frontend && npx eslint src/pages/Compare.jsx`
Expected: No errors (warnings are acceptable).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Compare.jsx frontend/src/App.css
git commit -m "feat: add per-class metrics table to compare page"
```

---

## Chunk 5: Integration Guide

### Task 8: Generate integration guide for pointcloud-benchmark

**Files:**
- Create: `docs/integration-guide-pointcloud-benchmark.md`

**Precondition:** The pointcloud-benchmark repo must exist at `/home/jan/Projects/pointcloud-benchmark`. If not found, skip this task and note it for the user.

This task is executed by a subagent that:
1. Reads `/home/jan/Projects/pointcloud-benchmark` to understand how results are produced
2. Reads the BenchVault submission endpoint and schema
3. Writes a guide explaining: JSON payload structure, how to map results.json output to the submission format, which metrics/datasets/versions need pre-registration, example curl and Python snippets

- [ ] **Step 1: Dispatch subagent to analyze both repos and write the guide**

The subagent should write to `docs/integration-guide-pointcloud-benchmark.md`.

- [ ] **Step 2: Review the generated guide**

Read `docs/integration-guide-pointcloud-benchmark.md` and verify it covers:
- JSON payload structure for POST /api/runs
- Mapping from the benchmark tool's results.json
- Pre-registration requirements
- Example curl/Python snippets

- [ ] **Step 3: Commit**

```bash
git add docs/integration-guide-pointcloud-benchmark.md
git commit -m "docs: add integration guide for pointcloud-benchmark repo"
```

---

## Chunk 6: Final Verification

### Task 9: Run full test suite and apply migration

- [ ] **Step 1: Run all backend tests**

Run: `cd /home/jan/Projects/benchvault/backend && uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Build frontend**

Run: `cd /home/jan/Projects/benchvault/frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Apply migration in Docker (if running)**

Run: `docker compose exec backend alembic upgrade head` (only if Docker is running)
Expected: Migration applies successfully.

- [ ] **Step 4: Verify no uncommitted changes**

Run: `git status`
Expected: Clean working tree (all changes committed).
