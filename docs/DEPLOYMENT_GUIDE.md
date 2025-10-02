# VPS Deployment Guide

This guide provides step-by-step instructions for deploying the Contact Center API to a VPS (Virtual Private Server).

## 📋 Prerequisites

### VPS Requirements

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| **RAM** | 2 GB | 4 GB | More RAM for high call volume |
| **CPU** | 2 cores | 4 cores | Needed for concurrent calls |
| **Storage** | 20 GB | 50 GB | SSD preferred for database |
| **Network** | 100 Mbps | 1 Gbps | Important for call quality |
| **OS** | Ubuntu 20.04+ | Ubuntu 22.04 LTS | Debian/CentOS also supported |

### Required Software

- Docker Engine 24.0+
- Docker Compose 2.0+
- Git
- Domain name with DNS access
- SSL certificate (automatic via Let's Encrypt)

### External Services Needed

- **Asterisk Server** (for call processing)
- **SIP Trunk Provider** (for outbound calling)
- Optional: Backup solution, monitoring alerts

---

## 🚀 Deployment Steps

### Step 1: Prepare Your VPS

#### 1.1 Connect to Your VPS

```bash
ssh root@your-vps-ip
```

#### 1.2 Update System

```bash
apt update && apt upgrade -y
apt install -y curl git vim ufw
```

#### 1.3 Configure Firewall

```bash
# Allow SSH
ufw allow 22/tcp

# Allow HTTP/HTTPS (for Traefik)
ufw allow 80/tcp
ufw allow 443/tcp

# Optional: Allow Asterisk SIP (if deployed on same VPS)
# ufw allow 5060/udp
# ufw allow 10000:20000/udp  # RTP ports

# Enable firewall
ufw --force enable
ufw status
```

#### 1.4 Create Non-Root User (Recommended)

```bash
adduser deploy
usermod -aG sudo deploy
usermod -aG docker deploy

# Copy SSH keys
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy

# Switch to deploy user
su - deploy
```

---

### Step 2: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Log out and back in for group changes to take effect
exit
ssh deploy@your-vps-ip
```

---

### Step 3: Clone and Configure Application

#### 3.1 Clone Repository

```bash
cd /home/deploy
git clone https://github.com/dny1020/api-contact-center.git
cd api-contact-center
```

#### 3.2 Create Environment File

```bash
cp .env.example .env
vim .env
```

**Critical Settings to Change:**

```bash
# Generate strong secrets
openssl rand -hex 32  # For SECRET_KEY
openssl rand -hex 24  # For POSTGRES_PASSWORD
openssl rand -hex 16  # For ARI_PASSWORD

# Update .env file
APP_NAME="Contact Center API"
DEBUG=false
LOG_LEVEL=INFO

# CRITICAL: Change these!
SECRET_KEY=<generated-secret-key>
API_HOST=api.yourdomain.com
ACME_EMAIL=admin@yourdomain.com

# Database
POSTGRES_DB=contact_center_db
POSTGRES_USER=contact_center
POSTGRES_PASSWORD=<generated-db-password>
DATABASE_URL=postgresql://contact_center:<generated-db-password>@postgres:5432/contact_center_db

# Asterisk ARI (adjust to your Asterisk server)
ARI_HTTP_URL=http://asterisk.yourdomain.com:8088/ari
ARI_USERNAME=ariuser
ARI_PASSWORD=<generated-ari-password>
ARI_APP=contactcenter

# JWT
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Security
DOCS_ENABLED=false  # Disable in production
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Grafana
GF_SECURITY_ADMIN_PASSWORD=<generated-grafana-password>

# Workers (adjust based on CPU cores)
WORKERS=4
```

#### 3.3 Configure DNS

Point your domain to your VPS IP:

```bash
# A Records needed:
api.yourdomain.com    → YOUR_VPS_IP
# Optional for Grafana:
# grafana.yourdomain.com → YOUR_VPS_IP
```

Verify DNS propagation:
```bash
dig api.yourdomain.com +short
# Should show your VPS IP
```

---

### Step 4: Prepare Directories and Permissions

```bash
# Create required directories
mkdir -p logs uploads audio traefik/letsencrypt

# Set permissions
chmod 700 traefik/letsencrypt
chmod 755 logs uploads audio

# Verify structure
ls -la
```

---

### Step 5: Run Database Migrations

```bash
# First, start only the database
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 10

# Run migrations
docker-compose run --rm api alembic upgrade head

# Verify migrations
docker-compose exec postgres psql -U contact_center -d contact_center_db -c "\dt"
```

---

### Step 6: Create First User

```bash
# Option 1: Use the create_user script
docker-compose run --rm api python -m app.auth.create_user

# Option 2: Direct database insert (if script doesn't exist)
docker-compose exec postgres psql -U contact_center -d contact_center_db

# In psql:
INSERT INTO users (username, email, hashed_password, is_active, is_superuser)
VALUES (
  'admin',
  'admin@yourdomain.com',
  '$2b$12$YOUR_BCRYPT_HASH_HERE',  -- Generate with: python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your_password'))"
  true,
  true
);
```

Generate bcrypt hash:
```bash
docker-compose run --rm api python -c "from passlib.hash import bcrypt; print(bcrypt.hash('YourSecurePassword123!'))"
```

---

### Step 7: Deploy Services

#### 7.1 Build and Start All Services

```bash
# Build the API image
docker-compose build api

# Start all services
docker-compose up -d

# Verify all containers are running
docker-compose ps
```

Expected output:
```
NAME                        STATUS          PORTS
contactcenter_api           Up (healthy)    
contactcenter_grafana       Up              
contactcenter_postgres      Up (healthy)    
contactcenter_prometheus    Up              
contactcenter_traefik       Up              0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

#### 7.2 Check Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f traefik
docker-compose logs -f postgres
```

#### 7.3 Verify SSL Certificate

```bash
# Check Traefik logs for Let's Encrypt
docker-compose logs traefik | grep -i acme

# Verify certificate file was created
ls -la traefik/letsencrypt/acme.json

# Should show file with 600 permissions
```

---

### Step 8: Configure Asterisk Connection

If Asterisk is on a separate server:

#### 8.1 Configure Asterisk ARI

On your Asterisk server, edit `/etc/asterisk/ari.conf`:

```ini
[general]
enabled = yes
pretty = yes
allowed_origins = https://api.yourdomain.com

[ariuser]
type = user
read_only = no
password = <your-ari-password>
password_format = plain
```

Edit `/etc/asterisk/http.conf`:

```ini
[general]
enabled = yes
bindaddr = 0.0.0.0
bindport = 8088
enablestatic = yes
```

Restart Asterisk:
```bash
asterisk -rx "core reload"
```

#### 8.2 Test ARI Connection

```bash
# From your VPS
curl -u ariuser:your-ari-password \
  http://asterisk.yourdomain.com:8088/ari/applications

# Should return JSON with Stasis applications
```

---

### Step 9: Test Deployment

#### 9.1 Health Check

```bash
curl https://api.yourdomain.com/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "ok",
  "asterisk": "ok",
  "services": {
    "api": "running",
    "database": "ok",
    "asterisk_ari": "ok"
  }
}
```

#### 9.2 Get Authentication Token

```bash
curl -X POST https://api.yourdomain.com/api/v2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=YourSecurePassword123!"
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 9.3 Test Call Origination

