from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Project, BenchmarkRun
from app.schemas import (
    ProjectResponse,
    RunResponse,
    MetricValueResponse,
)

router = APIRouter(prefix="/api")


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


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()


@router.get("/projects/{project_name}/runs", response_model=list[RunResponse])
def list_runs_for_project(project_name: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(name=project_name).first()
    if not project:
        raise HTTPException(404, detail=f"Project not found: {project_name}")

    runs = (
        db.query(BenchmarkRun)
        .filter_by(project_id=project.id)
        .options(
            joinedload(BenchmarkRun.project),
            joinedload(BenchmarkRun.model_version),
            joinedload(BenchmarkRun.dataset_version).joinedload(
                BenchmarkRun.dataset_version.property.mapper.class_.dataset
            ),
            joinedload(BenchmarkRun.run_metrics).joinedload(
                BenchmarkRun.run_metrics.property.mapper.class_.metric
            ),
        )
        .all()
    )
    return [_run_to_response(r) for r in runs]
