"""add deleted_at to experiments

Revision ID: 011_add_experiment_deleted_at
Revises: 010_add_experiments
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '011_add_experiment_deleted_at'
down_revision: Union[str, Sequence[str], None] = '010_add_experiments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('experiments', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        'ix_experiments_deleted_at',
        'experiments',
        ['deleted_at'],
        postgresql_where=sa.text('deleted_at IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_experiments_deleted_at', table_name='experiments')
    op.drop_column('experiments', 'deleted_at')
