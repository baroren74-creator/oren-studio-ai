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
  if (res.status === 204) {
    // e.g. DELETE /api/prompt-library/{id} — no body to parse.
    return undefined as T;
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

export type ScriptResult = {
  hook: string | null;
  body: string | null;
  cta: string | null;
  caption: string | null;
  title: string | null;
  hashtags: string[] | null;
};

// One scene from workflows/storyboard.py's generate_storyboard() —
// visual_ref is always null for now (no asset library/B-roll search
// wired up yet, see that module's docstring).
export type StoryboardScene = {
  order: number;
  description: string;
  duration: number;
  caption_cue: string | null;
  visual_ref: string | null;
};

// Response shape for POST /api/projects/{id}/run — see
// apps/api/app/services/orchestrator.py's module docstring for what
// this endpoint actually does (a synchronous v0 graph run).
export type ProjectRun = {
  run_id: string;
  events: string[];
  rejected: boolean;
  interrupted: boolean;
  idea_score: number | null;
  research_note_id: string | null;
  script_id: string | null;
  script: ScriptResult | null;
  approval_id: string | null;
  total_cost_usd: number;
  storyboard_id: string | null;
  storyboard_scenes: StoryboardScene[] | null;
};

// GET /api/projects/{id}/storyboard — Phase 3.8. Unlike
// ProjectRun.storyboard_scenes (which only lives as long as one run
// response), this survives a page reload — see
// app.services.storyboard.get_latest_storyboard_for_project.
export type Storyboard = {
  id: string;
  script_id: string;
  scenes: StoryboardScene[];
  created_at: string;
};

// Phase 3.6, Approval Gate #1 — see
// apps/api/app/services/approvals.py's module docstring for why this is
// a standalone DB-backed gate rather than resuming a paused graph run.
export type Approval = {
  id: string;
  project_id: string;
  stage: string;
  status: string; // pending | approved | rejected | edited
  notes: string | null;
  decided_at: string | null;
};

// Phase 3.5 — see apps/api/app/services/prompt_library.py's module
// docstring for the versioning model (edit = new row + parent_id,
// never an in-place update).
export type Prompt = {
  id: string;
  name: string;
  category: string | null;
  prompt_text: string | null;
  version: number;
  parent_id: string | null;
  created_at: string;
};

export const api = {
  listProjects: () => request<Project[]>("/api/projects"),
  createProject: (body: { title?: string; source_type: string; source_url: string }) =>
    request<Project>("/api/projects", { method: "POST", body: JSON.stringify(body) }),
  getProject: (id: string) => request<Project>(`/api/projects/${id}`),
  getProjectTimeline: (id: string) => request<AgentEvent[]>(`/api/projects/${id}/timeline`),
  listAgentRuns: () => request<AgentRun[]>("/api/agent-runs"),
  runProject: (id: string) => request<ProjectRun>(`/api/projects/${id}/run`, { method: "POST" }),
  getStoryboard: (projectId: string) => request<Storyboard>(`/api/projects/${projectId}/storyboard`),

  listPrompts: () => request<Prompt[]>("/api/prompt-library"),
  createPrompt: (body: { name: string; category?: string; prompt_text?: string }) =>
    request<Prompt>("/api/prompt-library", { method: "POST", body: JSON.stringify(body) }),
  getPromptHistory: (id: string) => request<Prompt[]>(`/api/prompt-library/${id}/history`),
  createPromptVersion: (id: string, body: { prompt_text?: string; category?: string }) =>
    request<Prompt>(`/api/prompt-library/${id}/versions`, { method: "POST", body: JSON.stringify(body) }),
  deletePrompt: (id: string) => request<void>(`/api/prompt-library/${id}`, { method: "DELETE" }),

  listApprovals: (projectId: string) => request<Approval[]>(`/api/projects/${projectId}/approvals`),
  approveApproval: (id: string) => request<Approval>(`/api/approvals/${id}/approve`, { method: "POST" }),
  rejectApproval: (id: string) => request<Approval>(`/api/approvals/${id}/reject`, { method: "POST" }),
  requestEditApproval: (id: string, notes: string) =>
    request<Approval>(`/api/approvals/${id}/request-edit`, { method: "POST", body: JSON.stringify({ notes }) }),
};
