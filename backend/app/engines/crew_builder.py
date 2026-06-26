"""Crew Builder — generates valid crew combinations from scored candidates."""
from dataclasses import dataclass, field
from itertools import combinations

from app.models.service_order import ServiceOrder
from app.engines.scoring import ScoredCandidate, ScoringResult
from app.engines.rules import APPRENTICE_RATIO_RULES, vehicle_driver_meets_requirement


@dataclass
class CrewCandidate:
    leads: list[ScoredCandidate]
    members: list[ScoredCandidate]
    driver_id: str | None
    total_score: float
    composition_valid: bool
    tc_count: int
    apprentice_count: int

    @property
    def all_personnel_ids(self) -> list[str]:
        ids = [lead.personnel.id for lead in self.leads]
        ids.extend(m.personnel.id for m in self.members)
        return ids


class CrewBuilder:
    def __init__(self, max_leads: int = 5, max_members: int = 10, max_crews: int = 10,
                 min_crew_score: float = 0.0):
        self.max_leads = max_leads
        self.max_members = max_members
        self.max_crews = max_crews
        self.min_crew_score = min_crew_score  # H1: quality gate

    def build_crews(
        self, scoring: ScoringResult, order: ServiceOrder,
        eligible_driver_ids: set[str] | None = None,
    ) -> list[CrewCandidate]:
        required_driver_class = order.vehicle.required_driver_class if order.vehicle else None
        
        leads_needed = min(order.leads_required, self.max_leads)
        members_needed = order.crew_size - order.leads_required
        if members_needed < 0:
            return [] # Invalid order crew size vs leads needed
            
        import random

        top_leads = scoring.scored_leads[: self.max_leads]
        top_members = scoring.scored_members[: self.max_members]

        # Shuffle pools to ensure diverse crew candidates for overlapping orders
        random.seed(order.id)
        random.shuffle(top_leads)
        random.shuffle(top_members)


        # M3 FIX: Ensure the truncated pools contain required specialities (Drivers / Cone Trucks)
        pool_ids = {l.personnel.id for l in top_leads} | {m.personnel.id for m in top_members}

        if order.vehicle and eligible_driver_ids:
            if not any(d_id in pool_ids for d_id in eligible_driver_ids):
                extra_drivers = [m for m in scoring.scored_members if m.personnel.id in eligible_driver_ids][:10]
                top_members.extend(extra_drivers)
                for d in extra_drivers: pool_ids.add(d.personnel.id)
                
        if order.vehicle and "Stakebed" in order.vehicle.type and order.closure_type == "freeway_closure":
            has_cone = False
            for p in top_leads + top_members:
                if any(s.name == "Cone Truck Operator Skill" for s in p.personnel.skills):
                    has_cone = True
                    break
            if not has_cone:
                extra_cones = [m for m in scoring.scored_members if any(s.name == "Cone Truck Operator Skill" for s in m.personnel.skills)][:10]
                top_members.extend(extra_cones)

        if len(top_leads) < leads_needed:
            return [] # Cannot fulfill lead requirement

        crews: list[CrewCandidate] = []

        for lead_combo in combinations(top_leads, leads_needed):
            lead_ids = {l.personnel.id for l in lead_combo}
            
            # Exclude the leads from the member pool to avoid duplicates
            available_members = [m for m in top_members if m.personnel.id not in lead_ids]

            if len(available_members) < members_needed:
                continue

            for member_combo in combinations(available_members, members_needed):
                crew_members = list(member_combo)
                all_in_crew = list(lead_combo) + crew_members

                # M2 FIX: Use eligible_driver_ids from EligibilityEngine
                if order.vehicle and eligible_driver_ids is not None:
                    can_drive = any(c.personnel.id in eligible_driver_ids for c in all_in_crew)
                    if not can_drive:
                        continue

                # Phase 4: Stakebed Cone Truck requirement is ONLY for freeway closures per flowchart
                if order.vehicle and "Stakebed" in order.vehicle.type and order.closure_type == "freeway_closure":
                    has_cone_truck = any(any(s.name == "Cone Truck Operator Skill" for s in c.personnel.skills) for c in all_in_crew)
                    if not has_cone_truck:
                        continue

                tc_crew = [c for c in all_in_crew if c.personnel.type == "TC"]
                # if tc_crew:
                #     max_seniority = max(getattr(c.personnel, "seniority", 1) for c in tc_crew)
                #     lead_seniorities = [getattr(l.personnel, "seniority", 1) for l in lead_combo]
                #     if not any(ls >= max_seniority for ls in lead_seniorities):
                #         continue

                # Validate composition
                j_count = sum(1 for c in all_in_crew if c.personnel.type == "TC")
                a_count = sum(1 for c in all_in_crew if c.personnel.type == "apprentice")

                composition_valid = self._validate_composition(
                    order.crew_size, j_count, a_count
                )
                if not composition_valid:
                    continue

                # Validate driver requirement
                driver_id = None
                if required_driver_class:
                    driver_id = self._find_driver(all_in_crew, order, eligible_driver_ids=eligible_driver_ids)
                    if driver_id is None:
                        continue

                total_score = self._compute_crew_score(all_in_crew)

                # H1 FIX: Enforce minimum crew score threshold
                if total_score < self.min_crew_score:
                    continue

                crews.append(CrewCandidate(
                    leads=list(lead_combo),
                    members=crew_members,
                    driver_id=driver_id,
                    total_score=total_score,
                    composition_valid=composition_valid,
                    tc_count=j_count,
                    apprentice_count=a_count,
                ))

                # Break early to prevent combinatorial explosion when pools are large
                if len(crews) >= self.max_crews * 2:
                    break
            
            if len(crews) >= self.max_crews * 2:
                break

        crews.sort(key=lambda c: c.total_score, reverse=True)
        return crews[: self.max_crews]

    def _validate_composition(self, crew_size: int, j_count: int, a_count: int) -> bool:
        rule = APPRENTICE_RATIO_RULES.get(crew_size)
        if rule is None:
            return j_count >= a_count
        min_journeymen, max_apprentices = rule
        return j_count >= min_journeymen and a_count <= max_apprentices

    def _find_driver(
        self, crew: list[ScoredCandidate], order: ServiceOrder,
        eligible_driver_ids: set[str] | None = None,
    ) -> str | None:
        if not order.vehicle or not order.vehicle.required_driver_class:
            return None

        required_class = order.vehicle.required_driver_class
        vehicle_type = order.vehicle.type
        operating_state = getattr(order, "operating_state", "CA")
        is_freeway = order.closure_type == "freeway_closure"

        for c in crew:
            # M2 FIX: Use pre-computed eligible_drivers list if available, else re-validate
            if eligible_driver_ids is not None:
                if c.personnel.id in eligible_driver_ids:
                    return c.personnel.id
            else:
                certs = [cert.name for cert in c.personnel.certifications]
                if vehicle_driver_meets_requirement(
                    c.personnel.driver_class, certs, vehicle_type, required_class, operating_state, is_freeway
                ):
                    return c.personnel.id
        return None

    def _compute_crew_score(self, crew: list[ScoredCandidate]) -> float:
        if not crew:
            return 0.0
        return sum(c.score for c in crew) / len(crew)
