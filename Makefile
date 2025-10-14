.PHONY: help install test clean build up down logs shell db-shell migrate user health docs dev stop restart ps

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
DOCKER_COMPOSE := docker-compose
DOCKER := docker
APP_NAME := contact-center-api

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ Help

help: ## Display this help message
	@echo "$(GREEN)Ari API - Makefile Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make $(YELLOW)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup & Installation

install: ## Install Python dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: ## Install development dependencies
	@echo "$(GREEN)Installing dev dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov black flake8 mypy
	@echo "$(GREEN)✓ Dev dependencies installed$(NC)"

env: ## Create .env file from example
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creating .env file...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env created. Please edit with your settings$(NC)"; \
	else \
		echo "$(RED)✗ .env already exists$(NC)"; \
	fi

setup: env install ## Complete initial setup
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Run: make up"
	@echo "  3. Run: make migrate"
	@echo "  4. Run: make user"

##@ Docker Operations

build: ## Build Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Images built$(NC)"

up: ## Start all services
	@echo "$(GREEN)Starting services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@make ps

down: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Services stopped$(NC)"

stop: down ## Alias for down

restart: ## Restart all services
	@echo "$(YELLOW)Restarting services...$(NC)"
	$(DOCKER_COMPOSE) restart
	@echo "$(GREEN)✓ Services restarted$(NC)"

ps: ## Show running containers
	@$(DOCKER_COMPOSE) ps

logs: ## Show logs (use ARGS="api" for specific service)
	$(DOCKER_COMPOSE) logs -f $(ARGS)

logs-api: ## Show API logs only
	$(DOCKER_COMPOSE) logs -f api

logs-db: ## Show database logs only
	$(DOCKER_COMPOSE) logs -f postgres

##@ Database Operations

migrate: ## Run database migrations
	@echo "$(GREEN)Running migrations...$(NC)"
	$(DOCKER_COMPOSE) run --rm api alembic upgrade head
	@echo "$(GREEN)✓ Migrations complete$(NC)"

migrate-create: ## Create new migration (use MSG="message")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)✗ Please provide MSG=\"migration message\"$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Creating migration: $(MSG)$(NC)"
	$(DOCKER_COMPOSE) run --rm api alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)✓ Migration created$(NC)"

migrate-down: ## Rollback last migration
	@echo "$(YELLOW)Rolling back migration...$(NC)"
	$(DOCKER_COMPOSE) run --rm api alembic downgrade -1
	@echo "$(GREEN)✓ Migration rolled back$(NC)"

migrate-history: ## Show migration history
	$(DOCKER_COMPOSE) run --rm api alembic history

db-shell: ## Open PostgreSQL shell
	$(DOCKER_COMPOSE) exec postgres psql -U contact_center contact_center_db

db-backup: ## Backup database
	@echo "$(GREEN)Backing up database...$(NC)"
	@mkdir -p backups
	$(DOCKER_COMPOSE) exec postgres pg_dump -U contact_center contact_center_db > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Database backed up to backups/$(NC)"

db-restore: ## Restore database (use FILE="backup.sql")
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)✗ Please provide FILE=\"backup.sql\"$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restoring database from $(FILE)...$(NC)"
	$(DOCKER_COMPOSE) exec -T postgres psql -U contact_center contact_center_db < $(FILE)
	@echo "$(GREEN)✓ Database restored$(NC)"

##@ User Management

user: ## Create new user
	@echo "$(GREEN)Creating new user...$(NC)"
	$(DOCKER_COMPOSE) run --rm api python -m app.auth.create_user

##@ Development

dev: ## Run API in development mode locally (no Docker)
	@echo "$(GREEN)Starting development server...$(NC)"
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

shell: ## Open shell in API container
	$(DOCKER_COMPOSE) exec api bash

shell-api: shell ## Alias for shell

python-shell: ## Open Python shell in API container
	$(DOCKER_COMPOSE) exec api python

format: ## Format code with black
	@echo "$(GREEN)Formatting code...$(NC)"
	black app/ config/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Lint code with flake8
	@echo "$(GREEN)Linting code...$(NC)"
	flake8 app/ config/ tests/ --max-line-length=120 --exclude=venv,__pycache__
	@echo "$(GREEN)✓ Linting complete$(NC)"

type-check: ## Type check with mypy
	@echo "$(GREEN)Type checking...$(NC)"
	mypy app/ config/ --ignore-missing-imports
	@echo "$(GREEN)✓ Type check complete$(NC)"

check: format lint ## Format and lint code

##@ Testing

test: ## Run tests
	@echo "$(GREEN)Running tests...$(NC)"
	PYTHONPATH=. DISABLE_DB=true SECRET_KEY=test pytest tests/ -v
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-cov: ## Run tests with coverage
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	@if command -v pytest-cov >/dev/null 2>&1 || python3 -m pytest --cov >/dev/null 2>&1; then \
		PYTHONPATH=. DISABLE_DB=true SECRET_KEY=test pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing; \
		echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"; \
	else \
		echo "$(YELLOW)pytest-cov not installed. Installing...$(NC)"; \
		pip3 install pytest-cov; \
		PYTHONPATH=. DISABLE_DB=true SECRET_KEY=test pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing; \
		echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"; \
	fi

