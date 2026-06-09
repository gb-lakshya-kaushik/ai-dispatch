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
        context["assignments"] = {
            a.service_order_id: {
                "personnel_id": a.personnel_id,
                "role": a.role,
                "score": a.individual_score,
            }
            for a in assignments
        }

    answer = await copilot.ask(request.question, context)
    return CopilotResponse(
        answer=answer,
        follow_up_suggestions=[
            "Why was this person selected?",
            "Show alternative crews",
            "What if this person is unavailable?",
        ],
    )
