from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.personnel import Personnel
from app.schemas.schemas import PersonnelSchema

router = APIRouter()


@router.get("/personnel", response_model=list[PersonnelSchema])
def list_personnel(db: Session = Depends(get_db)):
    return db.query(Personnel).all()


@router.get("/personnel/{personnel_id}", response_model=PersonnelSchema)
def get_personnel(personnel_id: str, db: Session = Depends(get_db)):
    # H4 FIX: Return 404 instead of 500 on missing personnel
    p = db.query(Personnel).filter_by(id=personnel_id).first()
    if p is None:
        raise HTTPException(status_code=404, detail=f"Personnel '{personnel_id}' not found")
    return p
