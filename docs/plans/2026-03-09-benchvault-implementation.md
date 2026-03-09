# BenchVault Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build v1 of BenchVault — a full-stack ML benchmark tracking tool with strict validation, a REST API for submissions, and a React frontend for browsing/comparing results.

**Architecture:** FastAPI backend with SQLAlchemy + Alembic talking to PostgreSQL. React SPA frontend served by Nginx. All three services orchestrated via Docker Compose. Backend handles all validation and comparison logic; frontend is read-only.

**Tech Stack:** Python (FastAPI, SQLAlchemy, Alembic, Pydantic, pytest), PostgreSQL, React (Vite, React Router), plain CSS, Docker Compose.

---

## Task 1: Repo Structure and Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `backend/requirements.txt`
- Create: `frontend/Dockerfile`
- Create: `.gitignore`

**Step 1: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Node
node_modules/
dist/

# Environment
.env
*.env.local

# IDE
.vscode/
.idea/
```

**Step 2: Create `backend/requirements.txt`**

```
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
alembic
pydantic
```

**Step 3: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Step 4: Create `frontend/Dockerfile`**

Two-stage: Node for building, Nginx for serving. Dev mode uses Vite dev server instead.

```dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
```

For dev, use a simpler override that just runs `npm run dev`.

**Step 5: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: benchvault
      POSTGRES_PASSWORD: benchvault
      POSTGRES_DB: benchvault
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://benchvault:benchvault@db:5432/benchvault
    depends_on:
      - db
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  pgdata:
```

**Step 6: Verify `docker compose config` parses without errors**

Run: `docker compose config`
Expected: valid YAML output, no errors.

**Step 7: Commit**

```bash
git add .gitignore docker-compose.yml backend/Dockerfile backend/requirements.txt frontend/Dockerfile
git commit -m "feat: repo scaffold with Docker Compose, Dockerfiles, and dependencies"
```

---

## Task 2: Backend Foundation

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/database.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/requirements-dev.txt`

**Step 1: Create `backend/requirements-dev.txt`**

```
-r requirements.txt
pytest
httpx
```

**Step 2: Create `backend/app/config.py`**

```python
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://benchvault:benchvault@localhost:5432/benchvault",
)
```

**Step 3: Create `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 4: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BenchVault")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

**Step 5: Write the failing test**

Create `backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)
```

Create `backend/tests/test_health.py`:

```python
def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 6: Run test to verify it passes**

Run: `cd backend && pip install -r requirements-dev.txt && pytest tests/test_health.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add backend/
git commit -m "feat: FastAPI backend foundation with health endpoint and test"
```

---

## Task 3: Database Models

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/tests/test_models.py`

**Step 1: Write model test**

Create `backend/tests/test_models.py` — test that all models can be instantiated and have expected columns:

```python
from app.models import (
    Project, Dataset, DatasetVersion, Metric,
    ModelVersion, BenchmarkRun, RunMetric,
)


def test_project_has_name():
    p = Project(name="test-project")
    assert p.name == "test-project"


def test_metric_has_higher_is_better():
    m = Metric(name="accuracy", higher_is_better=True)
    assert m.higher_is_better is True


def test_model_version_has_name_and_version():
    mv = ModelVersion(model_name="gpt-4", model_version="v1")
    assert mv.model_name == "gpt-4"
    assert mv.model_version == "v1"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: FAIL — cannot import models.

**Step 3: Create `backend/app/models.py`**

```python
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    runs = relationship("BenchmarkRun", back_populates="project")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    versions = relationship("DatasetVersion", back_populates="dataset")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    version = Column(String, nullable=False)

    dataset = relationship("Dataset", back_populates="versions")
    runs = relationship("BenchmarkRun", back_populates="dataset_version")

    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_dataset_version"),
    )


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    higher_is_better = Column(Boolean, nullable=False, default=True)
    description = Column(Text, nullable=True)

    run_metrics = relationship("RunMetric", back_populates="metric")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)

    runs = relationship("BenchmarkRun", back_populates="model_version")

    __table_args__ = (
        UniqueConstraint("model_name", "model_version", name="uq_model_version"),
    )


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False)
    dataset_version_id = Column(Integer, ForeignKey("dataset_versions.id"), nullable=False)
    epoch = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="runs")
    model_version = relationship("ModelVersion", back_populates="runs")
    dataset_version = relationship("DatasetVersion", back_populates="runs")
    run_metrics = relationship("RunMetric", back_populates="run", cascade="all, delete-orphan")


