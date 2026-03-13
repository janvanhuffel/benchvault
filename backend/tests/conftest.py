import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(db):
    """Insert the minimum controlled entities for a valid run submission."""
    from app.models import Project, Dataset, DatasetVersion, Metric

    db.add(Project(name="test-project"))
    db.add(Dataset(name="test-dataset"))
    db.flush()

    dataset = db.query(Dataset).filter_by(name="test-dataset").one()
    db.add(DatasetVersion(
        dataset_id=dataset.id, version="v1.0",
        num_classes=10, train_count=800, val_count=100, test_count=100,
        total_samples=1000, total_size_gb=0.5, file_type="jpg",
        storage_url="s3://test-bucket/test-dataset/v1.0/",
    ))

    db.add(Metric(name="accuracy", higher_is_better=True))
    db.add(Metric(name="f1_score", higher_is_better=True))
    db.commit()
    return db


@pytest.fixture
def seeded_client(seeded_db):
    def override_get_db():
        try:
            yield seeded_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
