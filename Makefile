SHELL := /bin/bash
UV ?= uv
SOURCE_DIRS := server tests
SUPPORT_SERVICES_COMPOSE_FILE := compose.support-services.yaml
DOCKER_COMPOSE ?= docker compose -f $(SUPPORT_SERVICES_COMPOSE_FILE)

.DEFAULT_GOAL := help

.PHONY: help setup install install-dev hooks format format-check lint test pre-commit quality ci support-services-up support-services-down support-services-logs support-services-ps db-upgrade db-reset

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

test: ## Run the behavior-first API test suite.
	$(UV) run pytest

pre-commit: ## Run the repository hooks across all files.
	$(UV) run pre-commit run --all-files --show-diff-on-failure

quality: format-check lint test ## Run the local quality gate.

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

db-upgrade: ## Apply Alembic migrations to the configured database.
	$(UV) run alembic upgrade head

db-reset: ## Rebuild the configured database schema from base to head.
	$(UV) run alembic downgrade base
	$(UV) run alembic upgrade head