class RunMetric(Base):
    __tablename__ = "run_metrics"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("benchmark_runs.id"), nullable=False)
    metric_id = Column(Integer, ForeignKey("metrics.id"), nullable=False)
    value = Column(Float, nullable=False)

    run = relationship("BenchmarkRun", back_populates="run_metrics")
    metric = relationship("Metric", back_populates="run_metrics")

    __table_args__ = (
        UniqueConstraint("run_id", "metric_id", name="uq_run_metric"),
    )
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat: SQLAlchemy models for all tables"
```

---

## Task 4: Alembic Setup and Seed Data

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial_schema.py`
- Create: `backend/alembic/versions/002_seed_data.py`

**Step 1: Initialize Alembic**

Run: `cd backend && alembic init alembic`

**Step 2: Configure `alembic/env.py`**

Edit to import `Base` and all models, use `DATABASE_URL` from config:

```python
from app.config import DATABASE_URL
from app.database import Base
from app.models import *  # noqa: F401, F403 — ensures all models are registered

config.set_main_option("sqlalchemy.url", DATABASE_URL)
target_metadata = Base.metadata
```

**Step 3: Create initial migration**

Run: `cd backend && alembic revision --autogenerate -m "initial schema"`

Verify it creates all 7 tables with correct columns, constraints, and foreign keys.

**Step 4: Create seed data migration**

Create manually (not autogenerated):

```python
"""seed dummy data"""

from alembic import op

def upgrade():
    # Projects
    op.execute("INSERT INTO projects (name) VALUES ('demo-ocr-pipeline')")
    op.execute("INSERT INTO projects (name) VALUES ('demo-nlp-classifier')")

    # Datasets
    op.execute("INSERT INTO datasets (name) VALUES ('COCO-2017')")
    op.execute("INSERT INTO datasets (name) VALUES ('ImageNet-Val')")
    op.execute("INSERT INTO datasets (name) VALUES ('GLUE-MNLI')")

    # Dataset versions
    op.execute("""
        INSERT INTO dataset_versions (dataset_id, version)
        VALUES
            ((SELECT id FROM datasets WHERE name='COCO-2017'), 'v1.0'),
            ((SELECT id FROM datasets WHERE name='COCO-2017'), 'v2.0-cleaned'),
            ((SELECT id FROM datasets WHERE name='ImageNet-Val'), 'v1.0'),
            ((SELECT id FROM datasets WHERE name='GLUE-MNLI'), 'v1.0')
    """)

    # Metrics
    op.execute("""
        INSERT INTO metrics (name, higher_is_better, description) VALUES
            ('accuracy', true, 'Overall accuracy'),
            ('f1_score', true, 'F1 score'),
            ('precision', true, 'Precision'),
            ('recall', true, 'Recall'),
            ('loss', false, 'Loss value')
    """)

def downgrade():
    op.execute("DELETE FROM metrics")
    op.execute("DELETE FROM dataset_versions")
    op.execute("DELETE FROM datasets")
    op.execute("DELETE FROM projects")
```

**Step 5: Test migrations run against a real database**

Run: `docker compose up db -d && cd backend && alembic upgrade head`
Expected: all tables created, seed data inserted.

Verify: `docker compose exec db psql -U benchvault -c "SELECT * FROM metrics;"`
Expected: 5 rows.

**Step 6: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: Alembic migrations with initial schema and dummy seed data"
```

---

## Task 5: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas.py`

**Step 1: Create `backend/app/schemas.py`**

Request and response schemas for all API endpoints:

```python
from pydantic import BaseModel
from datetime import datetime


# --- Submission ---

class RunSubmission(BaseModel):
    project: str
    model_name: str
    model_version: str
    dataset: str
    dataset_version: str
    epoch: int | None = None
    note: str | None = None
    metrics: dict[str, float]


class RunCreatedResponse(BaseModel):
    id: int
    created_at: datetime


# --- Read responses ---

class ProjectResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class DatasetVersionResponse(BaseModel):
    id: int
    dataset_name: str
    version: str


class MetricResponse(BaseModel):
    id: int
    name: str
    higher_is_better: bool
    description: str | None

    model_config = {"from_attributes": True}


class MetricValueResponse(BaseModel):
    metric_name: str
    value: float
    higher_is_better: bool


class RunResponse(BaseModel):
    id: int
    project: str
    model_name: str
    model_version: str
    dataset: str
    dataset_version: str
    epoch: int | None
    note: str | None
    created_at: datetime
    metrics: list[MetricValueResponse]


class CompareResponse(BaseModel):
    metric_names: list[str]
    higher_is_better: dict[str, bool]
    runs: list[RunResponse]
```

