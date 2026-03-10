import json

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator

from app.database import Base


class StringArray(TypeDecorator):
    """Stores a list of strings. Uses ARRAY on PostgreSQL, JSON text on SQLite."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value  # ARRAY handles it
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value  # already a list
        return json.loads(value)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    runs = relationship("BenchmarkRun", back_populates="project")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    modality = Column(String, nullable=True)
    task = Column(String, nullable=True)
    license = Column(String, nullable=True)
    source_url = Column(String, nullable=True)

    versions = relationship("DatasetVersion", back_populates="dataset")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    version = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    num_classes = Column(Integer, nullable=True)
    class_names = Column(StringArray, nullable=True)
    train_count = Column(Integer, nullable=True)
    val_count = Column(Integer, nullable=True)
    test_count = Column(Integer, nullable=True)
    total_samples = Column(Integer, nullable=True)
    total_size_gb = Column(Float, nullable=True)
    collection_method = Column(String, nullable=True)
    sensor = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    storage_url = Column(String, nullable=True)

    dataset = relationship("Dataset", back_populates="versions")
    runs = relationship("BenchmarkRun", back_populates="dataset_version")

    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_dataset_version"),
    )


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    higher_is_better = Column(Boolean, nullable=False, default=True)
    description = Column(Text, nullable=True)

    run_metrics = relationship("RunMetric", back_populates="metric")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    runs = relationship("BenchmarkRun", back_populates="model_version")

    __table_args__ = (
        UniqueConstraint("model_name", "model_version", name="uq_model_version"),
    )


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False)
    dataset_version_id = Column(Integer, ForeignKey("dataset_versions.id"), nullable=False)
    epoch = Column(Integer, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    project = relationship("Project", back_populates="runs")
    model_version = relationship("ModelVersion", back_populates="runs")
    dataset_version = relationship("DatasetVersion", back_populates="runs")
    run_metrics = relationship("RunMetric", back_populates="run", cascade="all, delete-orphan")


class RunMetric(Base):
    __tablename__ = "run_metrics"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("benchmark_runs.id"), nullable=False)
    metric_id = Column(Integer, ForeignKey("metrics.id"), nullable=False)
    value = Column(Float, nullable=False)

    run = relationship("BenchmarkRun", back_populates="run_metrics")
    metric = relationship("Metric", back_populates="run_metrics")

    __table_args__ = (
        UniqueConstraint("run_id", "metric_id", name="uq_run_metric"),
    )
