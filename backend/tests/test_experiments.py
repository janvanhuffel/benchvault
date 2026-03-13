from datetime import datetime, timedelta, timezone

import pytest


def test_create_experiment(seeded_client):
    resp = seeded_client.post("/api/experiments", json={
        "project_name": "test-project",
        "name": "My Experiment",
        "description": "Testing something",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Experiment"
    assert data["project_name"] == "test-project"
    assert data["status"] == "active"
    assert data["run_count"] == 0


def test_create_experiment_unknown_project(seeded_client):
    resp = seeded_client.post("/api/experiments", json={
        "project_name": "nonexistent",
        "name": "Exp",
    })
    assert resp.status_code == 404


def test_create_experiment_duplicate_name(seeded_client):
    seeded_client.post("/api/experiments", json={
        "project_name": "test-project",
        "name": "Dup",
    })
    resp = seeded_client.post("/api/experiments", json={
        "project_name": "test-project",
        "name": "Dup",
    })
    assert resp.status_code == 409


def test_list_experiments(seeded_client):
    seeded_client.post("/api/experiments", json={
        "project_name": "test-project",
        "name": "Exp A",
    })
    resp = seeded_client.get("/api/experiments")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_experiments_filter_by_project(seeded_client):
    seeded_client.post("/api/experiments", json={
        "project_name": "test-project",
        "name": "Exp A",
    })
    resp = seeded_client.get("/api/experiments?project_name=test-project")
    assert len(resp.json()) == 1
    resp = seeded_client.get("/api/experiments?project_name=other")
    assert len(resp.json()) == 0


def test_get_experiment_detail(experiment_client):
    resp = experiment_client.get("/api/experiments/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Experiment"
    assert data["runs"] == []


def test_get_experiment_not_found(seeded_client):
    resp = seeded_client.get("/api/experiments/999")
    assert resp.status_code == 404


def test_update_experiment(experiment_client):
    resp = experiment_client.patch("/api/experiments/1", json={
        "notes": "## Findings\nGood results.",
        "status": "concluded",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "concluded"

    # Verify notes persisted via detail
    detail = experiment_client.get("/api/experiments/1").json()
    assert detail["notes"] == "## Findings\nGood results."


def test_update_experiment_invalid_status(experiment_client):
    resp = experiment_client.patch("/api/experiments/1", json={
        "status": "invalid",
    })
    assert resp.status_code == 422


def test_delete_experiment(experiment_client):
    resp = experiment_client.delete("/api/experiments/1")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 1}

    resp = experiment_client.get("/api/experiments/1")
    assert resp.status_code == 404


def test_add_runs_to_experiment(experiment_client):
    # First submit a run
    run_resp = experiment_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "test-model",
        "model_version": "v1",
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 10,
        "metrics": {"accuracy": 0.9},
    })
    run_id = run_resp.json()["id"]

    # Add run to experiment
    resp = experiment_client.post(f"/api/experiments/1/runs", json={
        "run_ids": [run_id],
    })
    assert resp.status_code == 204

    # Verify run appears in experiment detail
    detail = experiment_client.get("/api/experiments/1").json()
    assert len(detail["runs"]) == 1
    assert detail["runs"][0]["id"] == run_id


def test_add_run_wrong_project(experiment_client):
    # Submit a run to a different project (create project first via a run won't work
    # since projects are pre-registered -- test the error)
    resp = experiment_client.post("/api/experiments/1/runs", json={
        "run_ids": [99999],
    })
    assert resp.status_code == 422


def test_add_runs_idempotent(experiment_client):
    run_resp = experiment_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "test-model",
        "model_version": "v1",
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 10,
        "metrics": {"accuracy": 0.9},
    })
    run_id = run_resp.json()["id"]

    experiment_client.post("/api/experiments/1/runs", json={"run_ids": [run_id]})
    # Adding again should not error
    resp = experiment_client.post("/api/experiments/1/runs", json={"run_ids": [run_id]})
    assert resp.status_code == 204

    detail = experiment_client.get("/api/experiments/1").json()
    assert len(detail["runs"]) == 1


def test_remove_runs_from_experiment(experiment_client):
    run_resp = experiment_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "test-model",
        "model_version": "v1",
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 10,
        "metrics": {"accuracy": 0.9},
    })
    run_id = run_resp.json()["id"]

    experiment_client.post("/api/experiments/1/runs", json={"run_ids": [run_id]})

    resp = experiment_client.request(
        "DELETE", "/api/experiments/1/runs", json={"run_ids": [run_id]}
    )
    assert resp.status_code == 204

    detail = experiment_client.get("/api/experiments/1").json()
    assert len(detail["runs"]) == 0


