from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dispatch import DispatchService
from app.schemas.schemas import EligibilityResponseSchema, PersonnelSchema

router = APIRouter()


@router.post("/eligibility/{order_id}", response_model=EligibilityResponseSchema)
def run_eligibility(order_id: str, db: Session = Depends(get_db)):
    service = DispatchService(db)
    result = service.run_eligibility(order_id)
    return EligibilityResponseSchema(
        service_order_id=result.service_order_id,
        eligible_leads=[PersonnelSchema.model_validate(p) for p in result.eligible_leads],
        eligible_members=[PersonnelSchema.model_validate(p) for p in result.eligible_members],
        eligible_drivers=[PersonnelSchema.model_validate(p) for p in result.eligible_drivers],
        rejections=result.rejections,
    )
