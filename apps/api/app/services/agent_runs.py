"""Persistence for real Agent cost/usage tracking — docs/database.md's
`agent_runs` table (migrated since Phase 1, powers `apps/web`'s Ops
view). Every real Agent already computes real cost on its `AgentOutput`
(`core.schemas.agent.CostInfo`, from LiteLLM's own `completion_cost()`
— see `providers/llm/llm_provider/client.py`), but nothing previously
read that back out of a graph run: `workflows/graph.py`'s node wrappers
discarded it, and `app/services/orchestrator.py` never wrote to this
table at all. The Ops page (`apps/web/app/ops/page.tsx`) has existed
since Phase 1 and always showed "No agent runs yet" as a result — this
closes that gap.

`workflows/graph.py`'s `StudioState.agent_costs` is the wire format:
one dict per real Agent/scoring call, accumulated across the whole
graph run (`Annotated[list[dict], add]`). This module turns that list
into real `AgentRun` rows.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AgentRun


def persist_agent_runs(db: Session, *, project_id: str, agent_costs: list[dict[str, Any]]) -> list[AgentRun]:
    """One `AgentRun` row per entry in `agent_costs`. Deliberately no
    per-node `started_at`/`finished_at` (the v0 synchronous graph run
    doesn't track that at this granularity yet — see
    `app/services/orchestrator.py`) — every row from one run shares the
    same (default `now()`) timestamp. Good enough for "how much has
    this cost me so far", not yet a precise per-step timing profile."""
    runs = [
        AgentRun(
            project_id=project_id,
            agent_name=entry.get("agent_name", "unknown"),
            status=entry.get("status", "success"),
            cost_usd=entry.get("cost_usd") or 0.0,
            tokens_used=entry.get("tokens_used") or 0,
        )
        for entry in agent_costs
    ]
    if not runs:
        return runs
    db.add_all(runs)
    db.commit()
    for run in runs:
        db.refresh(run)
    return runs
