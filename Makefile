SHELL := /bin/bash
UV ?= uv
SOURCE_DIRS := server tests agent-sdk/python
SUPPORT_SERVICES_COMPOSE_FILE := compose.support-services.yaml
DOCKER_COMPOSE ?= docker compose -f $(SUPPORT_SERVICES_COMPOSE_FILE)

.DEFAULT_GOAL := help

.PHONY: help setup install install-dev hooks format format-check lint test smoke-test regression-test test-real-api test-smoke launch-readiness-smoke pre-commit quality ci client-install client-lint client-typecheck client-test client-build support-services-up support-services-down support-services-logs support-services-ps db-setup db-upgrade db-reset

help: ## Show the available developer workflow commands.
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%-14s %s\n", $$1, $$2}'

setup: install hooks ## Install dependencies and git hooks.

install: ## Sync the locked development environment.
	$(UV) sync --extra dev --frozen

install-dev: install ## Backwards-compatible alias for install.

hooks: ## Install the pre-commit and pre-push hooks.
	$(UV) run pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push

format: ## Apply formatting fixes.
	$(UV) run ruff format $(SOURCE_DIRS)

format-check: ## Verify formatting without changing files.
	$(UV) run ruff format --check $(SOURCE_DIRS)

lint: ## Run linting and static type checks.
	$(UV) run ruff check $(SOURCE_DIRS)
	$(UV) run mypy $(SOURCE_DIRS)

test: ## Run the full behavior-first test suite, including real-process DB-backed checks.
	$(UV) run pytest

smoke-test: ## Run only the deterministic gameplay smoke scenarios for targeted reruns.
	$(UV) run pytest --no-cov tests/test_simulation_smoke.py

regression-test: ## Run the deterministic simulation regression batch harness.
	$(UV) run pytest --no-cov tests/test_simulation_regression.py

test-real-api: ## Run the real-process, real-DB API integration checks.
	$(UV) run pytest --no-cov tests/api/test_agent_process_api.py

test-smoke: ## Run the small real-process API smoke flow suite.
	$(UV) run pytest --no-cov tests/e2e/test_api_smoke.py

launch-readiness-smoke: ## Run the packaged-runtime launch-readiness smoke slice.
	$(UV) run pytest --no-cov tests/e2e/test_launch_readiness_smoke.py

pre-commit: ## Run the repository hooks across all files.
	$(UV) run pre-commit run --all-files --show-diff-on-failure

client-install: ## Install locked client dependencies.
	cd client && npm ci

client-lint: client-install ## Run the client lint/typecheck verification.
	cd client && npm run lint

client-typecheck: client-lint ## Backwards-compatible alias for client lint/typecheck.

client-test: client-install ## Run the client behavior checks.
	cd client && npm test

client-build: client-install ## Build the client production bundle.
	cd client && npm run build

quality: format-check lint test client-typecheck client-test client-build ## Run the local quality gate, including the client checks.

ci: pre-commit quality ## Run the CI quality gate locally.

support-services-up: ## Start the required local backing services for dev and integration tests.
	@if $(DOCKER_COMPOSE) up --help 2>/dev/null | grep -q -- '--wait'; then \
		$(DOCKER_COMPOSE) up -d --wait postgres; \
	else \
		$(DOCKER_COMPOSE) up -d postgres; \
	fi

support-services-down: ## Stop and remove the local backing services stack.
	$(DOCKER_COMPOSE) down

support-services-logs: ## Tail logs for the local backing services stack.
	$(DOCKER_COMPOSE) logs -f postgres

support-services-ps: ## Show the local backing services status.
	$(DOCKER_COMPOSE) ps

db-setup: ## Provision the current worktree database with migrations and deterministic seed data.
	$(UV) run python -m server.db.tooling setup

db-upgrade: db-setup ## Backwards-compatible alias for database setup.

db-reset: ## Rebuild the current worktree database from migrations plus deterministic seed data.
	$(UV) run python -m server.db.tooling reset
