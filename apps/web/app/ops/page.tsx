"use client";

// Ops view — docs/roadmap.md 1.17: a plain table of agent_runs, so
// debugging a pipeline doesn't require reading raw DB rows. Deliberately
// boring/simple per docs/architecture.md section 9 (cheap to build now,
// saves debugging time later).
//
// Cost tracking added afterward, found live to be a real gap: every
// real Agent already computes its own cost, but nothing previously
// persisted it here, so this page always showed "No agent runs yet"
// even after real runs. The total at the top exists specifically so
// there's always one place that answers "how much has this cost me so
// far" — see apps/api/app/services/agent_runs.py's module docstring.

import { useEffect, useState } from "react";
import { api, type AgentRun } from "@/lib/api";

function formatCost(usd: number | null): string {
  if (usd === null) return "—";
  if (usd === 0) return "$0";
  // Real per-call costs are often well under a cent — 2 decimals would
  // just show "$0.00" for almost everything, so use more precision.
  return `$${usd.toFixed(6)}`;
}

export default function OpsPage() {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listAgentRuns().then(setRuns).catch((err) => setError(err instanceof Error ? err.message : "failed to load"));
  }, []);

  const totalCostUsd = runs.reduce((sum, r) => sum + (r.cost_usd ?? 0), 0);
  const totalTokens = runs.reduce((sum, r) => sum + (r.tokens_used ?? 0), 0);

  return (
    <div>
      <h1>Ops — agent runs</h1>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {runs.length > 0 && (
        <p style={{ fontSize: "1.1rem" }}>
          Total spent so far: <strong>{formatCost(totalCostUsd)}</strong> across {runs.length} agent run
          {runs.length === 1 ? "" : "s"} ({totalTokens.toLocaleString()} tokens).
        </p>
      )}

      {runs.length === 0 ? (
        <p>No agent runs yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Agent</th>
              <th>Status</th>
              <th>Cost (USD)</th>
              <th>Tokens</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td>{r.agent_name}</td>
                <td>{r.status}</td>
                <td>{formatCost(r.cost_usd)}</td>
                <td>{r.tokens_used ?? "—"}</td>
                <td>{new Date(r.started_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
