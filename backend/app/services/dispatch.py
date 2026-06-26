"""Pipeline orchestrator — runs the full dispatch flow."""
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.personnel import Personnel
from app.models.service_order import ServiceOrder
from app.models.assignment import Assignment
from app.models.scoring_weight import ScoringWeight
from app.engines.eligibility import EligibilityEngine, EligibilityResult
from app.engines.scoring import ScoringEngine, ScoringResult
from app.engines.crew_builder import CrewBuilder, CrewCandidate
from app.engines.optimizer import OptimizationEngine, OptimizationResult
from app.config import settings


@dataclass
class PipelineResult:
    run_id: str
    eligibility: dict[str, EligibilityResult] = field(default_factory=dict)
    scoring: dict[str, ScoringResult] = field(default_factory=dict)
    crews: dict[str, list[CrewCandidate]] = field(default_factory=dict)
    optimization: OptimizationResult | None = None


class DispatchService:
    def __init__(self, db: Session):
        self.db = db

    def run_full_pipeline(self, dispatch_date: str | None = None) -> PipelineResult:
        run_id = str(uuid.uuid4())[:8]
        personnel = self.db.query(Personnel).filter_by(status="Active").all()

        # C1 FIX: Only fetch orders for the target date, not all historical orders
        if dispatch_date is None:
            # For POC robustness: If no date passed, default to the date of the latest order in the database
            latest_order = self.db.query(ServiceOrder).order_by(ServiceOrder.start_time.desc()).first()
            if latest_order:
                dispatch_date = latest_order.start_time[:10]
            else:
                from datetime import date
                dispatch_date = date.today().isoformat()
        
        orders = self.db.query(ServiceOrder).filter(
            ServiceOrder.start_time.startswith(dispatch_date)
        ).all()
        weights = self._load_weights()

        eligibility_engine = EligibilityEngine()
        scoring_engine = ScoringEngine(weights)
        # H1 FIX: Pass score threshold from settings
        # M4 FIX: Increase max_crews, max_leads, max_members to ensure diverse crews for concurrent orders
        crew_builder = CrewBuilder(
            max_leads=100, 
            max_members=200, 
            max_crews=50, 
            min_crew_score=settings.min_crew_score_threshold
        )
        # H2 FIX: Pass configured timeout to solver
        optimizer = OptimizationEngine(timeout_seconds=settings.optimization_timeout_seconds)

        result = PipelineResult(run_id=run_id)

        # Step 1 & 2: Eligibility and Scoring for each order
        for order in orders:
            elig = eligibility_engine.get_eligible(order, personnel, self.db)
            result.eligibility[order.id] = elig

            scoring = scoring_engine.score_candidates(elig, order, self.db)
            result.scoring[order.id] = scoring

            # M2 FIX: Pass pre-computed eligible_driver_ids to avoid redundant validation
            eligible_driver_ids = {p.id for p in elig.eligible_drivers}
            crews = crew_builder.build_crews(scoring, order, eligible_driver_ids=eligible_driver_ids)
            result.crews[order.id] = crews

        # Step 3: Optimization
        opt_result = optimizer.optimize(
            orders=orders,
            crews=result.crews,
        )
        result.optimization = opt_result

        # Persist assignments
        if opt_result.status in ("optimal", "feasible"):
            for order_id, assignments in opt_result.assignments.items():
                for a in assignments:
                    self.db.add(Assignment(
                        run_id=run_id,
                        service_order_id=a.service_order_id,
                        personnel_id=a.personnel_id,
                        role=a.role,
                        individual_score=a.individual_score,
                        crew_score=a.crew_score,
                    ))
            self.db.commit()

        return result

    def run_eligibility(self, order_id: str) -> EligibilityResult:
        order = self.db.query(ServiceOrder).get(order_id)
        personnel = self.db.query(Personnel).filter_by(status="Active").all()
        engine = EligibilityEngine()
        return engine.get_eligible(order, personnel, self.db)

    def run_scoring(self, order_id: str) -> ScoringResult:
        order = self.db.query(ServiceOrder).get(order_id)
        personnel = self.db.query(Personnel).filter_by(status="Active").all()
        weights = self._load_weights()
        elig_engine = EligibilityEngine()
        scoring_engine = ScoringEngine(weights)
        elig = elig_engine.get_eligible(order, personnel, self.db)
        return scoring_engine.score_candidates(elig, order, self.db)

    def run_crew_building(self, order_id: str) -> list[CrewCandidate]:
        scoring = self.run_scoring(order_id)
        order = self.db.query(ServiceOrder).get(order_id)
        builder = CrewBuilder()
        return builder.build_crews(scoring, order)

    def _load_weights(self) -> dict[str, float]:
        rows = self.db.query(ScoringWeight).all()
        if rows:
            return {r.factor: r.weight for r in rows}
        from app.config import settings
        return settings.scoring_weights