```bash
TOKEN="your-token-here"

curl -X POST https://api.yourdomain.com/api/v2/interaction/1234567890 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

#### 9.4 Check Metrics

```bash
curl https://api.yourdomain.com/metrics
```

---

### Step 10: Setup Monitoring (Optional but Recommended)

#### 10.1 Access Grafana

If you want to expose Grafana, add to `docker-compose.yml`:

```yaml
grafana:
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.grafana.rule=Host(`grafana.yourdomain.com`)"
    - "traefik.http.routers.grafana.entrypoints=websecure"
    - "traefik.http.routers.grafana.tls.certresolver=le"
    - "traefik.http.services.grafana.loadbalancer.server.port=3000"
```

Access at: `https://grafana.yourdomain.com`
- Username: `admin`
- Password: (from `GF_SECURITY_ADMIN_PASSWORD`)

#### 10.2 Configure Alerting

Edit `monitoring/prometheus.yml` to add Alertmanager if needed.

---

## 🔒 Security Hardening

### 1. Disable OpenAPI Docs in Production

```bash
# In .env
DOCS_ENABLED=false
```

### 2. Restrict CORS Origins

```bash
# In .env
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### 3. Setup Fail2Ban (Optional)

```bash
sudo apt install fail2ban

# Configure for SSH protection
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 4. Enable Automatic Security Updates

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 5. Regular Backups

```bash
# Backup script example
#!/bin/bash
BACKUP_DIR=/home/deploy/backups
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
docker-compose exec -T postgres pg_dump -U contact_center contact_center_db > $BACKUP_DIR/db_$DATE.sql

# Backup .env and configs
tar -czf $BACKUP_DIR/config_$DATE.tar.gz .env docker-compose.yml monitoring/

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete
```

