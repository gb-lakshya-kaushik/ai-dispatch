"use client";

import { useState } from "react";
import Link from "next/link";
import {
  api,
  type PipelineResponse,
  type Assignment,
  type ScoredCandidate,
  type CrewCandidate,
  type EligibilityResponse,
  type ScoringResponse,
} from "../lib/api";
import { useDispatch, type ExplanationData } from "../lib/dispatch-context";

interface ExplanationProgress {
  completed: number;
  failed: number;
  total: number;
  currentOrder: string;
  status: "running" | "done" | "failed";
  failReason?: string;
}

export default function DispatchPage() {
  const {
    step, result, selectedOrder, error, explanations,
    setStep, setResult, setSelectedOrder, setError, setExplanations,
  } = useDispatch();

  const [explainProgress, setExplainProgress] = useState<ExplanationProgress | null>(null);

  const runPipeline = async () => {
    setStep("running");
    setError(null);
    setExplanations(null);
    setExplainProgress(null);
    try {
      const data = await api.runFullPipeline();
      setResult(data);

      if (Object.keys(data.assignments).length > 0) {
        setSelectedOrder(Object.keys(data.assignments).sort()[0]);
      }

      setStep("explaining");
      const orderIds = Object.keys(data.assignments).sort();
      const total = orderIds.length + 1; // +1 for verdict
      setExplainProgress({ completed: 0, failed: 0, total, currentOrder: "verdict", status: "running" });

      const expData = await generateExplanations(data, (progress) => {
        setExplainProgress(progress);
      });

      if (expData) {
        setExplanations(expData);
        setExplainProgress((p) => p ? { ...p, status: "done" } : null);
      }
      setStep("done");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Pipeline failed");
      setStep("idle");
    }
  };

  return (
    <div className="max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Dispatch Flow</h1>
          <p className="text-muted-foreground text-sm">
            Eligibility → Scoring → Crew Building → Optimization → Explanation
          </p>
        </div>
        <button
          onClick={runPipeline}
          disabled={step === "running" || step === "explaining"}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {step === "running"
            ? "Optimizing..."
            : step === "explaining"
            ? "Generating Explanations..."
            : step === "done"
            ? "Re-run Pipeline"
            : "Run Full Pipeline"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-md p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {(step === "running" || step === "explaining") && (
        <div className="py-8">
          {step === "running" && (
            <div className="flex items-center gap-3 text-muted-foreground justify-center">
              <div className="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full" />
              Running optimization pipeline...
            </div>
          )}
          {step === "explaining" && explainProgress && (
            <div className="max-w-lg mx-auto space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  Generating explanations... <span className="font-medium text-foreground">{explainProgress.currentOrder}</span>
                </span>
                <span className="font-mono text-xs">
                  {explainProgress.completed}/{explainProgress.total}
                  {explainProgress.failed > 0 && (
                    <span className="text-red-500 ml-2">{explainProgress.failed} failed</span>
                  )}
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 rounded-full ${
                    explainProgress.failed > 0 ? "bg-yellow-500" : "bg-primary"
                  }`}
                  style={{ width: `${(explainProgress.completed / explainProgress.total) * 100}%` }}
                />
              </div>
              {explainProgress.status === "failed" && explainProgress.failReason && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-md p-3 text-xs">
                  <span className="font-medium">First call failed — aborting:</span> {explainProgress.failReason}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {result && (step === "done" || step === "explaining") && (
        <div className="space-y-6">
          {/* Summary Banner */}
          <div className="bg-card border border-border rounded-lg p-4 flex items-center gap-6">
            <StatusBadge status={result.status} />
            <div>
              <div className="text-sm text-muted-foreground">Total Score</div>
              <div className="text-xl font-bold">{result.total_score.toFixed(1)}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Solve Time</div>
              <div className="text-xl font-bold">{result.solve_time_ms}ms</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Orders Assigned</div>
              <div className="text-xl font-bold">{Object.keys(result.assignments).length}</div>
            </div>
            {explanations && (
              <Link
                href="/dispatch/summary"
                className="ml-auto px-3 py-1.5 bg-blue-100 text-blue-700 rounded-md text-xs font-medium hover:bg-blue-200 transition-colors"
              >
                View Full Summary →
              </Link>
            )}
          </div>

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
                explanation={explanations?.perOrder[selectedOrder]}
              />
            </div>
          )}

          {/* Full Assignment Matrix */}
          <AssignmentMatrix assignments={result.assignments} />
        </div>
      )}

      {step === "idle" && !result && (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg mb-2">Ready to optimize</p>
          <p className="text-sm">
            Click &quot;Run Full Pipeline&quot; to start the dispatch optimization
          </p>
        </div>
      )}
    </div>
  );
}

async function generateExplanations(
  data: PipelineResponse,
  onProgress: (progress: ExplanationProgress) => void,
): Promise<ExplanationData | null> {
  const orderIds = Object.keys(data.assignments).sort();
  const total = orderIds.length + 1;
  let completed = 0;
  let failed = 0;

  const assignmentSummary = Object.entries(data.assignments)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([orderId, crew]) => {
      const lead = crew.find((a) => a.role === "lead");
      const members = crew.filter((a) => a.role === "member");
      return `${orderId}: Lead=${lead?.personnel_name} (score ${lead?.individual_score.toFixed(1)}), Members=[${members.map((m) => `${m.personnel_name} (score ${m.individual_score.toFixed(1)})`).join(", ")}]`;
    })
    .join("\n");

  const context = {
    total_score: data.total_score,
    status: data.status,
    solve_time_ms: data.solve_time_ms,
    assignments: data.assignments,
    scoring_summary: Object.fromEntries(
      Object.entries(data.scoring).map(([orderId, scoring]) => [
        orderId,
        {
          top_leads: scoring.scored_leads.slice(0, 3).map((s) => ({
            name: s.personnel_name, score: s.score, type: s.personnel_type, breakdown: s.breakdown,
          })),
          top_members: scoring.scored_members.slice(0, 5).map((s) => ({
            name: s.personnel_name, score: s.score, type: s.personnel_type, breakdown: s.breakdown,
          })),
        },
      ])
    ),
  };

  // Step 1: Generate verdict (fail fast if this fails)
  onProgress({ completed: 0, failed: 0, total, currentOrder: "verdict", status: "running" });
  let verdict = "";
  try {
    const verdictResp = await api.askCopilot(
      `Provide a comprehensive final verdict for this dispatch optimization run. Explain the overall strategy the optimizer used, why certain personnel appeared in multiple consideration sets, and what trade-offs were made. Here is the full assignment plan:\n\n${assignmentSummary}\n\nTotal score: ${data.total_score.toFixed(1)}, Status: ${data.status}, Solve time: ${data.solve_time_ms}ms.\n\nProvide:\n1. Overall optimization strategy summary\n2. Key trade-offs made (who was assigned where and why that was globally optimal)\n3. Any notable constraints that shaped the result (overlapping time windows, driver requirements, composition rules)\n4. Score distribution analysis`,
      undefined,
      context
    );
    verdict = verdictResp.answer;
    if (verdict.includes("Error calling Gemini:")) {
      onProgress({ completed: 0, failed: 1, total, currentOrder: "verdict", status: "failed", failReason: verdict.split("\n")[0] });
      return { verdict, perOrder: {} };
    }
    completed = 1;
    onProgress({ completed, failed, total, currentOrder: orderIds[0], status: "running" });
  } catch (e) {
    const reason = e instanceof Error ? e.message : "Unknown error";
    onProgress({ completed: 0, failed: 1, total, currentOrder: "verdict", status: "failed", failReason: reason });
    return null;
  }

  // Step 2: Generate per-order explanations
  const perOrder: Record<string, string> = {};

  for (let i = 0; i < orderIds.length; i += 2) {
    if (i > 0) await new Promise((r) => setTimeout(r, 1500));
    const batch = orderIds.slice(i, i + 2);
    const promises = batch.map(async (orderId) => {
      const crew = data.assignments[orderId];
      const scoring = data.scoring[orderId];
      const lead = crew.find((a) => a.role === "lead");
      const members = crew.filter((a) => a.role === "member");

      const leadScoring = scoring?.scored_leads.find(
        (s) => s.personnel_id === lead?.personnel_id
      );
      const memberScorings = members.map((m) =>
        scoring?.scored_members.find((s) => s.personnel_id === m.personnel_id)
      );

      const orderContext = {
        ...context,
        current_order: orderId,
        assigned_lead: lead
          ? { name: lead.personnel_name, score: lead.individual_score, breakdown: leadScoring?.breakdown, type: leadScoring?.personnel_type }
          : null,
        assigned_members: members.map((m, idx) => ({
          name: m.personnel_name, score: m.individual_score, breakdown: memberScorings[idx]?.breakdown, type: memberScorings[idx]?.personnel_type,
        })),
        alternative_leads: scoring?.scored_leads.filter((s) => s.personnel_id !== lead?.personnel_id).slice(0, 3).map((s) => ({ name: s.personnel_name, score: s.score, breakdown: s.breakdown })),
        alternative_members: scoring?.scored_members.filter((s) => !members.find((m) => m.personnel_id === s.personnel_id)).slice(0, 3).map((s) => ({ name: s.personnel_name, score: s.score, breakdown: s.breakdown })),
      };

      try {
        const resp = await api.askCopilot(
          `For service order ${orderId}, provide a detailed explanation of the crew assignment. Explain:\n\n1. **Why the Lead was chosen**: ${lead?.personnel_name} was selected as lead with score ${lead?.individual_score.toFixed(1)}. Break down which scoring factors gave them the edge.\n\n2. **Why each Member was chosen**: For each member (${members.map((m) => m.personnel_name).join(", ")}), explain what made them the best fit.\n\n3. **Why alternatives were NOT chosen**: Who else was considered and why they scored lower.\n\n4. **Crew composition validation**: How this crew satisfies journeyman/apprentice ratio and driver requirements.\n\nBe specific with numbers and factor names.`,
          undefined,
          orderContext
        );
        const answer = resp.answer;
        if (answer.includes("Error calling Gemini:")) {
          return { orderId, explanation: answer, isError: true };
        }
        return { orderId, explanation: answer, isError: false };
      } catch {
        return { orderId, explanation: "Unable to generate explanation for this order.", isError: true };
      }
    });

    const results = await Promise.all(promises);
    for (const { orderId, explanation, isError } of results) {
      perOrder[orderId] = explanation;
      completed++;
      if (isError) failed++;
    }

    const nextOrder = orderIds[i + 2] || orderIds[orderIds.length - 1];
    onProgress({ completed, failed, total, currentOrder: nextOrder, status: "running" });
  }

  return { verdict, perOrder };
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "optimal" ? "bg-green-100 text-green-800" : status === "feasible" ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800";
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
      {Object.keys(data.rejections).length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground">Rejection reasons</summary>
          <div className="mt-2 space-y-1">
            {Object.entries(data.rejections).slice(0, 5).map(([id, reasons]) => (
              <div key={id} className="text-red-600">{id}: {reasons.join(", ")}</div>
            ))}
          </div>
        </details>
      )}
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

function AssignmentPanel({ orderId, assignments, scoring, explanation }: { orderId: string; assignments?: Assignment[]; scoring?: ScoringResponse; explanation?: string }) {
  if (!assignments) return null;

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="font-semibold mb-3 text-sm">Step 4: Final Assignment ({orderId})</h3>
      <div className="space-y-3 mb-4">
        {assignments.map((a) => {
          const scoringData = a.role === "lead"
            ? scoring?.scored_leads.find((s) => s.personnel_id === a.personnel_id)
            : scoring?.scored_members.find((s) => s.personnel_id === a.personnel_id);

          return (
            <div key={a.personnel_id} className="border border-border rounded-md p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2.5 h-2.5 rounded-full ${a.role === "lead" ? "bg-purple-500" : "bg-blue-500"}`} />
                <span className="font-medium flex-1">{a.personnel_name}</span>
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

      {explanation && (
        <div className="border-t border-border pt-3 mt-3">
          <div className="flex items-center gap-1.5 mb-2">
            <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-xs font-semibold text-blue-700">AI Explanation</span>
          </div>
          <div className="prose prose-xs max-w-none text-xs text-muted-foreground leading-relaxed" dangerouslySetInnerHTML={{ __html: renderMarkdown(explanation) }} />
        </div>
      )}
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
      <h3 className="font-semibold mb-3">Assignment Matrix</h3>
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

function renderMarkdown(text: string): string {
  return text
    .replace(/### (.*)/g, '<h4 class="font-semibold text-sm mt-3 mb-1">$1</h4>')
    .replace(/## (.*)/g, '<h3 class="font-semibold text-base mt-3 mb-1">$1</h3>')
    .replace(/# (.*)/g, '<h2 class="font-bold text-lg mt-4 mb-2">$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-xs">$1</code>')
    .replace(/^- (.*)/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/^\d+\. (.*)/gm, '<li class="ml-4 list-decimal">$1</li>')
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
}
