"""Eligibility Engine — determines which personnel can work a given service order."""
from dataclasses import dataclass, field

from app.models.personnel import Personnel
from app.models.service_order import ServiceOrder
from app.engines.rules import (
    CLOSURE_TYPE_LEAD_SKILL,
    CLOSURE_TYPE_MEMBER_SKILL,
    REQUIRED_CERTIFICATION,
    driver_class_meets_requirement,
)


@dataclass
class EligibilityResult:
    service_order_id: str
    eligible_leads: list[Personnel] = field(default_factory=list)
    eligible_members: list[Personnel] = field(default_factory=list)
    eligible_drivers: list[Personnel] = field(default_factory=list)
    rejections: dict[str, list[str]] = field(default_factory=dict)


class EligibilityEngine:
    def get_eligible(
        self, order: ServiceOrder, personnel: list[Personnel]
    ) -> EligibilityResult:
        result = EligibilityResult(service_order_id=order.id)
        required_driver_class = order.vehicle.required_driver_class if order.vehicle else None

        for p in personnel:
            if not p.is_available:
                result.rejections.setdefault(p.id, []).append("Not available")
                continue

            reasons: list[str] = []

            has_cert = self._has_required_certification(p)
            if not has_cert:
                reasons.append(f"Missing {REQUIRED_CERTIFICATION}")

            has_lead_skill = self._has_lead_skill(p, order.closure_type)
            has_member_skill = self._has_member_skill(p)
            can_drive = False

            if required_driver_class:
                can_drive = driver_class_meets_requirement(p.driver_class, required_driver_class)

            if not has_lead_skill and not has_member_skill:
                reasons.append("No matching skills for this closure type")

            if reasons:
                result.rejections[p.id] = reasons
                continue

            if has_lead_skill:
                result.eligible_leads.append(p)
            if has_member_skill:
                result.eligible_members.append(p)
            if can_drive:
                result.eligible_drivers.append(p)

        return result

    def _has_required_certification(self, personnel: Personnel) -> bool:
        return any(c.name == REQUIRED_CERTIFICATION for c in personnel.certifications)

    def _has_lead_skill(self, personnel: Personnel, closure_type: str) -> bool:
        required_skill = CLOSURE_TYPE_LEAD_SKILL.get(closure_type)
        if not required_skill:
            return False
        return any(s.name == required_skill for s in personnel.skills)

    def _has_member_skill(self, personnel: Personnel) -> bool:
        return any(s.name == CLOSURE_TYPE_MEMBER_SKILL for s in personnel.skills)
