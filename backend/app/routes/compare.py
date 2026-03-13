from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

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

    # Collect all metric names and higher_is_better map
    metric_names: set[str] = set()
    higher_is_better: dict[str, bool] = {}
    for rr in run_responses:
        for m in rr.metrics:
            metric_names.add(m.metric_name)
            higher_is_better[m.metric_name] = m.higher_is_better

    return CompareResponse(
        metric_names=sorted(metric_names),
        higher_is_better=higher_is_better,
        runs=run_responses,
        per_class_metrics=[],
    )
