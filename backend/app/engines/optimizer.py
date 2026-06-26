"""OR-Tools CP-SAT Optimization Engine — finds optimal crew assignments across all service orders."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ortools.sat.python import cp_model

from app.models.personnel import Personnel
from app.models.service_order import ServiceOrder
from app.engines.rules import (
    APPRENTICE_RATIO_RULES,
)
from app.engines.crew_builder import CrewCandidate


@dataclass
class AssignmentResult:
    service_order_id: str
    personnel_id: str
    role: str  # 'lead' or 'member'
    individual_score: float
    crew_score: float


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
        crews: dict[str, list[CrewCandidate]],
    ) -> OptimizationResult:
        model = cp_model.CpModel()
        o_ids = [o.id for o in orders]

        # y[o_id, c_idx] = 1 if crew c_idx is assigned to order o_id
        y: dict[tuple[str, int], cp_model.IntVar] = {}
        for o_id in o_ids:
            if o_id in crews:
                for c_idx in range(len(crews[o_id])):
                    y[o_id, c_idx] = model.new_bool_var(f"y_{o_id}_{c_idx}")

        # --- CONSTRAINTS ---

        # C1: At most one crew per order (allows unassigned orders if conflicts exist)
        unassigned_orders = []
        for o_id in o_ids:
            if o_id in crews and len(crews[o_id]) > 0:
                model.add(sum(y[o_id, c_idx] for c_idx in range(len(crews[o_id]))) <= 1)
            else:
                unassigned_orders.append(o_id)

        # C2: No double-booking overlapping orders for any person
        overlapping = self._find_overlapping_orders(orders)
        
        # Precompute mapping: person -> order -> list of crew indices they are in
        person_to_order_crews = {}
        for o_id in o_ids:
            if o_id in crews:
                for c_idx, crew in enumerate(crews[o_id]):
                    for p_id in crew.all_personnel_ids:
                        if p_id not in person_to_order_crews:
                            person_to_order_crews[p_id] = {}
                        if o_id not in person_to_order_crews[p_id]:
                            person_to_order_crews[p_id][o_id] = []
                        person_to_order_crews[p_id][o_id].append(c_idx)

        overlapping_set = set(overlapping)
        overlap_check = set()
        for o1, o2 in overlapping_set:
            overlap_check.add((o1, o2))
            overlap_check.add((o2, o1))

        for p_id, order_map in person_to_order_crews.items():
            p_orders = list(order_map.keys())
            for i in range(len(p_orders)):
                for j in range(i + 1, len(p_orders)):
                    o1 = p_orders[i]
                    o2 = p_orders[j]
                    if (o1, o2) in overlap_check:
                        model.add(
                            sum(y[o1, c] for c in order_map[o1]) + 
                            sum(y[o2, c] for c in order_map[o2]) <= 1
                        )

        # --- OBJECTIVE: Maximize total weighted score * priority ---
        objective_terms = []
        order_priorities = {o.id: o.priority for o in orders}
        for o_id in o_ids:
            if o_id in crews:
                priority = order_priorities.get(o_id, 1)
                for c_idx, crew in enumerate(crews[o_id]):
                    int_score = int(crew.total_score * 100)
                    if int_score > 0:
                        objective_terms.append(y[o_id, c_idx] * int_score * priority)

        model.maximize(sum(objective_terms))

        # --- SOLVE ---
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.timeout_seconds
        status_code = solver.solve(model)

        result = OptimizationResult(unassigned_orders=unassigned_orders)

        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            result.status = "optimal" if status_code == cp_model.OPTIMAL else "feasible"
            result.total_score = solver.objective_value / 100.0
            result.solve_time_ms = int(solver.wall_time * 1000)

            for o_id in o_ids:
                if o_id in unassigned_orders:
                    continue
                assigned = False
                for c_idx, crew in enumerate(crews[o_id]):
                    if solver.value(y[o_id, c_idx]) == 1:
                        assigned = True
                        result.assignments[o_id] = []
                        # Add Leads
                        for lead in crew.leads:
                            role = "driver" if crew.driver_id == lead.personnel.id else "lead"
                            result.assignments[o_id].append(AssignmentResult(
                                service_order_id=o_id,
                                personnel_id=lead.personnel.id,
                                role=role,
                                individual_score=lead.score,
                                crew_score=crew.total_score,
                            ))
                        # Add Members
                        for member in crew.members:
                            role = "driver" if crew.driver_id == member.personnel.id else "member"
                            result.assignments[o_id].append(AssignmentResult(
                                service_order_id=o_id,
                                personnel_id=member.personnel.id,
                                role=role,
                                individual_score=member.score,
                                crew_score=crew.total_score,
                            ))
                        break
                if not assigned:
                    result.unassigned_orders.append(o_id)
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
        
        # Add 1 hour padding for travel time
        padding = timedelta(hours=1)
        return (start1 - padding) < end2 and (start2 - padding) < end1
