# Per-Class Metrics Design

## Problem

BenchVault stores benchmark metrics as flat `{metric_name: float}` dicts. Point cloud segmentation benchmarks produce per-class metrics (IoU, precision, recall per class) that are critical for model comparison but don't fit this flat structure. The class list varies by dataset version (e.g. railway has 13 classes, WHU has 10).

## Decisions

- **Storage**: New `run_class_metrics` table (Approach 1 — dedicated table, not JSON blob or nullable column on existing table)
- **Submission format**: Nested dict under a new optional `per_class_metrics` field — `{ "iou": {"ground": 0.98, ...}, ... }`
- **Metric registration**: Reuse existing `metrics` table with `is_per_class` boolean flag to distinguish scalar vs per-class metric types
- **Validation**: Strict — submitted class names must exactly match the dataset version's `class_names` (no missing, no extras)
- **Project-scoping of metrics**: Deferred — metrics remain global for now

## Data Model

### Modified table: `metrics`

Add column:
- `is_per_class` — `Boolean`, default `False`, non-nullable, `server_default=False` (safe for existing rows)

Scalar metrics (`miou`, `oa`, `macc`) have `is_per_class=False`. Per-class metric types (`iou`, `precision`, `recall`) have `is_per_class=True`.

### New table: `run_class_metrics`

| Column       | Type    | Constraints                          |
|--------------|---------|--------------------------------------|
| `id`         | Integer | PK                                   |
| `run_id`     | Integer | FK → `benchmark_runs.id`, not null   |
| `metric_id`  | Integer | FK → `metrics.id`, not null          |
| `class_name` | String  | not null                             |
| `value`      | Float   | not null                             |

- Unique constraint: `(run_id, metric_id, class_name)`
- Cascade delete from `BenchmarkRun` (like `run_metrics`)

### New SQLAlchemy model: `RunClassMetric`

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

Add to `BenchmarkRun`:
```python
run_class_metrics = relationship("RunClassMetric", back_populates="run", cascade="all, delete-orphan")
```

Add to `Metric`:
```python
run_class_metrics = relationship("RunClassMetric", back_populates="metric")
```

### Migration

Single Alembic migration that:
1. Adds `is_per_class` column to `metrics` with `server_default=sa.false()` (existing rows get `False`)
2. Creates `run_class_metrics` table with unique constraint
3. Inserts seed per-class metric rows: `iou` (`higher_is_better=True`), `precision` (`higher_is_better=True`), `recall` (`higher_is_better=True`) — all with `is_per_class=True`

### Unchanged tables

`benchmark_runs`, `run_metrics`, `dataset_versions`, `projects`, `datasets`, `model_versions` — no changes.

The existing `dataset_versions.class_names` (`StringArray`) serves as the validation source for per-class metric submissions.

## API Changes

### Submission: `POST /api/runs`

**Schema change** — `RunSubmission` adds:

```python
per_class_metrics: dict[str, dict[str, float]] | None = None
```

Example payload:

```json
{
  "project": "pointcloud-segmentation",
  "model_name": "copernnet",
  "model_version": "new-labels-val",
  "dataset": "railway",
  "dataset_version": "v2.0",
  "epoch": 1000,
  "metrics": {
    "miou": 0.618,
    "oa": 0.9795,
    "macc": 0.6343
  },
  "per_class_metrics": {
    "iou": {
      "ground": 0.9863,
      "platform": 0.9724,
      "cable": 0.9676,
      "vegetation": 0.9451,
      "rail": 0.6630,
      "traverse": 0.9280,
      "pole": 0.8965,
      "registration arm": 0.7910,
      "tensiondevice": 0.4586,
      "balise": 0.3247,
      "diskinsulator": 0.0000,
      "sectioninsulator": 0.0000,
      "noise": 0.1013
    },
    "precision": {
      "ground": 0.9987,
      "platform": 0.9948,
      "...": "..."
    },
    "recall": {
      "ground": 0.9876,
      "platform": 0.9773,
      "...": "..."
    }
  }
}
```

**Validation rules:**

1. Each key in `per_class_metrics` must be a registered metric with `is_per_class=True` → 422 if not
2. Each key in `metrics` (scalar) must reference a metric with `is_per_class=False` → 422 if a per-class metric is submitted as scalar
3. If the dataset version's `class_names` is null/empty and `per_class_metrics` is provided → 422 ("Dataset version does not define class names")
4. For each per-class metric dict, the set of class name keys must exactly equal the dataset version's `class_names` — same count, same names → 422 if mismatch
5. `per_class_metrics` is optional — omitting it is fine (backward compatible)

**Response**: Unchanged — `RunCreatedResponse` with `id` and `created_at`.

### Compare: `GET /api/compare`

**Schema change** — `CompareResponse` adds:

```python
per_class_metrics: list[PerClassCompareGroup]
```

