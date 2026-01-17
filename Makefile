.PHONY: help install install-dev test test-unit test-integration test-cov lint format type-check clean build up down logs

# Default target
help:
	@echo "Agent Zero (L.A.B.) - Development Commands"
	@echo "==========================================="
	@echo ""
	@echo "Installation:"
	@echo "  make install           - Install project dependencies"
	@echo "  make install-dev       - Install project with development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run all tests"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make test-cov          - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint              - Run flake8 linter"
	@echo "  make format            - Format code with black"
	@echo "  make type-check        - Run mypy type checking"
	@echo "  make pre-commit        - Run pre-commit checks"
	@echo ""
	@echo "Docker:"
	@echo "  make build             - Build Docker images"
	@echo "  make up                - Start all services"
	@echo "  make down              - Stop all services"
	@echo "  make logs              - View Docker logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             - Remove Python artifacts"
	@echo ""

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Testing
test:
	pytest tests/ -v --tb=short

test-unit:
	pytest tests/ -v --tb=short -m "not integration"

test-integration:
	pytest tests/ -v --tb=short -m "integration"

test-cov:
	pytest tests/ -v --tb=short --cov=src --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

# Code Quality
lint:
	flake8 src tests --max-line-length=100 --ignore=E501,W503,E203

format:
	black src tests --line-length=100
	isort src tests --profile=black

type-check:
	mypy src --ignore-missing-imports

pre-commit:
	pre-commit run --all-files

# Docker
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f app-agent

logs-all:
	docker-compose logs -f

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	find . -type f -name ".coverage" -delete
	@echo "Cleaned up Python artifacts"

# Development helpers
dev-shell:
	docker-compose exec app-agent /bin/bash

dev-test:
	docker-compose exec app-agent pytest tests/ -v --tb=short

dev-format:
	docker-compose exec app-agent black src tests --line-length=100
