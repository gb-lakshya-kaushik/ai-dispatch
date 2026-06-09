from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dispatch import DispatchService
from app.schemas.schemas import ScoringResponseSchema, ScoredCandidateSchema, ScoreBreakdownSchema

router = APIRouter()


@router.post("/scoring/{order_id}", response_model=ScoringResponseSchema)
def run_scoring(order_id: str, db: Session = Depends(get_db)):
    service = DispatchService(db)
    result = service.run_scoring(order_id)

    def to_schema(sc):
        return ScoredCandidateSchema(
            personnel_id=sc.personnel.id,
            personnel_name=sc.personnel.name,
            personnel_type=sc.personnel.type,
            score=sc.score,
            breakdown=ScoreBreakdownSchema(
                customer_preference=sc.breakdown.customer_preference,
                similar_job_experience=sc.breakdown.similar_job_experience,
                hour_balancing=sc.breakdown.hour_balancing,
                cost_efficiency=sc.breakdown.cost_efficiency,
                skill_match=sc.breakdown.skill_match,
                total=sc.breakdown.total,
            ),
            role=sc.role,
        )

    return ScoringResponseSchema(
        service_order_id=result.service_order_id,
        scored_leads=[to_schema(sc) for sc in result.scored_leads],
        scored_members=[to_schema(sc) for sc in result.scored_members],
    )
