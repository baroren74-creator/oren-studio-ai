"""FastAPI app entrypoint — see docs/api.md for the full route contract.

This is also the process that hosts the embedded LangGraph Orchestrator
(docs/decisions.md ADR-001, apps/api/app/services/orchestrator.py's
`POST /api/projects/{id}/run` — a deliberate v0 shortcut, see that
module's docstring).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import every agent module so it registers itself on
# core.registry.default_registry (each agents/*/agent.py module
# self-registers as an import side-effect — see core.registry.
# AgentRegistry). Without this, orchestrator.run_project()'s default
# registry would be empty and every node would fail with "unknown
# agent". Same import list as apps/api/tests/test_smoke_e2e.py, kept in
# sync deliberately — that test file is effectively already testing
# "does the real registry have everything main.py needs".
import agents.knowledge_agent.agent  # noqa: F401
import agents.publishing_agent.agent  # noqa: F401
import agents.recording_agent.agent  # noqa: F401
import agents.research_agent.agent  # noqa: F401
import agents.script_agent.agent  # noqa: F401
import agents.trend_agent.agent  # noqa: F401
import agents.video_agent.agent  # noqa: F401
import agents.voice_agent.agent  # noqa: F401

from app.routers import agent_runs, knowledge, projects, style_profile
from app.ws import router as ws_router

app = FastAPI(title="Oren Studio AI API", version="0.1.0")

# apps/web (Next.js dev server, localhost:3000) calls this API from the
# browser at a different origin (localhost:8000) — without CORS headers
# the browser blocks every request before it even reaches a route
# (surfaces in apps/web as a generic "Failed to fetch", no server log
# at all, which is what made this easy to miss during backend-only
# testing). Wide open for now: this is a single-user local dev tool
# with no cookies/session auth (ADR-006's static API key doesn't rely
# on the browser's own trust model), so there's no meaningful CSRF
# surface to restrict origins against yet.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(agent_runs.router)
app.include_router(knowledge.router)
app.include_router(style_profile.router)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
