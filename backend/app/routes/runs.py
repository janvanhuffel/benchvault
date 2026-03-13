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
