"""seed 30 demo benchmark runs

Revision ID: 003_seed_demo_runs
Revises: 4295d3d94a6f
Create Date: 2026-03-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '003_seed_demo_runs'
down_revision: Union[str, Sequence[str], None] = '4295d3d94a6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed model versions, 30 benchmark runs, and run metrics."""

    # ── Model versions ──────────────────────────────────────────────
    op.execute("""
        INSERT INTO model_versions (model_name, model_version, description) VALUES
            ('tesseract-ocr', 'v4.1', 'Tesseract OCR engine v4.1'),
            ('paddleocr',     'v2.1', 'PaddleOCR v2.1'),
            ('easyocr',       'v1.4', 'EasyOCR v1.4'),
            ('trocr-base',    'v0.3', 'TrOCR base model v0.3'),
            ('bert-base',     'v1.0', 'BERT base uncased v1.0'),
            ('roberta-large', 'v1.0', 'RoBERTa large v1.0'),
            ('distilbert',    'v1.0', 'DistilBERT v1.0'),
            ('deberta-v3',    'v0.9', 'DeBERTa v3 base v0.9')
    """)

    # ── Benchmark runs ──────────────────────────────────────────────
    # Helper aliases used in subselects:
    #   proj_ocr  = (SELECT id FROM projects WHERE name='demo-ocr-pipeline')
    #   proj_nlp  = (SELECT id FROM projects WHERE name='demo-nlp-classifier')
    #   mv(n,v)   = (SELECT id FROM model_versions WHERE model_name=n AND model_version=v)
    #   dv(d,v)   = (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name=d) AND version=v)

    op.execute("""
        INSERT INTO benchmark_runs (project_id, model_version_id, dataset_version_id, epoch, created_at) VALUES

        -- tesseract-ocr v4.1 / COCO-2017 v1.0  (3 runs)
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='tesseract-ocr' AND model_version='v4.1'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v1.0'),
            5,  '2026-01-03 09:12:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='tesseract-ocr' AND model_version='v4.1'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v1.0'),
            10, '2026-01-06 14:35:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='tesseract-ocr' AND model_version='v4.1'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v1.0'),
            20, '2026-01-10 11:48:00'
        ),

        -- paddleocr v2.1 / COCO-2017 v1.0  (3 runs)
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='paddleocr' AND model_version='v2.1'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v1.0'),
            5,  '2026-01-14 08:22:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='paddleocr' AND model_version='v2.1'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v1.0'),
            10, '2026-01-18 16:05:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='paddleocr' AND model_version='v2.1'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v1.0'),
            20, '2026-01-22 10:30:00'
        ),

        -- easyocr v1.4 / COCO-2017 v1.0  (2 runs)
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='easyocr' AND model_version='v1.4'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v1.0'),
            10, '2026-01-25 13:15:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='easyocr' AND model_version='v1.4'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v1.0'),
            20, '2026-01-29 17:42:00'
        ),

        -- trocr-base v0.3 / COCO-2017 v2.0-cleaned  (3 runs)
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='trocr-base' AND model_version='v0.3'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v2.0-cleaned'),
            5,  '2026-02-02 09:50:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='trocr-base' AND model_version='v0.3'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v2.0-cleaned'),
            10, '2026-02-06 11:28:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='trocr-base' AND model_version='v0.3'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v2.0-cleaned'),
            20, '2026-02-10 15:03:00'
        ),

        -- paddleocr v2.1 / COCO-2017 v2.0-cleaned  (2 runs)
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='paddleocr' AND model_version='v2.1'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v2.0-cleaned'),
            10, '2026-02-13 08:17:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='paddleocr' AND model_version='v2.1'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='COCO-2017') AND version='v2.0-cleaned'),
            20, '2026-02-17 14:45:00'
        ),

        -- tesseract-ocr v4.1 / ImageNet-Val v1.0  (2 runs)
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='tesseract-ocr' AND model_version='v4.1'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='ImageNet-Val') AND version='v1.0'),
            10, '2026-02-20 10:33:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-ocr-pipeline'),
            (SELECT id FROM model_versions WHERE model_name='tesseract-ocr' AND model_version='v4.1'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='ImageNet-Val') AND version='v1.0'),
            20, '2026-02-24 16:20:00'
        ),

        -- ── NLP runs ───────────────────────────────────────────────

        -- bert-base v1.0 / GLUE-MNLI v1.0  (3 runs)
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='bert-base' AND model_version='v1.0'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            3,  '2026-02-01 09:00:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='bert-base' AND model_version='v1.0'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            5,  '2026-02-04 12:15:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='bert-base' AND model_version='v1.0'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            10, '2026-02-08 15:40:00'
        ),

        -- roberta-large v1.0 / GLUE-MNLI v1.0  (3 runs)
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='roberta-large' AND model_version='v1.0'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            3,  '2026-02-12 10:22:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='roberta-large' AND model_version='v1.0'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            5,  '2026-02-16 13:55:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='roberta-large' AND model_version='v1.0'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            10, '2026-02-21 08:10:00'
        ),

        -- distilbert v1.0 / GLUE-MNLI v1.0  (2 runs)
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='distilbert' AND model_version='v1.0'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            5,  '2026-02-25 11:30:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='distilbert' AND model_version='v1.0'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            10, '2026-03-01 14:48:00'
        ),

        -- deberta-v3 v0.9 / GLUE-MNLI v1.0  (3 runs)
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='deberta-v3' AND model_version='v0.9'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            3,  '2026-03-03 09:25:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='deberta-v3' AND model_version='v0.9'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            5,  '2026-03-06 12:40:00'
        ),
        (
            (SELECT id FROM projects WHERE name='demo-nlp-classifier'),
            (SELECT id FROM model_versions WHERE model_name='deberta-v3' AND model_version='v0.9'),
            (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='GLUE-MNLI') AND version='v1.0'),
            10, '2026-03-09 16:55:00'
        )
    """)

    # ── Run metrics ─────────────────────────────────────────────────
    # Each run gets 5 metrics (accuracy, f1_score, precision, recall, loss).
    # We reference runs by their unique (model_version_id, dataset_version_id, epoch) combo.

    # -- tesseract-ocr v4.1 / COCO-2017 v1.0 / epoch 5
    _insert_run_metrics('tesseract-ocr', 'v4.1', 'COCO-2017', 'v1.0', 5,
                        0.721, 0.685, 0.712, 0.660, 0.643)
    # -- tesseract-ocr v4.1 / COCO-2017 v1.0 / epoch 10
    _insert_run_metrics('tesseract-ocr', 'v4.1', 'COCO-2017', 'v1.0', 10,
                        0.768, 0.734, 0.751, 0.718, 0.489)
    # -- tesseract-ocr v4.1 / COCO-2017 v1.0 / epoch 20
    _insert_run_metrics('tesseract-ocr', 'v4.1', 'COCO-2017', 'v1.0', 20,
                        0.793, 0.761, 0.778, 0.745, 0.412)

    # -- paddleocr v2.1 / COCO-2017 v1.0 / epoch 5
    _insert_run_metrics('paddleocr', 'v2.1', 'COCO-2017', 'v1.0', 5,
                        0.782, 0.756, 0.769, 0.743, 0.501)
    # -- paddleocr v2.1 / COCO-2017 v1.0 / epoch 10
    _insert_run_metrics('paddleocr', 'v2.1', 'COCO-2017', 'v1.0', 10,
                        0.841, 0.819, 0.833, 0.806, 0.347)
    # -- paddleocr v2.1 / COCO-2017 v1.0 / epoch 20
    _insert_run_metrics('paddleocr', 'v2.1', 'COCO-2017', 'v1.0', 20,
                        0.873, 0.854, 0.865, 0.843, 0.271)

    # -- easyocr v1.4 / COCO-2017 v1.0 / epoch 10
    _insert_run_metrics('easyocr', 'v1.4', 'COCO-2017', 'v1.0', 10,
                        0.798, 0.771, 0.784, 0.759, 0.445)
    # -- easyocr v1.4 / COCO-2017 v1.0 / epoch 20
    _insert_run_metrics('easyocr', 'v1.4', 'COCO-2017', 'v1.0', 20,
                        0.831, 0.808, 0.821, 0.796, 0.358)

    # -- trocr-base v0.3 / COCO-2017 v2.0-cleaned / epoch 5
    _insert_run_metrics('trocr-base', 'v0.3', 'COCO-2017', 'v2.0-cleaned', 5,
                        0.823, 0.801, 0.815, 0.788, 0.402)
    # -- trocr-base v0.3 / COCO-2017 v2.0-cleaned / epoch 10
    _insert_run_metrics('trocr-base', 'v0.3', 'COCO-2017', 'v2.0-cleaned', 10,
                        0.889, 0.871, 0.882, 0.861, 0.238)
    # -- trocr-base v0.3 / COCO-2017 v2.0-cleaned / epoch 20
    _insert_run_metrics('trocr-base', 'v0.3', 'COCO-2017', 'v2.0-cleaned', 20,
                        0.934, 0.921, 0.928, 0.914, 0.142)

    # -- paddleocr v2.1 / COCO-2017 v2.0-cleaned / epoch 10
    _insert_run_metrics('paddleocr', 'v2.1', 'COCO-2017', 'v2.0-cleaned', 10,
                        0.862, 0.843, 0.855, 0.832, 0.298)
    # -- paddleocr v2.1 / COCO-2017 v2.0-cleaned / epoch 20
    _insert_run_metrics('paddleocr', 'v2.1', 'COCO-2017', 'v2.0-cleaned', 20,
                        0.901, 0.886, 0.894, 0.878, 0.211)

    # -- tesseract-ocr v4.1 / ImageNet-Val v1.0 / epoch 10
    _insert_run_metrics('tesseract-ocr', 'v4.1', 'ImageNet-Val', 'v1.0', 10,
                        0.743, 0.709, 0.728, 0.691, 0.534)
    # -- tesseract-ocr v4.1 / ImageNet-Val v1.0 / epoch 20
    _insert_run_metrics('tesseract-ocr', 'v4.1', 'ImageNet-Val', 'v1.0', 20,
                        0.771, 0.739, 0.755, 0.724, 0.461)

    # -- bert-base v1.0 / GLUE-MNLI v1.0 / epoch 3
    _insert_run_metrics('bert-base', 'v1.0', 'GLUE-MNLI', 'v1.0', 3,
                        0.789, 0.762, 0.781, 0.744, 0.523)
    # -- bert-base v1.0 / GLUE-MNLI v1.0 / epoch 5
    _insert_run_metrics('bert-base', 'v1.0', 'GLUE-MNLI', 'v1.0', 5,
                        0.832, 0.811, 0.825, 0.797, 0.389)
    # -- bert-base v1.0 / GLUE-MNLI v1.0 / epoch 10
    _insert_run_metrics('bert-base', 'v1.0', 'GLUE-MNLI', 'v1.0', 10,
                        0.854, 0.836, 0.848, 0.824, 0.321)

    # -- roberta-large v1.0 / GLUE-MNLI v1.0 / epoch 3
    _insert_run_metrics('roberta-large', 'v1.0', 'GLUE-MNLI', 'v1.0', 3,
                        0.841, 0.823, 0.837, 0.810, 0.378)
    # -- roberta-large v1.0 / GLUE-MNLI v1.0 / epoch 5
    _insert_run_metrics('roberta-large', 'v1.0', 'GLUE-MNLI', 'v1.0', 5,
                        0.887, 0.873, 0.882, 0.864, 0.251)
    # -- roberta-large v1.0 / GLUE-MNLI v1.0 / epoch 10
    _insert_run_metrics('roberta-large', 'v1.0', 'GLUE-MNLI', 'v1.0', 10,
                        0.912, 0.901, 0.908, 0.894, 0.189)

    # -- distilbert v1.0 / GLUE-MNLI v1.0 / epoch 5
    _insert_run_metrics('distilbert', 'v1.0', 'GLUE-MNLI', 'v1.0', 5,
                        0.774, 0.748, 0.763, 0.734, 0.551)
    # -- distilbert v1.0 / GLUE-MNLI v1.0 / epoch 10
    _insert_run_metrics('distilbert', 'v1.0', 'GLUE-MNLI', 'v1.0', 10,
                        0.806, 0.783, 0.796, 0.771, 0.442)

    # -- deberta-v3 v0.9 / GLUE-MNLI v1.0 / epoch 3
    _insert_run_metrics('deberta-v3', 'v0.9', 'GLUE-MNLI', 'v1.0', 3,
                        0.836, 0.817, 0.829, 0.806, 0.391)
    # -- deberta-v3 v0.9 / GLUE-MNLI v1.0 / epoch 5
    _insert_run_metrics('deberta-v3', 'v0.9', 'GLUE-MNLI', 'v1.0', 5,
                        0.878, 0.862, 0.873, 0.851, 0.267)
    # -- deberta-v3 v0.9 / GLUE-MNLI v1.0 / epoch 10
    _insert_run_metrics('deberta-v3', 'v0.9', 'GLUE-MNLI', 'v1.0', 10,
                        0.903, 0.890, 0.898, 0.882, 0.204)