test-watch: ## Run tests in watch mode
	@echo "$(GREEN)Running tests in watch mode...$(NC)"
	PYTHONPATH=. DISABLE_DB=true SECRET_KEY=test pytest-watch tests/

##@ Health & Status

health: ## Check API health
	@echo "$(GREEN)Checking API health...$(NC)"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "$(RED)✗ API not responding$(NC)"

status: health ## Alias for health

ping: ## Ping API
	@curl -s http://localhost:8000/ | python -m json.tool || echo "$(RED)✗ API not responding$(NC)"

docs: ## Open API documentation
	@echo "$(GREEN)Opening API docs...$(NC)"
	@echo "$(YELLOW)Swagger UI:$(NC) http://localhost:8000/docs"
	@echo "$(YELLOW)ReDoc:$(NC) http://localhost:8000/redoc"
	@command -v open >/dev/null 2>&1 && open http://localhost:8000/docs || \
	command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:8000/docs || \
	echo "$(YELLOW)Please open http://localhost:8000/docs in your browser$(NC)"

##@ Cleanup

clean: ## Clean up temporary files
	@echo "$(GREEN)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-docker: ## Remove Docker containers and volumes
	@echo "$(YELLOW)Removing Docker containers and volumes...$(NC)"
	$(DOCKER_COMPOSE) down -v
	@echo "$(GREEN)✓ Docker cleanup complete$(NC)"

clean-all: clean clean-docker ## Clean everything
	@echo "$(GREEN)✓ All cleaned$(NC)"

##@ Production

deploy-prod: ## Deploy to production
	@echo "$(YELLOW)Deploying to production...$(NC)"
	@echo "$(RED)Make sure you have:$(NC)"
	@echo "  1. Updated .env with production values"
	@echo "  2. Set strong SECRET_KEY"
	@echo "  3. Configured DATABASE_URL"
	@echo "  4. Set ARI_HTTP_URL to production Asterisk"
	@echo ""
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	$(DOCKER_COMPOSE) -f docker-compose.yml up -d --build
	@make migrate
	@echo "$(GREEN)✓ Production deployment complete$(NC)"

##@ Docker Registry

docker-login: ## Login to GitHub Container Registry
	@echo "$(GREEN)Logging in to GitHub Container Registry...$(NC)"
	@echo "$(YELLOW)Enter your GitHub Personal Access Token:$(NC)"
	@read -s token && echo $$token | docker login ghcr.io -u $(USER) --password-stdin
	@echo "$(GREEN)✓ Logged in$(NC)"

docker-push: ## Push image to registry (use TAG=latest)
	@if [ -z "$(TAG)" ]; then \
		TAG="latest"; \
	fi
	@echo "$(GREEN)Pushing image with tag: $(TAG)$(NC)"
	$(DOCKER) tag $(APP_NAME):$(TAG) ghcr.io/$(USER)/$(APP_NAME):$(TAG)
	$(DOCKER) push ghcr.io/$(USER)/$(APP_NAME):$(TAG)
	@echo "$(GREEN)✓ Image pushed$(NC)"

docker-pull: ## Pull image from registry (use TAG=latest)
	@if [ -z "$(TAG)" ]; then \
		TAG="latest"; \
	fi
	@echo "$(GREEN)Pulling image with tag: $(TAG)$(NC)"
	$(DOCKER) pull ghcr.io/$(USER)/$(APP_NAME):$(TAG)
	@echo "$(GREEN)✓ Image pulled$(NC)"

##@ Quick Commands

quick-start: env up migrate user ## Quick start for first time (setup + start)
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║  ✓ Quick Start Complete!              ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)API is running at:$(NC) http://localhost:8000"
	@echo "$(YELLOW)API docs at:$(NC) http://localhost:8000/docs"
	@echo "$(YELLOW)Health check:$(NC) make health"
	@echo "$(YELLOW)View logs:$(NC) make logs"
	@echo ""

full-reset: clean-docker quick-start ## Full reset and restart
	@echo "$(GREEN)✓ Full reset complete$(NC)"

##@ Information

version: ## Show version information
	@echo "$(GREEN)Contact Center API$(NC)"
	@echo "Version: 1.0.0"
	@$(PYTHON) --version
	@$(DOCKER) --version
	@$(DOCKER_COMPOSE) --version

info: ## Show project information
	@echo "$(GREEN)╔════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║     API Realtime - Info         ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Services:$(NC)"
	@make ps
	@echo ""
	@echo "$(YELLOW)API URL:$(NC) http://localhost:8000"
	@echo "$(YELLOW)API Docs:$(NC) http://localhost:8000/docs"
	@echo "$(YELLOW)Database:$(NC) PostgreSQL on port 5432"
	@echo ""
	@echo "$(YELLOW)Quick commands:$(NC)"
	@echo "  make help      - Show all commands"
	@echo "  make health    - Check API health"
	@echo "  make logs      - View logs"
	@echo "  make shell     - Open container shell"
