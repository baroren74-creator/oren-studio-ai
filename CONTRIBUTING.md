# Contributing

This is a single-owner, single-contributor project (for now). This document
exists anyway, because "contributing" here really means "how do I not make
a mess of my own codebase in six months." If this project ever gains
collaborators, these rules become load-bearing rather than aspirational.

Full standards live in `docs/standards.md` — this file is the short,
practical version.

## Workflow

1. Create a branch off `main`: `feat/<short-description>`, `fix/<short-description>`,
   `docs/<short-description>`, or `chore/<short-description>`.
2. Make the change. Keep PRs scoped to one Agent, one Provider, or one
   layer at a time — cross-cutting PRs are hard to review even when you're
   reviewing your own work later.
3. Run `make pre-commit` before opening a PR.
4. Open a PR against `main` using the template in
   `.github/PULL_REQUEST_TEMPLATE.md`. CI must pass.
5. Squash-merge. Delete the branch.

## Commit messages

Conventional Commits, enforced by convention (not yet by a bot):

```
feat(script-agent): add hook generator
fix(video-agent): correct hebrew caption bidi ordering
docs(architecture): record ADR-007 on temporal usage
chore(deps): bump litellm to 1.52.0
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`.
Scope = the folder most affected (`research-agent`, `video-agent`,
`core`, `api`, `web`, `infra`, etc.).

## Before you add a new dependency

Check `docs/open-source-landscape.md` first — there's a real chance the
category was already researched (license, maturity, alternatives). If it's
a genuinely new category, add an entry there with the same structure
(Maturity / Community / License / Pros / Cons / Recommendation) before
merging the dependency in.

## Before you add a new Agent

1. It must implement the `Agent` contract in `packages/core/schemas`
   (`AgentInput` → `AgentOutput`, see `docs/agents.md`).
2. It must be registered in the Agent Registry — not called directly by
   another agent.
3. It communicates only via events (`docs/api.md` section on Event Types)
   and the database — never by importing another agent's module.
4. Add it to `docs/agents.md` with its input/output schema.

## Before you change the database schema

Add a migration (see `docs/database.md`), and update `docs/database.md`
itself in the same PR. Schema drift between the doc and reality is exactly
the kind of thing that's cheap to prevent and expensive to debug later.

## Architectural changes

Anything that changes a decision recorded in `docs/decisions.md` (choice of
orchestrator, vector DB, provider, license posture, etc.) needs a new ADR
entry explaining what changed and why — not a silent edit of the old one.
