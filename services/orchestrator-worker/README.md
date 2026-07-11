# services/orchestrator-worker

Consumes Redis Streams events and drives the LangGraph orchestration
graph (`workflows/`). Separated from `apps/api` so a long video-render
step never blocks an HTTP request. Not implemented yet — see
`docs/roadmap.md` Phase 1.13.
