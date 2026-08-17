.PHONY: help install dev build test lint format clean docker-up docker-down docker-logs migrate

help:
	@echo "AI Support Platform - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install all dependencies (backend + frontend)"
	@echo "  dev              Start development environment with Docker"
	@echo ""
	@echo "Backend:"
	@echo "  backend-install  Install backend dependencies"
	@echo "  backend-dev      Start backend development server"
	@echo "  backend-test     Run backend tests"
	@echo "  backend-lint     Run backend linting"
	@echo "  backend-format   Format backend code"
	@echo "  migrate          Run database migrations"
	@echo "  migrate-create   Create new migration"
	@echo ""
	@echo "Frontend:"
	@echo "  frontend-install Install frontend dependencies"
	@echo "  frontend-dev     Start frontend development server"
	@echo "  frontend-test    Run frontend tests"
	@echo "  frontend-lint    Run frontend linting"
	@echo "  frontend-format  Format frontend code"
	@echo "  frontend-build   Build frontend for production"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up        Start all services with Docker Compose"
	@echo "  docker-down      Stop all services"
	@echo "  docker-logs      View Docker logs"
	@echo "  docker-build     Build all Docker images"
	@echo ""
	@echo "Quality:"
	@echo "  test             Run all tests"
	@echo "  lint             Run all linting"
	@echo "  format           Format all code"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean            Clean build artifacts"

install: backend-install frontend-install

backend-install:
	cd backend && pip install -e ".[dev]"

frontend-install:
	cd frontend && npm ci

dev: docker-up

backend-dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-test:
	cd backend && pytest -v --cov=src --cov-report=term-missing

backend-lint:
	cd backend && ruff check src tests && black --check src tests && isort --check-only src tests && mypy src

backend-format:
	cd backend && ruff check --fix src tests && black src tests && isort src tests

migrate:
	cd backend && alembic upgrade head

migrate-create:
	@read -p "Migration message: " msg; \
	cd backend && alembic revision --autogenerate -m "$$msg"

frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm run test

frontend-lint:
	cd frontend && npm run lint

frontend-format:
	cd frontend && npm run format

frontend-build:
	cd frontend && npm run build

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

docker-logs:
	docker compose -f docker/docker-compose.yml logs -f

docker-build:
	docker compose -f docker/docker-compose.yml build

docker-restart:
	docker compose -f docker/docker-compose.yml restart

test: backend-test frontend-test

lint: backend-lint frontend-lint

format: backend-format frontend-format

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/uploads/* 2>/dev/null || true