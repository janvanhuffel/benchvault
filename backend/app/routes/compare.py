from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import BenchmarkRun
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
