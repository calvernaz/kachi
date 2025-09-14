# Makefile for Kachi Billing System

.PHONY: help install test test-unit test-integration test-performance test-property test-fast test-coverage lint format type-check quality-check clean dev-setup run-ingest run-dashboard run-frontend start-ingest-api start-dashboard-api start-frontend start-workers dev dev-stop db-migrate db-reset docker-build docker-run docker-stop deps-update deps-audit pre-commit ci-test ci-full

# Default target
help:
	@echo "Kachi Billing System - Available Commands:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  install          Install dependencies with uv"
	@echo "  dev-setup        Set up development environment"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-performance Run performance tests only"
	@echo "  test-property    Run property-based tests only"
	@echo "  test-fast        Run fast tests (skip slow ones)"
	@echo "  test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run ruff linting"
	@echo "  format           Format code with ruff"
	@echo "  type-check       Run mypy type checking"
	@echo "  quality-check    Run all quality checks"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  dev              Start complete development environment"
	@echo "  dev-stop         Stop development environment"
	@echo ""
	@echo "🛠️  Development Services:"
	@echo "  start-ingest-api     Start ingest API server (port 8001)"
	@echo "  start-dashboard-api  Start dashboard API server (port 8002)"
	@echo "  start-frontend       Start frontend dev server (port 5173)"
	@echo "  start-workers        Start Celery background workers"
	@echo ""
	@echo "🗄️  Database:"
	@echo "  db-migrate       Run database migrations"
	@echo "  db-reset         Reset database (destructive)"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  docker-build     Build Docker images"
	@echo "  docker-run       Start all services with Docker"
	@echo "  docker-stop      Stop Docker services"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  clean            Clean up generated files"
	@echo "  deps-update      Update dependencies"

# Installation and setup
install:
	uv sync

dev-setup: install
	uv run pre-commit install
	@echo "Development environment set up successfully!"

# Testing targets
test:
	python scripts/run_tests.py

test-unit:
	python scripts/run_tests.py --unit

test-integration:
	python scripts/run_tests.py --integration

test-performance:
	python scripts/run_tests.py --performance

test-property:
	python scripts/run_tests.py --property

test-fast:
	python scripts/run_tests.py --fast

test-coverage:
	python scripts/run_tests.py --coverage

# Code quality targets
lint:
	uv run ruff check --fix src/ tests/

format:
	uv run ruff format src/ tests/

type-check:
	uv run mypy src/kachi

quality-check: lint type-check
	@echo "All quality checks completed!"

# Development servers
run-ingest:
	DATABASE_URL=postgresql+asyncpg://kachi:kachi_password@localhost:5432/kachi \
	REDIS_URL=redis://localhost:6379/0 \
	uv run uvicorn kachi.apps.ingest_api.main:app --host 0.0.0.0 --port 8001 --reload

run-dashboard:
	DATABASE_URL=postgresql+asyncpg://kachi:kachi_password@localhost:5432/kachi \
	REDIS_URL=redis://localhost:6379/0 \
	uv run uvicorn kachi.apps.dashboard_api.main:app --host 0.0.0.0 --port 8002 --reload

run-frontend:
	cd frontend/dashboard && yarn dev

# Alias targets for README compatibility
start-ingest-api: run-ingest

start-dashboard-api: run-dashboard

start-frontend: run-frontend

start-workers:
	@echo "Starting Celery workers..."
	uv run celery -A kachi.lib.celery_app worker --loglevel=info --concurrency=2

# Development mode - start all services
dev:
	@echo "🚀 Starting Kachi development environment..."
	@echo "📊 Starting databases..."
	@docker compose up -d postgres redis
	@echo "⏳ Waiting for databases to be ready..."
	@sleep 10
	@echo "🔄 Running database migrations..."
	@DATABASE_URL=postgresql+asyncpg://kachi:kachi_password@localhost:5432/kachi $(MAKE) db-migrate
	@echo "🎯 Starting all services..."
	@echo "   - Ingest API will be available at http://localhost:8001"
	@echo "   - Dashboard API will be available at http://localhost:8002"
	@echo "   - Frontend will be available at http://localhost:5173"
	@echo ""
	@echo "💡 Use Ctrl+C to stop all services"
	@echo ""
	@echo "Starting services in background..."
	@DATABASE_URL=postgresql+asyncpg://kachi:kachi_password@localhost:5432/kachi REDIS_URL=redis://localhost:6379/0 $(MAKE) run-ingest &
	@DATABASE_URL=postgresql+asyncpg://kachi:kachi_password@localhost:5432/kachi REDIS_URL=redis://localhost:6379/0 $(MAKE) run-dashboard &
	@$(MAKE) run-frontend &
	@echo "All services started! Press Ctrl+C to stop."
	@trap 'echo "🛑 Stopping services..."; docker compose stop postgres redis; exit 0' INT; wait

# Database operations
db-migrate:
	uv run alembic upgrade head

db-reset:
	uv run alembic downgrade base
	uv run alembic upgrade head

# Cleanup
clean:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Docker operations
docker-build:
	docker build -t kachi-billing .

docker-run:
	docker compose up -d

docker-stop:
	docker compose down

# Stop development environment
dev-stop:
	@echo "🛑 Stopping development environment..."
	@docker compose stop postgres redis
	@echo "✅ Development environment stopped"

# Production deployment
deploy-staging:
	@echo "Deploying to staging environment..."
	# Add staging deployment commands here

deploy-production:
	@echo "Deploying to production environment..."
	# Add production deployment commands here

# Documentation
docs-build:
	uv run mkdocs build

docs-serve:
	uv run mkdocs serve

# Monitoring and health checks
health-check:
	curl -f http://localhost:8001/health || exit 1
	curl -f http://localhost:8002/health || exit 1

# Load testing
load-test:
	uv run locust -f tests/load_test.py --host=http://localhost:8001

# Security scanning
security-scan:
	uv run bandit -r src/
	uv run safety check

# Dependency management
deps-update:
	uv lock --upgrade

deps-audit:
	uv run pip-audit

# Git hooks and pre-commit
pre-commit:
	uv run pre-commit run --all-files

# CI/CD helpers
ci-test: test-fast quality-check
	@echo "CI tests completed successfully!"

ci-full: test quality-check security-scan
	@echo "Full CI pipeline completed successfully!"