New schemas:

```python
class PerClassRunValues(BaseModel):
    run_id: int
    values: dict[str, float]  # class_name → value

class PerClassCompareGroup(BaseModel):
    metric_name: str              # e.g. "iou"
    higher_is_better: bool
    classes: list[str]            # ordered class names from dataset version
    runs: list[PerClassRunValues] # one entry per run, in same order as CompareResponse.runs

class CompareResponse(BaseModel):
    metric_names: list[str]                        # scalar metrics only (is_per_class=False)
    higher_is_better: dict[str, bool]              # scalar metrics only
    runs: list[RunResponse]
    per_class_metrics: list[PerClassCompareGroup]  # NEW
```

**Behavior:**

- `metric_names` and `higher_is_better` continue to list only scalar metrics (`is_per_class=False`). Per-class metrics have their own section and are not duplicated here.
- If all compared runs share the same dataset version AND have per-class data → populate `per_class_metrics` groups
- If runs have different dataset versions → `per_class_metrics` is an empty list
- If no runs have per-class data → `per_class_metrics` is an empty list
- `classes` list uses the ordering from `dataset_version.class_names`

**Per-class data is compare-only.** `RunResponse` and `_run_to_response()` are unchanged — individual run listings and the project page do not include per-class metrics.

## Frontend: Compare Page

The existing scalar metrics table stays unchanged. A new section appears below it:

### Per-Class Metrics Table

- **Rows**: Class names (ordered as in dataset version)
- **Column groups**: One group per per-class metric type (e.g. precision, recall, iou)
- **Sub-columns**: One per compared run (model name in header)
- **Cell coloring**: Inline `background-color` using HSL interpolation — red (0.0) → yellow (0.5) → green (1.0). Values are always in [0, 1] for these metrics. Uses opacity to work with the existing dark/light theme in `App.css`.
- **Best highlighting**: Bold for best value per class per metric across runs
- **Visibility**: Only shown when `per_class_metrics` is non-empty
- **Cross-dataset message**: When compared runs have different dataset versions, show: "Per-class comparison is only available when all runs use the same dataset version."
- **No changes to `api.js`**: `compareRuns` already returns whatever the backend sends; the frontend just reads the new fields.

### Layout reference

```
┌─────────────────────────────────────────────────────────┐
│ Scalar Metrics (existing)                               │
│ ┌─────────┬──────────┬──────────┐                       │
│ │ Metric  │ Model A  │ Model B  │                       │
│ │ miou    │ 0.6180   │ 0.6995   │                       │
│ │ oa      │ 0.9795   │ 0.9844   │                       │
│ │ macc    │ 0.6343   │ 0.8437   │                       │
│ └─────────┴──────────┴──────────┘                       │
│                                                         │
│ Per-Class Metrics (new)                                 │
│ ┌───────────┬────────────────┬──────────────┬──────────…│
│ │ Class     │  precision (↑) │  recall (↑)  │  iou (↑) …│
│ │           │  A    │  B    │  A    │  B   │  A   │  B …│
│ │ ground    │ .9987 │ .9996 │ .9876 │ .963 │ .986 │ .96…│
│ │ platform  │ .9948 │ .9228 │ .9773 │ .999 │ .972 │ .92…│
│ │ ...       │       │       │       │      │      │    …│
│ └───────────┴───────┴───────┴───────┴──────┴──────┴────…│
└─────────────────────────────────────────────────────────┘
```

## Testing

### Backend tests

Extend `conftest.py` seed data:
- Add per-class metrics (`iou`, `precision`, `recall` with `is_per_class=True`) to the seeded metrics
- Add `class_names` to the seeded `DatasetVersion` (currently missing — needed for per-class validation tests)

**Submission tests:**
- Happy path: submit run with scalar + per-class metrics → 201, data stored correctly
- Submit with only scalar metrics (no `per_class_metrics`) → 201 (backward compatible)
- Unknown per-class metric name → 422
- Scalar metric submitted as per-class (or vice versa) → 422
- Class names don't match dataset version (missing class) → 422
- Class names don't match dataset version (extra class) → 422
- Class names don't match dataset version (wrong name) → 422

**Compare tests:**
- Compare runs with per-class data → response includes populated `per_class_metrics`
- Compare runs without per-class data → `per_class_metrics` is empty list
- Compare runs from different dataset versions → `per_class_metrics` is empty list

## Integration Guide (post-implementation deliverable)

Separate from the BenchVault code changes. Produced after implementation is complete by a subagent that analyzes both repos.

A guide for the `pointcloud-benchmark` repo explaining:
- The JSON payload structure to POST to BenchVault
- How to map `results.json` output to the submission format
- Which metrics/datasets/dataset versions need to be pre-registered in BenchVault
- Example curl commands and/or Python snippet for submitting results
