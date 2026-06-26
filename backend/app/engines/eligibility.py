"""Eligibility Engine — determines which personnel can work a given service order."""
from dataclasses import dataclass, field

from app.models.personnel import Personnel
from app.models.service_order import ServiceOrder
from app.engines.rules import (
    REQUIRED_CERTIFICATION,
    vehicle_driver_meets_requirement,
)
from app.models.rules import ClosureSkillRule, VehicleDriverRule
from sqlalchemy.orm import Session


@dataclass
class EligibilityResult:
    service_order_id: str
    eligible_leads: list[Personnel] = field(default_factory=list)
    eligible_members: list[Personnel] = field(default_factory=list)
    eligible_drivers: list[Personnel] = field(default_factory=list)
    rejections: dict[str, list[str]] = field(default_factory=dict)


class EligibilityEngine:
    def get_eligible(
        self, order: ServiceOrder, personnel: list[Personnel], db: Session
    ) -> EligibilityResult:
        result = EligibilityResult(service_order_id=order.id)
        
        # Phase 1: Query dynamic rules instead of hardcoded matrices
        rule = db.query(ClosureSkillRule).filter_by(closure_type=order.closure_type).first()
        req_lead_skill = rule.lead_skill if rule else None
        req_member_skill = rule.member_skill if rule else "General Assistant"

        required_driver_class = None
        if order.vehicle:
            v_rule = db.query(VehicleDriverRule).filter_by(vehicle_type=order.vehicle.type).first()
            required_driver_class = v_rule.required_driver_class if v_rule else order.vehicle.required_driver_class

        for p in personnel:
            if p.status in ("DND", "LOA", "PTO"):
                result.rejections.setdefault(p.id, []).append(f"Not available ({p.status})")
                continue

            reasons: list[str] = []
            lead_reasons: list[str] = []  # C2 FIX: track lead-specific reasons separately

            has_cert = self._has_required_certification(p, order.closure_type)
            if not has_cert:
                reasons.append(f"Missing {REQUIRED_CERTIFICATION} or Freeway Certification")

            # Phase 2: Check Customer Required Certifications
            if order.customer and order.customer.required_certifications:
                cust_req_ids = {rc.certification_id for rc in order.customer.required_certifications}
                p_cert_ids = {c.id for c in p.certifications}
                missing_cust_certs = cust_req_ids - p_cert_ids
                if missing_cust_certs:
                    reasons.append("Missing Customer Required Certification(s)")

            has_lead_skill = self._has_lead_skill(p, req_lead_skill)
            has_member_skill = self._has_member_skill(p, req_member_skill)
            can_drive = False

            if order.vehicle:
                p_certs = [c.name for c in p.certifications]
                is_freeway = order.closure_type == "freeway_closure"
                can_drive = vehicle_driver_meets_requirement(
                    p.driver_class, p_certs, order.vehicle.type, required_driver_class,
                    getattr(order, "operating_state", "CA"), is_freeway
                )

            if not has_lead_skill and not has_member_skill:
                reasons.append("No matching skills for this closure type")

            if reasons:
                result.rejections[p.id] = reasons
                continue

            # Only add as lead if no lead-specific blockers
            if has_lead_skill and not lead_reasons:
                result.eligible_leads.append(p)
            elif has_lead_skill and lead_reasons:
                result.rejections.setdefault(p.id, []).extend(lead_reasons)
            if has_member_skill:
                result.eligible_members.append(p)
            if can_drive:
                result.eligible_drivers.append(p)

        return result

    def _has_required_certification(self, personnel: Personnel, closure_type: str) -> bool:
        has_local = any(c.name == REQUIRED_CERTIFICATION for c in personnel.certifications)
        if not has_local:
            return False
        if closure_type in ("freeway_closure", "high_speed_single_lane"):
            return any(c.name == "Freeway Certification" for c in personnel.certifications)
        return True

    def _has_lead_skill(self, personnel: Personnel, required_skill: str | None) -> bool:
        if not required_skill:
            return False
        return any(s.name == required_skill for s in personnel.skills)

    def _has_member_skill(self, personnel: Personnel, required_skill: str | None) -> bool:
        if not required_skill:
            return False
        return any(s.name == required_skill for s in personnel.skills)
