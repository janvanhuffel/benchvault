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
