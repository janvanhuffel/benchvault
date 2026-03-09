VALID_PAYLOAD = {
    "project": "test-project",
    "model_name": "my-model",
    "model_version": "v1",
    "dataset": "test-dataset",
    "dataset_version": "v1.0",
    "epoch": 10,
    "note": "test run",
    "metrics": {"accuracy": 0.95, "f1_score": 0.90},
}


def test_submit_valid_run(seeded_client):
    response = seeded_client.post("/api/runs", json=VALID_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "created_at" in data


def test_submit_unknown_project_rejected(seeded_client):
    payload = {**VALID_PAYLOAD, "project": "nonexistent"}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "project" in response.json()["detail"].lower()


def test_submit_unknown_dataset_rejected(seeded_client):
    payload = {**VALID_PAYLOAD, "dataset": "nonexistent"}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "dataset" in response.json()["detail"].lower()


def test_submit_unknown_dataset_version_rejected(seeded_client):
    payload = {**VALID_PAYLOAD, "dataset_version": "v99"}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "dataset_version" in response.json()["detail"].lower()


def test_submit_unknown_metric_rejected(seeded_client):
    payload = {**VALID_PAYLOAD, "metrics": {"accuracy": 0.9, "bogus_metric": 0.5}}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "bogus_metric" in response.json()["detail"].lower()


def test_submit_upserts_new_model_version(seeded_client):
    response = seeded_client.post("/api/runs", json=VALID_PAYLOAD)
    assert response.status_code == 201

    # Same model, new version
    payload = {**VALID_PAYLOAD, "model_version": "v2"}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 201
