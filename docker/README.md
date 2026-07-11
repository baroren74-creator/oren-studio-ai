# docker

Per-app/service Dockerfiles and any docker-compose override fragments
(e.g. `docker/searxng/` config mounted by the root `docker-compose.yml`).
Root-level infra (Postgres/Redis/Qdrant/MinIO/SearXNG) is defined
directly in the root `docker-compose.yml`; this folder is for
*application* containers once `apps/`, `agents/`, and `services/` have
real code to containerize.
