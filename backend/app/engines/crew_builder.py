"""Crew Builder — generates valid crew combinations from scored candidates."""
from dataclasses import dataclass, field
from itertools import combinations

from app.models.service_order import ServiceOrder
from app.engines.scoring import ScoredCandidate, ScoringResult
from app.engines.rules import APPRENTICE_RATIO_RULES, driver_class_meets_requirement


@dataclass
class CrewCandidate:
    lead: ScoredCandidate
    members: list[ScoredCandidate]
    driver_id: str | None
    total_score: float
    composition_valid: bool
    tc_count: int
    apprentice_count: int

    @property
    def all_personnel_ids(self) -> list[str]:
        ids = [self.lead.personnel.id]
        ids.extend(m.personnel.id for m in self.members)
        return ids


class CrewBuilder:
    def __init__(self, max_leads: int = 5, max_members: int = 10, max_crews: int = 10):
        self.max_leads = max_leads
        self.max_members = max_members
        self.max_crews = max_crews

    def build_crews(
        self, scoring: ScoringResult, order: ServiceOrder
    ) -> list[CrewCandidate]:
        required_driver_class = order.vehicle.required_driver_class if order.vehicle else None
        members_needed = order.crew_size - order.leads_required

        top_leads = scoring.scored_leads[: self.max_leads]
        top_members = scoring.scored_members[: self.max_members]

        crews: list[CrewCandidate] = []

        for lead in top_leads:
            # Exclude the lead from the member pool to avoid duplicates
            available_members = [m for m in top_members if m.personnel.id != lead.personnel.id]

            if len(available_members) < members_needed:
                continue

            for member_combo in combinations(available_members, members_needed):
                crew_members = list(member_combo)
                all_in_crew = [lead] + crew_members

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
                    driver_id = self._find_driver(all_in_crew, required_driver_class)
                    if driver_id is None:
                        continue

                total_score = self._compute_crew_score(all_in_crew)

                crews.append(CrewCandidate(
                    lead=lead,
                    members=crew_members,
                    driver_id=driver_id,
                    total_score=total_score,
                    composition_valid=composition_valid,
                    tc_count=j_count,
                    apprentice_count=a_count,
                ))

        crews.sort(key=lambda c: c.total_score, reverse=True)
        return crews[: self.max_crews]

    def _validate_composition(self, crew_size: int, j_count: int, a_count: int) -> bool:
        rule = APPRENTICE_RATIO_RULES.get(crew_size)
        if rule is None:
            return j_count >= a_count
        min_journeymen, max_apprentices = rule
        return j_count >= min_journeymen and a_count <= max_apprentices

    def _find_driver(
        self, crew: list[ScoredCandidate], required_class: str
    ) -> str | None:
        for c in crew:
            if driver_class_meets_requirement(c.personnel.driver_class, required_class):
                return c.personnel.id
        return None

    def _compute_crew_score(self, crew: list[ScoredCandidate]) -> float:
        if not crew:
            return 0.0
        return sum(c.score for c in crew) / len(crew)