**Step 2: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat: Pydantic request/response schemas"
```

---

## Task 6: API — Submit Run Endpoint

**Files:**
- Create: `backend/app/routes/__init__.py`
- Create: `backend/app/routes/runs.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/test_submit_run.py`
- Modify: `backend/tests/conftest.py` (add DB fixtures)

**Step 1: Update `conftest.py` with an in-memory SQLite test database**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(db):
    """Insert the minimum controlled entities for a valid run submission."""
    from app.models import Project, Dataset, DatasetVersion, Metric

    db.add(Project(name="test-project"))
    db.add(Dataset(name="test-dataset"))
    db.flush()

    dataset = db.query(Dataset).filter_by(name="test-dataset").one()
    db.add(DatasetVersion(dataset_id=dataset.id, version="v1.0"))

    db.add(Metric(name="accuracy", higher_is_better=True))
    db.add(Metric(name="f1_score", higher_is_better=True))
    db.commit()
    return db


@pytest.fixture
def seeded_client(seeded_db):
    def override_get_db():
        try:
            yield seeded_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

**Step 2: Write the failing tests**

Create `backend/tests/test_submit_run.py`:

```python
VALID_PAYLOAD = {
    "project": "test-project",
    "model_name": "my-model",
    "model_version": "v1",
    "dataset": "test-dataset",
    "dataset_version": "v1.0",
    "epoch": 10,
    "note": "test run",
    "metrics": {"accuracy": 0.95, "f1_score": 0.90},
}


