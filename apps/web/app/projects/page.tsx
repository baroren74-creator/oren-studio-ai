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

export default function ProjectsPage() {
  const router = useRouter();

  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceType, setSourceType] = useState<(typeof SOURCE_TYPES)[number]>("github");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      const project = await api.createProject({ source_type: sourceType, source_url: sourceUrl });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to create project");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h1>Projects</h1>

      {loadingProjects ? (
        <p>Loading…</p>
      ) : listError ? (
        <p style={{ color: "crimson" }}>{listError}</p>
      ) : projects.length === 0 ? (
        <p>No projects yet — create one below.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, marginBottom: "2rem" }}>
          {projects.map((p) => (
            <li key={p.id} style={{ marginBottom: "0.5rem" }}>
              <Link href={`/projects/${p.id}`}>
                {p.title ?? "(untitled project)"} — <span style={{ opacity: 0.7 }}>{p.status}</span>
                {p.source_type ? ` · ${p.source_type}` : ""}
              </Link>
            </li>
          ))}
        </ul>
      )}

      <h2>New project</h2>
      <p>Paste a source URL to create a new project row.</p>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxWidth: 480 }}>
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
        <button type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create project"}
        </button>
        {error && <p style={{ color: "crimson" }}>{error}</p>}
      </form>
    </div>
  );
}
