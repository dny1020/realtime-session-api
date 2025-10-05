# Quick Start Guide

## Prerequisites
- Asterisk server with ARI enabled (external service)
- Docker and Docker Compose installed

## Setup in 5 Minutes

### 1. Configure Environment

```bash
# Copy environment file
cp .env.example .env

# Generate secrets
openssl rand -hex 32  # Copy this for SECRET_KEY
openssl rand -hex 24  # Copy this for POSTGRES_PASSWORD
```

Edit `.env`:
```env
SECRET_KEY=<paste-your-generated-secret>
POSTGRES_PASSWORD=<paste-your-db-password>

# Point to your Asterisk server
ARI_HTTP_URL=http://your-asterisk-ip:8088/ari
ARI_USERNAME=ariuser
ARI_PASSWORD=your_ari_password
ARI_APP=contactcenter

# Update database URL with your password
DATABASE_URL=postgresql://contact_center:<paste-your-db-password>@postgres:5432/contact_center_db
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Run Migrations

```bash
docker-compose run --rm api alembic upgrade head
```

### 4. Create User

```bash
docker-compose run --rm api python -m app.auth.create_user
```

Enter username and password when prompted.

### 5. Test API

```bash
# Get health status
curl http://localhost:8000/health

# Should show:
# {
#   "status": "ok",
#   "database": "ok",
#   "asterisk": "ok",
#   ...
# }
```

## Make Your First Call

### Get Token

```bash
curl -X POST http://localhost:8000/api/v2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"

# Returns:
# {
#   "access_token": "eyJhbGci...",
#   "token_type": "bearer"
# }
```

### Originate Call

```bash
TOKEN="your_access_token_here"

curl -X POST "http://localhost:8000/api/v2/interaction/+1234567890" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": "outbound-ivr",
    "extension": "s",
    "timeout": 30000,
    "caller_id": "Test Call"
  }'

# Returns:
# {
#   "success": true,
#   "call_id": "abc-123-...",
#   "status": "dialing",
#   ...
# }
```

### Check Call Status

```bash
CALL_ID="abc-123-..."

curl -X GET "http://localhost:8000/api/v2/status/$CALL_ID" \
  -H "Authorization: Bearer $TOKEN"

# Returns real-time status:
# {
#   "call_id": "abc-123-...",
#   "status": "answered",  # or "ringing", "completed", etc.
#   "answered_at": "2025-01-05T12:00:05Z",
#   "duration": 45,
#   ...
# }
```

## View API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Monitor Logs

```bash
# All logs
docker-compose logs -f

# API only
docker-compose logs -f api

# See real-time events
docker-compose logs -f api | grep "ARI Event"
```

## Common Commands

```bash
# Stop services
docker-compose down

# Restart API
docker-compose restart api

# View running services
docker-compose ps

# Enter API container
docker-compose exec api bash

# View database
docker-compose exec postgres psql -U contact_center contact_center_db

# Backup database
docker exec contactcenter_postgres pg_dump -U contact_center contact_center_db > backup.sql
```

## Troubleshooting

### Can't connect to Asterisk

Check logs:
```bash
docker-compose logs api | grep -i asterisk
```

Should see:
```
Connected to Asterisk ARI (HTTP + WebSocket)
WebSocket connected to ARI
```

If not:
1. Verify `ARI_HTTP_URL` in `.env`
2. Check Asterisk ARI is running: `asterisk -rx "ari show status"`
3. Test connectivity: `docker-compose exec api curl http://your-asterisk:8088/ari/applications`

### Database errors

```bash
# Check database is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres psql -U contact_center -l

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
docker-compose run --rm api alembic upgrade head
```

### Authentication fails

Make sure you created a user:
```bash
docker-compose run --rm api python -m app.auth.create_user
```

### Call status not updating

1. Check WebSocket connection in logs
2. Verify Stasis app is configured in Asterisk dialplan
3. Check database for call records:
```bash
docker-compose exec postgres psql -U contact_center contact_center_db -c "SELECT call_id, phone_number, status FROM calls ORDER BY created_at DESC LIMIT 5;"
```

## Production Deployment

See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for:
- SSL/HTTPS setup
- Reverse proxy configuration
- Security hardening
- Scaling strategies

## Need Help?

1. Check logs: `docker-compose logs -f`
2. Check health: `curl http://localhost:8000/health`
3. View API docs: http://localhost:8000/docs
4. Read full documentation in README.md