def test_submit_valid_run(seeded_client):
    response = seeded_client.post("/api/runs", json=VALID_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "created_at" in data


def test_submit_unknown_project_rejected(seeded_client):
    payload = {**VALID_PAYLOAD, "project": "nonexistent"}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "project" in response.json()["detail"].lower()


def test_submit_unknown_dataset_rejected(seeded_client):
    payload = {**VALID_PAYLOAD, "dataset": "nonexistent"}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "dataset" in response.json()["detail"].lower()


def test_submit_unknown_dataset_version_rejected(seeded_client):
    payload = {**VALID_PAYLOAD, "dataset_version": "v99"}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "dataset_version" in response.json()["detail"].lower()


def test_submit_unknown_metric_rejected(seeded_client):
    payload = {**VALID_PAYLOAD, "metrics": {"accuracy": 0.9, "bogus_metric": 0.5}}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "bogus_metric" in response.json()["detail"].lower()


def test_submit_upserts_new_model_version(seeded_client):
    response = seeded_client.post("/api/runs", json=VALID_PAYLOAD)
    assert response.status_code == 201

    # Same model, new version
    payload = {**VALID_PAYLOAD, "model_version": "v2"}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 201
```

**Step 3: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_submit_run.py -v`
Expected: FAIL — route not found.

**Step 4: Implement the submit endpoint**

Create `backend/app/routes/__init__.py` (empty).

Create `backend/app/routes/runs.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Project, Dataset, DatasetVersion, Metric,
    ModelVersion, BenchmarkRun, RunMetric,
)
from app.schemas import RunSubmission, RunCreatedResponse

router = APIRouter(prefix="/api")


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

    # Validate all metrics
    submitted_metric_names = set(submission.metrics.keys())
    registered_metrics = (
        db.query(Metric).filter(Metric.name.in_(submitted_metric_names)).all()
    )
    registered_names = {m.name for m in registered_metrics}
    unknown = submitted_metric_names - registered_names
    if unknown:
        raise HTTPException(
            422,
            detail=f"Unknown metric(s): {', '.join(sorted(unknown))}. Register them first.",
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

    # Create run metrics
    metric_map = {m.name: m for m in registered_metrics}
    for metric_name, value in submission.metrics.items():
        db.add(RunMetric(run_id=run.id, metric_id=metric_map[metric_name].id, value=value))

    db.commit()
    db.refresh(run)

    return RunCreatedResponse(id=run.id, created_at=run.created_at)
```

Register in `backend/app/main.py`:

```python
from app.routes.runs import router as runs_router

app.include_router(runs_router)
```

**Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_submit_run.py -v`
Expected: all 6 PASS

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: POST /api/runs endpoint with strict validation"
```

---

## Task 7: API — Read and Compare Endpoints

**Files:**
- Create: `backend/app/routes/projects.py`
- Create: `backend/app/routes/compare.py`
- Create: `backend/app/routes/datasets.py`
- Create: `backend/app/routes/metrics.py`
- Modify: `backend/app/main.py` (register routers)
- Create: `backend/tests/test_read_endpoints.py`
- Create: `backend/tests/test_compare.py`

**Step 1: Write failing tests for read endpoints**

Create `backend/tests/test_read_endpoints.py`:

```python
def test_list_projects(seeded_client):
    response = seeded_client.get("/api/projects")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "test-project" in names


def test_list_datasets(seeded_client):
    response = seeded_client.get("/api/datasets")
    assert response.status_code == 200
    names = [d["name"] for d in response.json()]
    assert "test-dataset" in names


def test_list_metrics(seeded_client):
    response = seeded_client.get("/api/metrics")
    assert response.status_code == 200
    names = [m["name"] for m in response.json()]
    assert "accuracy" in names


def test_list_runs_for_project(seeded_client):
    # Submit a run first
    seeded_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "m", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v1.0",
        "metrics": {"accuracy": 0.9},
    })
    response = seeded_client.get("/api/projects/test-project/runs")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["metrics"][0]["metric_name"] == "accuracy"
```

**Step 2: Write failing tests for compare endpoint**

Create `backend/tests/test_compare.py`:

```python
def test_compare_runs(seeded_client):
    # Submit two runs
    r1 = seeded_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "m1", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v1.0",
        "metrics": {"accuracy": 0.9, "f1_score": 0.85},
    })
    r2 = seeded_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "m2", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v1.0",
        "metrics": {"accuracy": 0.95, "f1_score": 0.88},
    })

    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    response = seeded_client.get(f"/api/compare?run_ids={id1},{id2}")
    assert response.status_code == 200

    data = response.json()
    assert len(data["runs"]) == 2
    assert "accuracy" in data["metric_names"]
    assert data["higher_is_better"]["accuracy"] is True


def test_compare_no_ids_returns_error(seeded_client):
    response = seeded_client.get("/api/compare")
    assert response.status_code == 422
```

**Step 3: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_read_endpoints.py tests/test_compare.py -v`
Expected: FAIL

**Step 4: Implement read endpoints**

Create `backend/app/routes/projects.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, BenchmarkRun, RunMetric, Metric, ModelVersion, DatasetVersion, Dataset
from app.schemas import ProjectResponse, RunResponse, MetricValueResponse

router = APIRouter(prefix="/api")


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()


@router.get("/projects/{project_name}/runs", response_model=list[RunResponse])
def list_runs_for_project(project_name: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(name=project_name).first()
    if not project:
        raise HTTPException(404, detail=f"Project not found: {project_name}")

    runs = db.query(BenchmarkRun).filter_by(project_id=project.id).all()
    return [_run_to_response(run) for run in runs]


def _run_to_response(run: BenchmarkRun) -> RunResponse:
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
    )
```

Create `backend/app/routes/datasets.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dataset
from app.schemas import DatasetResponse

router = APIRouter(prefix="/api")


@router.get("/datasets", response_model=list[DatasetResponse])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).all()
```

Create `backend/app/routes/metrics.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Metric
from app.schemas import MetricResponse

router = APIRouter(prefix="/api")


@router.get("/metrics", response_model=list[MetricResponse])
def list_metrics(db: Session = Depends(get_db)):
    return db.query(Metric).all()
```

Create `backend/app/routes/compare.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BenchmarkRun
from app.routes.projects import _run_to_response
from app.schemas import CompareResponse

router = APIRouter(prefix="/api")


@router.get("/compare", response_model=CompareResponse)
def compare_runs(
    run_ids: str = Query(..., description="Comma-separated run IDs"),
    db: Session = Depends(get_db),
):
    try:
        ids = [int(x.strip()) for x in run_ids.split(",")]
    except ValueError:
        raise HTTPException(422, detail="run_ids must be comma-separated integers")

    runs = db.query(BenchmarkRun).filter(BenchmarkRun.id.in_(ids)).all()
    if len(runs) != len(ids):
        found_ids = {r.id for r in runs}
        missing = set(ids) - found_ids
        raise HTTPException(404, detail=f"Runs not found: {missing}")

    run_responses = [_run_to_response(r) for r in runs]

    # Collect all metric names and their directions
    all_metrics = {}
    for run_resp in run_responses:
        for m in run_resp.metrics:
            all_metrics[m.metric_name] = m.higher_is_better

    return CompareResponse(
        metric_names=sorted(all_metrics.keys()),
        higher_is_better=all_metrics,
        runs=run_responses,
    )
