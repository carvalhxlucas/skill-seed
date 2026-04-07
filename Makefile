.PHONY: install dev test lint format clean help

# Default target
help:
	@echo "SkillSeed — available make targets:"
	@echo ""
	@echo "  install    Install all packages in editable mode"
	@echo "  dev        Start local services (postgres + redis) and API server"
	@echo "  test       Run all test suites"
	@echo "  lint       Run ruff + mypy across all packages"
	@echo "  format     Auto-format with ruff"
	@echo "  clean      Remove build artifacts and __pycache__"

install:
	pip install -e packages/core
	pip install -e packages/sdk-python
	pip install -e packages/api
	pip install -e packages/mcp-server

install-dev:
	pip install -e "packages/core[dev]"
	pip install -e "packages/sdk-python[dev]"
	pip install -e "packages/api[dev]"
	pip install -e "packages/mcp-server[dev]"
	pip install pytest pytest-asyncio httpx ruff mypy

dev:
	docker-compose up -d postgres redis
	@echo "Waiting for services to be ready..."
	@sleep 2
	uvicorn packages.api.main:app --reload --port 8000

dev-docker:
	docker-compose up --build

test:
	PYTHONPATH=packages/core:packages/sdk-python:packages/api:packages/mcp-server \
	pytest packages/core/tests packages/api/tests packages/sdk-python/tests packages/mcp-server/tests -v

test-core:
	PYTHONPATH=packages/core \
	pytest packages/core/tests -v

test-api:
	PYTHONPATH=packages/core:packages/api \
	pytest packages/api/tests -v

test-sdk:
	PYTHONPATH=packages/core:packages/sdk-python \
	pytest packages/sdk-python/tests -v

test-mcp:
	PYTHONPATH=packages/core:packages/sdk-python:packages/mcp-server \
	pytest packages/mcp-server/tests -v

lint:
	ruff check packages/
	mypy packages/core/skillseed packages/api packages/sdk-python/skillseed

format:
	ruff format packages/
	ruff check --fix packages/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api
