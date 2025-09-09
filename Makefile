# MakeMyRecipe Development Makefile

.PHONY: help install dev-install test test-unit test-integration lint format clean run

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  dev-install  - Install development dependencies"
	@echo "  test         - Run all tests"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  lint         - Run linting (flake8, mypy)"
	@echo "  format       - Format code (black, isort)"
	@echo "  clean        - Clean up temporary files"
	@echo "  run          - Run the development server"

# Installation
install:
	uv sync

dev-install:
	uv sync --extra dev

# Testing
test:
	uv run pytest

test-unit:
	uv run pytest tests/unit/

test-integration:
	uv run pytest tests/integration/

test-cov:
	uv run pytest --cov=src/makemyrecipe --cov-report=html --cov-report=term

# Code quality
lint:
	uv run flake8 src/ tests/
	uv run mypy src/

format:
	uv run black src/ tests/
	uv run isort src/ tests/

format-check:
	uv run black --check src/ tests/
	uv run isort --check-only src/ tests/

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

# Development server
run:
	uv run python -m makemyrecipe.api.main

# Database operations (for future use)
db-init:
	@echo "Database initialization will be implemented in future phases"

db-migrate:
	@echo "Database migration will be implemented in future phases"