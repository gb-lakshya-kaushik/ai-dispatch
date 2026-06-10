"""Pydantic schemas for API request/response models."""
from pydantic import BaseModel


# --- Personnel ---
class SkillSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class CertificationSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class PersonnelSchema(BaseModel):
    id: str
    name: str
    type: str
    hourly_rate: float
    hours_worked_ytd: float
    is_available: bool
    driver_class: str | None
    skills: list[SkillSchema]
    certifications: list[CertificationSchema]

    model_config = {"from_attributes": True}


# --- Customer ---
class CustomerPreferenceSchema(BaseModel):
    personnel_id: str
    preference_level: int

    model_config = {"from_attributes": True}


class CustomerSchema(BaseModel):
    id: str
    name: str
    notes: str | None
    preferred_personnel: list[CustomerPreferenceSchema]

    model_config = {"from_attributes": True}


# --- Vehicle ---
class VehicleSchema(BaseModel):
    id: str
    name: str
    type: str
    required_driver_class: str

    model_config = {"from_attributes": True}


# --- Service Order ---
class ServiceOrderSchema(BaseModel):
    id: str
    customer_id: str
    customer_name: str | None = None
    closure_type: str
    crew_size: int
    leads_required: int
    vehicle_id: str | None
    vehicle_name: str | None = None
    location: str | None
    start_time: str
    end_time: str
    priority: int
    notes: str | None

    model_config = {"from_attributes": True}


# --- Eligibility ---
class EligibilityResponseSchema(BaseModel):
    service_order_id: str
    eligible_leads: list[PersonnelSchema]
    eligible_members: list[PersonnelSchema]
    eligible_drivers: list[PersonnelSchema]
    rejections: dict[str, list[str]]


# --- Scoring ---
class ScoreBreakdownSchema(BaseModel):
    customer_preference: float
    similar_job_experience: float
    hour_balancing: float
    cost_efficiency: float
    skill_match: float
    total: float


class ScoredCandidateSchema(BaseModel):
    personnel_id: str
    personnel_name: str
    personnel_type: str
    score: float
    breakdown: ScoreBreakdownSchema
    role: str


class ScoringResponseSchema(BaseModel):
    service_order_id: str
    scored_leads: list[ScoredCandidateSchema]
    scored_members: list[ScoredCandidateSchema]


# --- Crews ---
class CrewCandidateSchema(BaseModel):
    lead_id: str
    lead_name: str
    member_ids: list[str]
    member_names: list[str]
    driver_id: str | None
    total_score: float
    tc_count: int
    apprentice_count: int


class CrewResponseSchema(BaseModel):
    service_order_id: str
    crews: list[CrewCandidateSchema]
    count: int


# --- Optimization ---
class AssignmentSchema(BaseModel):
    service_order_id: str
    personnel_id: str
    personnel_name: str | None = None
    role: str
    individual_score: float


class OptimizationResponseSchema(BaseModel):
    run_id: str
    status: str
    total_score: float
    solve_time_ms: int
    assignments: dict[str, list[AssignmentSchema]]
    unassigned_orders: list[str]


# --- Full Pipeline ---
class PipelineResponseSchema(BaseModel):
    run_id: str
    status: str
    total_score: float
    solve_time_ms: int
    eligibility: dict[str, EligibilityResponseSchema]
    scoring: dict[str, ScoringResponseSchema]
    crews: dict[str, CrewResponseSchema]
    assignments: dict[str, list[AssignmentSchema]]


# --- Copilot ---
class CopilotRequest(BaseModel):
    question: str
    run_id: str | None = None
    context: dict | None = None


class CopilotResponse(BaseModel):
    answer: str
    follow_up_suggestions: list[str] = []


# --- Config ---
class WeightsSchema(BaseModel):
    customer_preference: float
    similar_job_experience: float
    hour_balancing: float
    cost_efficiency: float
    skill_match: float
