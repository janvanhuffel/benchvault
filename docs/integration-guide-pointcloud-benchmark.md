# Integration Guide: pointcloud-benchmark → BenchVault

This guide explains how to submit evaluation results from the `pointcloud-benchmark`
pipeline into BenchVault via the `POST /api/runs` endpoint.

## Overview of the data flow

```
evaluate.py --dataset <ds> --models <model> --output results.json
                            |
                            v
                      results.json   (per-model, per-class metrics)
                            |
                   submit_to_benchvault.py
                            |
                            v
                  POST /api/runs  (BenchVault)
```

`evaluate.py` writes a `results.json` that contains scalar metrics (`miou`, `oa`,
`macc`) and per-class breakdowns (`per_class_iou`, `per_class_precision`,
`per_class_recall`). The BenchVault submission endpoint accepts exactly this split:
scalar values go into `metrics`, per-class dicts go into `per_class_metrics`.

---

## Pre-registration requirements

BenchVault validates that the project, dataset, dataset version, and all metrics
referenced in a submission already exist in the database. Create them via Alembic
migrations (or the dataset API) before the first run is submitted.

### Project

One project per benchmark initiative, e.g. `pointcloud-segmentation`.

### Datasets and dataset versions

Each base dataset in `datasets.py` needs a corresponding BenchVault dataset and at
least one dataset version. The class names registered on the dataset version must
**exactly match** the keys used in the per-class metric dicts that `evaluate.py`
emits.

`evaluate.py` uses integer string keys (`"0"`, `"1"`, …) in `results.json` when no
class names are supplied, and named class strings when they are (via `--class-names`
or the registry). The BenchVault validation enforces an exact set match, so the class
names on the dataset version must match whatever keys appear in the submitted
`per_class_metrics` dict.

**Recommended approach:** always pass `--class-names` (or rely on the dataset
registry in `datasets.py`) and register the same names in BenchVault.

#### railway dataset

| Field | Value |
|---|---|
| BenchVault name | `railway` |
| Version | `v1.0` (or whichever version your data is at) |
| num_classes | 13 |
| class_names | `ground`, `platform`, `cable`, `vegetation`, `rail`, `traverse`, `pole`, `registration arm`, `tensiondevice`, `balise`, `diskinsulator`, `sectioninsulator`, `noise` |
| sensor | LiDAR |
| file_type | `laz` |

#### whu dataset

| Field | Value |
|---|---|
| BenchVault name | `whu` |
| Version | `v1.0` |
| num_classes | 10 |
| class_names | `rail`, `trackbed`, `masts`, `supportdevices`, `cable`, `fences`, `pole`, `vegetation`, `buildings`, `ground` |
| sensor | LiDAR |
| file_type | `laz` |

#### whu-new dataset

Same class schema as `whu`; register as a separate BenchVault dataset `whu-new` with
version `v1.0`.

### Metrics

The following metrics must be registered in BenchVault before any run can reference
them. The migration `008_add_per_class_metrics.py` already seeds `iou`,
`precision_class`, and `recall_class` as per-class metrics. Note that `precision` and
`recall` exist as separate scalar metrics from the demo seed data. Add the scalar
metrics separately.

| name | higher_is_better | is_per_class | maps from |
|---|---|---|---|
| `miou` | true | false | `results["miou"]` |
| `oa` | true | false | `results["oa"]` |
| `macc` | true | false | `results["macc"]` |
| `iou` | true | **true** | `results["per_class_iou"]` |
| `precision_class` | true | **true** | `results["per_class_precision"]` |
| `recall_class` | true | **true** | `results["per_class_recall"]` |

`iou`, `precision_class`, and `recall_class` are already seeded by migration
`008_add_per_class_metrics`. Add `miou`, `oa`, and `macc` in a new migration or via
the API.

---

## `POST /api/runs` payload structure

```json
{
  "project": "pointcloud-segmentation",
  "model_name": "ptv3-base",
  "model_version": "v1.0",
  "dataset": "railway",
  "dataset_version": "v1.0",
  "epoch": 50,
  "note": "baseline run, no augmentation",
  "metrics": {
    "miou": 0.712,
    "oa":   0.891,
    "macc": 0.734
  },
  "per_class_metrics": {
    "iou": {
      "ground": 0.91,
      "platform": 0.77,
      "cable": 0.65,
      "vegetation": 0.88,
      "rail": 0.83,
      "traverse": 0.72,
      "pole": 0.69,
      "registration arm": 0.61,
      "tensiondevice": 0.58,
      "balise": 0.54,
      "diskinsulator": 0.48,
      "sectioninsulator": 0.52,
      "noise": 0.79
    },
    "precision_class": { "ground": 0.93, "..." : 0.0 },
    "recall_class":    { "ground": 0.89, "..." : 0.0 }
  }
}
```

