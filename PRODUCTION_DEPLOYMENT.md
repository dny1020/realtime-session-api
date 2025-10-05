# Production Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL database (or use the included docker-compose)
- Asterisk server with ARI enabled (deployed separately)
- SSL certificate (for production, use reverse proxy like Nginx/Traefik)

## 1. Configuration

### Create .env file

```bash
cp .env.example .env
```

### Generate secure secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate database password
openssl rand -hex 24

# Generate ARI password
openssl rand -hex 16
```

### Update .env with your values

```env
# REQUIRED: Change these values
SECRET_KEY=<your-generated-secret-key>
POSTGRES_PASSWORD=<your-generated-db-password>
ARI_HTTP_URL=http://your-asterisk-server:8088/ari
ARI_USERNAME=ariuser
ARI_PASSWORD=<your-ari-password>

# Database connection
DATABASE_URL=postgresql://contact_center:<your-generated-db-password>@postgres:5432/contact_center_db

# Production settings
DEBUG=false
LOG_LEVEL=INFO
DOCS_ENABLED=false  # Disable in production or protect with authentication
ALLOWED_ORIGINS=https://yourdomain.com  # Your frontend domain
```

## 2. Configure Asterisk ARI

On your Asterisk server, configure ARI in `/etc/asterisk/ari.conf`:

```ini
[general]
enabled = yes
pretty = yes

[ariuser]
type = user
read_only = no
password = <your-ari-password>
```

Create a Stasis application in `/etc/asterisk/extensions.conf`:

```ini
[outbound-ivr]
exten => _X.,1,NoOp(Outbound call to ${EXTEN})
 same => n,Answer()
 same => n,Stasis(contactcenter)
 same => n,Playback(hello-world)
 same => n,Hangup()
```

Restart Asterisk:

```bash
asterisk -rx "module reload res_ari"
asterisk -rx "dialplan reload"
```

## 3. Database Setup

### Run migrations

```bash
# Using docker-compose
docker-compose run --rm api alembic upgrade head

# Or locally
alembic upgrade head
```

### Create initial user

```bash
# Using docker-compose
docker-compose run --rm api python -m app.auth.create_user

# Or locally
python -m app.auth.create_user
```

Follow prompts to create a user with username and password.

## 4. Deploy with Docker Compose

### Start services

```bash
# Production mode
docker-compose up -d

# Check logs
docker-compose logs -f api

# Check health
curl http://localhost:8000/health
```

### Verify services

```bash
# Check API health
curl http://localhost:8000/health

# Should return:
# {
#   "status": "ok",
#   "version": "1.0.0",
#   "database": "ok",
#   "asterisk": "ok",
#   "services": {
#     "api": "running",
#     "database": "ok",
#     "asterisk_ari": "ok"
#   }
# }
```

## 5. Test the API

### Get JWT token

```bash
curl -X POST http://localhost:8000/api/v2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Make a test call

```bash
TOKEN="your_token_here"

curl -X POST http://localhost:8000/api/v2/interaction/+1234567890 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": "outbound-ivr",
    "extension": "s",
    "priority": 1,
    "timeout": 30000,
    "caller_id": "Test Call"
  }'
```

Response:
```json
{
  "success": true,
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "+1234567890",
  "message": "Call originated successfully",
  "channel": "550e8400-e29b-41d4-a716-446655440000",
  "status": "dialing",
  "created_at": "2025-01-05T12:00:00Z"
}
```

### Check call status

```bash
CALL_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X GET http://localhost:8000/api/v2/status/$CALL_ID \
  -H "Authorization: Bearer $TOKEN"
```

## 6. Production Deployment with Reverse Proxy

### Using Nginx

Create `/etc/nginx/sites-available/contactcenter`:

```nginx
upstream contactcenter_api {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://contactcenter_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Protect docs in production
    location /docs {
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://contactcenter_api;
    }
}
```

Enable site:
```bash
ln -s /etc/nginx/sites-available/contactcenter /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Using Traefik

Create `docker-compose.prod.yml`:

```yaml
version: "3.8"

services:
  api:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls=true"
      - "traefik.http.routers.api.tls.certresolver=le"
      - "traefik.http.services.api.loadbalancer.server.port=8000"

  traefik:
    image: traefik:v2.11
    command:
      - --providers.docker=true
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.le.acme.httpchallenge=true
      - --certificatesresolvers.le.acme.email=you@example.com
      - --certificatesresolvers.le.acme.storage=/letsencrypt/acme.json
    ports:
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt
```

Deploy:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 7. Monitoring and Logs

### View logs

```bash
# API logs
docker-compose logs -f api

# All services
docker-compose logs -f
```

### Health check endpoint

```bash
curl http://localhost:8000/health
```

### Log to file (production)

Update `docker-compose.yml`:

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 8. Backup and Maintenance

### Backup database

```bash
docker exec contactcenter_postgres pg_dump -U contact_center contact_center_db > backup.sql
```

### Restore database

```bash
docker exec -i contactcenter_postgres psql -U contact_center contact_center_db < backup.sql
```

### Update application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose build api
docker-compose up -d api

# Run migrations if needed
docker-compose run --rm api alembic upgrade head
```

## 9. Security Checklist

- [ ] Changed SECRET_KEY from default
- [ ] Changed all passwords (DB, ARI)
- [ ] Set ALLOWED_ORIGINS to specific domains
- [ ] Disabled or protected /docs endpoint
- [ ] Using HTTPS with valid SSL certificate
- [ ] Asterisk ARI not publicly accessible
- [ ] Database not publicly accessible
- [ ] Regular backups configured
- [ ] Logs monitoring configured
- [ ] Rate limiting configured (consider external solution for production)

## 10. Scaling

### Horizontal scaling

```yaml
services:
  api:
    deploy:
      replicas: 3
```

**Note**: The built-in rate limiter is in-memory only. For multi-instance deployments, use:
- Redis-backed rate limiting
- API Gateway (AWS API Gateway, Kong, etc.)
- Reverse proxy rate limiting (Nginx, Traefik)

### Database connection pooling

Update settings.py for production:

```python
# Increase connection pool
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

## Troubleshooting

### API can't connect to Asterisk

1. Check ARI_HTTP_URL is correct
2. Verify Asterisk ARI is enabled: `asterisk -rx "ari show status"`
3. Check network connectivity: `docker exec contactcenter_api curl http://asterisk-server:8088/ari/applications`
4. Verify ARI credentials match

### Database connection errors

1. Check DATABASE_URL is correct
2. Verify PostgreSQL is running: `docker-compose ps postgres`
3. Check database exists: `docker exec contactcenter_postgres psql -U contact_center -l`

### WebSocket connection issues

1. Check Asterisk ARI WebSocket is accessible
2. Verify firewall allows WebSocket connections
3. Check logs: `docker-compose logs -f api | grep WebSocket`

### Call status not updating

1. Verify WebSocket connection is established (check logs)
2. Confirm Stasis application is running in Asterisk dialplan
3. Check database for call records: `docker exec contactcenter_postgres psql -U contact_center -d contact_center_db -c "SELECT * FROM calls;"`

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
