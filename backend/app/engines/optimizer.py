"""OR-Tools CP-SAT Optimization Engine — finds optimal crew assignments across all service orders."""
from dataclasses import dataclass, field
from datetime import datetime

from ortools.sat.python import cp_model

from app.models.personnel import Personnel
from app.models.service_order import ServiceOrder
from app.engines.rules import (
    CLOSURE_TYPE_LEAD_SKILL,
    REQUIRED_CERTIFICATION,
    APPRENTICE_RATIO_RULES,
    driver_class_meets_requirement,
)


@dataclass
class AssignmentResult:
    service_order_id: str
    personnel_id: str
    role: str  # 'lead' or 'member'
    individual_score: float


@dataclass
class OptimizationResult:
    assignments: dict[str, list[AssignmentResult]] = field(default_factory=dict)
    total_score: float = 0.0
    solve_time_ms: int = 0
    status: str = "unknown"
    unassigned_orders: list[str] = field(default_factory=list)


class OptimizationEngine:
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    def optimize(
        self,
        orders: list[ServiceOrder],
        personnel: list[Personnel],
        scores: dict[tuple[str, str], float],  # (personnel_id, order_id) -> score
        eligible_leads: dict[str, set[str]],  # order_id -> set of personnel_ids
        eligible_members: dict[str, set[str]],  # order_id -> set of personnel_ids
        eligible_drivers: dict[str, set[str]],  # order_id -> set of personnel_ids
    ) -> OptimizationResult:
        model = cp_model.CpModel()

        p_ids = [p.id for p in personnel]
        o_ids = [o.id for o in orders]
        personnel_map = {p.id: p for p in personnel}
        order_map = {o.id: o for o in orders}

        # Decision variables: x[p_id, o_id] = 1 if person p assigned to order o
        x: dict[tuple[str, str], cp_model.IntVar] = {}
        for p_id in p_ids:
            for o_id in o_ids:
                x[p_id, o_id] = model.new_bool_var(f"x_{p_id}_{o_id}")

        # Lead indicator: lead[p_id, o_id] = 1 if person p is lead on order o
        lead: dict[tuple[str, str], cp_model.IntVar] = {}
        for p_id in p_ids:
            for o_id in o_ids:
                lead[p_id, o_id] = model.new_bool_var(f"lead_{p_id}_{o_id}")

        # --- CONSTRAINTS ---

        # C1: No double-booking for overlapping orders
        overlapping = self._find_overlapping_orders(orders)
        for o1_id, o2_id in overlapping:
            for p_id in p_ids:
                model.add(x[p_id, o1_id] + x[p_id, o2_id] <= 1)

        # C2: Crew size exactly met
        for o in orders:
            model.add(sum(x[p_id, o.id] for p_id in p_ids) == o.crew_size)

        # C3: Exactly one lead per order
        for o in orders:
            model.add(sum(lead[p_id, o.id] for p_id in p_ids) == 1)

        # C4: Lead must be assigned to the order
        for p_id in p_ids:
            for o_id in o_ids:
                model.add(lead[p_id, o_id] <= x[p_id, o_id])

        # C5: Only eligible leads can be lead
        for o_id in o_ids:
            for p_id in p_ids:
                if p_id not in eligible_leads.get(o_id, set()):
                    model.add(lead[p_id, o_id] == 0)

        # C6: Only eligible personnel (leads + members) can be assigned
        for o_id in o_ids:
            eligible_for_order = eligible_leads.get(o_id, set()) | eligible_members.get(o_id, set())
            for p_id in p_ids:
                if p_id not in eligible_for_order:
                    model.add(x[p_id, o_id] == 0)

        # C7: Driver requirement — at least one qualified driver assigned
        for o in orders:
            if o.vehicle_id:
                drivers = eligible_drivers.get(o.id, set())
                if drivers:
                    model.add(sum(x[p_id, o.id] for p_id in drivers) >= 1)

        # C8: Apprentice/Journeyman ratio
        for o in orders:
            rule = APPRENTICE_RATIO_RULES.get(o.crew_size)
            if rule:
                min_j, max_a = rule
                journeymen = [p_id for p_id in p_ids if personnel_map[p_id].type == "journeyman"]
                apprentices = [p_id for p_id in p_ids if personnel_map[p_id].type == "apprentice"]
                model.add(sum(x[p_id, o.id] for p_id in journeymen) >= min_j)
                model.add(sum(x[p_id, o.id] for p_id in apprentices) <= max_a)

        # --- OBJECTIVE: Maximize total weighted score ---
        objective_terms = []
        for p_id in p_ids:
            for o_id in o_ids:
                score = scores.get((p_id, o_id), 0.0)
                int_score = int(score * 100)
                if int_score > 0:
                    objective_terms.append(x[p_id, o_id] * int_score)

        model.maximize(sum(objective_terms))

        # --- SOLVE ---
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.timeout_seconds
        status_code = solver.solve(model)

        result = OptimizationResult()

        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            result.status = "optimal" if status_code == cp_model.OPTIMAL else "feasible"
            result.total_score = solver.objective_value / 100.0
            result.solve_time_ms = int(solver.wall_time * 1000)

            for o_id in o_ids:
                result.assignments[o_id] = []
                for p_id in p_ids:
                    if solver.value(x[p_id, o_id]) == 1:
                        role = "lead" if solver.value(lead[p_id, o_id]) == 1 else "member"
                        result.assignments[o_id].append(AssignmentResult(
                            service_order_id=o_id,
                            personnel_id=p_id,
                            role=role,
                            individual_score=scores.get((p_id, o_id), 0.0),
                        ))
        else:
            result.status = "infeasible"
            result.unassigned_orders = o_ids

        return result

    def _find_overlapping_orders(
        self, orders: list[ServiceOrder]
    ) -> list[tuple[str, str]]:
        overlapping: list[tuple[str, str]] = []
        for i, o1 in enumerate(orders):
            for o2 in orders[i + 1:]:
                if self._times_overlap(o1.start_time, o1.end_time, o2.start_time, o2.end_time):
                    overlapping.append((o1.id, o2.id))
        return overlapping

    def _times_overlap(self, s1: str, e1: str, s2: str, e2: str) -> bool:
        start1 = datetime.fromisoformat(s1)
        end1 = datetime.fromisoformat(e1)
        start2 = datetime.fromisoformat(s2)
        end2 = datetime.fromisoformat(e2)
        return start1 < end2 and start2 < end1
