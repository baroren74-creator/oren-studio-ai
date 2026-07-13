"use client";

// Project detail view — docs/roadmap.md 1.16: chronological list of
// agent_events for a project, plus (Phase 3.5+) a manual "Run" button
// that calls POST /api/projects/{id}/run — see
// apps/api/app/services/orchestrator.py's module docstring for what
// that endpoint does (a synchronous v0 graph run, not the eventual
// services/orchestrator-worker). The resulting script is rendered
// below the timeline once a run completes; before Phase 3.7's real
// Storyboard UI exists, this is the fastest way to see actual pipeline
// output rather than just a raw event list.
//
// Phase 3.6, Approval Gate #1: a drafted script always comes with a
// pending Approval row (apps/api/app/services/orchestrator.py). This
// page shows it and lets Oren approve / reject / request an edit — see
// apps/api/app/services/approvals.py's module docstring for why this
// is a standalone review step rather than resuming a paused graph run.

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type AgentEvent, type Approval, type Project, type ProjectRun } from "@/lib/api";

export default function ProjectTimelinePage() {
  const params = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<ProjectRun | null>(null);

  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [deciding, setDeciding] = useState(false);
  const [decideError, setDecideError] = useState<string | null>(null);
  const [editNotes, setEditNotes] = useState("");
  const [showEditForm, setShowEditForm] = useState(false);

  function loadProject(id: string) {
    return Promise.all([api.getProject(id), api.getProjectTimeline(id)]).then(([p, e]) => {
      setProject(p);
      setEvents(e);
    });
  }

  function loadApprovals(id: string) {
    return api.listApprovals(id).then(setApprovals);
  }

  useEffect(() => {
    if (!params.id) return;
    Promise.all([loadProject(params.id), loadApprovals(params.id)]).catch((err) =>
      setError(err instanceof Error ? err.message : "failed to load project")
    );
  }, [params.id]);

  async function handleRun() {
    if (!params.id) return;
    setRunning(true);
    setRunError(null);
    try {
      const run = await api.runProject(params.id);
      setLastRun(run);
      await Promise.all([loadProject(params.id), loadApprovals(params.id)]);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "run failed");
    } finally {
      setRunning(false);
    }
  }

  async function handleApprove(approval: Approval) {
    setDeciding(true);
    setDecideError(null);
    try {
      await api.approveApproval(approval.id);
      if (params.id) await loadApprovals(params.id);
    } catch (err) {
      setDecideError(err instanceof Error ? err.message : "failed to approve");
    } finally {
      setDeciding(false);
    }
  }

  async function handleReject(approval: Approval) {
    setDeciding(true);
    setDecideError(null);
    try {
      await api.rejectApproval(approval.id);
      if (params.id) await loadApprovals(params.id);
    } catch (err) {
      setDecideError(err instanceof Error ? err.message : "failed to reject");
    } finally {
      setDeciding(false);
    }
  }

  async function handleRequestEdit(approval: Approval) {
    setDeciding(true);
    setDecideError(null);
    try {
      await api.requestEditApproval(approval.id, editNotes);
      setEditNotes("");
      setShowEditForm(false);
      if (params.id) await loadApprovals(params.id);
    } catch (err) {
      setDecideError(err instanceof Error ? err.message : "failed to request edit");
    } finally {
      setDeciding(false);
    }
  }

  if (error) return <p style={{ color: "crimson" }}>{error}</p>;
  if (!project) return <p>Loading…</p>;

  const pendingApproval = approvals.find((a) => a.status === "pending") ?? null;
  const decidedApprovals = approvals.filter((a) => a.status !== "pending");

  return (
    <div>
      <h1>{project.title ?? "(untitled project)"}</h1>
      <p>
        Status: <strong>{project.status}</strong> · Source: {project.source_type} — {project.source_url}
      </p>

      <div style={{ margin: "1rem 0" }}>
        <button type="button" onClick={handleRun} disabled={running}>
          {running ? "Running…" : "Run"}
        </button>
        {runError && <p style={{ color: "crimson" }}>{runError}</p>}
      </div>

      {lastRun && (
        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: "1rem", marginBottom: "1.5rem" }}>
          <h2>Latest run</h2>
          <p>
            Idea score: <strong>{lastRun.idea_score ?? "n/a"}</strong>
            {lastRun.rejected && <span style={{ color: "crimson" }}> — rejected, below threshold</span>}
          </p>

          {lastRun.script ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxWidth: 640 }}>
              <p>
                <strong>Title:</strong> {lastRun.script.title ?? "—"}
              </p>
              <p>
                <strong>Hook:</strong> {lastRun.script.hook ?? "—"}
              </p>
              <p>
                <strong>Body:</strong> {lastRun.script.body ?? "—"}
              </p>
              <p>
                <strong>CTA:</strong> {lastRun.script.cta ?? "—"}
              </p>
              <p>
                <strong>Caption:</strong> {lastRun.script.caption ?? "—"}
              </p>
              <p>
                <strong>Hashtags:</strong> {lastRun.script.hashtags?.join(" ") ?? "—"}
              </p>
            </div>
          ) : (
            <p>No script produced for this run (idea rejected, or no ANTHROPIC_API_KEY/VOYAGE_API_KEY configured — see Makefile's run-api target).</p>
          )}
        </div>
      )}

      {pendingApproval && (
        <div style={{ border: "2px solid #d9a441", borderRadius: 6, padding: "1rem", marginBottom: "1.5rem" }}>
          <h2>Approval needed — {pendingApproval.stage}</h2>
          <p>The drafted script is waiting for a decision before this project moves on.</p>
          {decideError && <p style={{ color: "crimson" }}>{decideError}</p>}
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
            <button type="button" onClick={() => handleApprove(pendingApproval)} disabled={deciding}>
              Approve
            </button>
            <button type="button" onClick={() => handleReject(pendingApproval)} disabled={deciding}>
              Reject
            </button>
            <button type="button" onClick={() => setShowEditForm((v) => !v)} disabled={deciding}>
              Request edit
            </button>
          </div>
          {showEditForm && (
            <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.5rem", maxWidth: 480 }}>
              <textarea
                placeholder="What should change?"
                rows={3}
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
              />
              <button
                type="button"
                onClick={() => handleRequestEdit(pendingApproval)}
                disabled={deciding || editNotes.trim() === ""}
              >
                Send edit request
              </button>
            </div>
          )}
        </div>
      )}

      {decidedApprovals.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <h3>Approval history</h3>
          <ul>
            {decidedApprovals.map((a) => (
              <li key={a.id}>
                {a.stage}: <strong>{a.status}</strong>
                {a.notes ? ` — "${a.notes}"` : ""}
                {a.decided_at ? ` (${new Date(a.decided_at).toLocaleString()})` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      <h2>Timeline</h2>
      {events.length === 0 ? (
        <p>No agent_events yet — run the pipeline above to generate some.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Event</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{new Date(e.created_at).toLocaleString()}</td>
                <td>{e.event_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
