"use client";

// Project detail view — docs/roadmap.md 1.16: chronological list of
// agent_events for a project, plus (Phase 3.5+) a manual "Run" button
// that calls POST /api/projects/{id}/run — see
// apps/api/app/services/orchestrator.py's module docstring for what
// that endpoint does (a synchronous v0 graph run, not the eventual
// services/orchestrator-worker). The resulting script is rendered
// below the timeline once a run completes.
//
// Phase 3.6, Approval Gate #1: a drafted script always comes with a
// pending Approval row (apps/api/app/services/orchestrator.py). This
// page shows it and lets Oren approve / reject / request an edit — see
// apps/api/app/services/approvals.py's module docstring for why this
// is a standalone review step rather than resuming a paused graph run.
//
// Phase 3.8: the "Latest run" card only shows a compact storyboard
// summary + a link to the real Storyboard view
// (/projects/[id]/storyboard) — the full scene-by-scene inline list
// that used to live here was always documented as a stopgap for exactly
// this phase, see that page's module comment.

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

  if (error) return <p style={{ color: "var(--danger)" }}>{error}</p>;
  if (!project) return <p>Loading…</p>;

  const pendingApproval = approvals.find((a) => a.status === "pending") ?? null;
  const decidedApprovals = approvals.filter((a) => a.status !== "pending");

  return (
    <div className="stack" style={{ gap: "var(--space-6)" }}>
      <div>
        <h1>{project.title ?? "(untitled project)"}</h1>
        <p style={{ margin: 0 }}>
          <span className="badge badge-neutral">{project.status}</span>{" "}
          <span style={{ color: "var(--text-faint)" }}>
            {project.source_type} — {project.source_url}
          </span>
        </p>
      </div>

      <div>
        <button type="button" className="btn btn-primary" onClick={handleRun} disabled={running}>
          {running ? "Running…" : "Run"}
        </button>
        {runError && <p style={{ color: "var(--danger)", marginTop: "var(--space-2)" }}>{runError}</p>}
      </div>

      {lastRun && (
        <div className="card stack">
          <h2 style={{ margin: 0 }}>Latest run</h2>
          <div className="row" style={{ gap: "var(--space-5)" }}>
            <div className="stat">
              <span className="stat-value">{lastRun.idea_score ?? "n/a"}</span>
              <span className="stat-label">Idea score</span>
            </div>
            <div className="stat">
              <span className="stat-value">${lastRun.total_cost_usd.toFixed(6)}</span>
              <span className="stat-label">
                Cost — <a href="/ops">running total</a>
              </span>
            </div>
          </div>
          {lastRun.rejected && <span className="badge badge-danger">Rejected — below threshold</span>}

          {lastRun.script ? (
            <div className="stack" style={{ maxWidth: 640 }}>
              <p>
                <strong style={{ color: "var(--text)" }}>Title:</strong> {lastRun.script.title ?? "—"}
              </p>
              <p>
                <strong style={{ color: "var(--text)" }}>Hook:</strong> {lastRun.script.hook ?? "—"}
              </p>
              <p>
                <strong style={{ color: "var(--text)" }}>Body:</strong> {lastRun.script.body ?? "—"}
              </p>
              <p>
                <strong style={{ color: "var(--text)" }}>CTA:</strong> {lastRun.script.cta ?? "—"}
              </p>
              <p>
                <strong style={{ color: "var(--text)" }}>Caption:</strong> {lastRun.script.caption ?? "—"}
              </p>
              <p>
                <strong style={{ color: "var(--text)" }}>Hashtags:</strong> {lastRun.script.hashtags?.join(" ") ?? "—"}
              </p>
            </div>
          ) : (
            <p>No script produced for this run (idea rejected, or no ANTHROPIC_API_KEY/VOYAGE_API_KEY configured — see Makefile&apos;s run-api target).</p>
          )}

          {lastRun.storyboard_scenes && lastRun.storyboard_scenes.length > 0 && (
            <p style={{ margin: 0 }}>
              <span className="badge badge-warning">{lastRun.storyboard_scenes.length} scenes</span>{" "}
              <a href={`/projects/${params.id}/storyboard`}>View full storyboard →</a>
            </p>
          )}
        </div>
      )}

      {pendingApproval && (
        <div className="card stack" style={{ borderColor: "var(--warning)" }}>
          <h2 style={{ margin: 0 }}>Approval needed — {pendingApproval.stage}</h2>
          <p>The drafted script is waiting for a decision before this project moves on.</p>
          {decideError && <p style={{ color: "var(--danger)" }}>{decideError}</p>}
          <div className="row">
            <button type="button" className="btn btn-primary" onClick={() => handleApprove(pendingApproval)} disabled={deciding}>
              Approve
            </button>
            <button type="button" className="btn btn-danger" onClick={() => handleReject(pendingApproval)} disabled={deciding}>
              Reject
            </button>
            <button type="button" className="btn" onClick={() => setShowEditForm((v) => !v)} disabled={deciding}>
              Request edit
            </button>
          </div>
          {showEditForm && (
            <div className="stack" style={{ maxWidth: 480 }}>
              <textarea
                placeholder="What should change?"
                rows={3}
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
              />
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => handleRequestEdit(pendingApproval)}
                disabled={deciding || editNotes.trim() === ""}
                style={{ alignSelf: "flex-start" }}
              >
                Send edit request
              </button>
            </div>
          )}
        </div>
      )}

      {decidedApprovals.length > 0 && (
        <div>
          <h3>Approval history</h3>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "var(--text-muted)" }}>
            {decidedApprovals.map((a) => (
              <li key={a.id}>
                {a.stage}: <strong style={{ color: "var(--text)" }}>{a.status}</strong>
                {a.notes ? ` — "${a.notes}"` : ""}
                {a.decided_at ? ` (${new Date(a.decided_at).toLocaleString()})` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h2>Timeline</h2>
        {events.length === 0 ? (
          <div className="empty-state">No agent_events yet — run the pipeline above to generate some.</div>
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
    </div>
  );
}