Add to crontab:
```bash
crontab -e
# Add: 0 2 * * * /home/deploy/api-contact-center/backup.sh
```

---

## 🔄 Maintenance

### Update Application

```bash
cd /home/deploy/api-contact-center

# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose build api
docker-compose up -d

# Run migrations if any
docker-compose run --rm api alembic upgrade head

# Check logs
docker-compose logs -f api
```

### View Logs

```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service
docker-compose logs -f api

# Save logs to file
docker-compose logs > logs/docker-$(date +%Y%m%d).log
```

### Database Maintenance

```bash
# Backup database
docker-compose exec postgres pg_dump -U contact_center contact_center_db > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U contact_center contact_center_db

# Access psql console
docker-compose exec postgres psql -U contact_center contact_center_db

# Vacuum database (optimize)
docker-compose exec postgres psql -U contact_center -d contact_center_db -c "VACUUM ANALYZE;"
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart api

# Restart with rebuild
docker-compose up -d --build api
```

---

## 🐛 Troubleshooting

### Issue: Cannot Connect to API

**Check:**
1. DNS is properly configured: `dig api.yourdomain.com`
2. Traefik is running: `docker-compose ps traefik`
3. Firewall allows 80/443: `ufw status`
4. Check Traefik logs: `docker-compose logs traefik`

### Issue: SSL Certificate Not Working

**Solutions:**
```bash
# Check Let's Encrypt logs
docker-compose logs traefik | grep acme

# Ensure acme.json has correct permissions
chmod 600 traefik/letsencrypt/acme.json

# Restart Traefik
docker-compose restart traefik

# Force certificate renewal (if needed)
rm traefik/letsencrypt/acme.json
docker-compose restart traefik
```

### Issue: Cannot Connect to Asterisk

**Check:**
1. ARI URL is correct in .env
2. Asterisk ARI is enabled
3. Network connectivity: `docker-compose exec api curl http://asterisk:8088/ari/applications`
4. Check API logs: `docker-compose logs api | grep -i asterisk`

### Issue: Database Connection Failed

**Solutions:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Verify connection from API
docker-compose exec api python -c "from app.database import engine; print(engine.connect())"

# Restart database
docker-compose restart postgres
```

### Issue: High Memory Usage

**Solutions:**
```bash
# Check resource usage
docker stats

# Limit API container memory (add to docker-compose.yml)
api:
  deploy:
    resources:
      limits:
        memory: 1G

# Increase VPS resources if needed
```

---

## 📊 Monitoring Checklist

- [ ] API health endpoint responds
- [ ] Database is healthy
- [ ] Asterisk ARI is connected
- [ ] SSL certificate is valid
- [ ] Prometheus is collecting metrics
- [ ] Disk space is sufficient (>20% free)
- [ ] Memory usage is normal (<80%)
- [ ] No critical errors in logs
- [ ] Backups are running daily
- [ ] Security updates are applied

---

## 🎯 Production Readiness Checklist

### Before Going Live:

- [ ] Strong `SECRET_KEY` generated and set
- [ ] All default passwords changed
- [ ] `DEBUG=false` in production
- [ ] `DOCS_ENABLED=false` in production
- [ ] DNS properly configured
- [ ] SSL certificate obtained
- [ ] Firewall configured
- [ ] Database backups scheduled
- [ ] Monitoring alerts configured
- [ ] Test call successfully completed
- [ ] Asterisk properly configured
- [ ] SIP trunk provider configured
- [ ] Rate limiting tested
- [ ] Load testing completed
- [ ] Documentation reviewed
- [ ] Team trained on deployment

---

## 📞 Support

If you encounter issues:

1. Check logs: `docker-compose logs -f`
2. Review this guide's troubleshooting section
3. Check project issues on GitHub
4. Review documentation in `docs/` folder

---

## 🎉 Success!

Your Contact Center API is now deployed and ready for production use!

**Next Steps:**
1. Monitor metrics in Grafana
2. Test call flows thoroughly
3. Configure additional users
4. Set up monitoring alerts
5. Schedule regular backups
6. Plan for scaling if needed

**Important URLs:**
- API: `https://api.yourdomain.com`
- API Docs (if enabled): `https://api.yourdomain.com/docs`
- Health Check: `https://api.yourdomain.com/health`
- Metrics: `https://api.yourdomain.com/metrics`
- Grafana (if exposed): `https://grafana.yourdomain.com`
