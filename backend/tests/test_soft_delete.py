from datetime import datetime, timezone


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
