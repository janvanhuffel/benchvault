from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import BenchmarkRun

_last_cleanup: datetime | None = None
_CLEANUP_INTERVAL = timedelta(hours=24)
_TRASH_RETENTION = timedelta(days=7)


def maybe_cleanup_trash(db: Session, force: bool = False) -> None:
    """Purge trashed runs older than 7 days. Runs at most once per 24h unless forced."""
    global _last_cleanup

    now = datetime.now(timezone.utc)

    if not force and _last_cleanup is not None:
        if now - _last_cleanup < _CLEANUP_INTERVAL:
            return

    cutoff = now - _TRASH_RETENTION
    db.query(BenchmarkRun).filter(
        BenchmarkRun.deleted_at.isnot(None),
        BenchmarkRun.deleted_at < cutoff,
    ).delete(synchronize_session="fetch")
    db.commit()

    _last_cleanup = now
