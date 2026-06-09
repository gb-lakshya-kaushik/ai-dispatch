from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.schemas.schemas import CustomerSchema

router = APIRouter()


@router.get("/customers", response_model=list[CustomerSchema])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()
