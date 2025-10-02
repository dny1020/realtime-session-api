#!/bin/bash

##############################################################################
# Contact Center API - Quick Deployment Script
# 
# This script helps with the initial deployment to a VPS
# 
# Usage: ./deploy.sh [environment]
# Example: ./deploy.sh production
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    log_error "Please do not run this script as root"
    exit 1
fi

# Banner
echo "========================================"
echo "  Contact Center API Deployment"
echo "========================================"
echo ""

# Check prerequisites
log_info "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker first."
    exit 1
fi
log_success "Docker found: $(docker --version)"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
log_success "Docker Compose found: $(docker-compose --version)"

# Check if .env exists
if [ ! -f .env ]; then
    log_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        log_warning "Please edit .env file with your configuration before continuing."
        log_warning "Run: vim .env"
        exit 1
    else
        log_error ".env.example not found. Cannot proceed."
        exit 1
    fi
fi

# Validate critical env vars
log_info "Validating environment configuration..."

# Source .env
set -a
source .env
set +a

# Check for placeholder values
ERRORS=0

if [ "$SECRET_KEY" == "CHANGE_ME_STRONG_HEX_64" ] || [ "$SECRET_KEY" == "your-secret-key-change-in-production" ]; then
    log_error "SECRET_KEY is still using default value. Please generate a strong key."
    ERRORS=$((ERRORS + 1))
fi

if [[ "$POSTGRES_PASSWORD" == *"CHANGE_ME"* ]]; then
    log_error "POSTGRES_PASSWORD is still using default value."
    ERRORS=$((ERRORS + 1))
fi

if [[ "$ARI_PASSWORD" == *"CHANGE_ME"* ]]; then
    log_error "ARI_PASSWORD is still using default value."
    ERRORS=$((ERRORS + 1))
fi

if [ "$DEBUG" == "true" ]; then
    log_warning "DEBUG is set to true. Consider setting to false for production."
fi

if [ "$DOCS_ENABLED" != "false" ]; then
    log_warning "DOCS_ENABLED is not false. Consider disabling docs in production."
fi

if [ $ERRORS -gt 0 ]; then
    log_error "Found $ERRORS configuration error(s). Please fix before deploying."
    exit 1
fi

log_success "Environment configuration validated"

# Create necessary directories
log_info "Creating necessary directories..."
mkdir -p logs uploads audio traefik/letsencrypt
chmod 700 traefik/letsencrypt
chmod 755 logs uploads audio
log_success "Directories created"

# Ask for confirmation
echo ""
log_warning "You are about to deploy the Contact Center API"
log_info "API Host: $API_HOST"
log_info "Database: $POSTGRES_DB"
log_info "Asterisk: $ARI_HTTP_URL"
echo ""
read -p "Do you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Deployment cancelled"
    exit 0
fi

# Build images
log_info "Building Docker images..."
docker-compose build api
log_success "Images built successfully"

# Start database first
log_info "Starting PostgreSQL..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
log_info "Waiting for PostgreSQL to be ready..."
sleep 10

# Check if database is healthy
if docker-compose exec -T postgres pg_isready -U "$POSTGRES_USER" &> /dev/null; then
    log_success "PostgreSQL is ready"
else
    log_error "PostgreSQL is not ready. Check logs with: docker-compose logs postgres"
    exit 1
fi

# Run migrations
log_info "Running database migrations..."
docker-compose run --rm api alembic upgrade head
log_success "Migrations completed"

# Check if we need to create first user
log_info "Checking for existing users..."
USER_COUNT=$(docker-compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")

if [ "$USER_COUNT" -eq 0 ]; then
    log_warning "No users found in database"
    log_info "You can create a user manually later with:"
    echo "  docker-compose run --rm api python -m app.auth.create_user"
fi

# Start all services
log_info "Starting all services..."
docker-compose up -d

# Wait for services to start
log_info "Waiting for services to start..."
sleep 15

# Check service health
log_info "Checking service health..."

# Check if all containers are running
RUNNING=$(docker-compose ps --services --filter "status=running" | wc -l)
TOTAL=$(docker-compose ps --services | wc -l)

if [ "$RUNNING" -eq "$TOTAL" ]; then
    log_success "All services are running ($RUNNING/$TOTAL)"
else
    log_warning "Some services are not running ($RUNNING/$TOTAL)"
    log_info "Check status with: docker-compose ps"
fi

# Test health endpoint
log_info "Testing health endpoint..."
if [ -n "$API_HOST" ]; then
    HEALTH_URL="http://localhost:8000/health"
    
    # Try to access health endpoint
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        log_success "Health endpoint is responding"
        
        # Show health status
        HEALTH_RESPONSE=$(curl -s "$HEALTH_URL")
        echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    else
        log_warning "Health endpoint not responding yet. Give it a few more seconds..."
        log_info "Try: curl http://localhost:8000/health"
    fi
fi

# Display summary
echo ""
echo "========================================"
echo "  Deployment Summary"
echo "========================================"
log_success "Deployment completed!"
echo ""
log_info "Services Status:"
docker-compose ps
echo ""
log_info "View logs:"
echo "  docker-compose logs -f"
echo ""
log_info "Useful commands:"
echo "  docker-compose ps              # Check service status"
echo "  docker-compose logs -f api     # View API logs"
echo "  docker-compose restart api     # Restart API"
echo "  docker-compose down            # Stop all services"
echo ""

if [ -n "$API_HOST" ]; then
    log_info "Access your API at:"
    echo "  https://$API_HOST"
    echo "  https://$API_HOST/health"
    echo "  https://$API_HOST/docs (if enabled)"
fi

echo ""
log_warning "Next steps:"
echo "  1. Create your first user if not done yet"
echo "  2. Test authentication: curl -X POST https://$API_HOST/api/v2/token ..."
echo "  3. Monitor logs for any errors"
echo "  4. Configure monitoring alerts"
echo "  5. Setup automated backups"
echo ""
log_info "For detailed instructions, see docs/DEPLOYMENT_GUIDE.md"
echo ""
