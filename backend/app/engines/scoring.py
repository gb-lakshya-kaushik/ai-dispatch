"""Scoring Engine — ranks eligible personnel for a service order using weighted factors."""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.personnel import Personnel
from app.models.service_order import ServiceOrder
from app.models.job_history import JobHistory
from app.models.customer import CustomerPreference
from app.engines.eligibility import EligibilityResult
from app.engines.rules import CLOSURE_TYPE_LEAD_SKILL


@dataclass
class ScoreBreakdown:
    customer_preference: float = 0.0
    similar_job_experience: float = 0.0
    hour_balancing: float = 0.0
    cost_efficiency: float = 0.0
    skill_match: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.customer_preference
            + self.similar_job_experience
            + self.hour_balancing
            + self.cost_efficiency
            + self.skill_match
        )


@dataclass
class ScoredCandidate:
    personnel: Personnel
    score: float
    breakdown: ScoreBreakdown
    role: str  # 'lead' or 'member'


@dataclass
class ScoringResult:
    service_order_id: str
    scored_leads: list[ScoredCandidate] = field(default_factory=list)
    scored_members: list[ScoredCandidate] = field(default_factory=list)


class ScoringEngine:
    def __init__(self, weights: dict[str, float]):
        self.weights = weights

    def score_candidates(
        self,
        eligibility: EligibilityResult,
        order: ServiceOrder,
        db: Session,
    ) -> ScoringResult:
        all_eligible = list(set(eligibility.eligible_leads + eligibility.eligible_members))
        hours_range = self._get_hours_range(all_eligible)
        rate_range = self._get_rate_range(all_eligible)

        preferences = self._get_customer_preferences(order.customer_id, db)
        job_history = self._get_job_history(db)

        result = ScoringResult(service_order_id=order.id)

        for p in eligibility.eligible_leads:
            breakdown = self._compute_breakdown(
                p, order, preferences, job_history, hours_range, rate_range, "lead"
            )
            result.scored_leads.append(ScoredCandidate(
                personnel=p, score=breakdown.total, breakdown=breakdown, role="lead"
            ))

        for p in eligibility.eligible_members:
            breakdown = self._compute_breakdown(
                p, order, preferences, job_history, hours_range, rate_range, "member"
            )
            result.scored_members.append(ScoredCandidate(
                personnel=p, score=breakdown.total, breakdown=breakdown, role="member"
            ))

        result.scored_leads.sort(key=lambda c: c.score, reverse=True)
        result.scored_members.sort(key=lambda c: c.score, reverse=True)
        return result

    def _compute_breakdown(
        self,
        personnel: Personnel,
        order: ServiceOrder,
        preferences: set[str],
        job_history: dict[str, list[JobHistory]],
        hours_range: tuple[float, float],
        rate_range: tuple[float, float],
        role: str,
    ) -> ScoreBreakdown:
        return ScoreBreakdown(
            customer_preference=self._score_customer_preference(personnel, preferences),
            similar_job_experience=self._score_experience(personnel, order, job_history),
            hour_balancing=self._score_hour_balance(personnel, hours_range),
            cost_efficiency=self._score_cost(personnel, rate_range),
            skill_match=self._score_skill_match(personnel, order, role),
        )

    def _score_customer_preference(self, personnel: Personnel, preferences: set[str]) -> float:
        w = self.weights["customer_preference"]
        return w if personnel.id in preferences else 0.0

    def _score_experience(
        self, personnel: Personnel, order: ServiceOrder,
        job_history: dict[str, list[JobHistory]],
    ) -> float:
        w = self.weights["similar_job_experience"]
        history = job_history.get(personnel.id, [])
        if not history:
            return 0.0

        same_closure = [h for h in history if h.closure_type == order.closure_type]
        same_customer = [h for h in history if h.customer_id == order.customer_id]

        score = 0.0
        if same_closure:
            score += 0.6
        if same_customer:
            score += 0.4
        return score * w

    def _score_hour_balance(self, personnel: Personnel, hours_range: tuple[float, float]) -> float:
        w = self.weights["hour_balancing"]
        min_h, max_h = hours_range
        if max_h == min_h:
            return w * 0.5
        # Lower hours = higher score (favor less-worked employees)
        normalized = 1.0 - (personnel.hours_worked_ytd - min_h) / (max_h - min_h)
        return w * normalized

    def _score_cost(self, personnel: Personnel, rate_range: tuple[float, float]) -> float:
        w = self.weights["cost_efficiency"]
        min_r, max_r = rate_range
        if max_r == min_r:
            return w * 0.5
        # Lower rate = higher score
        normalized = 1.0 - (personnel.hourly_rate - min_r) / (max_r - min_r)
        return w * normalized

    def _score_skill_match(self, personnel: Personnel, order: ServiceOrder, role: str) -> float:
        w = self.weights["skill_match"]
        if role == "lead":
            required = CLOSURE_TYPE_LEAD_SKILL.get(order.closure_type, "")
            has_exact = any(s.name == required for s in personnel.skills)
            return w if has_exact else w * 0.3
        else:
            has_general = any(s.name == "General Assistant" for s in personnel.skills)
            return w * 0.8 if has_general else 0.0

    def _get_customer_preferences(self, customer_id: str, db: Session) -> set[str]:
        prefs = db.query(CustomerPreference).filter_by(customer_id=customer_id).all()
        return {p.personnel_id for p in prefs}

    def _get_job_history(self, db: Session) -> dict[str, list[JobHistory]]:
        all_history = db.query(JobHistory).all()
        result: dict[str, list[JobHistory]] = {}
        for h in all_history:
            result.setdefault(h.personnel_id, []).append(h)
        return result

    def _get_hours_range(self, personnel: list[Personnel]) -> tuple[float, float]:
        if not personnel:
            return (0.0, 0.0)
        hours = [p.hours_worked_ytd for p in personnel]
        return (min(hours), max(hours))

    def _get_rate_range(self, personnel: list[Personnel]) -> tuple[float, float]:
        if not personnel:
            return (0.0, 0.0)
        rates = [p.hourly_rate for p in personnel]
        return (min(rates), max(rates))
