.PHONY: help dev test build lint clean docker-up docker-down backend-dev frontend-dev

help:
	@echo "PageLens Development Makefile"
	@echo "=============================="
	@echo "make dev         - Run backend and frontend locally in parallel"
	@echo "make test        - Run backend and frontend test suites"
	@echo "make build       - Build docker images and frontend distribution"
	@echo "make lint        - Run linting and type checks"
	@echo "make docker-up   - Start services via docker-compose"
	@echo "make docker-down - Stop docker-compose services"
	@echo "make clean       - Clean temporary build and cache files"

dev:
	@echo "Starting backend and frontend in development mode..."
	docker compose up --build

backend-dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && npm run dev

test:
	@echo "Running backend test suite with coverage..."
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing
	@echo "Running frontend test suite..."
	cd frontend && npm test -- --run

build:
	@echo "Building frontend production bundle..."
	cd frontend && npm run build
	@echo "Building Docker images..."
	docker compose build

lint:
	@echo "Checking frontend types and linting..."
	cd frontend && npm run lint
	@echo "Checking backend syntax and imports..."
	cd backend && python -m py_compile app/main.py

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf backend/.pytest_cache backend/__pycache__ frontend/dist frontend/node_modules/.vite
