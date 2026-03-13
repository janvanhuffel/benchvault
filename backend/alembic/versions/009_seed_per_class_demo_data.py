"""seed per-class demo data for existing runs

Revision ID: 009_seed_per_class_demo
Revises: 008_per_class_metrics
Create Date: 2026-03-13

"""
from typing import Sequence, Union

import random

from alembic import op
import sqlalchemy as sa


revision: str = "009_seed_per_class_demo"
down_revision: Union[str, Sequence[str], None] = "008_per_class_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Runs that use dataset versions WITH class_names defined.
# (model_name, model_version, dataset_name, dataset_version, epoch)
COCO_V1_RUNS = [
    ("tesseract-ocr", "v4.1", "COCO-2017", "v1.0", 5),
    ("tesseract-ocr", "v4.1", "COCO-2017", "v1.0", 10),
    ("tesseract-ocr", "v4.1", "COCO-2017", "v1.0", 20),
    ("paddleocr", "v2.1", "COCO-2017", "v1.0", 5),
    ("paddleocr", "v2.1", "COCO-2017", "v1.0", 10),
    ("paddleocr", "v2.1", "COCO-2017", "v1.0", 20),
    ("easyocr", "v1.4", "COCO-2017", "v1.0", 10),
    ("easyocr", "v1.4", "COCO-2017", "v1.0", 20),
]

COCO_V1_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
    "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon",
    "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot",
    "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant",
    "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]

GLUE_RUNS = [
    ("bert-base", "v1.0", "GLUE-MNLI", "v1.0", 3),
    ("bert-base", "v1.0", "GLUE-MNLI", "v1.0", 5),
    ("bert-base", "v1.0", "GLUE-MNLI", "v1.0", 10),
    ("roberta-large", "v1.0", "GLUE-MNLI", "v1.0", 3),
    ("roberta-large", "v1.0", "GLUE-MNLI", "v1.0", 5),
    ("roberta-large", "v1.0", "GLUE-MNLI", "v1.0", 10),
    ("distilbert", "v1.0", "GLUE-MNLI", "v1.0", 5),
    ("distilbert", "v1.0", "GLUE-MNLI", "v1.0", 10),
    ("deberta-v3", "v0.9", "GLUE-MNLI", "v1.0", 3),
    ("deberta-v3", "v0.9", "GLUE-MNLI", "v1.0", 5),
    ("deberta-v3", "v0.9", "GLUE-MNLI", "v1.0", 10),
]

GLUE_CLASSES = ["entailment", "neutral", "contradiction"]

# Per-class metric ranges: (metric_name, low, high)
METRIC_RANGES = [
    ("iou", 0.30, 0.95),
    ("precision_class", 0.50, 0.98),
    ("recall_class", 0.40, 0.95),
]


def _run_subselect(model_name: str, model_version: str,
                   dataset_name: str, dataset_version: str, epoch: int) -> str:
    return (
        f"(SELECT id FROM benchmark_runs "
        f"WHERE model_version_id = (SELECT id FROM model_versions "
        f"WHERE model_name='{model_name}' AND model_version='{model_version}') "
        f"AND dataset_version_id = (SELECT id FROM dataset_versions "
        f"WHERE dataset_id=(SELECT id FROM datasets WHERE name='{dataset_name}') "
        f"AND version='{dataset_version}') "
        f"AND epoch={epoch})"
    )


def _metric_subselect(metric_name: str) -> str:
    return f"(SELECT id FROM metrics WHERE name='{metric_name}')"


def upgrade() -> None:
    """Seed run_class_metrics rows for demo runs with class_names."""
    rng = random.Random(42)  # fixed seed for reproducibility

    all_runs = [
        (run, COCO_V1_CLASSES) for run in COCO_V1_RUNS
    ] + [
        (run, GLUE_CLASSES) for run in GLUE_RUNS
    ]

    values_parts = []
    for run_info, class_names in all_runs:
        model_name, model_version, dataset_name, dataset_version, epoch = run_info
        run_sub = _run_subselect(model_name, model_version,
                                 dataset_name, dataset_version, epoch)
        for metric_name, low, high in METRIC_RANGES:
            metric_sub = _metric_subselect(metric_name)
            for cls in class_names:
                value = round(rng.uniform(low, high), 4)
                escaped_cls = cls.replace("'", "''")
                values_parts.append(
                    f"({run_sub}, {metric_sub}, '{escaped_cls}', {value})"
                )

    # Insert in batches to avoid overly long SQL statements
    batch_size = 200
    for i in range(0, len(values_parts), batch_size):
        batch = values_parts[i:i + batch_size]
        sql = (
            "INSERT INTO run_class_metrics (run_id, metric_id, class_name, value) "
            "VALUES " + ",\n".join(batch)
        )
        op.execute(sql)


def downgrade() -> None:
    """Remove all seeded per-class demo data."""
    op.execute("DELETE FROM run_class_metrics")
