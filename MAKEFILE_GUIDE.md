# Makefile Guide

Quick reference for all Makefile commands.

## Quick Start

```bash
# First time setup
make quick-start

# Daily development
make up          # Start services
make logs        # View logs
make test        # Run tests
make down        # Stop services
```

## Categories

### 🚀 Setup & Installation

```bash
make install      # Install Python dependencies
make install-dev  # Install dev dependencies
make env          # Create .env from example
make setup        # Complete initial setup
```

### 🐳 Docker Operations

```bash
make build        # Build Docker images
make up           # Start all services
make down         # Stop all services
make restart      # Restart services
make ps           # Show running containers
make logs         # Show all logs
make logs-api     # Show API logs only
make logs-db      # Show database logs
```

### 🗄️ Database Operations

```bash
make migrate                           # Run migrations
make migrate-create MSG="description"  # Create new migration
make migrate-down                      # Rollback last migration
make migrate-history                   # Show migration history
make db-shell                          # Open PostgreSQL shell
make db-backup                         # Backup database
make db-restore FILE="backup.sql"      # Restore database
```

### 👤 User Management

```bash
make user         # Create new user (interactive)
```

### 💻 Development

```bash
make dev          # Run API locally (no Docker)
make shell        # Open bash in container
make python-shell # Open Python shell in container
make format       # Format code with black
make lint         # Lint with flake8
make type-check   # Type check with mypy
make check        # Format + lint
```

### 🧪 Testing

```bash
make test         # Run tests
make test-cov     # Run tests with coverage
make test-watch   # Run tests in watch mode
```

### 🏥 Health & Status

```bash
make health       # Check API health
make status       # Alias for health
make ping         # Ping API root
make docs         # Open API documentation
```

### 🧹 Cleanup

```bash
make clean         # Clean temporary files
make clean-docker  # Remove Docker containers/volumes
make clean-all     # Clean everything
```

### 🚀 Production

```bash
make deploy-prod   # Deploy to production
```

### 📦 Docker Registry

```bash
make docker-login            # Login to GitHub Container Registry
make docker-push TAG=latest  # Push image to registry
make docker-pull TAG=latest  # Pull image from registry
```

### ⚡ Quick Commands

```bash
make quick-start  # Complete first-time setup
make full-reset   # Reset and restart everything
```

### ℹ️ Information

```bash
make help         # Show all commands
make version      # Show version info
make info         # Show project info
```

## Common Workflows

### First Time Setup

```bash
make quick-start
# This runs: env + up + migrate + user
```

### Daily Development

```bash
# Morning
make up
make logs

# Code changes
make test

# End of day
make down
```

### Database Changes

```bash
# Create migration
make migrate-create MSG="add new field"

# Apply migration
make migrate

# Rollback if needed
make migrate-down
```

### Testing Workflow

```bash
# Quick test
make test

# With coverage
make test-cov

# Watch mode
make test-watch
```

### Code Quality

```bash
# Format code
make format

# Check linting
make lint

# Type checking
make type-check

# All checks
make check
```

### Debugging

```bash
# View logs
make logs

# API logs only
make logs-api

# Open shell
make shell

# Check health
make health
```

### Production Deployment

```bash
# Build and deploy
make deploy-prod

# Or manual steps
make build
make up
make migrate
make user
```

### Cleanup

```bash
# Clean Python cache
make clean

# Remove Docker volumes
make clean-docker

# Full cleanup
make clean-all
```

## Tips

1. **Tab completion**: Most terminals support tab completion for make targets
2. **Parallel logs**: Use `make logs` then Ctrl+C to stop
3. **Specific service logs**: `make logs ARGS="api"`
4. **Custom commands**: Edit Makefile to add your own commands
5. **Help anytime**: Run `make help` to see all commands

## Environment Variables

Some commands use environment variables:

```bash
# Migration message
make migrate-create MSG="your message"

# Backup file
make db-restore FILE="backup.sql"

# Docker tag
make docker-push TAG="v1.0.0"

# Specific service logs
make logs ARGS="postgres"
```

## Troubleshooting

### Command not found
Make sure you're in the project root directory.

### Permission denied
Run with appropriate permissions or check Docker permissions.

### Service not starting
Check logs with `make logs` and verify .env configuration.

### Database connection error
Ensure PostgreSQL is running: `make ps`

## Quick Reference Card

```
Setup:     make quick-start
Start:     make up
Stop:      make down
Logs:      make logs
Test:      make test
Health:    make health
Shell:     make shell
Migrate:   make migrate
User:      make user
Clean:     make clean
Help:      make help
```

## Examples

```bash
# Complete first-time setup
make quick-start

# Start development
make up
make logs

# Run tests
make test

# Create migration
make migrate-create MSG="add phone_verified field"

# Apply migration
make migrate

# Create user
make user

# Check health
make health

# Stop
make down

# Full reset
make full-reset
```
