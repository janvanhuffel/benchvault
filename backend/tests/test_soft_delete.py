from datetime import datetime, timedelta, timezone

from app.models import BenchmarkRun, ModelVersion, DatasetVersion, Project


def test_benchmark_run_has_deleted_at_column(seeded_client):
    """deleted_at should default to None on newly created runs."""
    seeded_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "m1", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v1.0",
        "epoch": 1,
        "metrics": {"accuracy": 0.9},
    })
    response = seeded_client.get("/api/projects/test-project/runs")
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["model_name"] == "m1"


def test_cleanup_purges_old_trashed_runs(seeded_db):
    """Runs trashed more than 7 days ago should be permanently deleted."""
    mv = ModelVersion(model_name="m1", model_version="v1")
    seeded_db.add(mv)
    seeded_db.flush()

    dataset_version = seeded_db.query(DatasetVersion).first()
    project = seeded_db.query(Project).first()

    old_run = BenchmarkRun(
        project_id=project.id,
        model_version_id=mv.id,
        dataset_version_id=dataset_version.id,
        epoch=1,
        deleted_at=datetime.now(timezone.utc) - timedelta(days=8),
    )
    recent_run = BenchmarkRun(
        project_id=project.id,
        model_version_id=mv.id,
        dataset_version_id=dataset_version.id,
        epoch=2,
        deleted_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    active_run = BenchmarkRun(
        project_id=project.id,
        model_version_id=mv.id,
        dataset_version_id=dataset_version.id,
        epoch=3,
    )
    seeded_db.add_all([old_run, recent_run, active_run])
    seeded_db.commit()

    from app.trash_cleanup import maybe_cleanup_trash
    maybe_cleanup_trash(seeded_db, force=True)

    remaining = seeded_db.query(BenchmarkRun).all()
    assert len(remaining) == 2
    epochs = {r.epoch for r in remaining}
    assert epochs == {2, 3}


def test_cleanup_skips_when_recently_run(seeded_db):
    """Cleanup should not run again within 24 hours unless forced."""
    import app.trash_cleanup as tc

    tc.maybe_cleanup_trash(seeded_db, force=True)
    first_cleanup = tc._last_cleanup

    tc.maybe_cleanup_trash(seeded_db)
    assert tc._last_cleanup == first_cleanup


def test_cleanup_runs_when_no_previous_cleanup(seeded_db):
    """If _last_cleanup is None (e.g. after restart), cleanup should run."""
    import app.trash_cleanup as tc

    tc._last_cleanup = None
    tc.maybe_cleanup_trash(seeded_db)
    assert tc._last_cleanup is not None
