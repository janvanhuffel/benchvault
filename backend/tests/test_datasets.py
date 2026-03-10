from app.models import Dataset, DatasetVersion


def test_dataset_version_class_names_roundtrip(db):
    """class_names stored as ARRAY in Postgres, JSON in SQLite — both round-trip correctly."""
    db.add(Dataset(name="test-ds"))
    db.flush()
    ds = db.query(Dataset).filter_by(name="test-ds").one()
    db.add(DatasetVersion(
        dataset_id=ds.id,
        version="v1.0",
        class_names=["cat", "dog", "bird"],
    ))
    db.commit()
    dv = db.query(DatasetVersion).filter_by(version="v1.0").one()
    assert dv.class_names == ["cat", "dog", "bird"]


def test_create_dataset_minimal(client):
    """POST /api/datasets with only name returns 201."""
    resp = client.post("/api/datasets", json={"name": "my-dataset"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "my-dataset"
    assert data["modality"] is None


def test_create_dataset_full(client):
    """POST /api/datasets with all fields returns 201."""
    resp = client.post("/api/datasets", json={
        "name": "WHU-Railway3D",
        "modality": "point_cloud",
        "task": "semantic_segmentation",
        "license": "CC-BY-4.0",
        "source_url": "https://github.com/WHU-USI3DV/WHU-Railway3D",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["modality"] == "point_cloud"
    assert data["source_url"] == "https://github.com/WHU-USI3DV/WHU-Railway3D"


def test_create_dataset_duplicate(client):
    """POST /api/datasets with duplicate name returns 409."""
    client.post("/api/datasets", json={"name": "dup"})
    resp = client.post("/api/datasets", json={"name": "dup"})
    assert resp.status_code == 409


def test_update_dataset(client):
    """PATCH /api/datasets/{name} updates fields."""
    client.post("/api/datasets", json={"name": "ds1"})
    resp = client.patch("/api/datasets/ds1", json={"modality": "image", "task": "detection"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["modality"] == "image"
    assert data["task"] == "detection"


def test_update_dataset_not_found(client):
    """PATCH /api/datasets/{name} returns 404 for unknown dataset."""
    resp = client.patch("/api/datasets/nope", json={"modality": "image"})
    assert resp.status_code == 404


def test_create_version_minimal(client):
    """POST version with only version string returns 201."""
    client.post("/api/datasets", json={"name": "ds1"})
    resp = client.post("/api/datasets/ds1/versions", json={"version": "v1.0"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["version"] == "v1.0"
    assert data["class_names"] is None


def test_create_version_full(client):
    """POST version with all metadata returns 201."""
    client.post("/api/datasets", json={"name": "ds1"})
    resp = client.post("/api/datasets/ds1/versions", json={
        "version": "v1.0",
        "description": "First release",
        "num_classes": 11,
        "class_names": ["rails", "track_bed", "mast"],
        "train_count": 3200000000,
        "val_count": 800000000,
        "test_count": 600000000,
        "total_samples": 4600000000,
        "total_size_gb": 48.5,
        "collection_method": "Mobile Laser Scanning",
        "sensor": "Optech Lynx",
        "file_type": "laz",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["num_classes"] == 11
    assert data["class_names"] == ["rails", "track_bed", "mast"]
    assert data["file_type"] == "laz"


def test_create_version_dataset_not_found(client):
    """POST version for unknown dataset returns 404."""
    resp = client.post("/api/datasets/nope/versions", json={"version": "v1.0"})
    assert resp.status_code == 404


def test_create_version_duplicate(client):
    """POST duplicate version returns 409."""
    client.post("/api/datasets", json={"name": "ds1"})
    client.post("/api/datasets/ds1/versions", json={"version": "v1.0"})
    resp = client.post("/api/datasets/ds1/versions", json={"version": "v1.0"})
    assert resp.status_code == 409


def test_list_datasets_with_versions(client):
    """GET /api/datasets returns datasets with nested versions and metadata."""
    client.post("/api/datasets", json={"name": "ds1", "modality": "image"})
    client.post("/api/datasets/ds1/versions", json={
        "version": "v1.0",
        "num_classes": 5,
        "class_names": ["a", "b", "c", "d", "e"],
    })
    resp = client.get("/api/datasets")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    ds = next(d for d in data if d["name"] == "ds1")
    assert ds["modality"] == "image"
    assert len(ds["versions"]) == 1
    assert ds["versions"][0]["class_names"] == ["a", "b", "c", "d", "e"]
