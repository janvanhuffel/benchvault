from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Dataset, DatasetVersion
from app.schemas import (
    DatasetCreateRequest,
    DatasetUpdateRequest,
    DatasetVersionCreateRequest,
    DatasetDetailResponse,
    DatasetVersionDetailResponse,
)

router = APIRouter(prefix="/api")


@router.get("/datasets", response_model=list[DatasetDetailResponse])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).options(joinedload(Dataset.versions)).all()


@router.post("/datasets", response_model=DatasetDetailResponse, status_code=201)
def create_dataset(body: DatasetCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Dataset).filter_by(name=body.name).first()
    if existing:
        raise HTTPException(409, detail=f"Dataset '{body.name}' already exists")
    ds = Dataset(**body.model_dump())
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


@router.patch("/datasets/{name}", response_model=DatasetDetailResponse)
def update_dataset(name: str, body: DatasetUpdateRequest, db: Session = Depends(get_db)):
    ds = db.query(Dataset).options(joinedload(Dataset.versions)).filter_by(name=name).first()
    if not ds:
        raise HTTPException(404, detail=f"Dataset '{name}' not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(ds, key, value)
    db.commit()
    db.refresh(ds)
    return ds


@router.post("/datasets/{name}/versions", response_model=DatasetVersionDetailResponse, status_code=201)
def create_dataset_version(name: str, body: DatasetVersionCreateRequest, db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter_by(name=name).first()
    if not ds:
        raise HTTPException(404, detail=f"Dataset '{name}' not found")
    existing = db.query(DatasetVersion).filter_by(dataset_id=ds.id, version=body.version).first()
    if existing:
        raise HTTPException(409, detail=f"Version '{body.version}' already exists for dataset '{name}'")
    dv = DatasetVersion(dataset_id=ds.id, **body.model_dump())
    db.add(dv)
    db.commit()
    db.refresh(dv)
    return dv
