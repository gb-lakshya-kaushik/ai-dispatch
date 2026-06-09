"use client";

import { useDispatch } from "../../lib/dispatch-context";
import Link from "next/link";
import type { Assignment, ScoringResponse } from "../../lib/api";

export default function DispatchSummaryPage() {
  const { result, explanations, step } = useDispatch();

  if (step !== "done" || !result || !explanations) {
    return (
      <div className="max-w-4xl text-center py-16">
        <p className="text-lg text-muted-foreground mb-4">No dispatch results available</p>
        <Link
          href="/dispatch"
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
        >
          Go to Pipeline
        </Link>
      </div>
    );
  }

  const orderIds = Object.keys(result.assignments).sort();

  return (
    <div className="max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Dispatch Summary</h1>
          <p className="text-muted-foreground text-sm">
            Full AI analysis of the optimization results
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/dispatch"
            className="px-3 py-2 border border-border rounded-md text-xs font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            ← Back to Pipeline
          </Link>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard label="Status" value={result.status} highlight />
        <StatCard label="Total Score" value={result.total_score.toFixed(1)} />
        <StatCard label="Solve Time" value={`${result.solve_time_ms}ms`} />
        <StatCard label="Orders Assigned" value={String(orderIds.length)} />
      </div>

      {/* Overall Verdict */}
      <div className="bg-card border border-border rounded-lg p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <h2 className="text-lg font-bold">Optimization Verdict</h2>
        </div>
        <div
          className="prose prose-sm max-w-none text-sm text-foreground leading-relaxed"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(explanations.verdict) }}
        />
      </div>

      {/* Per-Order Explanations */}
      <h2 className="text-lg font-bold mb-4">Per-Order Breakdown</h2>
      <div className="space-y-4">
        {orderIds.map((orderId) => (
          <OrderSummaryCard
            key={orderId}
            orderId={orderId}
            assignments={result.assignments[orderId]}
            scoring={result.scoring[orderId]}
            explanation={explanations.perOrder[orderId]}
          />
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className={`text-xl font-bold ${highlight ? (value === "optimal" ? "text-green-600" : "text-yellow-600") : ""}`}>
        {value}
      </div>
    </div>
  );
}

function OrderSummaryCard({
  orderId,
  assignments,
  scoring,
  explanation,
}: {
  orderId: string;
  assignments: Assignment[];
  scoring?: ScoringResponse;
  explanation?: string;
}) {
  const lead = assignments.find((a) => a.role === "lead");
  const members = assignments.filter((a) => a.role === "member");
  const crewScore = assignments.reduce((sum, a) => sum + a.individual_score, 0);

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 bg-muted/50 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-bold text-sm">{orderId}</span>
          <span className="text-xs text-muted-foreground">Crew Score: {crewScore.toFixed(1)}</span>
        </div>
        <div className="flex gap-2">
          {lead && (
            <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-700">
              <span className="w-2 h-2 rounded-full bg-purple-500" />
              Lead: {lead.personnel_name}
            </span>
          )}
          <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700">
            {members.length} member{members.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Crew Table */}
      <div className="px-5 py-3 border-b border-border">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground">
              <th className="text-left py-1 font-medium">Name</th>
              <th className="text-left py-1 font-medium">Role</th>
              <th className="text-right py-1 font-medium">Score</th>
              <th className="text-right py-1 font-medium">Skill</th>
              <th className="text-right py-1 font-medium">Hours</th>
              <th className="text-right py-1 font-medium">Pref</th>
              <th className="text-right py-1 font-medium">Exp</th>
              <th className="text-right py-1 font-medium">Cost</th>
            </tr>
          </thead>
          <tbody>
            {assignments.map((a) => {
              const scoringData =
                a.role === "lead"
                  ? scoring?.scored_leads.find((s) => s.personnel_id === a.personnel_id)
                  : scoring?.scored_members.find((s) => s.personnel_id === a.personnel_id);

              return (
                <tr key={a.personnel_id} className="border-t border-border/50">
                  <td className="py-1.5 font-medium">{a.personnel_name}</td>
                  <td className="py-1.5">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${a.role === "lead" ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"}`}>
                      {a.role}
                    </span>
                  </td>
                  <td className="py-1.5 text-right font-mono font-bold">{a.individual_score.toFixed(1)}</td>
                  <td className="py-1.5 text-right font-mono">{scoringData?.breakdown.skill_match.toFixed(1) ?? "—"}</td>
                  <td className="py-1.5 text-right font-mono">{scoringData?.breakdown.hour_balancing.toFixed(1) ?? "—"}</td>
                  <td className="py-1.5 text-right font-mono">{scoringData?.breakdown.customer_preference.toFixed(1) ?? "—"}</td>
                  <td className="py-1.5 text-right font-mono">{scoringData?.breakdown.similar_job_experience.toFixed(1) ?? "—"}</td>
                  <td className="py-1.5 text-right font-mono">{scoringData?.breakdown.cost_efficiency.toFixed(1) ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* AI Explanation */}
      {explanation && (
        <div className="px-5 py-4">
          <div className="flex items-center gap-1.5 mb-2">
            <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-xs font-semibold text-blue-700">AI Explanation</span>
          </div>
          <div
            className="prose prose-xs max-w-none text-xs text-muted-foreground leading-relaxed"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(explanation) }}
          />
        </div>
      )}
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
