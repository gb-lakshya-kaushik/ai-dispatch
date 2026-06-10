"use client";

import { useState } from "react";
import Link from "next/link";
import {
  api,
  type Assignment,
  type ScoredCandidate,
  type CrewCandidate,
  type EligibilityResponse,
  type ScoringResponse,
} from "../lib/api";
import { useDispatch } from "../lib/dispatch-context";

export default function DispatchPage() {
  const {
    step, result, selectedOrder, error, explanations,
    setStep, setResult, setSelectedOrder, setError, setExplanations,
  } = useDispatch();

  const [orderSummaryLoading, setOrderSummaryLoading] = useState<string | null>(null);
  const [bulkSummaryLoading, setBulkSummaryLoading] = useState(false);
  const [bulkProgress, setBulkProgress] = useState({ done: 0, total: 0 });

  const requestOrderSummary = async (orderId: string) => {
    if (!result || orderSummaryLoading) return;
    setOrderSummaryLoading(orderId);
    try {
      const crew = result.assignments[orderId];
      const scoring = result.scoring[orderId];
      const lead = crew.find((a) => a.role === "lead");
      const members = crew.filter((a) => a.role === "member");

      const leadScoring = scoring?.scored_leads.find(
        (s) => s.personnel_id === lead?.personnel_id
      );
      const memberScorings = members.map((m) =>
        scoring?.scored_members.find((s) => s.personnel_id === m.personnel_id)
      );

      const orderContext = {
        total_score: result.total_score,
        status: result.status,
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

      const resp = await api.askCopilot(
        `Analyze the crew assignment for ${orderId}. Do NOT include any preamble, introduction, or restatement of the question. Start directly with the analysis.\n\nFormat as follows:\n\n## Lead: ${lead?.personnel_name} (Score: ${lead?.individual_score.toFixed(1)})\nExplain key scoring factors in a compact table or bullet list showing factor name and value.\n\n## Members\nFor each member (${members.map((m) => `${m.personnel_name}`).join(", ")}), list their score and top 2 contributing factors in one line each.\n\n## Alternatives Considered\nBriefly note top 2-3 candidates not selected and the primary reason (1 sentence each).\n\n## Composition\nConfirm TC/apprentice ratio and driver compliance in 1-2 sentences.\n\nKeep the entire response under 300 words. Use markdown formatting. Be factual and data-driven.`,
        undefined,
        orderContext
      );

      setExplanations({
        verdict: explanations?.verdict || "",
        perOrder: { ...(explanations?.perOrder || {}), [orderId]: resp.answer },
      });
    } catch {
      // silently fail — user can retry
    } finally {
      setOrderSummaryLoading(null);
    }
  };

  const runPipeline = async () => {
    setStep("running");
    setError(null);
    setExplanations(null);
    try {
      const data = await api.runFullPipeline();
      setResult(data);

      if (Object.keys(data.assignments).length > 0) {
        setSelectedOrder(Object.keys(data.assignments).sort()[0]);
      }

      setStep("done");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Pipeline failed");
      setStep("idle");
    }
  };

  const requestBulkSummary = async () => {
    if (!result || bulkSummaryLoading) return;
    const orderIds = Object.keys(result.assignments).sort();
    const remaining = orderIds.filter((id) => !explanations?.perOrder[id]);
    if (remaining.length === 0) return;

    setBulkSummaryLoading(true);
    setBulkProgress({ done: 0, total: remaining.length });

    const perOrder = { ...(explanations?.perOrder || {}) };

    for (let i = 0; i < remaining.length; i++) {
      const orderId = remaining[i];
      try {
        const crew = result.assignments[orderId];
        const scoring = result.scoring[orderId];
        const lead = crew.find((a) => a.role === "lead");
        const members = crew.filter((a) => a.role === "member");

        const leadScoring = scoring?.scored_leads.find(
          (s) => s.personnel_id === lead?.personnel_id
        );
        const memberScorings = members.map((m) =>
          scoring?.scored_members.find((s) => s.personnel_id === m.personnel_id)
        );

        const orderContext = {
          total_score: result.total_score,
          status: result.status,
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

        const resp = await api.askCopilot(
          `Analyze the crew assignment for ${orderId}. Do NOT include any preamble, introduction, or restatement of the question. Start directly with the analysis.\n\nFormat as follows:\n\n## Lead: ${lead?.personnel_name} (Score: ${lead?.individual_score.toFixed(1)})\nExplain key scoring factors in a compact table or bullet list showing factor name and value.\n\n## Members\nFor each member (${members.map((m) => `${m.personnel_name}`).join(", ")}), list their score and top 2 contributing factors in one line each.\n\n## Alternatives Considered\nBriefly note top 2-3 candidates not selected and the primary reason (1 sentence each).\n\n## Composition\nConfirm TC/apprentice ratio and driver compliance in 1-2 sentences.\n\nKeep the entire response under 300 words. Use markdown formatting. Be factual and data-driven.`,
          undefined,
          orderContext
        );
        perOrder[orderId] = resp.answer;
      } catch {
        perOrder[orderId] = "Unable to generate explanation for this order.";
      }
      setBulkProgress({ done: i + 1, total: remaining.length });
      setExplanations({ verdict: explanations?.verdict || "", perOrder: { ...perOrder } });
    }

    setBulkSummaryLoading(false);
  };

  return (
    <div className="max-w-7xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dispatch Flow</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Eligibility → Scoring → Crew Building → Optimization
          </p>
        </div>
        <div className="flex items-center gap-2">
          {step === "done" && result && (
            <button
              onClick={requestBulkSummary}
              disabled={bulkSummaryLoading}
              className="px-4 py-2.5 bg-card border border-border text-foreground rounded-lg text-sm font-medium hover:bg-accent disabled:opacity-50 transition-colors"
            >
              {bulkSummaryLoading
                ? `Generating... (${bulkProgress.done}/${bulkProgress.total})`
                : "Get AI Summary (All)"}
            </button>
          )}
          <button
            onClick={runPipeline}
            disabled={step === "running"}
            className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:bg-orange-600 disabled:opacity-50 transition-colors shadow-sm"
          >
            {step === "running"
              ? "Optimizing..."
              : step === "done"
              ? "Re-run Pipeline"
              : "Run Full Pipeline"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4 mb-6 text-sm">
          {error}
        </div>
      )}

      {step === "running" && (
        <div className="py-8">
          <div className="flex items-center gap-3 text-muted-foreground justify-center">
            <div className="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full" />
            Running optimization pipeline...
          </div>
        </div>
      )}

      {result && step === "done" && (
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
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <EligibilityPanel data={result.eligibility[selectedOrder]} />
                <ScoringPanel data={result.scoring[selectedOrder]} />
                <CrewsPanel data={result.crews[selectedOrder]} />
                <AssignmentPanel
                  orderId={selectedOrder}
                  assignments={result.assignments[selectedOrder]}
                  scoring={result.scoring[selectedOrder]}
                />
              </div>

              {/* AI Explanation — full width, compact */}
              {!explanations?.perOrder[selectedOrder] && orderSummaryLoading !== selectedOrder && (
                <div className="flex justify-start">
                  <button
                    onClick={() => requestOrderSummary(selectedOrder)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-accent text-primary rounded-lg text-xs font-medium hover:bg-orange-100 transition-colors border border-border"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    Get AI Summary
                  </button>
                </div>
              )}

              {!explanations?.perOrder[selectedOrder] && orderSummaryLoading === selectedOrder && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <div className="animate-spin w-3.5 h-3.5 border-2 border-primary border-t-transparent rounded-full" />
                  Generating summary...
                </div>
              )}

              {explanations?.perOrder[selectedOrder] && (
                <div className="bg-card border border-border rounded-lg p-5">
                  <div className="flex items-center gap-1.5 mb-3">
                    <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-xs font-semibold text-blue-700">AI Explanation — {selectedOrder}</span>
                  </div>
                  <div className="prose prose-sm max-w-none text-sm text-muted-foreground leading-relaxed columns-1 lg:columns-2 gap-8" dangerouslySetInnerHTML={{ __html: renderMarkdown(explanations.perOrder[selectedOrder]) }} />
                </div>
              )}
            </>
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
            <span className="text-muted-foreground">{crew.tc_count}TC/{crew.apprentice_count}A</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AssignmentPanel({ orderId, assignments, scoring }: { orderId: string; assignments?: Assignment[]; scoring?: ScoringResponse }) {
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