Rules enforced by the endpoint:
- `project`, `dataset`, and `dataset_version` must already exist.
- Every key in `metrics` must be a registered scalar metric (`is_per_class=false`).
- Every key in `per_class_metrics` must be a registered per-class metric
  (`is_per_class=true`).
- The class name keys in each per-class dict must **exactly match** the
  `class_names` list on the dataset version — no missing, no extra.
- `model_name` + `model_version` are auto-upserted if they do not yet exist.
- `epoch` is required (integer).

---

## Mapping `results.json` to the submission payload

`evaluate.py` (NAS mode) writes:

```json
{
  "dataset": "railway",
  "split": "test",
  "models": {
    "ptv3-base": {
      "miou": 0.712,
      "oa": 0.891,
      "macc": 0.734,
      "per_class_precision": { "ground": 0.93, ... },
      "per_class_recall":    { "ground": 0.89, ... },
      "per_class_iou":       { "ground": 0.91, ... }
    }
  }
}
```

Key name mapping:

| `results.json` key | BenchVault field | dest dict |
|---|---|---|
| `miou` | `miou` | `metrics` |
| `oa` | `oa` | `metrics` |
| `macc` | `macc` | `metrics` |
| `per_class_iou` | `iou` | `per_class_metrics` |
| `per_class_precision` | `precision_class` | `per_class_metrics` |
| `per_class_recall` | `recall_class` | `per_class_metrics` |

Note: when class names are taken from the dataset registry, `results.json` uses
**string class names** as keys. When `--class-names` is not passed, integer strings
(`"0"`, `"1"`, …) are used — in that case, the BenchVault dataset version must also
have class names registered as `["0", "1", ...]`, which is not recommended. Always
supply named class names.

---

## Python submission script

```python
#!/usr/bin/env python3
"""submit_to_benchvault.py — submit one model's results from results.json."""

import json
import sys
import requests

BENCHVAULT_URL = "http://localhost:8000"  # adjust for your deployment

# Metric name mapping: results.json key -> BenchVault metric name
SCALAR_METRICS = {"miou", "oa", "macc"}
PER_CLASS_METRIC_MAP = {
    "per_class_iou":       "iou",
    "per_class_precision": "precision_class",
    "per_class_recall":    "recall_class",
}


def submit_run(
    results_path: str,
    model_name: str,
    model_version: str,
    epoch: int,
    project: str,
    dataset_version: str = "v1.0",
    note: str | None = None,
):
    with open(results_path) as f:
        data = json.load(f)

    dataset_name = data["dataset"]

    # NAS-mode results.json has a "models" dict; local-mode has metrics at top level.
    if "models" in data:
        model_results = data["models"][model_name]
    else:
        model_results = data  # local mode: single model

    scalar_metrics = {k: v for k, v in model_results.items() if k in SCALAR_METRICS}
    per_class_metrics = {}
    for src_key, dst_key in PER_CLASS_METRIC_MAP.items():
        if src_key in model_results:
            per_class_metrics[dst_key] = model_results[src_key]

    payload = {
        "project": project,
        "model_name": model_name,
        "model_version": model_version,
        "dataset": dataset_name,
        "dataset_version": dataset_version,
        "epoch": epoch,
        "note": note,
        "metrics": scalar_metrics,
        "per_class_metrics": per_class_metrics or None,
    }

    resp = requests.post(f"{BENCHVAULT_URL}/api/runs", json=payload)
    resp.raise_for_status()
    created = resp.json()
    print(f"Submitted run id={created['id']} at {created['created_at']}")
    return created


if __name__ == "__main__":
    # Example: python submit_to_benchvault.py results.json ptv3-base v1.0 50
    results_path, model_name, model_version, epoch = sys.argv[1:5]
    submit_run(
        results_path=results_path,
        model_name=model_name,
        model_version=model_version,
        epoch=int(epoch),
        project="pointcloud-segmentation",
        dataset_version="v1.0",
    )
```

---

## curl example

```bash
curl -s -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project": "pointcloud-segmentation",
    "model_name": "ptv3-base",
    "model_version": "v1.0",
    "dataset": "railway",
    "dataset_version": "v1.0",
    "epoch": 50,
    "note": "baseline run",
    "metrics": {
      "miou": 0.712,
      "oa": 0.891,
      "macc": 0.734
    },
    "per_class_metrics": {
      "iou": {
        "ground": 0.91,
        "platform": 0.77,
        "cable": 0.65,
        "vegetation": 0.88,
        "rail": 0.83,
        "traverse": 0.72,
        "pole": 0.69,
        "registration arm": 0.61,
        "tensiondevice": 0.58,
        "balise": 0.54,
        "diskinsulator": 0.48,
        "sectioninsulator": 0.52,
        "noise": 0.79
      },
      "precision_class": {
        "ground": 0.93, "platform": 0.80, "cable": 0.68,
        "vegetation": 0.90, "rail": 0.85, "traverse": 0.74,
        "pole": 0.71, "registration arm": 0.63, "tensiondevice": 0.60,
        "balise": 0.57, "diskinsulator": 0.51, "sectioninsulator": 0.55,
        "noise": 0.82
      },
      "recall_class": {
        "ground": 0.89, "platform": 0.74, "cable": 0.62,
        "vegetation": 0.86, "rail": 0.81, "traverse": 0.70,
        "pole": 0.67, "registration arm": 0.59, "tensiondevice": 0.56,
        "balise": 0.51, "diskinsulator": 0.45, "sectioninsulator": 0.49,
        "noise": 0.76
      }
    }
  }'
```

