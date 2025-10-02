# Environment Variables Configuration

This document describes all environment variables used by the Contact Center API.

## Application Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `APP_NAME` | Application name | `Contact Center API` | No |
| `APP_VERSION` | Application version | `1.0.0` | No |
| `DEBUG` | Enable debug mode | `false` | No |
| `DOCS_ENABLED` | Enable OpenAPI docs (/docs, /redoc) | `true` | No |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` | No |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `*` | No |
| `WORKERS` | Number of Uvicorn workers | `1` | No |

## Database Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://contact_center:contact123@localhost:5432/contact_center_db` | Yes (if DB enabled) |
| `DISABLE_DB` | Disable database usage (minimal mode) | `false` | No |

Example DATABASE_URL:
```
postgresql://username:password@hostname:5432/database_name
```

## Asterisk ARI Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ASTERISK_HOST` | Asterisk hostname (for reference/logs) | `localhost` | No |
| `ARI_HTTP_URL` | Base URL for Asterisk ARI | `http://localhost:8088/ari` | Yes |
| `ARI_USERNAME` | ARI username | `ariuser` | Yes |
| `ARI_PASSWORD` | ARI password | `aripass` | Yes |
| `ARI_APP` | ARI Stasis application name | `contactcenter` | Yes |
| `ARI_MAX_KEEPALIVE` | Max keepalive connections to ARI | `20` | No |
| `ARI_MAX_CONNECTIONS` | Max total connections to ARI | `50` | No |

## Call Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEFAULT_CONTEXT` | Default Asterisk dialplan context | `outbound-ivr` | No |
| `DEFAULT_EXTENSION` | Default extension | `s` | No |
| `DEFAULT_PRIORITY` | Default priority | `1` | No |
| `DEFAULT_TIMEOUT` | Default timeout in milliseconds | `30000` | No |
| `DEFAULT_CALLER_ID` | Default caller ID | `Outbound Call` | No |

## Authentication & Security

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | JWT secret key (CHANGE IN PRODUCTION!) | `your-secret-key-change-in-production` | Yes |
| `ALGORITHM` | JWT algorithm | `HS256` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration in minutes | `30` | No |
| `JWT_ISSUER` | JWT issuer claim (optional) | `None` | No |
| `JWT_AUDIENCE` | JWT audience claim (optional) | `None` | No |

**IMPORTANT:** Always use a strong, randomly generated `SECRET_KEY` in production!

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Rate Limiting

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `RATE_LIMIT_REQUESTS` | Max requests per window | `10` | No |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds | `60` | No |

**Note:** The built-in rate limiter is in-memory and not distributed. For multi-instance deployments, use Redis or Traefik rate limiting.

## Monitoring & Metrics

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `METRICS_ENABLED` | Enable Prometheus metrics endpoint | `true` | No |
| `METRICS_PORT` | Port for metrics (future use) | `8001` | No |

## File Paths

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `UPLOAD_DIR` | Upload directory path | `./uploads` | No |
| `AUDIO_DIR` | Audio files directory path | `./audio` | No |
| `LOG_FILE` | Log file path (optional) | `None` | No |

## Docker Compose Specific

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `POSTGRES_DB` | PostgreSQL database name | - | Yes |
| `POSTGRES_USER` | PostgreSQL username | - | Yes |
| `POSTGRES_PASSWORD` | PostgreSQL password | - | Yes |
| `API_HOST` | API hostname for Traefik | - | Yes |
| `ACME_EMAIL` | Email for Let's Encrypt | - | Yes |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin password | - | Yes |

## Example .env File

```bash
# Application
APP_NAME="Contact Center API"
APP_VERSION="1.0.0"
DEBUG=false
DOCS_ENABLED=false
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://yourapp.com,https://admin.yourapp.com

# Database
DATABASE_URL=postgresql://contact_center:secure_password@postgres:5432/contact_center_db
DISABLE_DB=false

# PostgreSQL (for docker-compose)
POSTGRES_DB=contact_center_db
POSTGRES_USER=contact_center
POSTGRES_PASSWORD=secure_password_here

# Asterisk ARI
ASTERISK_HOST=asterisk.example.com
ARI_HTTP_URL=http://asterisk:8088/ari
ARI_USERNAME=ariuser
ARI_PASSWORD=secure_ari_password
ARI_APP=contactcenter
ARI_MAX_KEEPALIVE=20
ARI_MAX_CONNECTIONS=50

# Call Configuration
DEFAULT_CONTEXT=outbound-ivr
DEFAULT_EXTENSION=s
DEFAULT_PRIORITY=1
DEFAULT_TIMEOUT=30000
DEFAULT_CALLER_ID="My Company"

# Security
SECRET_KEY=your_64_character_hex_secret_key_here_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_ISSUER=https://api.yourcompany.com
JWT_AUDIENCE=https://api.yourcompany.com

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60

# Monitoring
METRICS_ENABLED=true

# Traefik
API_HOST=api.yourcompany.com
ACME_EMAIL=admin@yourcompany.com

# Grafana
GF_SECURITY_ADMIN_PASSWORD=secure_grafana_password

# Workers
WORKERS=4
```

## Security Best Practices

1. **Never commit `.env` files** to version control
2. Use **strong random passwords** for all services
3. Change **all default passwords** in production
4. Use **environment-specific configurations** (dev, staging, prod)
5. Rotate **secrets regularly**
6. Use a **secrets manager** in production (AWS Secrets Manager, HashiCorp Vault, etc.)
7. Restrict **database access** to only the API container
8. Enable **HTTPS only** in production (via Traefik)
9. Review **CORS settings** and restrict to known origins
10. Monitor **failed authentication attempts**