def test_project_runs_include_experiment_badges(experiment_client):
    run_resp = experiment_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "test-model",
        "model_version": "v1",
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 10,
        "metrics": {"accuracy": 0.9},
    })
    run_id = run_resp.json()["id"]

    experiment_client.post("/api/experiments/1/runs", json={"run_ids": [run_id]})

    # Fetch project runs -- should include experiment badge
    resp = experiment_client.get("/api/projects/test-project/runs")
    runs = resp.json()
    target_run = [r for r in runs if r["id"] == run_id][0]
    assert len(target_run["experiments"]) == 1
    assert target_run["experiments"][0]["name"] == "Test Experiment"


def test_soft_deleted_run_hidden_in_experiment(experiment_client):
    run_resp = experiment_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "test-model",
        "model_version": "v1",
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 10,
        "metrics": {"accuracy": 0.9},
    })
    run_id = run_resp.json()["id"]

    experiment_client.post("/api/experiments/1/runs", json={"run_ids": [run_id]})

    # Soft-delete the run
    experiment_client.request("DELETE", "/api/runs", json={"run_ids": [run_id]})

    # Run should not appear in experiment detail
    detail = experiment_client.get("/api/experiments/1").json()
    assert len(detail["runs"]) == 0


# --- Experiment soft-delete tests ---


def test_delete_experiment_soft_delete(experiment_client):
    resp = experiment_client.delete("/api/experiments/1")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 1}

    # Should disappear from the list
    listing = experiment_client.get("/api/experiments").json()
    assert len(listing) == 0

    # Should appear in trash
    trash = experiment_client.get("/api/experiments/trash").json()
    assert len(trash) == 1
    assert trash[0]["name"] == "Test Experiment"


def test_trash_list(experiment_client):
    # Trash is empty initially
    trash = experiment_client.get("/api/experiments/trash").json()
    assert len(trash) == 0

    # Delete the experiment
    experiment_client.delete("/api/experiments/1")

    # Now trash should have one entry
    trash = experiment_client.get("/api/experiments/trash").json()
    assert len(trash) == 1
    assert trash[0]["id"] == 1


def test_trash_list_filter_by_project(experiment_client):
    experiment_client.delete("/api/experiments/1")

    # Filter by correct project
    trash = experiment_client.get("/api/experiments/trash?project_name=test-project").json()
    assert len(trash) == 1

    # Filter by other project
    trash = experiment_client.get("/api/experiments/trash?project_name=nonexistent").json()
    assert len(trash) == 0


def test_restore_experiment(experiment_client):
    experiment_client.delete("/api/experiments/1")

    # Verify it's gone from list
    listing = experiment_client.get("/api/experiments").json()
    assert len(listing) == 0

    # Restore
    resp = experiment_client.post("/api/experiments/restore", json={"experiment_ids": [1]})
    assert resp.status_code == 200
    assert resp.json() == {"restored": 1}

    # Should be back in the list
    listing = experiment_client.get("/api/experiments").json()
    assert len(listing) == 1
    assert listing[0]["name"] == "Test Experiment"

    # Should be gone from trash
    trash = experiment_client.get("/api/experiments/trash").json()
    assert len(trash) == 0


def test_restore_empty_ids(experiment_client):
    resp = experiment_client.post("/api/experiments/restore", json={"experiment_ids": []})
    assert resp.status_code == 422


def test_restore_non_trashed(experiment_client):
    # Experiment 1 is active (not trashed)
    resp = experiment_client.post("/api/experiments/restore", json={"experiment_ids": [1]})
    assert resp.status_code == 404


def test_trashed_experiment_hidden_from_detail(experiment_client):
    experiment_client.delete("/api/experiments/1")
    resp = experiment_client.get("/api/experiments/1")
    assert resp.status_code == 404


def test_trashed_experiment_hidden_from_patch(experiment_client):
    experiment_client.delete("/api/experiments/1")
    resp = experiment_client.patch("/api/experiments/1", json={"notes": "updated"})
    assert resp.status_code == 404


def test_cleanup_purges_old_experiments(experiment_client):
    from app.database import get_db
    from app.main import app
    from app.models import Experiment
    from app.trash_cleanup import maybe_cleanup_trash

    # Soft-delete the experiment
    experiment_client.delete("/api/experiments/1")

    # Get the DB session used by the test client
    db = next(app.dependency_overrides[get_db]())

    # Set deleted_at to 8 days ago (beyond the 7-day retention)
    exp = db.query(Experiment).filter(Experiment.id == 1).first()
    exp.deleted_at = datetime.now(timezone.utc) - timedelta(days=8)
    db.commit()

    # Run cleanup
    maybe_cleanup_trash(db, force=True)

    # Experiment should be permanently deleted
    exp = db.query(Experiment).filter(Experiment.id == 1).first()
    assert exp is None

    # Trash should be empty
    trash = experiment_client.get("/api/experiments/trash").json()
    assert len(trash) == 0