A successful response returns HTTP 201:

```json
{"id": 42, "created_at": "2026-03-13T10:00:00Z"}
```

---

## Alembic migration to seed the pointcloud-benchmark project

Add a new migration in `backend/alembic/versions/` to register all entities before
any runs are submitted:

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Project
    op.execute("INSERT INTO projects (name) VALUES ('pointcloud-segmentation')")

    # Scalar metrics (miou, oa, macc not yet seeded)
    metrics_table = sa.table(
        "metrics",
        sa.column("name", sa.String),
        sa.column("higher_is_better", sa.Boolean),
        sa.column("description", sa.String),
        sa.column("is_per_class", sa.Boolean),
    )
    op.bulk_insert(metrics_table, [
        {"name": "miou",  "higher_is_better": True,  "description": "Mean IoU",            "is_per_class": False},
        {"name": "oa",    "higher_is_better": True,  "description": "Overall accuracy",     "is_per_class": False},
        {"name": "macc",  "higher_is_better": True,  "description": "Mean class accuracy",  "is_per_class": False},
    ])

    # railway dataset + version
    op.execute("""
        INSERT INTO datasets (name, modality, task, source_url)
        VALUES ('railway', 'point cloud', '3D semantic segmentation',
                'https://nas01.intern.kapernikov.com:9000/pointcloud.benchmark')
    """)
    op.execute("""
        INSERT INTO dataset_versions
          (dataset_id, version, num_classes, class_names,
           train_count, val_count, test_count, total_samples,
           total_size_gb, sensor, file_type, storage_url)
        VALUES
          ((SELECT id FROM datasets WHERE name='railway'), 'v1.0', 13,
           ARRAY['ground','platform','cable','vegetation','rail','traverse','pole',
                 'registration arm','tensiondevice','balise','diskinsulator',
                 'sectioninsulator','noise'],
           0, 0, 0, 0, 0.0, 'LiDAR', 'laz',
           's3://nas01.intern.kapernikov.com:9000/pointcloud.benchmark/datasets/railway')
    """)

    # whu dataset + version
    op.execute("""
        INSERT INTO datasets (name, modality, task, source_url)
        VALUES ('whu', 'point cloud', '3D semantic segmentation',
                'https://nas01.intern.kapernikov.com:9000/pointcloud.benchmark')
    """)
    op.execute("""
        INSERT INTO dataset_versions
          (dataset_id, version, num_classes, class_names,
           train_count, val_count, test_count, total_samples,
           total_size_gb, sensor, file_type, storage_url)
        VALUES
          ((SELECT id FROM datasets WHERE name='whu'), 'v1.0', 10,
           ARRAY['rail','trackbed','masts','supportdevices','cable',
                 'fences','pole','vegetation','buildings','ground'],
           0, 0, 0, 0, 0.0, 'LiDAR', 'laz',
           's3://nas01.intern.kapernikov.com:9000/pointcloud.benchmark/datasets/whu_railway')
    """)
```

---

## Handling NaN values

`evaluate.py` emits `NaN` for classes that have no ground-truth points (division by
zero). `json.dump` writes these as `NaN`, which is not valid JSON and will cause
`requests.post` to fail. Filter them before submitting:

```python
import math

def drop_nans(d: dict) -> dict:
    return {k: v for k, v in d.items() if not math.isnan(v)}

per_class_metrics = {
    dst_key: drop_nans(model_results[src_key])
    for src_key, dst_key in PER_CLASS_METRIC_MAP.items()
    if src_key in model_results
}
```

Note that dropping a class reduces the set of submitted class names. BenchVault
validates that the submitted set **exactly matches** the dataset version's
`class_names`. If NaN classes must be excluded, either register a dataset version
with only the non-NaN class names, or substitute `0.0` for NaN values instead.

---

## Common errors

| HTTP status | `detail` | Fix |
|---|---|---|
| 422 | `Project not found: …` | Add the project via migration or API |
| 422 | `Dataset not found: …` | Register the dataset |
| 422 | `Dataset_version not found: …` | Register the dataset version |
| 422 | `Unknown metric(s): …` | Add missing metrics to the metrics table |
| 422 | `Metric 'miou' is a per-class metric …` | Check `is_per_class` flag on that metric |
| 422 | `Class name mismatch for metric 'iou': missing: …` | Class names in payload must exactly match `dataset_version.class_names` |
| 422 | `Dataset version does not define class names` | Set `class_names` on the dataset version |
