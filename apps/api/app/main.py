"""FastAPI app entrypoint — see docs/api.md for the full route contract.

This is also the process that will host the embedded LangGraph
Orchestrator (docs/decisions.md ADR-001) once Phase 2 wires real Agents
into workflows/graph.py — deliberately not the hosted LangGraph Platform
server.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import agent_runs, knowledge, projects
from app.ws import router as ws_router

app = FastAPI(title="Oren Studio AI API", version="0.1.0")

app.include_router(projects.router)
app.include_router(agent_runs.router)
app.include_router(knowledge.router)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
