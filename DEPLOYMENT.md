# Production Deployment Guide

This guide covers deploying the Contact Center API to a production environment.

## Prerequisites

- Linux server (Ubuntu 20.04+ or Debian 11+ recommended)
- Docker & Docker Compose installed
- Domain name with DNS configured
- SSL certificate (Let's Encrypt recommended)
- External Asterisk server with ARI enabled
- PostgreSQL 15+ (can use Docker or external service)

## Quick Deployment Steps

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Create application user (optional)
sudo useradd -m -s /bin/bash appuser
sudo usermod -aG docker appuser
```

### 2. Clone Repository

```bash
# Clone from GitHub
git clone https://github.com/dny1020/api-contact-center.git
cd api-contact-center

# Or pull Docker image directly
docker pull ghcr.io/dny1020/api-contact-center:latest
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with production values
nano .env
```

**Critical `.env` settings:**

```env
# Security (MUST CHANGE!)
SECRET_KEY=<generate-64-character-random-hex>

# Database (PostgreSQL)
DATABASE_URL=postgresql://contact_center:STRONG_PASSWORD@postgres:5432/contact_center_db
POSTGRES_DB=contact_center_db
POSTGRES_USER=contact_center
POSTGRES_PASSWORD=STRONG_PASSWORD

# Asterisk ARI (external service)
ARI_HTTP_URL=http://your-asterisk-server:8088/ari
ARI_USERNAME=your_ari_username
ARI_PASSWORD=your_ari_password
ARI_APP=contactcenter

# Production settings
DEBUG=false
LOG_LEVEL=WARNING
DOCS_ENABLED=false  # Disable in production for security
ALLOWED_ORIGINS=https://yourdomain.com

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_ISSUER=yourdomain.com
JWT_AUDIENCE=api.yourdomain.com
```

**Generate strong SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Start Services

```bash
# Build and start containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

### 5. Database Migration

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create first admin user
docker-compose exec api python -m app.auth.create_user
# Follow prompts to create username/password
```

### 6. Verify Deployment

```bash
# Check health endpoint
curl http://localhost:8000/health

# Should return:
# {
#   "status": "ok",
#   "version": "1.0.0",
#   "database": "ok",
#   "asterisk": "ok"
# }
```

## SSL/TLS Configuration

### Option 1: Using Nginx as Reverse Proxy

**Install Nginx:**
```bash
sudo apt install nginx certbot python3-certbot-nginx
```

**Create Nginx config (`/etc/nginx/sites-available/api-contact-center`):**

```nginx
upstream api_backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL Configuration (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to FastAPI
    location / {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket support (if needed in future)
    location /ws {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;
}
```

**Enable site and get SSL certificate:**
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/api-contact-center /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Get SSL certificate
sudo certbot --nginx -d api.yourdomain.com

# Reload Nginx
sudo systemctl reload nginx
```

### Option 2: Using Traefik (Docker)

Add Traefik to `docker-compose.yml`:

```yaml
services:
  traefik:
    image: traefik:v2.10
    container_name: traefik
    command:
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"
    networks:
      - app-net

  api:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
```

## Database Backup

### Automated Backup Script

Create `/opt/backups/backup-api-db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/contact-center"
DATE=$(date +%Y%m%d_%H%M%S)
DB_CONTAINER="contactcenter_postgres"
DB_NAME="contact_center_db"
DB_USER="contact_center"
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
docker exec -t $DB_CONTAINER pg_dump -U $DB_USER $DB_NAME | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# Delete old backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: backup_$DATE.sql.gz"
```

**Schedule with cron:**
```bash
# Make executable
chmod +x /opt/backups/backup-api-db.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
# Add line:
0 2 * * * /opt/backups/backup-api-db.sh >> /var/log/backup-api.log 2>&1
```

### Restore from Backup

```bash
# Stop API
docker-compose stop api

# Restore database
gunzip < backup_20241012_020000.sql.gz | docker exec -i contactcenter_postgres psql -U contact_center contact_center_db

# Start API
docker-compose start api
```

## Monitoring

### Check Application Logs

```bash
# Real-time logs
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api

# With timestamps
docker-compose logs -t api
```

### Health Monitoring Script

Create `/opt/monitoring/health-check.sh`:

```bash
#!/bin/bash
API_URL="https://api.yourdomain.com/health"
ALERT_EMAIL="admin@yourdomain.com"

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ "$RESPONSE" != "200" ]; then
    echo "API health check failed! Status: $RESPONSE" | mail -s "API Alert" $ALERT_EMAIL
    exit 1
fi

echo "API health check passed"
```

**Schedule with cron (every 5 minutes):**
```bash
*/5 * * * * /opt/monitoring/health-check.sh
```

## Security Hardening

### Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (if using Nginx)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block direct access to API port (only via reverse proxy)
sudo ufw deny 8000/tcp

# Enable firewall
sudo ufw enable
```

### Docker Security

```bash
# Run Docker in rootless mode (optional)
# Follow: https://docs.docker.com/engine/security/rootless/

# Scan images for vulnerabilities
docker scan ghcr.io/dny1020/api-contact-center:latest
```

## Scaling

### Horizontal Scaling (Multiple Instances)

Update `docker-compose.yml`:

```yaml
api:
  deploy:
    replicas: 3
```

Add load balancer (Nginx example):

```nginx
upstream api_backend {
    least_conn;
    server api-1:8000;
    server api-2:8000;
    server api-3:8000;
}
```

### Vertical Scaling (Resource Limits)

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '1.0'
        memory: 1G
```

## Troubleshooting

### API won't start

```bash
# Check logs
docker-compose logs api

# Common issues:
# 1. Missing SECRET_KEY → Set in .env
# 2. Database connection failed → Check DATABASE_URL
# 3. Asterisk ARI unreachable → Check ARI_HTTP_URL
```

### Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker exec -it contactcenter_postgres psql -U contact_center -d contact_center_db
```

### Asterisk ARI connection issues

```bash
# Test ARI endpoint from API container
docker exec -it contactcenter_api curl http://asterisk-server:8088/ari/asterisk/info \
  -u username:password

# Check Asterisk ARI is enabled
# In Asterisk: /etc/asterisk/ari.conf
```

## Rollback Procedure

```bash
# Stop current version
docker-compose down

# Restore database backup (if needed)
gunzip < backup_YYYYMMDD_HHMMSS.sql.gz | docker exec -i contactcenter_postgres psql -U contact_center contact_center_db

# Pull previous version
docker pull ghcr.io/dny1020/api-contact-center:v1.0.0

# Update docker-compose.yml to use specific version
# image: ghcr.io/dny1020/api-contact-center:v1.0.0

# Start
docker-compose up -d
```

## Performance Tuning

### Database Connection Pool

Update `.env`:
```env
# SQLAlchemy pool settings (adjust based on load)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

### Uvicorn Workers

For production, run with multiple workers:

Update `Dockerfile` CMD:
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Or via docker-compose:
```yaml
api:
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Updating to New Version

```bash
# Pull latest code
git pull origin main

# Or pull new Docker image
docker pull ghcr.io/dny1020/api-contact-center:latest

# Backup database
/opt/backups/backup-api-db.sh

# Stop services
docker-compose down

# Run migrations
docker-compose run --rm api alembic upgrade head

# Start services
docker-compose up -d

# Verify health
curl https://api.yourdomain.com/health
```

## Support & Resources

- **Documentation:** [README.md](README.md)
- **GitHub Issues:** [Report bugs](https://github.com/dny1020/api-contact-center/issues)
- **API Docs:** `https://api.yourdomain.com/docs` (if enabled)

---

**Remember:** Always test changes in a staging environment before deploying to production!
