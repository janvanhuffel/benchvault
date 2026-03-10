from pydantic import BaseModel
from datetime import datetime


# --- Submission ---

class RunSubmission(BaseModel):
    project: str
    model_name: str
    model_version: str
    dataset: str
    dataset_version: str
    epoch: int
    note: str | None = None
    metrics: dict[str, float]


class RunCreatedResponse(BaseModel):
    id: int
    created_at: datetime


class RunIdsRequest(BaseModel):
    run_ids: list[int]


# --- Read responses ---

class ProjectResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class DatasetCreateRequest(BaseModel):
    name: str
    modality: str | None = None
    task: str | None = None
    license: str | None = None
    source_url: str | None = None


class DatasetUpdateRequest(BaseModel):
    modality: str | None = None
    task: str | None = None
    license: str | None = None
    source_url: str | None = None


class DatasetVersionCreateRequest(BaseModel):
    version: str
    description: str | None = None
    num_classes: int | None = None
    class_names: list[str] | None = None
    train_count: int | None = None
    val_count: int | None = None
    test_count: int | None = None
    total_samples: int | None = None
    total_size_gb: float | None = None
    collection_method: str | None = None
    sensor: str | None = None
    file_type: str | None = None
    storage_url: str | None = None


class DatasetVersionDetailResponse(BaseModel):
    id: int
    version: str
    description: str | None
    num_classes: int | None
    class_names: list[str] | None
    train_count: int | None
    val_count: int | None
    test_count: int | None
    total_samples: int | None
    total_size_gb: float | None
    collection_method: str | None
    sensor: str | None
    file_type: str | None
    storage_url: str | None

    model_config = {"from_attributes": True}


class DatasetDetailResponse(BaseModel):
    id: int
    name: str
    modality: str | None
    task: str | None
    license: str | None
    source_url: str | None
    versions: list[DatasetVersionDetailResponse]

    model_config = {"from_attributes": True}


class DatasetVersionResponse(BaseModel):
    id: int
    dataset_name: str
    version: str


class MetricResponse(BaseModel):
    id: int
    name: str
    higher_is_better: bool
    description: str | None

    model_config = {"from_attributes": True}


class MetricValueResponse(BaseModel):
    metric_name: str
    value: float
    higher_is_better: bool


class RunResponse(BaseModel):
    id: int
    project: str
    model_name: str
    model_version: str
    dataset: str
    dataset_version: str
    epoch: int
    note: str | None
    created_at: datetime
    metrics: list[MetricValueResponse]


class CompareResponse(BaseModel):
    metric_names: list[str]
    higher_is_better: dict[str, bool]
    runs: list[RunResponse]
