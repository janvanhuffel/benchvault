def test_list_projects(seeded_client):
    response = seeded_client.get("/api/projects")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "test-project" in names


def test_list_datasets(seeded_client):
    response = seeded_client.get("/api/datasets")
    assert response.status_code == 200
    names = [d["name"] for d in response.json()]
    assert "test-dataset" in names


def test_list_metrics(seeded_client):
    response = seeded_client.get("/api/metrics")
    assert response.status_code == 200
    names = [m["name"] for m in response.json()]
    assert "accuracy" in names


def test_list_runs_for_project(seeded_client):
    # Submit a run first
    seeded_client.post("/api/runs", json={
        "project": "test-project",
        "model_name": "m", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v1.0",
        "metrics": {"accuracy": 0.9},
    })
    response = seeded_client.get("/api/projects/test-project/runs")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["metrics"][0]["metric_name"] == "accuracy"


def test_list_runs_for_nonexistent_project(seeded_client):
    response = seeded_client.get("/api/projects/nonexistent/runs")
    assert response.status_code == 404
