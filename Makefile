.PHONY: help up down restart logs ps clean install lint format test migrate seed pre-commit

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

test: ## Run test suite (placeholder until apps/agents have code)
	@echo "No tests yet — placeholder target, see docs/standards.md"

migrate: ## Run DB migrations (placeholder — wired up once apps/api exists)
	@echo "Migrations not wired up yet — see docs/database.md"

seed: ## Seed local DB with dev data (placeholder)
	@echo "Seeding not wired up yet"

pre-commit: ## Run pre-commit hooks against all files
	pre-commit run --all-files
