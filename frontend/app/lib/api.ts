const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  getPersonnel: () => fetchApi<Personnel[]>("/api/personnel"),
  getServiceOrders: () => fetchApi<ServiceOrder[]>("/api/service-orders"),
  getVehicles: () => fetchApi<Vehicle[]>("/api/vehicles"),
  getCustomers: () => fetchApi<Customer[]>("/api/customers"),
  runEligibility: (orderId: string) =>
    fetchApi<EligibilityResponse>(`/api/eligibility/${orderId}`, { method: "POST" }),
  runScoring: (orderId: string) =>
    fetchApi<ScoringResponse>(`/api/scoring/${orderId}`, { method: "POST" }),
  runCrews: (orderId: string) =>
    fetchApi<CrewResponse>(`/api/crews/${orderId}`, { method: "POST" }),
  runOptimization: () =>
    fetchApi<OptimizationResponse>("/api/optimization/run", { method: "POST" }),
  runFullPipeline: () =>
    fetchApi<PipelineResponse>("/api/dispatch/run", { method: "POST" }),
  askCopilot: (question: string, runId?: string, context?: Record<string, unknown>) =>
    fetchApi<CopilotResponse>("/api/copilot/ask", {
      method: "POST",
      body: JSON.stringify({ question, run_id: runId, context }),
    }),
  getWeights: () => fetchApi<Weights>("/api/config/weights"),
  updateWeights: (weights: Weights) =>
    fetchApi<Weights>("/api/config/weights", {
      method: "PUT",
      body: JSON.stringify(weights),
    }),
  resetData: () => fetchApi<{ status: string }>("/api/data/reset", { method: "POST" }),
};

// Types
export interface Personnel {
  id: string;
  name: string;
  type: "TC" | "apprentice";
  hourly_rate: number;
  hours_worked_ytd: number;
  status: string;
  driver_class: string | null;
  skills: { id: number; name: string }[];
  certifications: { id: number; name: string }[];
}

export interface ServiceOrder {
  id: string;
  customer_id: string;
  customer_name: string | null;
  closure_type: string;
  crew_size: number;
  leads_required: number;
  vehicle_id: string | null;
  vehicle_name: string | null;
  location: string | null;
  start_time: string;
  end_time: string;
  priority: number;
  notes: string | null;
}

export interface Vehicle {
  id: string;
  name: string;
  type: string;
  required_driver_class: string;
}

export interface Customer {
  id: string;
  name: string;
  notes: string | null;
  preferred_personnel: { personnel_id: string; preference_level: number }[];
}

export interface ScoreBreakdown {
  customer_preference: number;
  similar_job_experience: number;
  hour_balancing: number;
  cost_efficiency: number;
  skill_match: number;
  total: number;
}

export interface ScoredCandidate {
  personnel_id: string;
  personnel_name: string;
  personnel_type: string;
  score: number;
  breakdown: ScoreBreakdown;
  role: string;
}

export interface EligibilityResponse {
  service_order_id: string;
  eligible_leads: Personnel[];
  eligible_members: Personnel[];
  eligible_drivers: Personnel[];
  rejections: Record<string, string[]>;
}

export interface ScoringResponse {
  service_order_id: string;
  scored_leads: ScoredCandidate[];
  scored_members: ScoredCandidate[];
}

export interface CrewCandidate {
  lead_id: string;
  lead_name: string;
  member_ids: string[];
  member_names: string[];
  driver_id: string | null;
  total_score: number;
  tc_count: number;
  apprentice_count: number;
}

export interface CrewResponse {
  service_order_id: string;
  crews: CrewCandidate[];
  count: number;
}

export interface Assignment {
  service_order_id: string;
  personnel_id: string;
  personnel_name: string | null;
  role: string;
  individual_score: number;
}

export interface OptimizationResponse {
  run_id: string;
  status: string;
  total_score: number;
  solve_time_ms: number;
  assignments: Record<string, Assignment[]>;
  unassigned_orders: string[];
}

export interface PipelineResponse {
  run_id: string;
  status: string;
  total_score: number;
  solve_time_ms: number;
  eligibility: Record<string, EligibilityResponse>;
  scoring: Record<string, ScoringResponse>;
  crews: Record<string, CrewResponse>;
  assignments: Record<string, Assignment[]>;
}

export interface CopilotResponse {
  answer: string;
  follow_up_suggestions: string[];
}

export interface Weights {
  customer_preference: number;
  similar_job_experience: number;
  hour_balancing: number;
  cost_efficiency: number;
  skill_match: number;
}