```

Register all routers in `backend/app/main.py`.

**Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/ -v`
Expected: all PASS

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: read and compare API endpoints"
```

---

## Task 8: Frontend Scaffold

**Files:**
- Create: `frontend/package.json` (via `npm create vite@latest`)
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/api.js`
- Create: `frontend/src/App.css`
- Create: `frontend/Dockerfile.dev`
- Create: `frontend/nginx.conf`

**Step 1: Scaffold React app with Vite**

Run: `cd frontend && npm create vite@latest . -- --template react`

**Step 2: Install React Router**

Run: `cd frontend && npm install react-router-dom`

**Step 3: Create `frontend/src/api.js`**

Thin wrapper for backend calls:

```javascript
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function fetchJson(path) {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

export function getProjects() {
  return fetchJson("/api/projects");
}

export function getProjectRuns(projectName) {
  return fetchJson(`/api/projects/${encodeURIComponent(projectName)}/runs`);
}

export function getDatasets() {
  return fetchJson("/api/datasets");
}

export function getMetrics() {
  return fetchJson("/api/metrics");
}

export function compareRuns(runIds) {
  return fetchJson(`/api/compare?run_ids=${runIds.join(",")}`);
}
```

**Step 4: Create `frontend/src/App.jsx` with routing**

```jsx
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import ProjectList from "./pages/ProjectList";
import ProjectDetail from "./pages/ProjectDetail";
import Compare from "./pages/Compare";
import Leaderboard from "./pages/Leaderboard";

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
```

**Step 5: Create `frontend/Dockerfile.dev`**

```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
```

**Step 6: Create `frontend/nginx.conf`**

```nginx
server {
    listen 3000;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Step 7: Verify dev server starts**

Run: `cd frontend && npm run dev` — confirm it starts without errors.

**Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: React frontend scaffold with routing and API client"
```

---

## Task 9: Frontend — Project List Page

**Files:**
- Create: `frontend/src/pages/ProjectList.jsx`
- Create: `frontend/src/pages/ProjectList.css`

**Step 1: Implement ProjectList page**

Fetches projects from API, renders as clickable list linking to `/projects/:name`.

```jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getProjects } from "../api";
import "./ProjectList.css";

export default function ProjectList() {
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    getProjects().then(setProjects);
  }, []);

  return (
    <div className="project-list">
      <h1>Projects</h1>
      <ul>
        {projects.map((p) => (
          <li key={p.id}>
            <Link to={`/projects/${encodeURIComponent(p.name)}`}>{p.name}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

**Step 2: Verify visually**

Run `docker compose up`, navigate to `http://localhost:3000`, confirm project list loads.

**Step 3: Commit**

```bash
git add frontend/src/pages/
git commit -m "feat: project list page"
```

---

## Task 10: Frontend — Project Detail Page

**Files:**
- Create: `frontend/src/pages/ProjectDetail.jsx`
- Create: `frontend/src/pages/ProjectDetail.css`

**Step 1: Implement ProjectDetail page**

Shows all runs for a project in a table. Columns: model, dataset, dataset version, epoch, date, and all metric values. Checkboxes to select runs for comparison. A "Compare Selected" button navigates to `/compare?run_ids=1,2,3`.

Filtering controls: dropdowns for dataset, dataset version, model name, model version. All client-side filtering against the fetched data.

```jsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getProjectRuns } from "../api";

export default function ProjectDetail() {
  const { name } = useParams();
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [filters, setFilters] = useState({
    dataset: "", datasetVersion: "", modelName: "", modelVersion: "",
  });

  useEffect(() => {
    getProjectRuns(name).then(setRuns);
  }, [name]);

  const filtered = runs.filter((r) => {
    if (filters.dataset && r.dataset !== filters.dataset) return false;
    if (filters.datasetVersion && r.dataset_version !== filters.datasetVersion) return false;
    if (filters.modelName && r.model_name !== filters.modelName) return false;
    if (filters.modelVersion && r.model_version !== filters.modelVersion) return false;
    return true;
  });

  // ... render table with checkboxes, filter dropdowns, compare button
}
```

