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
        exp_by_run: dict[int, list[RunExperimentInfo]] = {}
        for rid, eid, ename in exp_memberships:
            exp_by_run.setdefault(rid, []).append(RunExperimentInfo(id=eid, name=ename))
    else:
        exp_by_run = {}

    run_responses = []
    for run in runs:
        run_resp = _run_to_response(run, experiments=exp_by_run.get(run.id, []))
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
