"""add storage_url to dataset_versions

Revision ID: 006_add_storage_url
Revises: 005_seed_dataset_metadata
Create Date: 2026-03-10 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_storage_url'
down_revision: Union[str, Sequence[str], None] = '005_seed_dataset_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dataset_versions', sa.Column('storage_url', sa.String(), nullable=True))

    op.execute("""
        UPDATE dataset_versions SET storage_url = 's3://benchvault-data/coco-2017/v1.0/'
        WHERE dataset_id = (SELECT id FROM datasets WHERE name = 'COCO-2017') AND version = 'v1.0'
    """)
    op.execute("""
        UPDATE dataset_versions SET storage_url = 's3://benchvault-data/coco-2017/v2.0-cleaned/'
        WHERE dataset_id = (SELECT id FROM datasets WHERE name = 'COCO-2017') AND version = 'v2.0-cleaned'
    """)
    op.execute("""
        UPDATE dataset_versions SET storage_url = 's3://benchvault-data/imagenet-val/v1.0/'
        WHERE dataset_id = (SELECT id FROM datasets WHERE name = 'ImageNet-Val') AND version = 'v1.0'
    """)
    op.execute("""
        UPDATE dataset_versions SET storage_url = 's3://benchvault-data/glue-mnli/v1.0/'
        WHERE dataset_id = (SELECT id FROM datasets WHERE name = 'GLUE-MNLI') AND version = 'v1.0'
    """)


def downgrade() -> None:
    op.drop_column('dataset_versions', 'storage_url')
