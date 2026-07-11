"use client";

// Ops view — docs/roadmap.md 1.17: a plain table of agent_runs, so
// debugging a pipeline doesn't require reading raw DB rows. Deliberately
// boring/simple per docs/architecture.md section 9 (cheap to build now,
// saves debugging time later).

import { useEffect, useState } from "react";
import { api, type AgentRun } from "@/lib/api";

export default function OpsPage() {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listAgentRuns().then(setRuns).catch((err) => setError(err instanceof Error ? err.message : "failed to load"));
  }, []);

  return (
    <div>
      <h1>Ops — agent runs</h1>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
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
                <td>{r.cost_usd ?? "—"}</td>
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
