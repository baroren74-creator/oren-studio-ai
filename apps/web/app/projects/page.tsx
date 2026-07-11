"use client";

// New Project screen — docs/roadmap.md 1.15: URL paste only, no
// analysis yet (that's Phase 2, once Research Agent has real logic
// behind the stub).

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const SOURCE_TYPES = ["github", "youtube", "reel", "post", "tweet", "website"] as const;

export default function ProjectsPage() {
  const router = useRouter();
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceType, setSourceType] = useState<(typeof SOURCE_TYPES)[number]>("github");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      <h1>New project</h1>
      <p>Paste a source URL. Analysis (Research Agent) is not wired up yet in Phase 1 — this just creates the project row.</p>
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