**Step 2: Verify visually**

Seed some runs via API, confirm table renders with filters and selection.

**Step 3: Commit**

```bash
git add frontend/src/pages/ProjectDetail.*
git commit -m "feat: project detail page with run table and filters"
```

---

## Task 11: Frontend — Comparison Page

**Files:**
- Create: `frontend/src/pages/Compare.jsx`
- Create: `frontend/src/pages/Compare.css`

**Step 1: Implement Compare page**

Reads `run_ids` from URL query params. Calls `GET /api/compare?run_ids=...`. Renders a table where:
- Rows = metric names
- Columns = runs (labeled as model_name/model_version)
- Best value per row is highlighted (uses `higher_is_better` to determine direction)

```jsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { compareRuns } from "../api";

export default function Compare() {
  const [searchParams] = useSearchParams();
  const [data, setData] = useState(null);

  useEffect(() => {
    const ids = searchParams.get("run_ids")?.split(",").map(Number) || [];
    if (ids.length > 0) {
      compareRuns(ids).then(setData);
    }
  }, [searchParams]);

  // Highlight logic: for each metric row, find the best value
  // If higher_is_better, highlight the max. Otherwise, highlight the min.

  // ... render comparison table
}
```

**Step 2: Verify visually**

Navigate to `/compare?run_ids=1,2` with seeded data. Confirm side-by-side table with highlighting.

**Step 3: Commit**

```bash
git add frontend/src/pages/Compare.*
git commit -m "feat: comparison page with best-value highlighting"
```

---

## Task 12: Frontend — Leaderboard Page

**Files:**
- Create: `frontend/src/pages/Leaderboard.jsx`
- Create: `frontend/src/pages/Leaderboard.css`

**Step 1: Implement Leaderboard page**

Dropdowns to select: dataset, dataset version, metric to rank by. Fetches runs (can reuse project runs endpoint or add a cross-project runs endpoint if needed), sorts by chosen metric, displays ranked table.

For v1, scope leaderboard to a single project (selected via dropdown) to avoid needing a new endpoint. The table shows rank, model name, model version, metric value, sorted by the chosen metric respecting `higher_is_better`.

**Step 2: Verify visually**

Confirm leaderboard renders with correct ranking.

**Step 3: Commit**

```bash
git add frontend/src/pages/Leaderboard.*
git commit -m "feat: leaderboard page with metric ranking"
```

---

## Task 13: Docker Compose End-to-End Verification

**Files:**
- Modify: `docker-compose.yml` (if needed for final tweaks)
- Create: `backend/scripts/wait_for_db.py` (optional — wait for PostgreSQL readiness)

**Step 1: Run full stack**

```bash
docker compose up --build
```

**Step 2: Run Alembic migrations**

```bash
docker compose exec backend alembic upgrade head
```

**Step 3: Submit a test run via curl**

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project": "demo-ocr-pipeline",
    "model_name": "test-model",
    "model_version": "v1",
    "dataset": "COCO-2017",
    "dataset_version": "v1.0",
    "epoch": 5,
    "note": "smoke test",
    "metrics": {"accuracy": 0.92, "f1_score": 0.88}
  }'
```

Expected: 201 with run ID.

**Step 4: Verify frontend**

Open `http://localhost:3000`:
- Project list shows seeded projects
- Click project → runs table shows the submitted run
- Select run → compare page works
- Leaderboard ranks correctly

**Step 5: Verify rejection of unknown metric**

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project": "demo-ocr-pipeline",
    "model_name": "test-model",
    "model_version": "v1",
    "dataset": "COCO-2017",
    "dataset_version": "v1.0",
    "metrics": {"accuracy": 0.9, "fake_metric": 0.5}
  }'
```

Expected: 422 with error mentioning `fake_metric`.

**Step 6: Commit any final fixes**

```bash
git add -A
git commit -m "feat: docker compose end-to-end verified"
```

---

## Task 14: Document API Payload

**Files:**
- Create: `docs/api-payload.md`

**Step 1: Write submission payload documentation**

Document the JSON schema for `POST /api/runs`, the validation rules, example payloads (success + rejection), and a curl example. This is the reference your benchmark script will use.

**Step 2: Commit**

```bash
git add docs/api-payload.md
git commit -m "docs: API submission payload reference"
```
