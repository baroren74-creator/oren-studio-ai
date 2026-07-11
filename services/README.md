# services

Standalone, independently-deployable backend processes that are neither
"the API" (`apps/api`) nor "an Agent" (`agents/`). Currently:

- `orchestrator-worker/` — long-running process that consumes the Redis
  event bus and drives LangGraph runs (separated from `apps/api`'s
  request/response cycle so long pipelines don't block HTTP handling).
- `scheduler/` — cron-style triggers (e.g. daily Trend Agent runs, Phase
  6 monthly preference-learning batch job).

No business logic yet (Phase 1 is infra-only, see root `docker-compose.yml`
note).
