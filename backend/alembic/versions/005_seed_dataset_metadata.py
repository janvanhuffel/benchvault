"""seed dataset metadata

Revision ID: 005_seed_dataset_metadata
Revises: 6094973080e4
Create Date: 2026-03-10 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '005_seed_dataset_metadata'
down_revision: Union[str, Sequence[str], None] = '6094973080e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Populate metadata on seeded datasets and versions."""

    # --- Dataset-level metadata ---
    op.execute("""
        UPDATE datasets SET
            modality = 'image',
            task = 'object detection',
            license = 'CC BY 4.0',
            source_url = 'https://cocodataset.org'
        WHERE name = 'COCO-2017'
    """)
    op.execute("""
        UPDATE datasets SET
            modality = 'image',
            task = 'classification',
            license = 'Custom (research)',
            source_url = 'https://image-net.org'
        WHERE name = 'ImageNet-Val'
    """)
    op.execute("""
        UPDATE datasets SET
            modality = 'text',
            task = 'NLI',
            license = 'Various',
            source_url = 'https://gluebenchmark.com'
        WHERE name = 'GLUE-MNLI'
    """)

    # --- Version-level metadata ---

    # COCO-2017 v1.0
    op.execute("""
        UPDATE dataset_versions SET
            description = 'Original COCO 2017 release',
            num_classes = 80,
            class_names = ARRAY['person','bicycle','car','motorcycle','airplane','bus','train','truck','boat','traffic light','fire hydrant','stop sign','parking meter','bench','bird','cat','dog','horse','sheep','cow','elephant','bear','zebra','giraffe','backpack','umbrella','handbag','tie','suitcase','frisbee','skis','snowboard','sports ball','kite','baseball bat','baseball glove','skateboard','surfboard','tennis racket','bottle','wine glass','cup','fork','knife','spoon','bowl','banana','apple','sandwich','orange','broccoli','carrot','hot dog','pizza','donut','cake','chair','couch','potted plant','bed','dining table','toilet','tv','laptop','mouse','remote','keyboard','cell phone','microwave','oven','toaster','sink','refrigerator','book','clock','vase','scissors','teddy bear','hair drier','toothbrush'],
            train_count = 118287,
            val_count = 5000,
            total_samples = 123287,
            total_size_gb = 19.3,
            collection_method = 'web crawl + crowdsource annotation',
            file_type = 'jpg'
        WHERE dataset_id = (SELECT id FROM datasets WHERE name = 'COCO-2017')
          AND version = 'v1.0'
    """)

    # COCO-2017 v2.0-cleaned
    op.execute("""
        UPDATE dataset_versions SET
            description = 'Cleaned split with corrected annotations',
            num_classes = 80,
            train_count = 115000,
            val_count = 5000,
            test_count = 3287,
            total_samples = 123287,
            total_size_gb = 19.3,
            collection_method = 'web crawl + crowdsource annotation',
            file_type = 'jpg'
        WHERE dataset_id = (SELECT id FROM datasets WHERE name = 'COCO-2017')
          AND version = 'v2.0-cleaned'
    """)

    # ImageNet-Val v1.0
    op.execute("""
        UPDATE dataset_versions SET
            description = 'ILSVRC 2012 validation set',
            num_classes = 1000,
            val_count = 50000,
            total_samples = 50000,
            total_size_gb = 6.3,
            collection_method = 'web crawl + manual labelling',
            file_type = 'jpg'
        WHERE dataset_id = (SELECT id FROM datasets WHERE name = 'ImageNet-Val')
          AND version = 'v1.0'
    """)

    # GLUE-MNLI v1.0
    op.execute("""
        UPDATE dataset_versions SET
            description = 'Multi-Genre Natural Language Inference',
            num_classes = 3,
            class_names = ARRAY['entailment','neutral','contradiction'],
            train_count = 392702,
            val_count = 9815,
            test_count = 9796,
            total_samples = 412313,
            total_size_gb = 0.1,
            collection_method = 'crowdsource annotation',
            file_type = 'json'
        WHERE dataset_id = (SELECT id FROM datasets WHERE name = 'GLUE-MNLI')
          AND version = 'v1.0'
    """)


def downgrade() -> None:
    """Clear metadata from seeded datasets."""
    op.execute("""
        UPDATE datasets SET
            modality = NULL, task = NULL, license = NULL, source_url = NULL
    """)
    op.execute("""
        UPDATE dataset_versions SET
            description = NULL, num_classes = NULL, class_names = NULL,
            train_count = NULL, val_count = NULL, test_count = NULL,
            total_samples = NULL, total_size_gb = NULL,
            collection_method = NULL, sensor = NULL, file_type = NULL
    """)
