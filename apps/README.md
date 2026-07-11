# apps

Deployable applications: `web/` (Next.js Studio UI) and `api/` (FastAPI
backend/BFF, hosts the embedded LangGraph Orchestrator). Everything else
in this repo (`packages/`, `agents/`, `providers/`, `services/`) is a
dependency of one of these two, not deployed on its own — except the
processes under `services/`, which run independently.
