"""seed dummy data

Revision ID: 4cfe1c7ceeb2
Revises: 6d7933df4124
Create Date: 2026-03-09 16:59:23.143048

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4cfe1c7ceeb2'
down_revision: Union[str, Sequence[str], None] = '6d7933df4124'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed dummy data."""
    # Projects
    op.execute("INSERT INTO projects (name) VALUES ('demo-ocr-pipeline')")
    op.execute("INSERT INTO projects (name) VALUES ('demo-nlp-classifier')")

    # Datasets
    op.execute("INSERT INTO datasets (name) VALUES ('COCO-2017')")
    op.execute("INSERT INTO datasets (name) VALUES ('ImageNet-Val')")
    op.execute("INSERT INTO datasets (name) VALUES ('GLUE-MNLI')")

    # Dataset versions
    op.execute("""
        INSERT INTO dataset_versions (dataset_id, version)
        VALUES
            ((SELECT id FROM datasets WHERE name='COCO-2017'), 'v1.0'),
            ((SELECT id FROM datasets WHERE name='COCO-2017'), 'v2.0-cleaned'),
            ((SELECT id FROM datasets WHERE name='ImageNet-Val'), 'v1.0'),
            ((SELECT id FROM datasets WHERE name='GLUE-MNLI'), 'v1.0')
    """)

    # Metrics
    op.execute("""
        INSERT INTO metrics (name, higher_is_better, description) VALUES
            ('accuracy', true, 'Overall accuracy'),
            ('f1_score', true, 'F1 score'),
            ('precision', true, 'Precision'),
            ('recall', true, 'Recall'),
            ('loss', false, 'Loss value')
    """)


def downgrade() -> None:
    """Remove seed data."""
    op.execute("DELETE FROM metrics")
    op.execute("DELETE FROM dataset_versions")
    op.execute("DELETE FROM datasets")
    op.execute("DELETE FROM projects")
