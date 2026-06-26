from app.models.personnel import Personnel, Skill, Certification, PersonnelSkill, PersonnelCertification
from app.models.customer import Customer, CustomerPreference, CustomerRequiredCertification
from app.models.vehicle import Vehicle
from app.models.service_order import ServiceOrder
from app.models.assignment import Assignment
from app.models.scoring_weight import ScoringWeight
from app.models.job_history import JobHistory
from app.models.rules import ClosureSkillRule, VehicleDriverRule

__all__ = [
    "Personnel", "Skill", "Certification", "PersonnelSkill", "PersonnelCertification",
    "Customer", "CustomerPreference", "CustomerRequiredCertification",
    "Vehicle",
    "ServiceOrder",
    "Assignment",
    "ScoringWeight",
    "JobHistory",
    "ClosureSkillRule",
    "VehicleDriverRule",
]
