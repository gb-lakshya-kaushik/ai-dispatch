from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.assignment import Assignment
from app.services.copilot import CopilotService
from app.schemas.schemas import CopilotRequest, CopilotResponse

router = APIRouter()
copilot = CopilotService()


@router.post("/copilot/ask", response_model=CopilotResponse)
async def ask_copilot(request: CopilotRequest, db: Session = Depends(get_db)):
    context = request.context or {}

    if request.run_id:
        assignments = db.query(Assignment).filter_by(run_id=request.run_id).all()
        # C3 FIX: Group all crew members per order instead of overwriting with last person
        crew_by_order: dict = {}
        for a in assignments:
            crew_by_order.setdefault(a.service_order_id, []).append({
                "personnel_id": a.personnel_id,
                "role": a.role,
                "score": a.individual_score,
            })
        context["assignments"] = crew_by_order

    answer = await copilot.ask(request.question, context)
    return CopilotResponse(
        answer=answer,
        follow_up_suggestions=[
            "Why was this person selected?",
            "Show alternative crews",
            "What if this person is unavailable?",
        ],
    )
