"""add deleted_at to benchmark_runs

Revision ID: 007_add_deleted_at
Revises: 006_add_storage_url
Create Date: 2026-03-10 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_add_deleted_at'
down_revision: Union[str, Sequence[str], None] = '006_add_storage_url'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('benchmark_runs', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        'ix_benchmark_runs_deleted_at',
        'benchmark_runs',
        ['deleted_at'],
        postgresql_where=sa.text('deleted_at IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_benchmark_runs_deleted_at', table_name='benchmark_runs')
    op.drop_column('benchmark_runs', 'deleted_at')
