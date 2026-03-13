"""add per-class metrics support

Revision ID: 008_per_class_metrics
Revises: c78cbd41f4e2
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_per_class_metrics"
down_revision: Union[str, Sequence[str], None] = "c78cbd41f4e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_per_class column to metrics (existing rows get False)
    op.add_column(
        "metrics",
        sa.Column("is_per_class", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # 2. Create run_class_metrics table
    op.create_table(
        "run_class_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("benchmark_runs.id"), nullable=False),
        sa.Column("metric_id", sa.Integer(), sa.ForeignKey("metrics.id"), nullable=False),
        sa.Column("class_name", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.UniqueConstraint("run_id", "metric_id", "class_name", name="uq_run_class_metric"),
    )

    # 3. Seed per-class metric types
    metrics_table = sa.table(
        "metrics",
        sa.column("name", sa.String),
        sa.column("higher_is_better", sa.Boolean),
        sa.column("is_per_class", sa.Boolean),
    )
    op.bulk_insert(metrics_table, [
        {"name": "iou", "higher_is_better": True, "is_per_class": True},
        {"name": "precision", "higher_is_better": True, "is_per_class": True},
        {"name": "recall", "higher_is_better": True, "is_per_class": True},
    ])


def downgrade() -> None:
    op.drop_table("run_class_metrics")
    op.drop_column("metrics", "is_per_class")
    op.execute("DELETE FROM metrics WHERE name IN ('iou', 'precision', 'recall')")
