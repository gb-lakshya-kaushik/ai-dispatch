from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scoring_weight import ScoringWeight
from app.schemas.schemas import WeightsSchema

router = APIRouter()


@router.get("/config/weights", response_model=WeightsSchema)
def get_weights(db: Session = Depends(get_db)):
    rows = db.query(ScoringWeight).all()
    weights = {r.factor: r.weight for r in rows}
    return WeightsSchema(**weights)


@router.put("/config/weights", response_model=WeightsSchema)
def update_weights(new_weights: WeightsSchema, db: Session = Depends(get_db)):
    for factor, weight in new_weights.model_dump().items():
        row = db.query(ScoringWeight).filter_by(factor=factor).first()
        if row:
            row.weight = weight
        else:
            # H5 FIX: Insert new factor if it doesn't exist yet
            db.add(ScoringWeight(factor=factor, weight=weight))
    db.commit()
    return new_weights
