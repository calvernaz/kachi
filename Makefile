# Makefile for Kachi Billing System

.PHONY: help install test test-unit test-integration test-performance test-property test-fast test-coverage lint format type-check quality-check clean dev-setup

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
	@echo "Development:"
	@echo "  clean            Clean up generated files"
	@echo "  run-ingest       Run ingestion API server"
	@echo "  run-dashboard    Run dashboard API server"
	@echo "  run-frontend     Run frontend development server"

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
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

type-check:
	uv run mypy src/kachi

quality-check: lint type-check
	@echo "All quality checks completed!"

# Development servers
run-ingest:
	uv run uvicorn kachi.apps.ingest_api.main:app --host 0.0.0.0 --port 8001 --reload

run-dashboard:
	uv run uvicorn kachi.apps.dashboard_api.main:app --host 0.0.0.0 --port 8002 --reload

run-frontend:
	cd frontend/dashboard && yarn dev

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
	docker-compose up -d

docker-stop:
	docker-compose down

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
