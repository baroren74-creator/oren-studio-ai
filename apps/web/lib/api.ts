// Thin fetch wrapper around apps/api — see docs/api.md for the route
// contract this calls. Kept deliberately dumb (no framework/SDK) so it's
// easy to see exactly what's happening in a Phase 1 skeleton.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_STUDIO_API_KEY ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Studio-Api-Key": API_KEY,
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export type Project = {
  id: string;
  title: string | null;
  status: string;
  source_type: string | null;
  source_url: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentEvent = {
  id: string;
  run_id: string;
  event_type: string;
  payload: Record<string, unknown> | null;
  created_at: string;
};

export type AgentRun = {
  id: string;
  project_id: string;
  agent_name: string;
  status: string;
  cost_usd: number | null;
  tokens_used: number | null;
  started_at: string;
  finished_at: string | null;
};

export const api = {
  createProject: (body: { title?: string; source_type: string; source_url: string }) =>
    request<Project>("/api/projects", { method: "POST", body: JSON.stringify(body) }),
  getProject: (id: string) => request<Project>(`/api/projects/${id}`),
  getProjectTimeline: (id: string) => request<AgentEvent[]>(`/api/projects/${id}/timeline`),
  listAgentRuns: () => request<AgentRun[]>("/api/agent-runs"),
};
