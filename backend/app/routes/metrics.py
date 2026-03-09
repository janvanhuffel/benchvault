from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Metric
from app.schemas import MetricResponse

router = APIRouter(prefix="/api")


@router.get("/metrics", response_model=list[MetricResponse])
def list_metrics(db: Session = Depends(get_db)):
    return db.query(Metric).all()
