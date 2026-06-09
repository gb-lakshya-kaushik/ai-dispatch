"""LLM-only dispatch using GPT-5 to replicate OR-Tools optimization via prompting."""
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from openai import AsyncOpenAI

from app.config import settings
from app.models.personnel import Personnel
from app.models.service_order import ServiceOrder
from app.engines.eligibility import EligibilityEngine, EligibilityResult
from app.engines.scoring import ScoringEngine, ScoringResult
from app.engines.crew_builder import CrewBuilder, CrewCandidate
from app.engines.rules import APPRENTICE_RATIO_RULES, DRIVER_CLASS_HIERARCHY
from app.models.scoring_weight import ScoringWeight


@dataclass
class LlmOptimizationResult:
    assignments: dict[str, list[dict]] = field(default_factory=dict)
    total_score: float = 0.0
    solve_time_ms: int = 0
    status: str = "unknown"
    reasoning: str = ""
    unassigned_orders: list[str] = field(default_factory=list)


@dataclass
class LlmPipelineResult:
    run_id: str
    eligibility: dict[str, EligibilityResult] = field(default_factory=dict)
    scoring: dict[str, ScoringResult] = field(default_factory=dict)
    crews: dict[str, list[CrewCandidate]] = field(default_factory=dict)
    optimization: LlmOptimizationResult | None = None


