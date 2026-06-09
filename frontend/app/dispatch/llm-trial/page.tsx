"use client";

import { useState } from "react";
import Link from "next/link";
import {
  api,
  type LlmTrialResponse,
  type Assignment,
  type ScoredCandidate,
  type EligibilityResponse,
  type ScoringResponse,
  type CrewCandidate,
} from "../../lib/api";
import { useDispatch } from "../../lib/dispatch-context";

type TrialStep = "idle" | "running" | "done";

export default function LlmTrialPage() {
  const [step, setStep] = useState<TrialStep>("idle");
  const [result, setResult] = useState<LlmTrialResponse | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { result: orToolsResult } = useDispatch();

  const runTrial = async () => {
    setStep("running");
    setError(null);
    try {
      const data = await api.runLlmTrial();
      setResult(data);
      if (Object.keys(data.assignments).length > 0) {
        setSelectedOrder(Object.keys(data.assignments).sort()[0]);
      }
      setStep("done");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "LLM trial failed");
      setStep("idle");
    }
  };

  const scoreDiff = orToolsResult && result
    ? result.total_score - orToolsResult.total_score
    : null;

  return (
    <div className="max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">LLM Trial (Research)</h1>
          <p className="text-muted-foreground text-sm">
            Gemini 3.5 Pro replaces OR-Tools — same constraints, no algorithmic solver
          </p>
        </div>
        <button
          onClick={runTrial}
          disabled={step === "running"}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {step === "running"
            ? "Calling Gemini..."
            : step === "done"
            ? "Re-run LLM Trial"
            : "Run LLM Optimization"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-md p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {step === "running" && (
        <div className="flex items-center gap-3 text-muted-foreground py-12 justify-center">
          <div className="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full" />
          Running LLM-only optimization (this may take 15-30s)...
        </div>
      )}

      {result && step === "done" && (
        <div className="space-y-6">
          {/* Comparison Banner */}
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-6 flex-wrap">
              <StatusBadge status={result.status} />
              <div>
                <div className="text-sm text-muted-foreground">LLM Score</div>
                <div className="text-xl font-bold">{result.total_score.toFixed(1)}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Response Time</div>
                <div className="text-xl font-bold">{(result.solve_time_ms / 1000).toFixed(1)}s</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Orders Assigned</div>
                <div className="text-xl font-bold">{Object.keys(result.assignments).length}</div>
              </div>

              {orToolsResult && (
                <>
                  <div className="border-l border-border pl-6">
                    <div className="text-sm text-muted-foreground">OR-Tools Score</div>
                    <div className="text-xl font-bold text-green-600">{orToolsResult.total_score.toFixed(1)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Δ Score</div>
                    <div className={`text-xl font-bold ${scoreDiff !== null && scoreDiff >= 0 ? "text-green-600" : "text-red-600"}`}>
                      {scoreDiff !== null ? (scoreDiff >= 0 ? "+" : "") + scoreDiff.toFixed(1) : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">% of Optimal</div>
                    <div className="text-xl font-bold">
                      {orToolsResult.total_score > 0
                        ? ((result.total_score / orToolsResult.total_score) * 100).toFixed(1)
                        : "—"}%
                    </div>
                  </div>
                </>
              )}

              {!orToolsResult && (
                <div className="ml-auto">
                  <Link
                    href="/dispatch"
                    className="px-3 py-1.5 bg-muted text-muted-foreground rounded-md text-xs font-medium hover:bg-accent transition-colors"
                  >
                    Run OR-Tools first for comparison →
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* LLM Reasoning */}
          {result.reasoning && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span className="text-sm font-semibold text-blue-700">LLM Reasoning</span>
              </div>
              <p className="text-sm text-blue-800">{result.reasoning}</p>
            </div>
          )}

          {/* Order selector tabs */}
          <div className="flex flex-wrap gap-2">
            {Object.keys(result.assignments)
              .sort()
              .map((oid) => (
                <button
                  key={oid}
                  onClick={() => setSelectedOrder(oid)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    selectedOrder === oid
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground hover:bg-accent"
                  }`}
                >
                  {oid}
                </button>
              ))}
          </div>

          {selectedOrder && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <EligibilityPanel data={result.eligibility[selectedOrder]} />
              <ScoringPanel data={result.scoring[selectedOrder]} />
              <CrewsPanel data={result.crews[selectedOrder]} />
              <AssignmentPanel
                orderId={selectedOrder}
                assignments={result.assignments[selectedOrder]}
                scoring={result.scoring[selectedOrder]}
                orToolsAssignments={orToolsResult?.assignments[selectedOrder]}
              />
            </div>
          )}

          {/* Assignment Matrix */}
          <AssignmentMatrix assignments={result.assignments} />
        </div>
      )}

      {step === "idle" && !result && (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg mb-2">LLM-Only Optimization Trial</p>
          <p className="text-sm mb-4">
            Tests whether Gemini 3.5 Pro can solve the same constraint optimization problem
            that OR-Tools handles algorithmically.
          </p>
          <p className="text-xs text-muted-foreground/70">
            Tip: Run the regular pipeline first (/dispatch) so you can compare results side-by-side.
          </p>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "llm_solution"
      ? "bg-purple-100 text-purple-800"
      : status === "parse_error"
      ? "bg-red-100 text-red-800"
      : "bg-yellow-100 text-yellow-800";
  return <span className={`px-3 py-1 rounded-full text-sm font-medium ${color}`}>{status}</span>;
}

function EligibilityPanel({ data }: { data?: EligibilityResponse }) {
  if (!data) return null;
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="font-semibold mb-3 text-sm">Step 1: Eligibility</h3>
      <div className="grid grid-cols-3 gap-2 text-center mb-3">
        <div className="bg-green-50 rounded p-2">
          <div className="text-lg font-bold text-green-700">{data.eligible_leads.length}</div>
          <div className="text-xs text-green-600">Leads</div>
        </div>
        <div className="bg-blue-50 rounded p-2">
          <div className="text-lg font-bold text-blue-700">{data.eligible_members.length}</div>
          <div className="text-xs text-blue-600">Members</div>
        </div>
        <div className="bg-orange-50 rounded p-2">
          <div className="text-lg font-bold text-orange-700">{Object.keys(data.rejections).length}</div>
          <div className="text-xs text-orange-600">Rejected</div>
        </div>
      </div>
    </div>
  );
}

function ScoringPanel({ data }: { data?: { scored_leads: ScoredCandidate[]; scored_members: ScoredCandidate[] } }) {
  if (!data) return null;
  const topCandidates = [...data.scored_leads.slice(0, 3), ...data.scored_members.slice(0, 4)];
  const maxScore = Math.max(...topCandidates.map((c) => c.score), 1);

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="font-semibold mb-3 text-sm">Step 2: Scoring</h3>
      <div className="space-y-2">
        {topCandidates.map((c) => (
          <div key={`${c.personnel_id}-${c.role}`} className="flex items-center gap-2">
            <span className="text-xs w-24 truncate">{c.personnel_name}</span>
            <div className="flex-1 bg-muted rounded-full h-4 overflow-hidden">
              <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${(c.score / maxScore) * 100}%` }} />
            </div>
            <span className="text-xs font-mono w-10 text-right">{c.score.toFixed(0)}</span>
            <span className={`text-xs px-1 rounded ${c.role === "lead" ? "bg-purple-100 text-purple-700" : "bg-gray-100"}`}>{c.role}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CrewsPanel({ data }: { data?: { crews: CrewCandidate[]; count: number } }) {
  if (!data) return null;
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="font-semibold mb-3 text-sm">Step 3: Crew Building ({data.count} valid crews)</h3>
      <div className="space-y-2">
        {data.crews.slice(0, 5).map((crew, i) => (
          <div key={i} className="flex items-center gap-2 text-xs border border-border rounded p-2">
            <span className="font-bold text-primary">#{i + 1}</span>
            <span className="font-medium">{crew.lead_name}</span>
            <span className="text-muted-foreground">+</span>
            <span className="truncate flex-1">{crew.member_names.join(", ")}</span>
            <span className="font-mono bg-muted px-1.5 py-0.5 rounded">{crew.total_score.toFixed(0)}</span>
            <span className="text-muted-foreground">{crew.journeyman_count}J/{crew.apprentice_count}A</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AssignmentPanel({
  orderId,
  assignments,
  scoring,
  orToolsAssignments,
}: {
  orderId: string;
  assignments?: Assignment[];
  scoring?: ScoringResponse;
  orToolsAssignments?: Assignment[];
}) {
  if (!assignments) return null;

  const orToolsPersonnel = new Set(orToolsAssignments?.map((a) => a.personnel_id) || []);

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="font-semibold mb-3 text-sm">Step 4: LLM Assignment ({orderId})</h3>
      <div className="space-y-3">
        {assignments.map((a) => {
          const scoringData = a.role === "lead"
            ? scoring?.scored_leads.find((s) => s.personnel_id === a.personnel_id)
            : scoring?.scored_members.find((s) => s.personnel_id === a.personnel_id);

          const sameAsOrTools = orToolsPersonnel.has(a.personnel_id);

          return (
            <div key={a.personnel_id} className="border border-border rounded-md p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2.5 h-2.5 rounded-full ${a.role === "lead" ? "bg-purple-500" : "bg-blue-500"}`} />
                <span className="font-medium flex-1">{a.personnel_name}</span>
                {sameAsOrTools && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700">same as OR-Tools</span>
                )}
                {!sameAsOrTools && orToolsAssignments && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-100 text-orange-700">different</span>
                )}
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${a.role === "lead" ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"}`}>{a.role}</span>
                <span className="text-sm font-bold">{a.individual_score.toFixed(1)} pts</span>
              </div>
              {scoringData && (
                <div className="mt-2">
                  <div className="flex gap-0.5 h-3 rounded overflow-hidden">
                    <ScoreSegment value={scoringData.breakdown.skill_match} max={30} color="bg-indigo-400" />
                    <ScoreSegment value={scoringData.breakdown.hour_balancing} max={25} color="bg-emerald-400" />
                    <ScoreSegment value={scoringData.breakdown.customer_preference} max={20} color="bg-amber-400" />
                    <ScoreSegment value={scoringData.breakdown.similar_job_experience} max={15} color="bg-pink-400" />
                    <ScoreSegment value={scoringData.breakdown.cost_efficiency} max={10} color="bg-cyan-400" />
                  </div>
                  <div className="flex gap-2 mt-1.5 flex-wrap">
                    <ScoreLegend color="bg-indigo-400" label="Skill" value={scoringData.breakdown.skill_match} />
                    <ScoreLegend color="bg-emerald-400" label="Hours" value={scoringData.breakdown.hour_balancing} />
                    <ScoreLegend color="bg-amber-400" label="Pref" value={scoringData.breakdown.customer_preference} />
                    <ScoreLegend color="bg-pink-400" label="Exp" value={scoringData.breakdown.similar_job_experience} />
                    <ScoreLegend color="bg-cyan-400" label="Cost" value={scoringData.breakdown.cost_efficiency} />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ScoreSegment({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = (value / max) * (max / 100) * 100;
  if (value === 0) return null;
  return <div className={`${color} transition-all`} style={{ width: `${pct}%` }} title={`${value.toFixed(1)}`} />;
}

function ScoreLegend({ color, label, value }: { color: string; label: string; value: number }) {
  return (
    <span className="inline-flex items-center gap-1 text-[10px] text-muted-foreground">
      <span className={`w-2 h-2 rounded-sm ${color}`} />
      {label}: {value.toFixed(1)}
    </span>
  );
}

function AssignmentMatrix({ assignments }: { assignments: Record<string, Assignment[]> }) {
  const allPersonnel = new Map<string, string>();
  Object.values(assignments).flat().forEach((a) => {
    if (a.personnel_name) allPersonnel.set(a.personnel_id, a.personnel_name);
  });
  const orderIds = Object.keys(assignments).sort();
  const personnelIds = Array.from(allPersonnel.keys()).sort();

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="font-semibold mb-3">LLM Assignment Matrix</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="px-2 py-2 text-left">Personnel</th>
              {orderIds.map((oid) => (<th key={oid} className="px-2 py-2 text-center">{oid}</th>))}
            </tr>
          </thead>
          <tbody>
            {personnelIds.map((pid) => (
              <tr key={pid} className="border-b border-border/50">
                <td className="px-2 py-1.5 font-medium">{allPersonnel.get(pid)}</td>
                {orderIds.map((oid) => {
                  const assignment = assignments[oid]?.find((a) => a.personnel_id === pid);
                  return (
                    <td key={oid} className="px-2 py-1.5 text-center">
                      {assignment ? (
                        <span className={`inline-block w-6 h-6 rounded text-xs leading-6 ${assignment.role === "lead" ? "bg-purple-200 text-purple-800" : "bg-blue-200 text-blue-800"}`}>
                          {assignment.role === "lead" ? "L" : "M"}
                        </span>
                      ) : (<span className="text-muted-foreground">—</span>)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
