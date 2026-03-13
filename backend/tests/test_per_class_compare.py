def _submit_run(client, model_name, model_version, metrics, per_class=None):
    """Helper to submit a run and return its ID."""
    payload = {
        "project": "test-project",
        "model_name": model_name,
        "model_version": model_version,
        "dataset": "test-dataset",
        "dataset_version": "v1.0",
        "epoch": 1,
        "metrics": metrics,
    }
    if per_class is not None:
        payload["per_class_metrics"] = per_class
    resp = client.post("/api/runs", json=payload)
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def test_compare_with_per_class_metrics(seeded_client):
    """Compare runs that both have per-class data → populated per_class_metrics."""
    pc1 = {"iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7}}
    pc2 = {"iou": {"cat": 0.85, "dog": 0.9, "bird": 0.75}}
    id1 = _submit_run(seeded_client, "m1", "v1", {"accuracy": 0.9}, pc1)
    id2 = _submit_run(seeded_client, "m2", "v1", {"accuracy": 0.95}, pc2)

    resp = seeded_client.get(f"/api/compare?run_ids={id1},{id2}")
    assert resp.status_code == 200
    data = resp.json()

    # Scalar metrics should NOT include per-class metric names
    assert "iou" not in data["metric_names"]
    assert "accuracy" in data["metric_names"]

    # Per-class section should be populated
    assert len(data["per_class_metrics"]) == 1
    group = data["per_class_metrics"][0]
    assert group["metric_name"] == "iou"
    assert group["higher_is_better"] is True
    assert group["classes"] == ["cat", "dog", "bird"]
    assert len(group["runs"]) == 2
    assert group["runs"][0]["run_id"] == id1
    assert group["runs"][0]["values"] == {"cat": 0.9, "dog": 0.8, "bird": 0.7}


def test_compare_without_per_class_data(seeded_client):
    """Compare runs with no per-class data → empty per_class_metrics."""
    id1 = _submit_run(seeded_client, "m1", "v1", {"accuracy": 0.9})
    id2 = _submit_run(seeded_client, "m2", "v1", {"accuracy": 0.95})

    resp = seeded_client.get(f"/api/compare?run_ids={id1},{id2}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["per_class_metrics"] == []


def test_compare_different_dataset_versions_no_per_class(seeded_client, seeded_db):
    """Runs from different dataset versions → empty per_class_metrics."""
    from app.models import Dataset, DatasetVersion

    dataset = seeded_db.query(Dataset).filter_by(name="test-dataset").one()
    seeded_db.add(DatasetVersion(
        dataset_id=dataset.id, version="v2.0",
        num_classes=2, class_names=["x", "y"],
        train_count=100, val_count=10, test_count=10,
        total_samples=120, total_size_gb=0.1, file_type="las",
        storage_url="s3://test-bucket/v2.0/",
    ))
    seeded_db.commit()

    pc1 = {"iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7}}
    id1 = _submit_run(seeded_client, "m1", "v1", {"accuracy": 0.9}, pc1)

    # Submit to v2.0
    payload2 = {
        "project": "test-project",
        "model_name": "m2", "model_version": "v1",
        "dataset": "test-dataset", "dataset_version": "v2.0",
        "epoch": 1,
        "metrics": {"accuracy": 0.95},
        "per_class_metrics": {"iou": {"x": 0.8, "y": 0.7}},
    }
    r2 = seeded_client.post("/api/runs", json=payload2)
    assert r2.status_code == 201
    id2 = r2.json()["id"]

    resp = seeded_client.get(f"/api/compare?run_ids={id1},{id2}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["per_class_metrics"] == []


def test_compare_partial_per_class_data(seeded_client):
    """One run has per-class data, the other doesn't → per_class_metrics still populated with empty values for the run without data."""
    pc1 = {"iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7}}
    id1 = _submit_run(seeded_client, "m1", "v1", {"accuracy": 0.9}, pc1)
    id2 = _submit_run(seeded_client, "m2", "v1", {"accuracy": 0.95})  # no per-class

    resp = seeded_client.get(f"/api/compare?run_ids={id1},{id2}")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["per_class_metrics"]) == 1
    group = data["per_class_metrics"][0]
    assert group["metric_name"] == "iou"
    # Run 1 has values, run 2 has empty dict
    run1_data = next(r for r in group["runs"] if r["run_id"] == id1)
    run2_data = next(r for r in group["runs"] if r["run_id"] == id2)
    assert run1_data["values"] == {"cat": 0.9, "dog": 0.8, "bird": 0.7}
    assert run2_data["values"] == {}


def test_run_listing_excludes_per_class_data(seeded_client):
    """Individual run listing (project page) should NOT expose per-class metrics."""
    pc = {"iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7}}
    _submit_run(seeded_client, "m1", "v1", {"accuracy": 0.9}, pc)

    resp = seeded_client.get("/api/projects/test-project/runs")
    assert resp.status_code == 200
    data = resp.json()
    # RunResponse should not contain per_class_metrics
    for run in data:
        assert "per_class_metrics" not in run
        assert "run_class_metrics" not in run
