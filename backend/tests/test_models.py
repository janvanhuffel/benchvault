from app.models import (
    Project, Dataset, DatasetVersion, Metric,
    ModelVersion, BenchmarkRun, RunMetric,
)


def test_project_has_name():
    p = Project(name="test-project")
    assert p.name == "test-project"


def test_metric_has_higher_is_better():
    m = Metric(name="accuracy", higher_is_better=True)
    assert m.higher_is_better is True


def test_model_version_has_name_and_version():
    mv = ModelVersion(model_name="gpt-4", model_version="v1")
    assert mv.model_name == "gpt-4"
    assert mv.model_version == "v1"
