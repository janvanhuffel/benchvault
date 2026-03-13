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

    # 3. Seed per-class metric types (upsert to handle pre-existing rows)
    for name, higher_is_better in [("iou", True), ("precision", True), ("recall", True)]:
        op.execute(
            sa.text(
                "INSERT INTO metrics (name, higher_is_better, is_per_class) "
                "VALUES (:name, :hib, true) "
                "ON CONFLICT (name) DO UPDATE SET is_per_class = true, higher_is_better = EXCLUDED.higher_is_better"
            ).bindparams(name=name, hib=higher_is_better)
        )


def downgrade() -> None:
    op.drop_table("run_class_metrics")
    op.drop_column("metrics", "is_per_class")
