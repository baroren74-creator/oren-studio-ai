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

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type AgentEvent, type Project, type ProjectRun } from "@/lib/api";

export default function ProjectTimelinePage() {
  const params = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<ProjectRun | null>(null);

  function loadProject(id: string) {
    return Promise.all([api.getProject(id), api.getProjectTimeline(id)]).then(([p, e]) => {
      setProject(p);
      setEvents(e);
    });
  }

  useEffect(() => {
    if (!params.id) return;
    loadProject(params.id).catch((err) => setError(err instanceof Error ? err.message : "failed to load project"));
  }, [params.id]);

  async function handleRun() {
    if (!params.id) return;
    setRunning(true);
    setRunError(null);
    try {
      const run = await api.runProject(params.id);
      setLastRun(run);
      await loadProject(params.id);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "run failed");
    } finally {
      setRunning(false);
    }
  }

  if (error) return <p style={{ color: "crimson" }}>{error}</p>;
  if (!project) return <p>Loading…</p>;

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
