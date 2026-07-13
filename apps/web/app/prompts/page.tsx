"use client";

// Prompt Library — docs/roadmap.md 3.5: CRUD + versioning. See
// apps/api/app/services/prompt_library.py's module docstring for the
// versioning model (editing never overwrites a row — it inserts a new
// one with parent_id pointing at the version it was edited from).
// docs/architecture.md section 9.5 explicitly requires the UI to show a
// Diff between versions rather than silently applying an "update" — the
// live diff below the edit box, and the diff shown per step in the
// history list, are both here for that reason specifically, not just as
// a nice-to-have.

import { useEffect, useState } from "react";
import { diffWords } from "diff";
import { api, type Prompt } from "@/lib/api";

function DiffView({ before, after }: { before: string; after: string }) {
  const parts = diffWords(before ?? "", after ?? "");
  return (
    <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, border: "1px solid #444", borderRadius: 6, padding: "0.75rem" }}>
      {parts.map((part, i) => (
        <span
          key={i}
          style={{
            backgroundColor: part.added ? "#1f4d2b" : part.removed ? "#4d1f1f" : "transparent",
            textDecoration: part.removed ? "line-through" : "none",
            color: part.added ? "#8fe3a3" : part.removed ? "#e38f8f" : "inherit",
          }}
        >
          {part.value}
        </span>
      ))}
    </div>
  );
}

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [history, setHistory] = useState<Prompt[]>([]);

  const [draftText, setDraftText] = useState("");
  const [saving, setSaving] = useState(false);

  const [newName, setNewName] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [newText, setNewText] = useState("");
  const [creating, setCreating] = useState(false);

  function loadPrompts() {
    return api
      .listPrompts()
      .then(setPrompts)
      .catch((err) => setError(err instanceof Error ? err.message : "failed to load prompts"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadPrompts();
  }, []);

  const selected = prompts.find((p) => p.id === selectedId) ?? null;

  function selectPrompt(prompt: Prompt) {
    setSelectedId(prompt.id);
    setDraftText(prompt.prompt_text ?? "");
    api
      .getPromptHistory(prompt.id)
      .then(setHistory)
      .catch((err) => setError(err instanceof Error ? err.message : "failed to load history"));
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await api.createPrompt({ name: newName, category: newCategory || undefined, prompt_text: newText });
      setNewName("");
      setNewCategory("");
      setNewText("");
      await loadPrompts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to create prompt");
    } finally {
      setCreating(false);
    }
  }

  async function handleSaveVersion() {
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.createPromptVersion(selected.id, { prompt_text: draftText });
      await loadPrompts();
      selectPrompt(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to save new version");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!selected) return;
    setError(null);
    try {
      await api.deletePrompt(selected.id);
      setSelectedId(null);
      setHistory([]);
      await loadPrompts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to delete prompt");
    }
  }

  if (loading) return <p>Loading…</p>;

  return (
    <div>
      <h1>Prompt Library</h1>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div style={{ display: "flex", gap: "2rem", alignItems: "flex-start" }}>
        <div style={{ minWidth: 280 }}>
          <h2>Prompts</h2>
          {prompts.length === 0 ? (
            <p>No prompts yet — create one below.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0 }}>
              {prompts.map((p) => (
                <li key={p.id} style={{ marginBottom: "0.5rem" }}>
                  <button
                    type="button"
                    onClick={() => selectPrompt(p)}
                    style={{ fontWeight: p.id === selectedId ? "bold" : "normal" }}
                  >
                    {p.name} (v{p.version}){p.category ? ` — ${p.category}` : ""}
                  </button>
                </li>
              ))}
            </ul>
          )}

          <h3>New prompt</h3>
          <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxWidth: 320 }}>
            <input placeholder="name" required value={newName} onChange={(e) => setNewName(e.target.value)} />
            <input placeholder="category (optional)" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} />
            <textarea placeholder="prompt text" rows={4} value={newText} onChange={(e) => setNewText(e.target.value)} />
            <button type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create prompt"}
            </button>
          </form>
        </div>

        {selected && (
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2>
              {selected.name} — version {selected.version}
            </h2>
            <p>Category: {selected.category ?? "—"}</p>

            <textarea
              rows={8}
              style={{ width: "100%", maxWidth: 640 }}
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
            />

            {draftText !== (selected.prompt_text ?? "") && (
              <div style={{ marginTop: "0.75rem", maxWidth: 640 }}>
                <p>Unsaved changes — diff against version {selected.version}:</p>
                <DiffView before={selected.prompt_text ?? ""} after={draftText} />
              </div>
            )}

            <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem" }}>
              <button type="button" onClick={handleSaveVersion} disabled={saving || draftText === (selected.prompt_text ?? "")}>
                {saving ? "Saving…" : "Save as new version"}
              </button>
              <button type="button" onClick={handleDelete}>
                Delete prompt (all versions)
              </button>
            </div>

            <h3 style={{ marginTop: "1.5rem" }}>History</h3>
            {history.length <= 1 ? (
              <p>Only one version so far.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem", maxWidth: 640 }}>
                {history.slice(1).map((version, i) => (
                  <div key={version.id}>
                    <p>
                      Version {history[i].version} → {version.version} ({new Date(version.created_at).toLocaleString()})
                    </p>
                    <DiffView before={history[i].prompt_text ?? ""} after={version.prompt_text ?? ""} />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
