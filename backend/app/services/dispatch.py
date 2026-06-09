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

    def run_full_pipeline(self) -> PipelineResult:
        run_id = str(uuid.uuid4())[:8]
        personnel = self.db.query(Personnel).filter_by(is_available=True).all()
        orders = self.db.query(ServiceOrder).all()
        weights = self._load_weights()

        eligibility_engine = EligibilityEngine()
        scoring_engine = ScoringEngine(weights)
        crew_builder = CrewBuilder()
        optimizer = OptimizationEngine()

        result = PipelineResult(run_id=run_id)

        # Step 1 & 2: Eligibility and Scoring for each order
        all_scores: dict[tuple[str, str], float] = {}
        all_eligible_leads: dict[str, set[str]] = {}
        all_eligible_members: dict[str, set[str]] = {}
        all_eligible_drivers: dict[str, set[str]] = {}

        for order in orders:
            elig = eligibility_engine.get_eligible(order, personnel)
            result.eligibility[order.id] = elig
            all_eligible_leads[order.id] = {p.id for p in elig.eligible_leads}
            all_eligible_members[order.id] = {p.id for p in elig.eligible_members}
            all_eligible_drivers[order.id] = {p.id for p in elig.eligible_drivers}

            scoring = scoring_engine.score_candidates(elig, order, self.db)
            result.scoring[order.id] = scoring

            for sc in scoring.scored_leads + scoring.scored_members:
                key = (sc.personnel.id, order.id)
                if key not in all_scores or sc.score > all_scores[key]:
                    all_scores[key] = sc.score

            crews = crew_builder.build_crews(scoring, order)
            result.crews[order.id] = crews

        # Step 3: Optimization
        opt_result = optimizer.optimize(
            orders=orders,
            personnel=personnel,
            scores=all_scores,
            eligible_leads=all_eligible_leads,
            eligible_members=all_eligible_members,
            eligible_drivers=all_eligible_drivers,
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
                        crew_score=opt_result.total_score,
                    ))
            self.db.commit()

        return result

    def run_eligibility(self, order_id: str) -> EligibilityResult:
        order = self.db.query(ServiceOrder).get(order_id)
        personnel = self.db.query(Personnel).filter_by(is_available=True).all()
        engine = EligibilityEngine()
        return engine.get_eligible(order, personnel)

    def run_scoring(self, order_id: str) -> ScoringResult:
        order = self.db.query(ServiceOrder).get(order_id)
        personnel = self.db.query(Personnel).filter_by(is_available=True).all()
        weights = self._load_weights()
        elig_engine = EligibilityEngine()
        scoring_engine = ScoringEngine(weights)
        elig = elig_engine.get_eligible(order, personnel)
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
