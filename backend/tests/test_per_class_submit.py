VALID_PAYLOAD = {
    "project": "test-project",
    "model_name": "my-model",
    "model_version": "v1",
    "dataset": "test-dataset",
    "dataset_version": "v1.0",
    "epoch": 10,
    "metrics": {"accuracy": 0.95},
}

PER_CLASS = {
    "iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7},
    "precision": {"cat": 0.95, "dog": 0.85, "bird": 0.75},
}


def test_submit_with_per_class_metrics(seeded_client):
    """Happy path: scalar + per-class metrics → 201, data stored."""
    payload = {**VALID_PAYLOAD, "per_class_metrics": PER_CLASS}
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 201


def test_submit_without_per_class_metrics_still_works(seeded_client):
    """Backward compat: no per_class_metrics field → 201."""
    response = seeded_client.post("/api/runs", json=VALID_PAYLOAD)
    assert response.status_code == 201


def test_submit_unknown_per_class_metric_rejected(seeded_client):
    """Unknown per-class metric name → 422."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"bogus": {"cat": 0.9, "dog": 0.8, "bird": 0.7}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "bogus" in response.json()["detail"].lower()


def test_submit_scalar_metric_as_per_class_rejected(seeded_client):
    """Scalar metric (accuracy) submitted as per-class → 422."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"accuracy": {"cat": 0.9, "dog": 0.8, "bird": 0.7}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "per-class" in response.json()["detail"].lower() or "per_class" in response.json()["detail"].lower()


def test_submit_per_class_metric_as_scalar_rejected(seeded_client):
    """Per-class metric (iou) submitted as scalar → 422."""
    payload = {
        **VALID_PAYLOAD,
        "metrics": {"accuracy": 0.95, "iou": 0.85},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422


def test_submit_per_class_missing_class_rejected(seeded_client):
    """Missing class name → 422."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"iou": {"cat": 0.9, "dog": 0.8}},  # missing "bird"
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "class" in response.json()["detail"].lower()


def test_submit_per_class_extra_class_rejected(seeded_client):
    """Extra class name → 422."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7, "fish": 0.6}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "class" in response.json()["detail"].lower()


def test_submit_per_class_wrong_class_name_rejected(seeded_client):
    """Wrong class name → 422."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"iou": {"cat": 0.9, "dog": 0.8, "snake": 0.7}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "class" in response.json()["detail"].lower()


def test_submit_per_class_no_class_names_on_dataset_version_rejected(seeded_client, seeded_db):
    """Dataset version has no class_names (None) but per_class_metrics provided → 422."""
    from app.models import Dataset, DatasetVersion

    dataset = seeded_db.query(Dataset).filter_by(name="test-dataset").one()
    seeded_db.add(DatasetVersion(
        dataset_id=dataset.id, version="v2.0",
        num_classes=0,
        class_names=None,
        train_count=100, val_count=10, test_count=10,
        total_samples=120, total_size_gb=0.1, file_type="las",
        storage_url="s3://test-bucket/test-dataset/v2.0/",
    ))
    seeded_db.commit()

    payload = {
        **VALID_PAYLOAD,
        "dataset_version": "v2.0",
        "per_class_metrics": {"iou": {"something": 0.5}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "class names" in response.json()["detail"].lower()


def test_submit_per_class_empty_class_names_rejected(seeded_client, seeded_db):
    """Dataset version has empty class_names ([]) but per_class_metrics provided → 422."""
    from app.models import Dataset, DatasetVersion

    dataset = seeded_db.query(Dataset).filter_by(name="test-dataset").one()
    seeded_db.add(DatasetVersion(
        dataset_id=dataset.id, version="v3.0",
        num_classes=0,
        class_names=[],
        train_count=100, val_count=10, test_count=10,
        total_samples=120, total_size_gb=0.1, file_type="las",
        storage_url="s3://test-bucket/test-dataset/v3.0/",
    ))
    seeded_db.commit()

    payload = {
        **VALID_PAYLOAD,
        "dataset_version": "v3.0",
        "per_class_metrics": {"iou": {"something": 0.5}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 422
    assert "class names" in response.json()["detail"].lower()


def test_submit_per_class_data_stored_correctly(seeded_client, seeded_db):
    """Verify RunClassMetric rows are actually persisted with correct metric link."""
    payload = {
        **VALID_PAYLOAD,
        "per_class_metrics": {"iou": {"cat": 0.9, "dog": 0.8, "bird": 0.7}},
    }
    response = seeded_client.post("/api/runs", json=payload)
    assert response.status_code == 201
    run_id = response.json()["id"]

    from app.models import RunClassMetric, Metric

    iou_metric = seeded_db.query(Metric).filter_by(name="iou").one()
    rows = seeded_db.query(RunClassMetric).filter_by(run_id=run_id).all()
    assert len(rows) == 3
    for row in rows:
        assert row.metric_id == iou_metric.id
    values_by_class = {r.class_name: r.value for r in rows}
    assert values_by_class == {"cat": 0.9, "dog": 0.8, "bird": 0.7}
