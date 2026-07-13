"use client";

// The real Storyboard view — docs/roadmap.md 3.8: "UI: Storyboard view
// (scene list + preview)". Reads GET /api/projects/{id}/storyboard
// (app.services.storyboard.get_latest_storyboard_for_project) rather
// than the ephemeral ProjectRunOut.storyboard_scenes the project page's
// "Latest run" card shows — this page survives a reload.
//
// "Preview" here is a placeholder card, not a real thumbnail — there is
// no asset library/B-roll search yet (workflows/storyboard.py's
// docstring), so `visual_ref` is always null. The card still shows the
// visual *instruction* (what should be filmed/shown) prominently, since
// that's the actually-useful information at this stage: a shot list a
// human can film against, not a generated image.

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type Project, type Storyboard } from "@/lib/api";

function formatDuration(seconds: number): string {
  return `${seconds.toFixed(1)}s`;
}

export default function StoryboardPage() {
  const params = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!params.id) return;
    setLoading(true);
    api
      .getProject(params.id)
      .then(setProject)
      .catch((err) => setError(err instanceof Error ? err.message : "failed to load project"));

    api
      .getStoryboard(params.id)
      .then((sb) => {
        setStoryboard(sb);
        setNotFound(false);
      })
      .catch((err) => {
        // A 404 here just means "no storyboard yet" — the common,
        // expected case (no script produced, or the run predates
        // Phase 3.7) — not a real error to show.
        if (err instanceof Error && err.message.includes("404")) {
          setNotFound(true);
        } else {
          setError(err instanceof Error ? err.message : "failed to load storyboard");
        }
      })
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return <p>Loading…</p>;
  if (error) return <p style={{ color: "var(--danger)" }}>{error}</p>;

  const totalDuration = storyboard?.scenes.reduce((sum, s) => sum + s.duration, 0) ?? 0;

  return (
    <div className="stack" style={{ gap: "var(--space-6)" }}>
      <div>
        <a href={`/projects/${params.id}`} style={{ fontSize: "var(--text-sm)" }}>
          ← {project?.title ?? "Project"}
        </a>
        <h1 style={{ marginTop: "var(--space-2)" }}>Storyboard</h1>
      </div>

      {notFound ? (
        <div className="empty-state">
          <p style={{ margin: 0 }}>
            No storyboard yet for this project. Run the pipeline from the project page once a script has been
            drafted — a storyboard is generated automatically right after.
          </p>
        </div>
      ) : storyboard ? (
        <>
          <div className="row" style={{ gap: "var(--space-6)" }}>
            <div className="stat">
              <span className="stat-value">{storyboard.scenes.length}</span>
              <span className="stat-label">Scenes</span>
            </div>
            <div className="stat">
              <span className="stat-value">{formatDuration(totalDuration)}</span>
              <span className="stat-label">Total duration</span>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
              gap: "var(--space-4)",
            }}
          >
            {storyboard.scenes.map((scene) => (
              <div key={scene.order} className="card stack">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <span className="badge badge-neutral">Scene {scene.order}</span>
                  <span className="badge badge-warning">{formatDuration(scene.duration)}</span>
                </div>

                {/* Visual "preview" placeholder — no real asset yet (see
                    module comment above), so this shows the shot
                    instruction itself as the primary content instead of
                    a generated thumbnail. */}
                <div
                  style={{
                    background: "var(--bg-raised-2)",
                    border: "1px dashed var(--border-strong)",
                    borderRadius: "var(--radius-sm)",
                    padding: "var(--space-4)",
                    minHeight: 96,
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  <p style={{ margin: 0, color: "var(--text)" }}>{scene.description}</p>
                </div>

                {scene.caption_cue && (
                  <p style={{ margin: 0, fontSize: "var(--text-sm)", fontStyle: "italic" }}>
                    “{scene.caption_cue}”
                  </p>
                )}
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