class LlmDispatchService:
    def __init__(self, db: Session):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def run_full_pipeline(self) -> LlmPipelineResult:
        run_id = str(uuid.uuid4())[:8]
        personnel = self.db.query(Personnel).filter_by(is_available=True).all()
        orders = self.db.query(ServiceOrder).all()
        weights = self._load_weights()

        eligibility_engine = EligibilityEngine()
        scoring_engine = ScoringEngine(weights)
        crew_builder = CrewBuilder()

        result = LlmPipelineResult(run_id=run_id)

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

        # Instead of OR-Tools, call GPT-5
        llm_result = await self._llm_optimize(
            orders=orders,
            personnel=personnel,
            scores=all_scores,
            eligible_leads=all_eligible_leads,
            eligible_members=all_eligible_members,
            eligible_drivers=all_eligible_drivers,
            scoring_results=result.scoring,
        )
        result.optimization = llm_result

        return result

    async def _llm_optimize(
        self,
        orders: list[ServiceOrder],
        personnel: list[Personnel],
        scores: dict[tuple[str, str], float],
        eligible_leads: dict[str, set[str]],
        eligible_members: dict[str, set[str]],
        eligible_drivers: dict[str, set[str]],
        scoring_results: dict[str, ScoringResult],
    ) -> LlmOptimizationResult:
        if not self.client:
            return LlmOptimizationResult(status="error", reasoning="No API key configured")

        personnel_map = {p.id: p for p in personnel}

        prompt = self._build_optimization_prompt(
            orders, personnel, scores, eligible_leads,
            eligible_members, eligible_drivers, scoring_results,
        )

        start_time = time.time()
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an optimization assistant. Output valid JSON only.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )
                elapsed_ms = int((time.time() - start_time) * 1000)

                raw_text = ""
                if response.choices and response.choices[0].message.content:
                    raw_text = response.choices[0].message.content.strip()

                if not raw_text:
                    if attempt < max_retries:
                        continue
                    return LlmOptimizationResult(
                        status="error",
                        solve_time_ms=elapsed_ms,
                        reasoning="LLM returned empty response",
                    )

                parsed = json.loads(raw_text)

                result = LlmOptimizationResult(
                    status=parsed.get("status", "llm_solution"),
                    total_score=parsed.get("total_score", 0.0),
                    solve_time_ms=elapsed_ms,
                    reasoning=parsed.get("reasoning", ""),
                    assignments=parsed.get("assignments", {}),
                )

                # Validate and recalculate actual total score from our scoring data
                actual_total = 0.0
                normalized_assignments: dict[str, list[dict]] = {}
                for order_id, crew in result.assignments.items():
                    normalized_crew = []
                    for member in crew:
                        pid = member.get("id") or member.get("personnel_id", "")
                        role = member.get("role", "member")
                        actual_score = scores.get((pid, order_id), 0.0)
                        p_obj = personnel_map.get(pid)
                        normalized_crew.append({
                            "personnel_id": pid,
                            "personnel_name": p_obj.name if p_obj else pid,
                            "role": role,
                            "individual_score": actual_score,
                        })
                        actual_total += actual_score
                    normalized_assignments[order_id] = normalized_crew
                result.assignments = normalized_assignments
                result.total_score = actual_total

                return result

            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    continue
                elapsed_ms = int((time.time() - start_time) * 1000)
                return LlmOptimizationResult(
                    status="parse_error",
                    solve_time_ms=elapsed_ms,
                    reasoning=f"Failed to parse LLM JSON response after {max_retries + 1} attempts: {str(e)}. Raw: {raw_text[:500]}",
                )
            except Exception as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                return LlmOptimizationResult(
                    status="error",
                    solve_time_ms=elapsed_ms,
                    reasoning=f"LLM call failed: {str(e)}",
                )

        elapsed_ms = int((time.time() - start_time) * 1000)
        return LlmOptimizationResult(status="error", solve_time_ms=elapsed_ms, reasoning="All retries exhausted")

    def _build_optimization_prompt(
        self,
        orders: list[ServiceOrder],
        personnel: list[Personnel],
        scores: dict[tuple[str, str], float],
        eligible_leads: dict[str, set[str]],
        eligible_members: dict[str, set[str]],
        eligible_drivers: dict[str, set[str]],
        scoring_results: dict[str, ScoringResult],
    ) -> str:
        personnel_map = {p.id: p for p in personnel}

        # Build overlapping pairs
        overlapping = self._find_overlapping_orders(orders)

        # Build compact per-order data
        orders_compact = []
        for o in sorted(orders, key=lambda x: x.id):
            leads = []
            for pid in sorted(eligible_leads.get(o.id, set())):
                p = personnel_map[pid]
                s = scores.get((pid, o.id), 0.0)
                leads.append(f"{pid}({p.type[0]},drv={p.driver_class},s={s:.1f})")

            members = []
            for pid in sorted(eligible_members.get(o.id, set())):
                p = personnel_map[pid]
                s = scores.get((pid, o.id), 0.0)
                members.append(f"{pid}({p.type[0]},drv={p.driver_class},s={s:.1f})")

            drivers = sorted(eligible_drivers.get(o.id, set()))

            orders_compact.append(
                f"{o.id}: crew={o.crew_size}, vehicle={'YES' if o.vehicle_id else 'NO'}, "
                f"time={o.start_time[-8:-3]}-{o.end_time[-8:-3]}\n"
                f"  leads: [{', '.join(leads)}]\n"
                f"  members: [{', '.join(members)}]\n"
                f"  drivers: [{', '.join(drivers)}]"
            )

        orders_str = "\n\n".join(orders_compact)
        overlap_str = ", ".join([f"({a}-{b})" for a, b in overlapping]) if overlapping else "NONE"

        prompt = f"""Solve this workforce assignment optimization problem. Assign personnel to orders to MAXIMIZE total score.

CONSTRAINTS:
C1: No double-booking. Overlapping pairs: [{overlap_str}]. A person can only be in ONE of any overlapping pair.
C2: Each order needs EXACTLY crew_size people (lead included).
C3: Exactly 1 lead per order from the eligible leads list.
C4: Members can come from eligible_leads OR eligible_members.
C5: If vehicle=YES, at least 1 assigned person must be in the drivers list.
C6: Journeyman(j)/Apprentice(a) ratio per crew size: 2→1j+1a, 3→2j+1a, 4→3j+1a, 5→3j+2a, 6→4j+2a.

LEGEND: TC###(type, drv=driver_class, s=score_for_this_order). Type: j=journeyman, a=apprentice.

ORDERS:
{orders_str}

TASK: Find the assignment maximizing SUM of all individual scores. Output JSON only:
{{"assignments":{{"SO001":[{{"id":"TC###","role":"lead"}},{{"id":"TC###","role":"member"}}]}},"total_score":NUMBER,"reasoning":"SHORT"}}

Rules: every order must appear, crew_size people each, 1 lead each, no person in 2 overlapping orders, ratio rules met, driver rules met."""

        return prompt

    def _find_overlapping_orders(self, orders: list[ServiceOrder]) -> list[list[str]]:
        overlapping = []
        for i, o1 in enumerate(orders):
            for o2 in orders[i + 1:]:
                if self._times_overlap(o1.start_time, o1.end_time, o2.start_time, o2.end_time):
                    overlapping.append([o1.id, o2.id])
        return overlapping

    def _times_overlap(self, s1: str, e1: str, s2: str, e2: str) -> bool:
        start1 = datetime.fromisoformat(s1)
        end1 = datetime.fromisoformat(e1)
        start2 = datetime.fromisoformat(s2)
        end2 = datetime.fromisoformat(e2)
        return start1 < end2 and start2 < end1

    def _load_weights(self) -> dict[str, float]:
        rows = self.db.query(ScoringWeight).all()
        if rows:
            return {r.factor: r.weight for r in rows}
        from app.config import settings
        return settings.scoring_weights
