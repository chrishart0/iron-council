.PHONY: install-dev format lint test quality

install-dev:
	uv sync --extra dev

format:
	uv run ruff format server tests

lint:
	uv run ruff check server tests
	uv run mypy server tests

test:
	uv run pytest -q

quality: format lint test
