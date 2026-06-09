"""LLM Trial API — runs dispatch optimization using only Gemini instead of OR-Tools."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.personnel import Personnel
from app.services.llm_dispatch import LlmDispatchService
from app.schemas.schemas import (
    PipelineResponseSchema,
    AssignmentSchema,
    EligibilityResponseSchema,
    PersonnelSchema,
    ScoringResponseSchema,
    ScoredCandidateSchema,
    ScoreBreakdownSchema,
    CrewResponseSchema,
    CrewCandidateSchema,
)

router = APIRouter()


@router.post("/dispatch/llm-trial")
async def run_llm_trial(db: Session = Depends(get_db)):
    service = LlmDispatchService(db)
    result = await service.run_full_pipeline()
    opt = result.optimization

    personnel_map = {p.id: p.name for p in db.query(Personnel).all()}

    # Build eligibility response
    elig_out = {}
    for order_id, elig in result.eligibility.items():
        elig_out[order_id] = EligibilityResponseSchema(
            service_order_id=elig.service_order_id,
            eligible_leads=[PersonnelSchema.model_validate(p) for p in elig.eligible_leads],
            eligible_members=[PersonnelSchema.model_validate(p) for p in elig.eligible_members],
            eligible_drivers=[PersonnelSchema.model_validate(p) for p in elig.eligible_drivers],
            rejections=elig.rejections,
        )

    # Build scoring response
    scoring_out = {}
    for order_id, scoring in result.scoring.items():
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
        scoring_out[order_id] = ScoringResponseSchema(
            service_order_id=scoring.service_order_id,
            scored_leads=[to_schema(sc) for sc in scoring.scored_leads],
            scored_members=[to_schema(sc) for sc in scoring.scored_members],
        )

    # Build crews response
    crews_out = {}
    for order_id, crews in result.crews.items():
        crew_schemas = [
            CrewCandidateSchema(
                lead_id=c.lead.personnel.id,
                lead_name=c.lead.personnel.name,
                member_ids=[m.personnel.id for m in c.members],
                member_names=[m.personnel.name for m in c.members],
                driver_id=c.driver_id,
                total_score=c.total_score,
                journeyman_count=c.journeyman_count,
                apprentice_count=c.apprentice_count,
            )
            for c in crews
        ]
        crews_out[order_id] = CrewResponseSchema(
            service_order_id=order_id,
            crews=crew_schemas,
            count=len(crew_schemas),
        )

    # Build assignments from LLM response
    assignments_out = {}
    if opt and opt.assignments:
        for order_id, assigns in opt.assignments.items():
            assignments_out[order_id] = [
                AssignmentSchema(
                    service_order_id=order_id,
                    personnel_id=a.get("personnel_id", ""),
                    personnel_name=a.get("personnel_name") or personnel_map.get(a.get("personnel_id", "")),
                    role=a.get("role", "member"),
                    individual_score=a.get("individual_score", 0.0),
                )
                for a in assigns
            ]

    return {
        "run_id": result.run_id,
        "status": opt.status if opt else "error",
        "total_score": opt.total_score if opt else 0.0,
        "solve_time_ms": opt.solve_time_ms if opt else 0,
        "reasoning": opt.reasoning if opt else "",
        "eligibility": {k: v.model_dump() for k, v in elig_out.items()},
        "scoring": {k: v.model_dump() for k, v in scoring_out.items()},
        "crews": {k: v.model_dump() for k, v in crews_out.items()},
        "assignments": {k: [a.model_dump() for a in v] for k, v in assignments_out.items()},
    }
