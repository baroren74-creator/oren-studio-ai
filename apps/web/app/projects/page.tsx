"use client";

// Projects screen: list of existing projects (found missing live —
// there was previously no way back to a project you'd already created,
// only this page's New Project form) plus that same form to start a
// new one.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, type Project } from "@/lib/api";

const SOURCE_TYPES = ["github", "youtube", "reel", "post", "tweet", "website"] as const;

// Phase 3.9: no reliable, ToS-clean automated fetch exists for these
// source types (see agents/research_agent/agent.py's module docstring —
// Meta disabled most public Instagram Reel scraping/download endpoints
// in late 2024) — Oren pastes the caption/transcript himself instead.
const MANUAL_TEXT_SOURCE_TYPES = new Set<(typeof SOURCE_TYPES)[number]>(["reel", "post", "tweet"]);

export default function ProjectsPage() {
  const router = useRouter();

  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceType, setSourceType] = useState<(typeof SOURCE_TYPES)[number]>("github");
  const [sourceText, setSourceText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isManualText = MANUAL_TEXT_SOURCE_TYPES.has(sourceType);

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((err) => setListError(err instanceof Error ? err.message : "failed to load projects"))
      .finally(() => setLoadingProjects(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const project = await api.createProject({
        source_type: sourceType,
        source_url: sourceUrl,
        source_text: isManualText ? sourceText : undefined,
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to create project");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="stack" style={{ gap: "var(--space-6)" }}>
      <h1>Projects</h1>

      {loadingProjects ? (
        <p>Loading…</p>
      ) : listError ? (
        <p style={{ color: "var(--danger)" }}>{listError}</p>
      ) : projects.length === 0 ? (
        <div className="empty-state">No projects yet — create one below.</div>
      ) : (
        <div className="stack" style={{ gap: "var(--space-2)" }}>
          {projects.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="card row" style={{ justifyContent: "space-between", textDecoration: "none" }}>
              <span style={{ color: "var(--text)", fontWeight: 500 }}>{p.title ?? "(untitled project)"}</span>
              <span className="row" style={{ gap: "var(--space-2)" }}>
                {p.source_type && <span className="badge badge-neutral">{p.source_type}</span>}
                <span className="badge badge-neutral">{p.status}</span>
              </span>
            </Link>
          ))}
        </div>
      )}

      <div className="card stack" style={{ maxWidth: 480 }}>
        <h2 style={{ margin: 0 }}>New project</h2>
        <p style={{ margin: 0 }}>
          {isManualText
            ? "No automated fetch exists for this source type yet — paste the link plus the caption/transcript text yourself."
            : "Paste a source URL to create a new project row."}
        </p>
        <form onSubmit={handleSubmit} className="stack">
          <select value={sourceType} onChange={(e) => setSourceType(e.target.value as typeof sourceType)}>
            {SOURCE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <input
            type="url"
            required
            placeholder="https://github.com/..."
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
          />
          {isManualText && (
            <textarea
              required
              rows={6}
              placeholder="Paste the caption or transcript text here…"
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
            />
          )}
          <button type="submit" className="btn btn-primary" disabled={submitting} style={{ alignSelf: "flex-start" }}>
            {submitting ? "Creating…" : "Create project"}
          </button>
          {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        </form>
      </div>
    </div>
  );
}
