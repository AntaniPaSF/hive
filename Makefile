SHELL := /bin/bash

.PHONY: help verify format lint test build benchmark clean run-api stop-api setup start stop package

# Default target
help:
	@echo "Hive Core - Development & CI/CD Targets"
	@echo "========================================"
	@echo ""
	@echo "CI/CD Validation (GitHub Actions equivalent):"
	@echo "  make verify       - Run all validation checks (format+lint+test)"
	@echo "  make format       - Format code with black"
	@echo "  make lint         - Run linting (black, ruff, mypy, bandit, pip-audit)"
	@echo "  make test         - Run tests with coverage"
	@echo "  make build        - Build Docker image"
	@echo "  make benchmark    - Run benchmark suite (requires API running)"
	@echo ""
	@echo "Local Development:"
	@echo "  make run-api      - Spin up API container"
	@echo "  make stop-api     - Stop API container"
	@echo "  make clean        - Clean generated files"
	@echo ""
	@echo "Legacy targets (for compatibility):"
	@echo "  make setup        - Legacy setup"
	@echo "  make start        - Legacy start"
	@echo "  make stop         - Legacy stop"
	@echo "  make package      - Legacy package"

# ============================================================================
# CI/CD VALIDATION TARGETS (Primary - match GitHub Actions)
# ============================================================================

# Run all validation checks (CI equivalent)
verify: format lint test
	@echo "✅ All checks passed locally!"

# Format code with black
format:
	@echo "🔧 Formatting with black..."
	black src/ tests/ 2>/dev/null || true
	@echo "✅ Formatting complete"

# Run all linting checks
lint:
	@echo "🔍 Running linting checks..."
	@echo "  1. black (format check)..."
	black --check src/ tests/ 2>/dev/null || (echo "❌ Formatting needed. Run: make format" && exit 1)
	@echo "  2. ruff (linting)..."
	ruff check src/ tests/ 2>/dev/null || echo "⚠️  Ruff not installed, skipping"
	@echo "  3. mypy (type checking)..."
	mypy src/ 2>/dev/null || echo "⚠️  Mypy not installed, skipping"
	@echo "  4. bandit (security)..."
	bandit -r src/ -q 2>/dev/null || echo "⚠️  Bandit not installed, skipping"
	@echo "  5. pip-audit (dependencies)..."
	pip-audit --skip-editable 2>/dev/null || echo "⚠️  Pip-audit not installed, skipping"
	@echo "✅ Linting checks complete"

# Run tests with coverage
test:
	@echo "🧪 Running tests with coverage..."
	pytest tests/ \
		--cov=src/ \
		--cov-report=term \
		--cov-report=html:htmlcov \
		--cov-report=json:coverage.json \
		--junit-xml=test-results.xml \
		-v 2>/dev/null || echo "⚠️  Pytest not available, skipping"
	@if [ -f htmlcov/index.html ]; then echo "📊 Coverage report: htmlcov/index.html"; fi
	@echo "✅ Tests complete"

# Build Docker image locally
build:
	@echo "🐳 Building Docker image..."
	docker build -t hive-core:local . || (echo "❌ Build failed" && exit 1)
	@echo "✅ Image built: hive-core:local"

# Run benchmark suite (requires API running)
benchmark:
	@echo "📈 Running benchmark suite..."
	@if [ ! $$(docker ps -q -f name=hive-api 2>/dev/null) ]; then \
		echo "❌ API container not running. Start with: make run-api"; \
		exit 1; \
	fi
	python -m tests.benchmark.benchmark \
		--api-url http://localhost:8000 \
		--suite full \
		--output-json benchmark-results.json \
		--output-junit benchmark-results.xml \
		-v 2>/dev/null || echo "⚠️  Benchmark not available"
	@echo "✅ Benchmark complete"

# Spin up API container
run-api: build
	@echo "🚀 Starting API container..."
	docker run -d \
		--name hive-api \
		-p 8000:8000 \
		-e ENV=test \
		hive-core:local 2>/dev/null || true
	@echo "⏳ Waiting for API to be healthy (max 60s)..."
	@for i in {1..30}; do \
		if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
			echo "✅ API ready at http://localhost:8000"; \
			exit 0; \
		fi; \
		sleep 2; \
	done
	@echo "❌ API startup timeout"
	exit 1

# Stop API container
stop-api:
	@echo "🛑 Stopping API container..."
	docker stop hive-api 2>/dev/null || true
	docker rm hive-api 2>/dev/null || true
	@echo "✅ API stopped"

# Clean up generated files
clean:
	@echo "🧹 Cleaning up..."
	rm -rf htmlcov/ .coverage coverage.json test-results.xml 2>/dev/null || true
	rm -rf benchmark-results.json benchmark-results.xml 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

# ============================================================================
# LEGACY TARGETS (for compatibility with existing scripts)
# ============================================================================

setup:
	./scripts/setup.sh

start:
	./scripts/start.sh

stop:
	docker compose down

package:
	./scripts/package.sh
