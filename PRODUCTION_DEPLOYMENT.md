# Production Deployment Guide

## Prerequisites

1. **Traefik Setup**: Ensure Traefik is running with the `traefik_net` network created
2. **Docker & Docker Compose**: Installed on the host
3. **Domain**: DNS configured to point to your server

## 1. Create Traefik Network

If not already created:

```bash
docker network create traefik_net
```

## 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Generate secure secrets
export SECRET_KEY=$(openssl rand -hex 32)
export POSTGRES_PASSWORD=$(openssl rand -hex 24)
export ARI_PASSWORD=$(openssl rand -hex 16)

# Edit .env file with your values
nano .env
```

### Required Changes in `.env`:

- `DOMAIN_NAME`: Your actual domain (e.g., `api.yourdomain.com`)
- `SECRET_KEY`: Generated secret key
- `POSTGRES_PASSWORD`: Generated database password
- `DATABASE_URL`: Update with the generated password
- `ARI_PASSWORD`: Generated ARI password
- `ARI_HTTP_URL`: Point to your Asterisk server
- `ALLOWED_ORIGINS`: Your frontend domain(s)
- `JWT_ISSUER` & `JWT_AUDIENCE`: Your domain URL

### Production Settings:

```env
DEBUG=false
DOCS_ENABLED=false
METRICS_ENABLED=true
LOG_LEVEL=INFO
```

## 3. Traefik Configuration

Ensure your Traefik configuration includes:

```yaml
# traefik.yml or docker-compose.yml
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

certificatesResolvers:
  myresolver:
    acme:
      email: your-email@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web
```

## 4. Build and Deploy

```bash
# Build the API image
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f api

# Verify health
curl https://api.yourdomain.com/health
```

## 5. Database Migration

```bash
# Run migrations (if using Alembic)
docker-compose exec api alembic upgrade head
```

## 6. Create Initial User

```bash
# Access the container
docker-compose exec api python

# Create user (adjust according to your user creation script)
# Or use your initialization script
```

## 7. Monitoring & Metrics

- **Metrics endpoint**: `https://api.yourdomain.com/metrics` (protected)
- **Health check**: `https://api.yourdomain.com/health`
- **Configure Prometheus** to scrape: `https://api.yourdomain.com/metrics`

### Prometheus Configuration:

```yaml
scrape_configs:
  - job_name: 'contactcenter-api'
    static_configs:
      - targets: ['api.yourdomain.com:443']
    scheme: https
    metrics_path: /metrics
```

## 8. Security Checklist

- [ ] All secrets generated with strong random values
- [ ] `.env` file has proper permissions (600)
- [ ] DOCS_ENABLED=false in production
- [ ] ALLOWED_ORIGINS restricted to actual domains
- [ ] PostgreSQL not exposed publicly (no ports)
- [ ] API only accessible through Traefik
- [ ] HTTPS enforced with valid certificates
- [ ] Rate limiting enabled
- [ ] Security headers configured

## 9. Backup Strategy

### Database Backup:

```bash
# Create backup
docker-compose exec postgres pg_dump -U contact_center contact_center_db > backup_$(date +%Y%m%d).sql

# Restore backup
docker-compose exec -T postgres psql -U contact_center contact_center_db < backup_20231017.sql
```

### Automated Backups:

Add to crontab:

```bash
0 2 * * * cd /path/to/realtime-session-api && docker-compose exec postgres pg_dump -U contact_center contact_center_db | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

## 10. Scaling Considerations

For high availability:

```yaml
# docker-compose.yml
api:
  deploy:
    replicas: 3
    update_config:
      parallelism: 1
      delay: 10s
```

## 11. Troubleshooting

### Check Service Status:

```bash
docker-compose ps
docker-compose logs api
docker-compose logs postgres
```

### Test Traefik Routing:

```bash
# Check if service is registered
docker-compose exec api curl -s http://localhost:8000/health

# Check from outside
curl -I https://api.yourdomain.com/health
```

### Database Connection:

```bash
# Test database connection
docker-compose exec api python -c "from app.database import engine; print(engine.connect())"
```

## 12. Maintenance

### Update Application:

```bash
# Pull latest changes
git pull

# Rebuild
docker-compose build

# Rolling update
docker-compose up -d --no-deps --build api
```

### View Resource Usage:

```bash
docker stats contactcenter_api contactcenter_postgres
```

## Network Architecture

```
Internet → Traefik (HTTPS) → API Container (internal) → PostgreSQL (internal)
                                     ↓
                                Asterisk (external/internal)
```

- **traefik_net**: External network for Traefik routing
- **internal**: Internal bridge network for DB communication (isolated)
- PostgreSQL: Only accessible from API container
- API: Only accessible through Traefik

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DOMAIN_NAME` | Yes | - | Domain for API (e.g., api.yourdomain.com) |
| `SECRET_KEY` | Yes | - | JWT signing key (use openssl rand -hex 32) |
| `DATABASE_URL` | Yes* | - | PostgreSQL connection string |
| `DISABLE_DB` | No | false | Set true for DB-less mode |
| `DOCS_ENABLED` | No | false | Enable /docs endpoint |
| `METRICS_ENABLED` | No | true | Enable /metrics endpoint |
| `ALLOWED_ORIGINS` | Yes | - | CORS allowed origins (comma-separated) |
| `ARI_HTTP_URL` | Yes | - | Asterisk ARI endpoint |

*Required unless DISABLE_DB=true

## Support & Logs

Logs are persisted in `./logs` directory. Monitor them for issues:

```bash
tail -f logs/app.log
```
