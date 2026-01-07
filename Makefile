# ============================================================================
# SOLVER Monorepo Makefile
# ============================================================================
# Task runner for development, testing, and deployment
# Use: make <target>

.PHONY: help install clean test lint format dev build docker-up docker-down migrate test-gates test-recovery e2e

# Default target - show help
help:
	@echo "SOLVER Development Commands"
	@echo "============================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install        - Install all dependencies (API + Web)"
	@echo "  make install-api    - Install API dependencies only"
	@echo "  make install-web    - Install Web dependencies only"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Start all services in dev mode"
	@echo "  make dev-api        - Start API server in dev mode"
	@echo "  make dev-web        - Start Next.js in dev mode"
	@echo "  make dev-db         - Start PostgreSQL only"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests (API + Web)"
	@echo "  make test-api       - Run API tests only"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-e2e       - Run end-to-end tests"
	@echo "  make test-gates     - Run Gate C tests (gating enforcement)"
	@echo "  make test-recovery  - Run Gate D tests (restart/recovery)"
	@echo "  make e2e            - Run Gate E tests (API + SSE flow)"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run all linters"
	@echo "  make lint-api       - Lint Python code (ruff + mypy)"
	@echo "  make lint-web       - Lint TypeScript code (eslint)"
	@echo "  make format         - Format all code"
	@echo "  make format-api     - Format Python code (ruff)"
	@echo "  make format-web     - Format TypeScript code (prettier)"
	@echo "  make typecheck      - Run type checking (mypy + tsc)"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        - Run database migrations"
	@echo "  make migrate-create - Create new migration"
	@echo "  make migrate-down   - Rollback last migration"
	@echo "  make db-reset       - Reset database (WARNING: destroys data)"
	@echo "  make db-seed        - Seed database with test data"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      - Start all Docker services"
	@echo "  make docker-down    - Stop all Docker services"
	@echo "  make docker-build   - Build Docker images"
	@echo "  make docker-logs    - View Docker logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Clean build artifacts and caches"
	@echo "  make clean-api      - Clean Python artifacts"
	@echo "  make clean-web      - Clean Node.js artifacts"

# ============================================================================
# Installation
# ============================================================================

install: install-api install-web
	@echo "✓ All dependencies installed"

install-api:
	@echo "Installing API dependencies..."
	cd apps/api && pip install -e ".[dev,test,observability]"
	@echo "✓ API dependencies installed"

install-web:
	@echo "Installing Web dependencies..."
	cd apps/web && npm install
	@echo "✓ Web dependencies installed"

# ============================================================================
# Development
# ============================================================================

dev:
	@echo "Starting all services in development mode..."
	docker-compose -f infra/docker/docker-compose.yml up -d postgres
	@sleep 2
	@make dev-api & make dev-web

dev-api:
	@echo "Starting API server..."
	cd apps/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	@echo "Starting Next.js dev server..."
	cd apps/web && npm run dev

dev-db:
	@echo "Starting PostgreSQL..."
	docker-compose -f infra/docker/docker-compose.yml up -d postgres

# ============================================================================
# Testing
# ============================================================================

test: test-api
	@echo "✓ All tests passed"

test-api:
	@echo "Running API tests..."
	PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/ -v

test-unit:
	@echo "Running unit tests..."
	PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/integration/ -v

test-e2e:
	@echo "Running end-to-end tests..."
	PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/e2e/ -v

test-gates:
	@echo "Running Gate C tests (gating enforcement)..."
	PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/integration/test_gate_c.py -v
	@echo "✓ Gate C tests passed"

test-recovery:
	@echo "Running Recovery Gate tests (Gate D + P7.3 recovery scenarios)..."
	PYTHONPATH=apps/api .venv/bin/pytest \
		apps/api/tests/integration/test_gate_d.py \
		apps/api/tests/e2e/test_recovery_scenarios.py \
		-v
	@echo "✓ Recovery Gate tests passed"

e2e:
	@echo "Running Gate E tests (API + SSE flow)..."
	PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/e2e/test_gate_e.py -v
	@echo "✓ Gate E tests passed"

test-coverage:
	@echo "Running tests with coverage..."
	PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/ --cov=apps/api --cov-report=html --cov-report=term
	@echo "✓ Coverage report generated in apps/api/htmlcov/index.html"

# ============================================================================
# Code Quality
# ============================================================================

lint: lint-api
	@echo "✓ All linting passed"

lint-api:
	@echo "Linting Python code..."
	cd apps/api && ruff check . tests/
	cd apps/api && mypy .

lint-web:
	@echo "Linting TypeScript code..."
	cd apps/web && npm run lint

format: format-api
	@echo "✓ All code formatted"

format-api:
	@echo "Formatting Python code..."
	cd apps/api && ruff format . tests/
	cd apps/api && ruff check --fix . tests/

format-web:
	@echo "Formatting TypeScript code..."
	cd apps/web && npm run format

typecheck:
	@echo "Running type checks..."
	cd apps/api && mypy .
	@echo "✓ Type checking passed"

# ============================================================================
# Database
# ============================================================================

migrate:
	@echo "Running database migrations..."
	PYTHONPATH=apps/api alembic -c infra/db/migrations/alembic.ini upgrade head
	@echo "✓ Migrations applied"

migrate-create:
	@echo "Creating new migration..."
	@read -p "Migration name: " name; \
	PYTHONPATH=apps/api alembic -c infra/db/migrations/alembic.ini revision --autogenerate -m "$$name"

migrate-down:
	@echo "Rolling back last migration..."
	PYTHONPATH=apps/api alembic -c infra/db/migrations/alembic.ini downgrade -1

db-reset:
	@echo "WARNING: This will destroy all data!"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker-compose -f infra/docker/docker-compose.yml down -v; \
		docker-compose -f infra/docker/docker-compose.yml up -d postgres; \
		sleep 3; \
		make migrate; \
		echo "✓ Database reset complete"; \
	fi

db-seed:
	@echo "Seeding database..."
	cd apps/api && python scripts/seed_db.py
	@echo "✓ Database seeded"

# ============================================================================
# Docker
# ============================================================================

docker-up:
	@echo "Starting Docker services..."
	docker-compose -f infra/docker/docker-compose.yml up -d
	@echo "✓ Services started"

docker-down:
	@echo "Stopping Docker services..."
	docker-compose -f infra/docker/docker-compose.yml down
	@echo "✓ Services stopped"

docker-build:
	@echo "Building Docker images..."
	docker-compose -f infra/docker/docker-compose.yml build
	@echo "✓ Images built"

docker-logs:
	docker-compose -f infra/docker/docker-compose.yml logs -f

# ============================================================================
# Cleanup
# ============================================================================

clean: clean-api clean-web
	@echo "✓ Cleanup complete"

clean-api:
	@echo "Cleaning Python artifacts..."
	find apps/api -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find apps/api -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find apps/api -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find apps/api -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find apps/api -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find apps/api -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf apps/api/dist apps/api/build

clean-web:
	@echo "Cleaning Node.js artifacts..."
	rm -rf apps/web/.next
	rm -rf apps/web/node_modules
	rm -rf apps/web/.turbo

# ============================================================================
# Utilities
# ============================================================================

check-env:
	@echo "Checking environment configuration..."
	@test -f apps/api/.env || (echo "ERROR: apps/api/.env not found. Copy .env.example to .env" && exit 1)
	@echo "✓ Environment configured"

version:
	@echo "SOLVER v0.1.0"
	@echo "Python: $$(python --version)"
	@echo "Node: $$(node --version)"
	@echo "Docker: $$(docker --version)"
