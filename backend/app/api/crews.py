from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dispatch import DispatchService
from app.schemas.schemas import CrewResponseSchema, CrewCandidateSchema

router = APIRouter()


@router.post("/crews/{order_id}", response_model=CrewResponseSchema)
def build_crews(order_id: str, db: Session = Depends(get_db)):
    service = DispatchService(db)
    crews = service.run_crew_building(order_id)

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

    return CrewResponseSchema(
        service_order_id=order_id,
        crews=crew_schemas,
        count=len(crew_schemas),
    )
