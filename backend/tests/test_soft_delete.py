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


def _submit_run(client, model_name="m1", epoch=1):
    """Helper to submit a run and return its ID."""
    r = client.post("/api/runs", json={
        "project": "test-project",
        "model_name": model_name, "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v1.0",
        "epoch": epoch,
        "metrics": {"accuracy": 0.9},
    })
    assert r.status_code == 201
    return r.json()["id"]


def test_delete_runs_soft_deletes(seeded_client):
    """DELETE /api/runs should set deleted_at, not physically remove."""
    id1 = _submit_run(seeded_client, "m1")
    _submit_run(seeded_client, "m2")

    response = seeded_client.request("DELETE", "/api/runs", json={"run_ids": [id1]})
    assert response.status_code == 200
    assert response.json()["deleted"] == 1


def test_delete_runs_empty_list_returns_422(seeded_client):
    response = seeded_client.request("DELETE", "/api/runs", json={"run_ids": []})
    assert response.status_code == 422


def test_delete_runs_nonexistent_returns_404(seeded_client):
    response = seeded_client.request("DELETE", "/api/runs", json={"run_ids": [9999]})
    assert response.status_code == 404


def test_deleted_runs_excluded_from_project_listing(seeded_client):
    id1 = _submit_run(seeded_client, "m1")
    _submit_run(seeded_client, "m2")

    seeded_client.request("DELETE", "/api/runs", json={"run_ids": [id1]})

    runs = seeded_client.get("/api/projects/test-project/runs").json()
    assert len(runs) == 1
    assert runs[0]["model_name"] == "m2"


def test_deleted_runs_excluded_from_compare(seeded_client):
    id1 = _submit_run(seeded_client, "m1")
    id2 = _submit_run(seeded_client, "m2")

    seeded_client.request("DELETE", "/api/runs", json={"run_ids": [id1]})

    response = seeded_client.get(f"/api/compare?run_ids={id1},{id2}")
    assert response.status_code == 404


def test_trash_listing_shows_deleted_runs(seeded_client):
    id1 = _submit_run(seeded_client, "m1")
    _submit_run(seeded_client, "m2")

    seeded_client.request("DELETE", "/api/runs", json={"run_ids": [id1]})

    response = seeded_client.get("/api/projects/test-project/trash")
    assert response.status_code == 200
    trash = response.json()
    assert len(trash) == 1
    assert trash[0]["id"] == id1


def test_trash_listing_empty_when_no_deleted_runs(seeded_client):
    _submit_run(seeded_client, "m1")

    response = seeded_client.get("/api/projects/test-project/trash")
    assert response.status_code == 200
    assert response.json() == []


def test_trash_listing_nonexistent_project_returns_404(seeded_client):
    response = seeded_client.get("/api/projects/nonexistent/trash")
    assert response.status_code == 404


def test_restore_runs(seeded_client):
    id1 = _submit_run(seeded_client, "m1")

    seeded_client.request("DELETE", "/api/runs", json={"run_ids": [id1]})

    trash = seeded_client.get("/api/projects/test-project/trash").json()
    assert len(trash) == 1

    response = seeded_client.post("/api/runs/restore", json={"run_ids": [id1]})
    assert response.status_code == 200
    assert response.json()["restored"] == 1

    runs = seeded_client.get("/api/projects/test-project/runs").json()
    assert any(r["id"] == id1 for r in runs)

    trash = seeded_client.get("/api/projects/test-project/trash").json()
    assert len(trash) == 0


def test_restore_nonexistent_returns_404(seeded_client):
    response = seeded_client.post("/api/runs/restore", json={"run_ids": [9999]})
    assert response.status_code == 404


def test_restore_active_run_returns_404(seeded_client):
    """Restoring a non-deleted run should fail."""
    id1 = _submit_run(seeded_client, "m1")
    response = seeded_client.post("/api/runs/restore", json={"run_ids": [id1]})
    assert response.status_code == 404
