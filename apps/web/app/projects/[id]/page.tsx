"use client";

// Project timeline view — docs/roadmap.md 1.16: chronological list of
// agent_events for a project. Read-only in Phase 1 (no agents run yet).

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type AgentEvent, type Project } from "@/lib/api";

export default function ProjectTimelinePage() {
  const params = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.id) return;
    Promise.all([api.getProject(params.id), api.getProjectTimeline(params.id)])
      .then(([p, e]) => {
        setProject(p);
        setEvents(e);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "failed to load project"));
  }, [params.id]);

  if (error) return <p style={{ color: "crimson" }}>{error}</p>;
  if (!project) return <p>Loading…</p>;

  return (
    <div>
      <h1>{project.title ?? "(untitled project)"}</h1>
      <p>
        Status: <strong>{project.status}</strong> · Source: {project.source_type} — {project.source_url}
      </p>

      <h2>Timeline</h2>
      {events.length === 0 ? (
        <p>No agent_events yet — no agents have run for this project (expected in Phase 1).</p>
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
