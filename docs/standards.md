# Development Standards

These are binding conventions, not suggestions — the whole point of a
single-user long-lived project is that the only person who suffers from
inconsistency is future-you. Deviating requires a note in
`docs/decisions.md`, not a silent exception.

## 1. Naming conventions

- **Python**: `snake_case` for files/functions/variables, `PascalCase` for
  classes, `SCREAMING_SNAKE_CASE` for constants. Module = one clear
  responsibility (`research_agent/agent.py`, not `research_agent/utils.py`
  as a dumping ground).
- **TypeScript/React**: `camelCase` for variables/functions, `PascalCase`
  for components and types, files named after their default export
  (`ProjectTimeline.tsx` exports `ProjectTimeline`).
- **Database**: `snake_case` tables/columns, plural table names
  (`projects`, `agent_runs`), singular FK columns (`project_id`).
- **Events**: `noun.past_tense_verb` (`script.drafted`, `video.rendered`,
  `idea.rejected`) — matches `docs/api.md`'s Event Type list exactly. Never
  invent a new event name without adding it there first.
- **Agents**: folder name = `snake_case` + `_agent` suffix
  (`research_agent`, `video_agent`), matching the `agent_name` value stored
  in `agent_runs.agent_name`.
- **Providers**: folder name = category (`llm`, `video`, `avatar`, `voice`,
  `publish`, `search`, `crawl`), file name = provider name
  (`providers/llm/anthropic.py`, `providers/voice/elevenlabs.py`).

## 2. Folder structure rules

- An **Agent** never imports another Agent's module. Communication is only
  via events + the database (see `docs/architecture.md` section 3). If a
  PR adds `from agents.research_agent import ...` inside another agent,
  that's a bug, not a shortcut.
- A **Provider** implements a fixed interface (`packages/core/schemas` /
  provider protocol) and knows nothing about Agents or the Orchestrator.
  Providers are called, never call back into the system.
- `packages/` code must not import from `apps/`, `agents/`, `services/`,
  or `providers/` — dependency direction is one-way: apps/agents/services
  depend on packages, never the reverse.
- Anything under `docs/` that describes a schema, contract, or decision
  must be updated in the same PR that changes the corresponding code —
  not "later."

## 3. Code style

- **Python**: formatted and linted with `ruff` (format + lint in one tool,
  replaces black/isort/flake8 — see `.pre-commit-config.yaml`). Type hints
  required on all function signatures; `mypy` runs advisory in CI until
  the codebase is large enough to make it blocking.
- **TypeScript**: `prettier` for formatting, `eslint` for linting once
  `apps/web` has real code. Strict mode (`"strict": true` in
  `tsconfig.json`) — no `any` without a `// TODO` comment explaining why.
- All Pydantic/Zod schemas are the source of truth for a data shape —
  don't hand-roll a duplicate TypeScript interface for something already
  defined as a Pydantic model exposed over the API; generate or hand-sync
  deliberately, and note it in the schema's docstring.

## 4. Commit convention

Conventional Commits — see `CONTRIBUTING.md` for the exact format and
scope list.

## 5. Branch strategy

Trunk-based, single long-lived branch (`main`). Short-lived feature
branches (`feat/...`, `fix/...`, `docs/...`, `chore/...`), squash-merged.
No `develop`/`release` branches — for a single-user project with a human
approval gate already in front of every externally-visible action
(publishing), a heavier branching model buys nothing. Revisit this if the
project ever gains collaborators or a staging environment with independent
release cadence.

## 6. Versioning

- **Repository**: [SemVer](https://semver.org/)-flavored tags
  (`v0.1.0`, `v0.2.0`, ...), cut manually at the end of each Roadmap phase
  (see `ROADMAP.md`). Not tied to a public release — it's a checkpoint
  marker for "phase N was working end-to-end."
- **Agents**: each Agent implementation carries its own `version` string
  (part of the `Agent` protocol, stored on every `agent_runs` row) — bump
  it whenever the agent's *behavior* changes in a way that would make old
  runs non-reproducible with the new code (prompt changes count; typo
  fixes in comments don't).
- **Prompts**: versioned via `prompt_library.version` /
  `prompt_library.parent_id` in the database (see `docs/database.md`), not
  via git tags — prompts change independently of code deploys.
- **Database schema**: linear, ordered Alembic migrations. Never edit a
  migration that has already been applied to the local dev database;
  write a new one.

## 7. Logging

- Structured logging only (JSON lines), never bare `print()`/`console.log`
  left in committed code.
- Every log line inside an Agent run includes `run_id`, `agent_name`,
  `project_id` — this is what makes `agent_events` (see
  `docs/database.md`) actually useful for debugging instead of just an
  audit trail nobody reads.
- Log levels: `DEBUG` (verbose, local only), `INFO` (state transitions —
  event published, approval granted), `WARNING` (recovered from
  automatically, e.g. a retried provider call), `ERROR` (run failed, needs
  attention).
- Never log secrets, API keys, or full LLM prompts containing personal
  data at `INFO` level or above — `DEBUG` only, and `.env`-gated.

## 8. Error handling

- Every Agent's `run()` method catches its own exceptions and returns a
  well-formed `AgentOutput` with `status="failed"` and a clear `result`
  payload — it never lets a raw exception propagate up to the
  Orchestrator. The Orchestrator's job is to decide what to do about a
  failure (retry, halt, notify), not to parse stack traces.
- Provider adapters distinguish **retryable** failures (timeout, rate
  limit, transient 5xx) from **terminal** ones (bad API key, invalid
  input, content policy rejection) via a typed exception hierarchy in
  `packages/core` — Orchestrator retry logic depends on this distinction.
- Never silently swallow an error to "keep the pipeline moving" — a
  skipped step must produce an explicit `status="skipped"` with a reason,
  visible in the Ops view (`docs/architecture.md` section 9).

## 9. Testing strategy

- **Unit tests**: every Agent's pure logic (prompt construction, scoring,
  parsing) is tested without hitting a real LLM/provider — mock the
  Provider interface.
- **Contract tests**: every Provider adapter has a test that validates it
  actually satisfies the shared interface (`packages/core` protocol) —
  catches drift when a provider's SDK changes shape.
- **Integration tests**: the Orchestrator graph is tested end-to-end with
  Stub Agents (see `docs/roadmap.md` Phase 1.13) before any real Agent
  logic is trusted to plug into it.
- **No test-coverage percentage target.** For a single-user project,
  coverage theater is a worse use of time than testing the things that
  actually break silently (schema drift, Hebrew text rendering, event
  ordering) — prioritize by "what would I not notice was broken until
  publish time."

## 10. Documentation strategy

- `docs/` is the source of truth for *why*; code comments are for *how*,
  local and narrow. If a decision needs more than a one-line comment to
  justify, it belongs in `docs/decisions.md`, referenced from the code.
- Every Agent has a corresponding entry in `docs/agents.md`. Every new
  event type has an entry in `docs/api.md`. Every schema change has an
  entry in `docs/database.md`. This is enforced by PR review (self-review,
  realistically) via the checklist in `.github/PULL_REQUEST_TEMPLATE.md`,
  not by tooling — there's no CI job that can verify a doc is *accurate*,
  only that it exists.
