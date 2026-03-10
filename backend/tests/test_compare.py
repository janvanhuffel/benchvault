def test_compare_runs(seeded_client):
    # Submit two runs
    r1 = seeded_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "m1", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v1.0",
        "metrics": {"accuracy": 0.9, "f1_score": 0.85},
    })
    r2 = seeded_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "m2", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v1.0",
        "metrics": {"accuracy": 0.95, "f1_score": 0.88},
    })

    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    response = seeded_client.get(f"/api/compare?run_ids={id1},{id2}")
    assert response.status_code == 200

    data = response.json()
    assert len(data["runs"]) == 2
    assert "accuracy" in data["metric_names"]
    assert data["higher_is_better"]["accuracy"] is True


def test_compare_no_ids_returns_error(seeded_client):
    response = seeded_client.get("/api/compare")
    assert response.status_code == 422


def test_compare_nonexistent_run_returns_404(seeded_client):
    response = seeded_client.get("/api/compare?run_ids=9999")
    assert response.status_code == 404


def test_compare_invalid_run_ids_returns_422(seeded_client):
    response = seeded_client.get("/api/compare?run_ids=abc,def")
    assert response.status_code == 422
    assert "comma-separated integers" in response.json()["detail"].lower()


def test_compare_preserves_requested_run_order(seeded_client):
    r1 = seeded_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "m1", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v1.0",
        "metrics": {"accuracy": 0.9},
    })
    r2 = seeded_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "m2", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v1.0",
        "metrics": {"accuracy": 0.95},
    })

    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    # Request in reverse order
    response = seeded_client.get(f"/api/compare?run_ids={id2},{id1}")
    assert response.status_code == 200
    data = response.json()
    assert data["runs"][0]["id"] == id2
    assert data["runs"][1]["id"] == id1
