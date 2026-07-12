"""FastAPI app entrypoint — see docs/api.md for the full route contract.

This is also the process that hosts the embedded LangGraph Orchestrator
(docs/decisions.md ADR-001, apps/api/app/services/orchestrator.py's
`POST /api/projects/{id}/run` — a deliberate v0 shortcut, see that
module's docstring).
"""

from __future__ import annotations

from fastapi import FastAPI

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

app.include_router(projects.router)
app.include_router(agent_runs.router)
app.include_router(knowledge.router)
app.include_router(style_profile.router)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
