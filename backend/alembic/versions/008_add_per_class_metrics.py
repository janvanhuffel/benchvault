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
    # Note: precision and recall already exist as scalar metrics from seed data,
    # so we create separate precision_class and recall_class for per-class use.
    # iou may or may not exist, so use ON CONFLICT DO NOTHING.
    for name in ["iou", "precision_class", "recall_class"]:
        op.execute(
            sa.text(
                "INSERT INTO metrics (name, higher_is_better, is_per_class) "
                "VALUES (:name, true, true) "
                "ON CONFLICT (name) DO NOTHING"
            ).bindparams(name=name)
        )


def downgrade() -> None:
    op.drop_table("run_class_metrics")
    # Delete only the metrics added by this migration
    op.execute("DELETE FROM metrics WHERE name IN ('iou', 'precision_class', 'recall_class')")
    op.drop_column("metrics", "is_per_class")
