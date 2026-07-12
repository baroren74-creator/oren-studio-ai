.PHONY: help up down restart logs ps clean install lint format test migrate seed run-api run-web pre-commit

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Start local infra (postgres, redis, qdrant, minio, searxng)
	docker compose up -d

down: ## Stop local infra
	docker compose down

restart: down up ## Restart local infra

logs: ## Tail infra logs
	docker compose logs -f

ps: ## Show running infra containers
	docker compose ps

clean: ## Stop infra and remove volumes (DESTRUCTIVE — wipes local DB/vectors)
	docker compose down -v

install: ## Install pre-commit hooks (run once after cloning)
	pre-commit install

lint: ## Lint all packages (placeholder until apps/agents have code)
	@echo "No lintable code yet — placeholder target, see docs/standards.md"

format: ## Format all packages (placeholder until apps/agents have code)
	@echo "No formattable code yet — placeholder target, see docs/standards.md"

test: ## Run Python test suites (apps/api, agents/research_agent, agents/trend_agent, agents/knowledge_agent, agents/script_agent, workflows, packages/memory, providers/llm). apps/web has its own `npm test` once added.
	cd apps/api && PYTHONPATH="$(CURDIR):$(CURDIR)/packages/core:$(CURDIR)/workflows:$(CURDIR)/providers/llm:$(CURDIR)/packages/memory:$(CURDIR)/apps/api" python3 -m pytest tests/ -v
	cd agents/research_agent && PYTHONPATH="$(CURDIR):$(CURDIR)/packages/core:$(CURDIR)/providers/llm" python3 -m pytest tests/ -v
	cd agents/trend_agent && PYTHONPATH="$(CURDIR):$(CURDIR)/packages/core" python3 -m pytest tests/ -v
	cd agents/knowledge_agent && PYTHONPATH="$(CURDIR):$(CURDIR)/packages/core:$(CURDIR)/providers/llm:$(CURDIR)/packages/memory" python3 -m pytest tests/ -v
	cd agents/script_agent && PYTHONPATH="$(CURDIR):$(CURDIR)/packages/core:$(CURDIR)/providers/llm" python3 -m pytest tests/ -v
	cd workflows && PYTHONPATH="$(CURDIR):$(CURDIR)/packages/core:$(CURDIR)/providers/llm" python3 -m pytest tests/ -v
	cd packages/memory && PYTHONPATH="$(CURDIR)/providers/llm" python3 -m pytest tests/ -v
	cd providers/llm && python3 -m pytest tests/ -v

migrate: ## Run DB migrations against DATABASE_URL (apps/api/alembic)
	cd apps/api && python3 -m alembic upgrade head

seed: ## Seed local DB with dev data (currently: style_profile v0, Phase 3.1)
	PYTHONPATH="$(CURDIR):$(CURDIR)/packages/core:$(CURDIR)/workflows:$(CURDIR)/providers/llm:$(CURDIR)/packages/memory:$(CURDIR)/apps/api" python3 scripts/seed_style_profile.py

run-api: ## Run apps/api for real (uvicorn, reload on) — needs ANTHROPIC_API_KEY/VOYAGE_API_KEY in .env for real Agent output, see apps/api/app/services/orchestrator.py
	cd apps/api && PYTHONPATH="$(CURDIR):$(CURDIR)/packages/core:$(CURDIR)/workflows:$(CURDIR)/providers/llm:$(CURDIR)/packages/memory:$(CURDIR)/apps/api" python3 -m uvicorn app.main:app --reload --port 8000

run-web: ## Run apps/web for real (Next.js dev server) — needs apps/api running (make run-api) at NEXT_PUBLIC_API_BASE_URL
	cd apps/web && npm run dev

pre-commit: ## Run pre-commit hooks against all files
	pre-commit run --all-files
