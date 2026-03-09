# BenchVault API -- Submission Payload Reference

Base URL depends on your environment:

| Environment | Base URL |
|---|---|
| Local dev | `http://localhost:8000` |
| Production (Tailscale) | Your Kubernetes service address |

---

## POST /api/runs

Submit a benchmark run.

### JSON Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `project` | string | yes | Project name (must already exist in DB) |
| `model_name` | string | yes | Model identifier (auto-created if new) |
| `model_version` | string | yes | Model version string (auto-created if new) |
| `dataset` | string | yes | Dataset name (must already exist in DB) |
| `dataset_version` | string | yes | Version of the dataset (must already exist for the given dataset) |
| `epoch` | integer \| null | no | Training epoch, if applicable |
| `note` | string \| null | no | Free-text note |
| `metrics` | object | yes | Map of metric name to float value. Every key must be a pre-registered metric. |

### Validation Rules

**Must be pre-registered** (the API rejects unknown values with 422):

- `project` -- looked up by exact name
- `dataset` -- looked up by exact name
- `dataset_version` -- looked up by version string within the given dataset
- Every key in `metrics` -- looked up by exact metric name

**Upserted automatically** (created on first use):

- `model_name` / `model_version` -- if the combination does not exist yet, a new `model_versions` row is inserted

### Successful Submission

**Request:**

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project": "demo-ocr-pipeline",
    "model_name": "tesseract-lstm",
    "model_version": "v4.1",
    "dataset": "COCO-2017",
    "dataset_version": "v1.0",
    "epoch": 30,
    "note": "baseline run",
    "metrics": {
      "accuracy": 0.921,
      "f1_score": 0.887,
      "loss": 0.214
    }
  }'
```

**Response (201 Created):**

```json
{
  "id": 5,
  "created_at": "2026-03-09T14:22:07.123456"
}
```

### Rejected Submission -- Unknown Metric

**Request:**

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project": "demo-ocr-pipeline",
    "model_name": "tesseract-lstm",
    "model_version": "v4.1",
    "dataset": "COCO-2017",
    "dataset_version": "v1.0",
    "metrics": {
      "accuracy": 0.921,
      "bleu_score": 0.45
    }
  }'
```

**Response (422 Unprocessable Entity):**

```json
{
  "detail": "Unknown metric(s): bleu_score. Register them first."
}
```

Other 422 errors follow the same shape (`{"detail": "..."}`) for unknown projects, datasets, and dataset versions.

---

## Read Endpoints (GET)

| Endpoint | Description |
|---|---|
| `GET /api/projects` | List all projects. Returns `[{id, name}, ...]` |
| `GET /api/datasets` | List all datasets. Returns `[{id, name}, ...]` |
| `GET /api/metrics` | List all metrics. Returns `[{id, name, higher_is_better, description}, ...]` |
| `GET /api/projects/{name}/runs` | List runs for a project. Returns full run objects with nested metrics. |
| `GET /api/compare?run_ids=1,2,3` | Compare runs side-by-side. Returns `{metric_names, higher_is_better, runs}`. |

### Quick curl examples

```bash
# List projects
curl http://localhost:8000/api/projects

# List registered metrics (useful before submitting)
curl http://localhost:8000/api/metrics

# List runs for a project
curl http://localhost:8000/api/projects/demo-ocr-pipeline/runs

# Compare two runs
curl "http://localhost:8000/api/compare?run_ids=1,2"
```

---

## Seed Data Reference

Pre-registered in the default migration:

- **Projects:** `demo-ocr-pipeline`, `demo-nlp-classifier`
- **Datasets:** `COCO-2017`, `ImageNet-Val`, `GLUE-MNLI`
- **Dataset versions:** `COCO-2017/v1.0`, `COCO-2017/v2.0-cleaned`, `ImageNet-Val/v1.0`, `GLUE-MNLI/v1.0`
- **Metrics:** `accuracy` (higher is better), `f1_score` (higher is better), `precision` (higher is better), `recall` (higher is better), `loss` (lower is better)