def downgrade() -> None:
    """Remove seeded demo runs, run metrics, and model versions."""
    # Delete in reverse FK order: run_metrics -> benchmark_runs -> model_versions
    model_names = (
        "'tesseract-ocr','paddleocr','easyocr','trocr-base',"
        "'bert-base','roberta-large','distilbert','deberta-v3'"
    )

    op.execute(f"""
        DELETE FROM run_metrics
        WHERE run_id IN (
            SELECT id FROM benchmark_runs
            WHERE model_version_id IN (
                SELECT id FROM model_versions
                WHERE model_name IN ({model_names})
            )
        )
    """)

    op.execute(f"""
        DELETE FROM benchmark_runs
        WHERE model_version_id IN (
            SELECT id FROM model_versions
            WHERE model_name IN ({model_names})
        )
    """)

    op.execute(f"""
        DELETE FROM model_versions
        WHERE model_name IN ({model_names})
    """)


# ── Helper ──────────────────────────────────────────────────────────

def _insert_run_metrics(
    model_name: str,
    model_version: str,
    dataset_name: str,
    dataset_version: str,
    epoch: int,
    accuracy: float,
    f1_score: float,
    precision: float,
    recall: float,
    loss: float,
) -> None:
    """Insert the five standard metrics for one benchmark run."""
    run_subselect = (
        f"(SELECT id FROM benchmark_runs "
        f"WHERE model_version_id = (SELECT id FROM model_versions WHERE model_name='{model_name}' AND model_version='{model_version}') "
        f"AND dataset_version_id = (SELECT id FROM dataset_versions WHERE dataset_id=(SELECT id FROM datasets WHERE name='{dataset_name}') AND version='{dataset_version}') "
        f"AND epoch={epoch})"
    )
    for metric_name, value in [
        ('accuracy', accuracy),
        ('f1_score', f1_score),
        ('precision', precision),
        ('recall', recall),
        ('loss', loss),
    ]:
        op.execute(
            f"INSERT INTO run_metrics (run_id, metric_id, value) VALUES "
            f"({run_subselect}, (SELECT id FROM metrics WHERE name='{metric_name}'), {value})"
        )
