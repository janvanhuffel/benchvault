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
