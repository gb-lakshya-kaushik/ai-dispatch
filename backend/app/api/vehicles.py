from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.vehicle import Vehicle
from app.schemas.schemas import VehicleSchema

router = APIRouter()


@router.get("/vehicles", response_model=list[VehicleSchema])
def list_vehicles(db: Session = Depends(get_db)):
    return db.query(Vehicle).all()
